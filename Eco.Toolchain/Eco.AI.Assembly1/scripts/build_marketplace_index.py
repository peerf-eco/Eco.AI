#!/usr/bin/env python3
"""Build (or rebuild) ``marketplace_index.sqlite`` from ``marketplace_cache/``.

This is the production-index builder for the V7 ``search_marketplace`` EcoTool.
It reuses ``agent/rag/ingest.py``'s pipeline with the **production** stack:

    Chunker:   ASTChunker(target_chars=400)  — winner of the 4-way eval
    Embedder:  qwen/qwen3-embedding-8b via OpenRouter  — winner of ablations
    Store:     sqlite-vec + FTS5 (vector + BM25 in one file)
    Output:    project root / marketplace_index.sqlite

Usage::

    # First time, OR after pulling new components into marketplace_cache:
    python scripts/build_marketplace_index.py

    # Force re-embed even if the index exists:
    python scripts/build_marketplace_index.py --rebuild

Cost & time::

    ~1200 chunks @ Qwen3-Embedding-8B via OpenRouter ≈ $0.05, ~2 min.

After the index is written, the docker-compose ``api`` service mounts it
as ``/app/marketplace_index.sqlite:ro`` and the agents can immediately
call ``search_marketplace`` on it.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from agent.rag.chunker_ast import ASTChunker
from agent.rag.embedder import Embedder
from agent.rag.ingest import ingest_cache
from agent.rag.store import RagStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("build_index")

CACHE_DIR = PROJECT_ROOT / "marketplace_cache"
INDEX_PATH = PROJECT_ROOT / "marketplace_index.sqlite"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Force rebuild even if marketplace_index.sqlite exists.",
    )
    parser.add_argument(
        "--target-chars", type=int, default=400,
        help="ASTChunker chunk size (non-whitespace chars). Default 400 — "
             "the size that won the 4-way chunking eval on golden_queries.",
    )
    args = parser.parse_args()

    if not CACHE_DIR.exists():
        sys.exit(
            f"marketplace_cache not found at {CACHE_DIR}. "
            f"Pull components first via scripts/fetch_marketplace.py."
        )

    if INDEX_PATH.exists() and not args.rebuild:
        logger.info(
            "Index exists at %s. Re-run with --rebuild to wipe + re-embed.",
            INDEX_PATH,
        )
        return 0

    embedder = Embedder()
    # Probe embedding dimension once — store schema needs it.
    embedder.embed_one("warmup")
    logger.info(
        "Embedder ready: model=%s dim=%d", embedder.model, embedder.dim,
    )

    store = RagStore.create(INDEX_PATH, embed_dim=embedder.dim, reset=True)
    try:
        chunker = ASTChunker(target_chars=args.target_chars)
        stats = ingest_cache(CACHE_DIR, store, chunker, embedder)
    finally:
        store.close()

    logger.info(
        "Built %s: %d chunks across %d components in %.1fs (~$%.3f at "
        "$0.05/M tokens)",
        INDEX_PATH, stats["chunks"], stats["components_count"],
        stats["elapsed_s"],
        # rough: avg ~80 tokens / chunk, $0.05 per 1M
        stats["chunks"] * 80 / 1_000_000 * 0.05,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
