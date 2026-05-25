"""``search_marketplace`` — EcoTool for the RAG over marketplace_cache.

What this tool gives the agent
------------------------------
A semantic + structural search across all 30 EcoOS marketplace components
(~1200 chunks of C headers). The agent gives a natural-language query,
optionally filtered by ``kind`` (interface / struct / function / macro /
enum / mixed / unknown) and / or ``component`` name. We return the top-K
matches as markdown — each result shows ``component / file : line range``,
the kind / name metadata, and a snippet of the actual C source.

Why vector-only (and not hybrid BM25+RRF)
-----------------------------------------
On the 20-query golden eval and a held-out check, hybrid retrieval (BM25
fused with vector via Reciprocal Rank Fusion) **degrades** Recall@5 vs.
pure vector. The lexical branch finds different chunks for natural-language
queries, and RRF then downvotes the correct vector-#1 in favour of BM25's
noisy candidates. See ``memory/project_rag_retrieval_choice.md`` for the
full numbers + the bugs we found getting there.

Lazy loading
------------
``Embedder`` (httpx client + OpenRouter calls) and ``RagStore``
(sqlite-vec extension load + DB open) are NOT created at module import.
They wake up the first time the tool runs and cache themselves in a
closure inside ``make_search_marketplace_tool``. This keeps agent
startup cheap and lets you ``import`` the tool even in environments
where OpenRouter / the index file are unreachable.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from agent.v6.eco_agent import EcoTool, ToolResult

logger = logging.getLogger(__name__)


# Default index location — can be overridden by env or factory arg. The
# value matches the production volume in docker-compose.yml. On a dev host
# it falls back to the experiment artefact so manual runs Just Work.
_DEFAULT_INDEX = Path(os.environ.get(
    "MARKETPLACE_INDEX_PATH",
    "/app/marketplace_index.sqlite",
))


class _SearchArgs(BaseModel):
    """Arguments for ``search_marketplace``.

    The descriptions here are what the LLM sees in its tool schema — pick
    wording the model can use without further prompting.
    """
    query: str = Field(
        ...,
        description=(
            "Natural-language description of what you need. Examples: "
            "'mathematical functions like pow and sqrt', "
            "'how to register a component on the interface bus', "
            "'meaning of error code 0xFFEB', "
            "'IEcoComponentFactory vtable layout'. Both semantic queries "
            "and exact identifiers work — the embedding model handles both."
        ),
    )
    k: int = Field(
        5,
        ge=1, le=20,
        description=(
            "Number of results to return (1-20). Default 5. Bump to 10-15 "
            "when you suspect the right answer is across multiple files; "
            "leave at 5 for sharp lookups."
        ),
    )
    kind: Literal[
        "any", "interface", "struct", "function", "macro", "enum", "mixed",
    ] = Field(
        "any",
        description=(
            "Optional filter by declaration kind. "
            "'interface' = ACOM interface vtables (typedef struct + function pointers). "
            "'struct' = plain data structs. "
            "'macro' = #define (error codes, CIDs, calling-convention macros). "
            "'function' = free-standing function declarations. "
            "'enum' = typedef enum. "
            "'mixed' = AST-merged adjacent declarations (catch-all). "
            "'any' (default) = no filter."
        ),
    )
    component: Optional[str] = Field(
        None,
        description=(
            "Optional filter: restrict to a single component name "
            "(e.g. 'Eco.Math.C89'). Use when you already know which "
            "component to look inside; leave null to search across all 30."
        ),
    )


def _format_result_markdown(query: str, results: list) -> str:
    """Render top-k results as a compact markdown block the LLM can parse."""
    if not results:
        return f"=== search_marketplace: 0 results for {query!r} ===\n\n" \
               "(no matches; widen the query or remove filters)"
    lines = [
        f"=== search_marketplace: {len(results)} results for {query!r} ===",
        "",
    ]
    for i, r in enumerate(results, 1):
        snippet = (r.text or "").strip()
        if len(snippet) > 400:
            snippet = snippet[:400] + "\n...(truncated)"
        lines.append(f"[{i}] {r.component}/{r.file}:L{r.line_start}-L{r.line_end}")
        lines.append(
            f"    kind={r.kind} name={r.name or '-'} score={r.score:.4f}"
        )
        lines.append("    ```c")
        for snip_line in snippet.splitlines():
            lines.append(f"    {snip_line}")
        lines.append("    ```")
        lines.append("")
    return "\n".join(lines)


def make_search_marketplace_tool(
    *,
    index_path: Optional[Path] = None,
    embed_model: Optional[str] = None,
) -> EcoTool:
    """Build the ``search_marketplace`` EcoTool wired to a real index.

    Parameters
    ----------
    index_path:
        Path to ``marketplace_index.sqlite``. If None, reads from
        ``MARKETPLACE_INDEX_PATH`` env var, falling back to a sane container
        default. The file must exist by the time the tool is *invoked*;
        not by the time the factory runs.
    embed_model:
        Override for the embedding model id (default reads from
        ``EMBEDDINGS_MODEL`` env, falling back to qwen3-embedding-8b).

    Returns
    -------
    EcoTool
        Wired and ready. The first call lazy-initialises the underlying
        store + embedder; subsequent calls reuse the same instances.
    """
    resolved_index = Path(index_path) if index_path else _DEFAULT_INDEX

    # Closure state — set on first successful call.
    state: dict = {"store": None, "embedder": None, "retriever": None}

    def _lazy_open():
        """Build the (Embedder, RagStore, HybridRetriever) trio once."""
        if state["retriever"] is not None:
            return state["retriever"]

        if not resolved_index.exists():
            raise FileNotFoundError(
                f"marketplace index not found at {resolved_index}. "
                f"Build it first via scripts/build_marketplace_index.py."
            )

        # Local import so the tool module is importable even when the rag
        # subpackage's optional deps (sqlite-vec, etc.) aren't installed
        # yet — the factory still returns; failure surfaces at first call.
        from agent.rag.embedder import Embedder
        from agent.rag.retrieve import HybridRetriever
        from agent.rag.store import RagStore

        embedder = Embedder(model=embed_model) if embed_model else Embedder()
        # Probe dimension once so the store schema check passes.
        embedder.embed_one("warmup")
        store = RagStore(resolved_index, embed_dim=embedder.dim)
        retriever = HybridRetriever(store, embedder)

        state["embedder"] = embedder
        state["store"] = store
        state["retriever"] = retriever
        logger.info(
            "[search_marketplace] lazy-initialised: model=%s dim=%d index=%s",
            embedder.model, embedder.dim, resolved_index,
        )
        return retriever

    def _execute(args: _SearchArgs) -> ToolResult:
        try:
            retriever = _lazy_open()
        except FileNotFoundError as e:
            return ToolResult(
                content=f"search_marketplace: {e}", is_error=True,
            )
        except Exception as e:  # pragma: no cover — surfaces on first real call
            logger.exception("search_marketplace init failed")
            return ToolResult(
                content=f"search_marketplace: init failed: {e}",
                is_error=True,
            )

        kind = None if args.kind == "any" else args.kind
        try:
            # vector_only is the empirical winner — see module docstring +
            # project_rag_retrieval_choice.md memory.
            results = retriever.search_vector_only(
                args.query, k=args.k, kind=kind, component=args.component,
            )
        except Exception as e:  # pragma: no cover
            logger.exception("search_marketplace retrieval failed")
            return ToolResult(
                content=f"search_marketplace: retrieval error: {e}",
                is_error=True,
            )

        markdown = _format_result_markdown(args.query, results)
        details = {
            "query": args.query,
            "k": args.k,
            "kind_filter": kind,
            "component_filter": args.component,
            "result_count": len(results),
            "results": [
                {
                    "rank": i + 1,
                    "rowid": r.rowid,
                    "component": r.component,
                    "file": r.file,
                    "kind": r.kind,
                    "name": r.name,
                    "lines": f"L{r.line_start}-L{r.line_end}",
                    "score": round(r.score, 4),
                    "snippet_chars": len(r.text or ""),
                }
                for i, r in enumerate(results)
            ],
        }
        return ToolResult(content=markdown, details=details, is_error=False)

    return EcoTool(
        name="search_marketplace",
        description=(
            "Semantic search over the EcoOS marketplace corpus (30 components, "
            "all .h headers from latest DEVKITs). Use this BEFORE eco_cli to "
            "discover which component(s) implement what you need — by capability "
            "('component for pow and sqrt'), by exact identifier "
            "('IEcoComponentFactory vtable'), or by error code ('ERR_ECO_NOBUS'). "
            "Optional 'kind' filter narrows to interface / struct / macro / etc. "
            "Returns top-K matches with component, file, line range, kind, name, "
            "and a C-code snippet. After you decide which components to use, "
            "you still pull them via eco_cli — search_marketplace tells you "
            "WHICH, eco_cli FETCHES them."
        ),
        args_schema=_SearchArgs,
        execute=_execute,
    )
