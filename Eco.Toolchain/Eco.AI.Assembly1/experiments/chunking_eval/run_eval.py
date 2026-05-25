#!/usr/bin/env python3
"""Compare 4 chunking strategies on the marketplace_cache corpus.

For each chunker variant (naive / naive_overlap / recursive / ast):
    1. Build a separate sqlite-vec index ``artifacts/<chunker_id>.sqlite``
       (idempotent — reuses if present and meta matches the chunker repr).
    2. Run all 20 golden queries through the HybridRetriever.
    3. Compute Recall@k (k=1,3,5,10) and MRR per query and aggregated.

Output:
    - ``artifacts/<chunker_id>.sqlite`` — full index per variant (~50 MB each)
    - ``artifacts/<chunker_id>_results.json`` — per-query hits + metrics
    - ``report.md``                          — comparative markdown table

Usage:
    python experiments/chunking_eval/run_eval.py            # all 4 chunkers
    python experiments/chunking_eval/run_eval.py --only ast # one variant
    python experiments/chunking_eval/run_eval.py --rebuild  # force re-ingest

Environment:
    Reads .env via python-dotenv if available. Required keys:
        OPENAI_API_KEY (or OPENROUTER_API_KEY)
        EMBEDDINGS_MODEL  — default: qwen/qwen3-embedding-8b
        OPENROUTER_URL    — default: https://openrouter.ai/api/v1
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Make ``agent.rag.*`` importable when running this script directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from agent.rag.chunker_ast import ASTChunker, RegexFallbackChunker
from agent.rag.chunker_naive import NaiveChunker, NaiveOverlapChunker
from agent.rag.chunker_recursive import RecursiveChunker
from agent.rag.embedder import Embedder
from agent.rag.ingest import ingest_cache
from agent.rag.retrieve import HybridRetriever
from agent.rag.store import RagStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("eval")

CACHE_DIR = PROJECT_ROOT / "marketplace_cache"
EXP_DIR = PROJECT_ROOT / "experiments" / "chunking_eval"
ARTIFACTS = EXP_DIR / "artifacts"
QUERIES_FILE = EXP_DIR / "golden_queries.json"


def _build_chunkers() -> list:
    """All 4 variants. AST falls back to regex if tree-sitter unavailable."""
    chunkers = [
        NaiveChunker(target_chars=400),
        NaiveOverlapChunker(target_chars=400, overlap_chars=80),
        RecursiveChunker(target_chars=400),
    ]
    try:
        chunkers.append(ASTChunker(target_chars=400))
    except ImportError as e:
        logger.warning("AST chunker unavailable (%s) — using regex fallback", e)
        fallback = RegexFallbackChunker(target_chars=400)
        fallback.id = "ast_fallback_regex"
        chunkers.append(fallback)
    return chunkers


def _index_path(chunker_id: str) -> Path:
    return ARTIFACTS / f"{chunker_id}.sqlite"


def _ingest_one(chunker, embedder, *, rebuild: bool) -> dict:
    """Build (or reuse) the index for one chunker. Returns ingest stats."""
    db_path = _index_path(chunker.id)
    if db_path.exists() and not rebuild:
        # Sanity-check stats from a previous run. The Embedder may not yet
        # know its dimension on the reuse path (we haven't called embed()),
        # so we open with embed_dim=1 — that only affects schema *creation*,
        # and schema already exists. Then we restore the real dim from
        # ``ingest_stats["embed_dim"]`` so the subsequent evaluate() call
        # doesn't trip over ``embedder.dim`` accessor. Codex (2026-05-24)
        # reported this as a reproducible reuse-path crash.
        store = RagStore(db_path, embed_dim=embedder._dim or 1)
        prev = store.get_meta("ingest_stats")
        store.close()
        if prev and prev.get("chunker_repr") == repr(chunker) and prev.get("chunks", 0) > 0:
            if prev.get("embed_dim") and embedder._dim is None:
                embedder._dim = int(prev["embed_dim"])
            logger.info("[%s] reusing existing index (%d chunks)", chunker.id, prev["chunks"])
            return prev
        logger.info("[%s] index exists but stale — rebuilding", chunker.id)

    # Discover dim first via a single embed call so the store schema matches.
    _ = embedder.embed_one("dimensionality probe")
    store = RagStore.create(db_path, embed_dim=embedder.dim, reset=True)
    try:
        stats = ingest_cache(CACHE_DIR, store, chunker, embedder)
    finally:
        store.close()
    return stats


def _evaluate_one(chunker, embedder, queries: list[dict]) -> dict:
    """Run all queries through HybridRetriever, return per-query + aggregate metrics."""
    db_path = _index_path(chunker.id)
    store = RagStore(db_path, embed_dim=embedder.dim)
    retr = HybridRetriever(store, embedder)

    per_query: list[dict] = []
    sum_recall = {k: 0.0 for k in (1, 3, 5, 10)}
    sum_mrr = 0.0
    sum_comp_r5 = 0.0

    for q in queries:
        results = retr.search(q["query"], k=10)
        expected_comps = set(q["expected_components"])
        expected_files = [s.lower() for s in q.get("expected_files_substring", [])]

        # A hit = result.component in expected AND any expected_file substring
        # appears in result.file (case-insensitive). Same convention as
        # documented in golden_queries.json meta.
        def _is_hit(r) -> bool:
            if r.component not in expected_comps:
                return False
            if not expected_files:
                return True
            file_l = r.file.lower()
            return any(sub in file_l for sub in expected_files)

        ranks_of_hits = [i + 1 for i, r in enumerate(results) if _is_hit(r)]
        first_rank = ranks_of_hits[0] if ranks_of_hits else None
        comp_in_top5 = any(r.component in expected_comps for r in results[:5])

        rec = {
            k: 1.0 if (first_rank is not None and first_rank <= k) else 0.0
            for k in (1, 3, 5, 10)
        }
        mrr = 1.0 / first_rank if first_rank else 0.0

        for k, v in rec.items():
            sum_recall[k] += v
        sum_mrr += mrr
        sum_comp_r5 += 1.0 if comp_in_top5 else 0.0

        per_query.append({
            "id": q["id"],
            "category": q["category"],
            "query": q["query"],
            "expected_components": q["expected_components"],
            "first_correct_rank": first_rank,
            "mrr": round(mrr, 3),
            "recall_at": rec,
            "comp_in_top5": comp_in_top5,
            "top_results": [
                {
                    "rank": i + 1,
                    "component": r.component, "file": r.file,
                    "kind": r.kind, "name": r.name, "score": round(r.score, 4),
                    "lines": f"L{r.line_start}-L{r.line_end}",
                    "is_hit": _is_hit(r),
                }
                for i, r in enumerate(results[:5])
            ],
        })

    n = len(queries)
    aggregate = {
        "queries": n,
        "recall_at_1": round(sum_recall[1] / n, 3),
        "recall_at_3": round(sum_recall[3] / n, 3),
        "recall_at_5": round(sum_recall[5] / n, 3),
        "recall_at_10": round(sum_recall[10] / n, 3),
        "mrr": round(sum_mrr / n, 3),
        "comp_recall_at_5": round(sum_comp_r5 / n, 3),
    }
    # Per-category breakdown
    by_cat: dict[str, list[dict]] = {}
    for r in per_query:
        by_cat.setdefault(r["category"], []).append(r)
    aggregate["by_category"] = {
        cat: {
            "queries": len(rs),
            "recall_at_5": round(
                sum(r["recall_at"][5] for r in rs) / len(rs), 3
            ),
            "mrr": round(sum(r["mrr"] for r in rs) / len(rs), 3),
        }
        for cat, rs in by_cat.items()
    }
    store.close()
    return {"aggregate": aggregate, "per_query": per_query}


def _write_report(report: dict, out_path: Path) -> None:
    """Markdown comparison table — main artefact of the experiment."""
    lines = [
        "# Chunking Strategy Evaluation",
        "",
        "Source: `experiments/chunking_eval/run_eval.py`",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Aggregate metrics",
        "",
        "| chunker | R@1 | R@3 | R@5 | R@10 | MRR | CompR@5 | #chunks | #files | ingest_s |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for entry in report["chunkers"]:
        a = entry["evaluation"]["aggregate"]
        s = entry["ingest_stats"]
        lines.append(
            f"| {entry['chunker_id']} | "
            f"{a['recall_at_1']:.2f} | {a['recall_at_3']:.2f} | "
            f"{a['recall_at_5']:.2f} | {a['recall_at_10']:.2f} | "
            f"{a['mrr']:.2f} | {a['comp_recall_at_5']:.2f} | "
            f"{s['chunks']} | {s['files']} | {s['elapsed_s']:.0f} |"
        )
    lines += ["", "## Per-category Recall@5", ""]
    cats = sorted({
        cat
        for entry in report["chunkers"]
        for cat in entry["evaluation"]["aggregate"]["by_category"].keys()
    })
    lines.append("| chunker | " + " | ".join(cats) + " |")
    lines.append("|---|" + "|".join(["---"] * len(cats)) + "|")
    for entry in report["chunkers"]:
        bycat = entry["evaluation"]["aggregate"]["by_category"]
        row = [entry["chunker_id"]] + [
            f"{bycat.get(c, {}).get('recall_at_5', 0):.2f}" for c in cats
        ]
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "## Per-query top-5 results", ""]
    lines.append(
        "Format: each query × each chunker → top-5 with hit marker (`✓`/`·`)."
    )
    lines.append("")
    # Per-query mini-report — only the FIRST result per chunker for brevity.
    q_ids = [q["id"] for q in report["chunkers"][0]["evaluation"]["per_query"]]
    lines.append("| query | " + " | ".join(e["chunker_id"] for e in report["chunkers"]) + " |")
    lines.append("|---" * (1 + len(report["chunkers"])) + "|")
    for q_id in q_ids:
        cells: list[str] = []
        q_text = ""
        for entry in report["chunkers"]:
            pq = next(p for p in entry["evaluation"]["per_query"] if p["id"] == q_id)
            q_text = pq["query"]
            rank = pq["first_correct_rank"]
            cells.append(
                f"#{rank}" if rank else "—"
            )
        lines.append(
            f"| `{q_id}` {q_text[:60]} | " + " | ".join(cells) + " |"
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="run only this chunker_id")
    parser.add_argument("--rebuild", action="store_true",
                        help="force re-ingest even if index exists")
    args = parser.parse_args()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    queries = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))["queries"]
    logger.info("loaded %d golden queries", len(queries))

    embedder = Embedder()
    logger.info("embedder model=%s base=%s", embedder.model, embedder.base_url)

    chunkers = _build_chunkers()
    if args.only:
        chunkers = [c for c in chunkers if c.id == args.only]
        if not chunkers:
            sys.exit(f"no chunker with id={args.only}")

    report = {"chunkers": []}
    for chunker in chunkers:
        logger.info("=== %s ===", chunker.id)
        ingest_stats = _ingest_one(chunker, embedder, rebuild=args.rebuild)
        eval_stats = _evaluate_one(chunker, embedder, queries)
        a = eval_stats["aggregate"]
        logger.info(
            "[%s] R@1=%.2f R@5=%.2f MRR=%.2f CompR@5=%.2f",
            chunker.id, a["recall_at_1"], a["recall_at_5"],
            a["mrr"], a["comp_recall_at_5"],
        )

        (ARTIFACTS / f"{chunker.id}_results.json").write_text(
            json.dumps({"ingest_stats": ingest_stats,
                        "evaluation": eval_stats},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        report["chunkers"].append({
            "chunker_id": chunker.id,
            "ingest_stats": ingest_stats,
            "evaluation": eval_stats,
        })

    report_path = EXP_DIR / "report.md"
    _write_report(report, report_path)
    logger.info("report written: %s", report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
