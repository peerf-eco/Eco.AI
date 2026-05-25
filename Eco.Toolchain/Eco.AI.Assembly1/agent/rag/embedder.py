"""OpenRouter ``/embeddings`` client (sync, batched, retrying).

Why a hand-rolled client and not langchain-openai:
    The V7 stack deliberately removed langchain_openai (see pi-port phase 1).
    Reintroducing it for embeddings would re-couple us to a Pydantic-wrapped
    SDK that drops ``delta.reasoning`` in chat completions. We can hit
    ``POST /embeddings`` with stdlib + httpx and have a 100-LOC dependency.

Why sync, not async:
    The ingest pipeline runs offline as a script — async would complicate it
    for no measurable gain (we batch 32 inputs per request anyway). The
    retriever calls ``embed_one`` from the agent's *synchronous* tool path,
    which would force a sync wrapper around async otherwise.

API contract:
    Embedder.embed(texts) -> list[list[float]]
    All vectors are the same dimension (lazily discovered on first call;
    asserted on subsequent calls — mismatch raises).
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class EmbedderError(RuntimeError):
    """Raised when the embedding endpoint refuses to cooperate."""


class Embedder:
    """OpenRouter /embeddings client.

    Parameters
    ----------
    model:
        Model id, e.g. ``"qwen/qwen3-embedding-8b"``. Default reads from
        ``EMBEDDINGS_MODEL`` env var with the same fallback.
    api_key:
        OpenRouter / OpenAI-compatible API key. Default reads from
        ``OPENAI_API_KEY`` then ``OPENROUTER_API_KEY`` env vars.
    base_url:
        API base URL. Default ``https://openrouter.ai/api/v1``.
    batch_size:
        Number of inputs per HTTP request. 32 is a safe default for
        OpenRouter — larger batches may time out on slow embedding models.
    timeout_s:
        Per-request timeout. Embedding endpoints can be slow under load.
    max_retries:
        How many times to retry on 429 / 5xx with exponential backoff.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        batch_size: int = 32,
        timeout_s: float = 60.0,
        max_retries: int = 4,
    ) -> None:
        self.model = model or os.getenv("EMBEDDINGS_MODEL", "qwen/qwen3-embedding-8b")
        self.api_key = (
            api_key
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or ""
        )
        self.base_url = (
            base_url
            or os.getenv("OPENROUTER_URL")
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.batch_size = batch_size
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._dim: Optional[int] = None
        self._client = httpx.Client(timeout=timeout_s)

    @property
    def dim(self) -> int:
        """Output dimensionality. Available after the first successful call;
        raises if accessed before any embed() call has succeeded."""
        if self._dim is None:
            raise EmbedderError(
                "Embedding dimension unknown — call embed() at least once first."
            )
        return self._dim

    def close(self) -> None:
        self._client.close()

    def embed_one(self, text: str) -> list[float]:
        """Convenience for single-vector queries (the retriever path)."""
        return self.embed([text])[0]

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of strings, batched and retrying.

        Raises
        ------
        EmbedderError
            If a batch fails ``max_retries`` times in a row, or if the
            server returns a vector with a different dimension than the
            first successful call.
        """
        if not texts:
            return []
        if not self.api_key:
            raise EmbedderError("No API key — set OPENAI_API_KEY or OPENROUTER_API_KEY.")

        all_vecs: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            vecs = self._embed_batch(batch, batch_no=i // self.batch_size + 1,
                                     total_batches=(len(texts) + self.batch_size - 1) // self.batch_size)
            all_vecs.extend(vecs)
        return all_vecs

    def _embed_batch(
        self, batch: list[str], batch_no: int, total_batches: int,
    ) -> list[list[float]]:
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # OpenRouter is happy without these but some setups require them:
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_X_TITLE", "EcoOS AI Agent"),
        }
        # Replace pathological inputs that some endpoints reject (empty string,
        # >32 KB blobs). We never have empty chunks (chunker filters them) but
        # we do clip absurdly long ones defensively.
        payload_inputs = [t[:32000] if t else " " for t in batch]
        body = {"model": self.model, "input": payload_inputs}

        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                r = self._client.post(url, headers=headers, json=body)
            except httpx.HTTPError as e:
                last_err = e
                logger.warning(
                    "[embed] batch %d/%d attempt %d: %s",
                    batch_no, total_batches, attempt, e,
                )
                self._backoff(attempt)
                continue
            if r.status_code == 200:
                data = r.json().get("data") or []
                vecs = [item["embedding"] for item in data]
                if not vecs:
                    raise EmbedderError(f"empty response: {r.text[:300]}")
                if self._dim is None:
                    self._dim = len(vecs[0])
                    logger.info(
                        "[embed] discovered dim=%d for model=%s",
                        self._dim, self.model,
                    )
                else:
                    if len(vecs[0]) != self._dim:
                        raise EmbedderError(
                            f"dim mismatch: got {len(vecs[0])}, "
                            f"expected {self._dim}"
                        )
                return vecs
            # Retryable codes
            if r.status_code in (408, 425, 429, 500, 502, 503, 504):
                last_err = EmbedderError(
                    f"HTTP {r.status_code}: {r.text[:200]}"
                )
                logger.warning(
                    "[embed] batch %d/%d attempt %d: HTTP %d, retrying",
                    batch_no, total_batches, attempt, r.status_code,
                )
                self._backoff(attempt)
                continue
            # Non-retryable — fail loud
            raise EmbedderError(
                f"non-retryable HTTP {r.status_code}: {r.text[:500]}"
            )
        raise EmbedderError(
            f"batch {batch_no}/{total_batches} failed after "
            f"{self.max_retries} retries — last: {last_err}"
        )

    @staticmethod
    def _backoff(attempt: int) -> None:
        # 1s, 2s, 4s, 8s
        time.sleep(min(2 ** (attempt - 1), 8))
