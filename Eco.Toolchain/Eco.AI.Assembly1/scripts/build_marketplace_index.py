#!/usr/bin/env python3
"""Build (or rebuild) ``marketplace_index.sqlite`` from ``marketplace_cache/``.

This is the production-index builder for the ``search_marketplace`` EcoTool.
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

from agent.internal.tools.paths import framework_root
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
    parser.add_argument(
        "--source", choices=("cache", "framework"), default="cache",
        help="Corpus source: 'cache' (default) indexes marketplace_cache/; "
             "'framework' indexes the standard ACOM $ECO_FRAMEWORK "
             "development-kit tree (<Component>_DK_v.<ver>/<Component>/…), "
             "so DK headers are indexed without a prior fetch. Component "
             "names are normalized (the _DK_v.<ver> suffix is stripped).",
    )
    args = parser.parse_args()

    if args.source == "framework":
        corpus_dir = framework_root(repo=PROJECT_ROOT)
        if not corpus_dir.is_dir():
            sys.exit(
                f"ECO_FRAMEWORK corpus not found at {corpus_dir}. Set "
                f"ECO_FRAMEWORK to the ACOM development-kit directory or "
                f"populate {CACHE_DIR} and use --source cache."
            )
    else:
        corpus_dir = CACHE_DIR

    if not corpus_dir.exists():
        sys.exit(
            f"corpus dir not found at {corpus_dir}. "
            f"Pull components first via scripts/fetch_marketplace.py."
        )

    corpus_files = [p for p in corpus_dir.rglob("*") if p.is_file()]
    if not corpus_files:
        sys.exit(
            f"corpus dir at {corpus_dir} is empty — nothing to index. "
            f"Pull components first via scripts/fetch_marketplace.py."
        )

    if INDEX_PATH.exists() and not INDEX_PATH.is_file():
        # Stale directory (or other non-file) where the index should live —
        # remove it so --rebuild (and RagStore.create) can proceed.
        logger.warning(
            "%s exists but is not a file; removing it before rebuild.",
            INDEX_PATH,
        )
        import shutil as _shutil
        if INDEX_PATH.is_dir():
            _shutil.rmtree(INDEX_PATH)
        else:
            INDEX_PATH.unlink()

    if INDEX_PATH.is_file() and not args.rebuild:
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
        stats = ingest_cache(corpus_dir, store, chunker, embedder)
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
