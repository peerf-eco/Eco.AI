#!/usr/bin/env python3
"""Ablation: which retrieval branch drives AST's win?

Holds the index constant (``artifacts/ast.sqlite``) and varies *only* the
retrieval strategy:

    vector_only   — pure dense KNN (just embeddings)
    bm25_only     — pure BM25 lexical search (no embeddings)
    hybrid_rrf    — both branches fused via RRF k=60 (production default)

For each, runs the 20 golden queries through and reports Recall@k / MRR
per category and aggregate. Lets us answer:

    - Does AST win because BM25 finds exact identifiers?
    - Does it win because embeddings handle semantic queries?
    - Are the branches complementary (sum > parts) or redundant?

Why this matters for the diploma:
    "BM25 + vector hybrid" is the production default in our RAG, but the
    eval didn't *prove* that the hybrid is better than either branch alone.
    This script provides that evidence on the same 20-query dataset.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from agent.rag.embedder import Embedder
from agent.rag.retrieve import HybridRetriever
from agent.rag.store import RagStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("ablate")

INDEX = PROJECT_ROOT / "experiments" / "chunking_eval" / "artifacts" / "ast.sqlite"
QUERIES = PROJECT_ROOT / "experiments" / "chunking_eval" / "golden_queries.json"
OUT_JSON = PROJECT_ROOT / "experiments" / "chunking_eval" / "ablations.json"
OUT_MD = PROJECT_ROOT / "experiments" / "chunking_eval" / "ablations.md"


def _is_hit(r, expected_comps: set[str], expected_files: list[str]) -> bool:
    if r.component not in expected_comps:
        return False
    if not expected_files:
        return True
    f = r.file.lower()
    return any(sub in f for sub in expected_files)


def _evaluate(retriever_fn, queries: list[dict]) -> dict:
    """Run all queries through one retrieval function, return metrics dict."""
    per_query: list[dict] = []
    sum_recall = {k: 0.0 for k in (1, 3, 5, 10)}
    sum_mrr = 0.0
    sum_compr5 = 0.0

    for q in queries:
        results = retriever_fn(q["query"], 10)
        exp_c = set(q["expected_components"])
        exp_f = [s.lower() for s in q.get("expected_files_substring", [])]
        ranks = [i + 1 for i, r in enumerate(results) if _is_hit(r, exp_c, exp_f)]
        first = ranks[0] if ranks else None
        comp_top5 = any(r.component in exp_c for r in results[:5])
        rec = {k: 1.0 if first and first <= k else 0.0 for k in (1, 3, 5, 10)}
        mrr = 1.0 / first if first else 0.0
        for k, v in rec.items():
            sum_recall[k] += v
        sum_mrr += mrr
        sum_compr5 += 1.0 if comp_top5 else 0.0
        per_query.append({
            "id": q["id"], "category": q["category"], "query": q["query"],
            "first_rank": first, "mrr": round(mrr, 3),
            "recall_at": rec, "comp_in_top5": comp_top5,
            "top1": (
                f"{results[0].component}/{results[0].file}" if results else "—"
            ),
        })

    n = len(queries)
    by_cat: dict[str, list] = {}
    for r in per_query:
        by_cat.setdefault(r["category"], []).append(r)
    return {
        "aggregate": {
            "queries": n,
            "recall_at_1": round(sum_recall[1] / n, 3),
            "recall_at_3": round(sum_recall[3] / n, 3),
            "recall_at_5": round(sum_recall[5] / n, 3),
            "recall_at_10": round(sum_recall[10] / n, 3),
            "mrr": round(sum_mrr / n, 3),
            "comp_recall_at_5": round(sum_compr5 / n, 3),
            "by_category": {
                cat: {
                    "queries": len(rs),
                    "recall_at_5": round(
                        sum(r["recall_at"][5] for r in rs) / len(rs), 3
                    ),
                    "mrr": round(sum(r["mrr"] for r in rs) / len(rs), 3),
                }
                for cat, rs in by_cat.items()
            },
        },
        "per_query": per_query,
    }


def _write_md(report: dict) -> None:
    """Markdown table comparing the three retrieval variants."""
    lines = [
        "# Retrieval Ablations on AST Index",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Index: `{INDEX.name}` ({report['index_chunks']} chunks)",
        f"Queries: 20 golden",
        "",
        "## Aggregate (held: chunker=ast, embed=qwen3-8b, only retrieval varies)",
        "",
        "| retrieval | R@1 | R@3 | R@5 | R@10 | MRR | CompR@5 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, e in report["variants"].items():
        a = e["aggregate"]
        lines.append(
            f"| {name} | {a['recall_at_1']:.2f} | {a['recall_at_3']:.2f} | "
            f"{a['recall_at_5']:.2f} | {a['recall_at_10']:.2f} | "
            f"{a['mrr']:.2f} | {a['comp_recall_at_5']:.2f} |"
        )
    lines += ["", "## Per-category Recall@5", ""]
    cats = sorted(next(iter(report["variants"].values()))["aggregate"]["by_category"].keys())
    lines.append("| retrieval | " + " | ".join(cats) + " |")
    lines.append("|---|" + "|".join(["---"] * len(cats)) + "|")
    for name, e in report["variants"].items():
        bc = e["aggregate"]["by_category"]
        row = [name] + [f"{bc.get(c, {}).get('recall_at_5', 0):.2f}" for c in cats]
        lines.append("| " + " | ".join(row) + " |")

    lines += ["", "## Per-query first-correct-rank (— = not in top-10)", ""]
    q_ids = [pq["id"] for pq in next(iter(report["variants"].values()))["per_query"]]
    header = "| query | " + " | ".join(report["variants"].keys()) + " |"
    lines.append(header)
    lines.append("|" + "|".join(["---"] * (1 + len(report["variants"]))) + "|")
    for qid in q_ids:
        cells: list[str] = []
        q_text = ""
        for name, e in report["variants"].items():
            pq = next(p for p in e["per_query"] if p["id"] == qid)
            q_text = pq["query"]
            cells.append(f"#{pq['first_rank']}" if pq["first_rank"] else "—")
        lines.append(
            f"| `{qid}` {q_text[:55]} | " + " | ".join(cells) + " |"
        )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not INDEX.exists():
        sys.exit(f"index not found: {INDEX}")
    queries = json.loads(QUERIES.read_text(encoding="utf-8"))["queries"]
    logger.info("loaded %d queries", len(queries))

    embedder = Embedder()
    embedder.embed_one("dim probe")
    store = RagStore(INDEX, embed_dim=embedder.dim)
    n_chunks = store.count()
    logger.info("index ready: %d chunks", n_chunks)

    retr = HybridRetriever(store, embedder)

    variants = {
        "vector_only": lambda q, k: retr.search_vector_only(q, k=k),
        "bm25_only": lambda q, k: retr.search_bm25_only(q, k=k),
        "hybrid_rrf": lambda q, k: retr.search(q, k=k),
    }

    report = {"index_chunks": n_chunks, "variants": {}}
    for name, fn in variants.items():
        logger.info("=== %s ===", name)
        e = _evaluate(fn, queries)
        a = e["aggregate"]
        logger.info(
            "[%s] R@1=%.2f R@5=%.2f MRR=%.2f CompR@5=%.2f",
            name, a["recall_at_1"], a["recall_at_5"], a["mrr"],
            a["comp_recall_at_5"],
        )
        report["variants"][name] = e

    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_md(report)
    logger.info("written: %s, %s", OUT_JSON, OUT_MD)
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
