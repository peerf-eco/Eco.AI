"""Hybrid retriever: vector + BM25 → Reciprocal Rank Fusion → top-K.

RRF formula (with k=60, the production default from the playbook):

    rrf_score(d) = sum over query_branches[ 1 / (k_rrf + rank_branch(d)) ]

where rank_branch is 1-based within that branch's result list. Documents
missing from a branch contribute 0 from that branch.

RRF is the right fusion choice because BM25 scores and cosine distances
live in unrelated spaces — normalising them is fragile, ranks aren't.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agent.rag.embedder import Embedder
from agent.rag.store import RagStore


@dataclass
class RetrievalResult:
    """One ranked search hit, ready for display in tool output."""
    rowid: int
    score: float
    component: str
    file: str
    kind: str
    name: Optional[str]
    line_start: int
    line_end: int
    text: str

    def location(self) -> str:
        return f"{self.component}/{self.file}:L{self.line_start}-L{self.line_end}"


def reciprocal_rank_fusion(
    *ranked_lists: list[int],
    k: int = 60,
) -> list[tuple[int, float]]:
    """Fuse multiple ranked id-lists by RRF and return (id, score) sorted desc.

    Parameters
    ----------
    *ranked_lists:
        Each is a list of rowids in rank order (most relevant first).
    k:
        RRF damping constant. 60 is the production default — robust across
        corpora without per-corpus tuning.

    Returns
    -------
    list[(id, score)]
        Higher score = more relevant. Documents appearing in multiple
        branches accumulate score from each.
    """
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, rowid in enumerate(ranked, start=1):
            scores[rowid] = scores.get(rowid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda t: t[1], reverse=True)


class HybridRetriever:
    """BM25 + vector + RRF top-K retriever — the production search path.

    Usage
    -----
        retr = HybridRetriever(store, embedder)
        results = retr.search("how to register on the interface bus", k=5)

    Configure ``per_branch_k`` (how many candidates each of BM25/vector
    contributes to the RRF pool) and ``rrf_k`` (fusion damping). Defaults
    follow the playbook: 100 per branch, k=60.
    """

    def __init__(
        self,
        store: RagStore,
        embedder: Embedder,
        per_branch_k: int = 100,
        rrf_k: int = 60,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.per_branch_k = per_branch_k
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        k: int = 5,
        kind: Optional[str] = None,
        component: Optional[str] = None,
    ) -> list[RetrievalResult]:
        """Hybrid search returning top-``k`` ranked results.

        ``kind`` and ``component`` are passed to *both* branches so we don't
        retrieve a candidate only to discard it after fusion.
        """
        # Branch 1: vector
        query_vec = self.embedder.embed_one(query)
        vec_hits = self.store.vector_search(
            query_vec, k=self.per_branch_k, kind=kind, component=component,
        )
        # Branch 2: BM25 lexical
        bm25_hits = self.store.bm25_search(
            query, k=self.per_branch_k, kind=kind, component=component,
        )

        # RRF: extract id-only rank lists, fuse, take top-k by score.
        vec_ranked = [rid for rid, _ in vec_hits]
        bm25_ranked = [rid for rid, _ in bm25_hits]
        fused = reciprocal_rank_fusion(vec_ranked, bm25_ranked, k=self.rrf_k)
        top = fused[:k]

        # Hydrate to RetrievalResult
        out: list[RetrievalResult] = []
        for rowid, score in top:
            ch = self.store.get_chunk(rowid)
            if ch is None:
                continue
            out.append(RetrievalResult(
                rowid=rowid, score=score,
                component=ch["component"], file=ch["file"], kind=ch["kind"],
                name=ch["name"], line_start=ch["line_start"],
                line_end=ch["line_end"], text=ch["text"],
            ))
        return out

    def search_vector_only(
        self, query: str, k: int = 5, **kw,
    ) -> list[RetrievalResult]:
        """Ablation: pure vector retrieval, for A/B testing the BM25 branch."""
        vec = self.embedder.embed_one(query)
        hits = self.store.vector_search(vec, k=k, **kw)
        out: list[RetrievalResult] = []
        for rowid, dist in hits:
            ch = self.store.get_chunk(rowid)
            if ch is None:
                continue
            out.append(RetrievalResult(
                rowid=rowid, score=-dist,  # flip so higher = better
                component=ch["component"], file=ch["file"], kind=ch["kind"],
                name=ch["name"], line_start=ch["line_start"],
                line_end=ch["line_end"], text=ch["text"],
            ))
        return out

    def search_bm25_only(
        self, query: str, k: int = 5, **kw,
    ) -> list[RetrievalResult]:
        """Ablation: pure BM25 retrieval."""
        hits = self.store.bm25_search(query, k=k, **kw)
        out: list[RetrievalResult] = []
        for rowid, score in hits:
            ch = self.store.get_chunk(rowid)
            if ch is None:
                continue
            out.append(RetrievalResult(
                rowid=rowid, score=score,
                component=ch["component"], file=ch["file"], kind=ch["kind"],
                name=ch["name"], line_start=ch["line_start"],
                line_end=ch["line_end"], text=ch["text"],
            ))
        return out
