"""Ingest pipeline: walk marketplace_cache/, chunk, embed, store.

Build a hybrid sqlite-vec + FTS5 index from a corpus directory in three
phases:

    1. Walk    — find every .h / .hpp file under cache_dir, group by component.
    2. Chunk   — apply the supplied Chunker to each file, attach metadata.
    3. Embed   — batch-embed all chunk texts via the supplied Embedder.
    4. Store   — single transaction into RagStore.

The whole pipeline is *synchronous*. Embedding is the slow step (HTTP); we
batch into the Embedder's batch_size and the bottleneck is the network.
For our 30-component corpus (~175 .h files, ~3-5k chunks) one run finishes
in ~5-15 minutes depending on embedding provider throughput.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Iterable, Optional

from agent.rag.chunker_base import Chunk, Chunker
from agent.rag.embedder import Embedder
from agent.rag.store import RagStore

logger = logging.getLogger(__name__)


# File extensions worth chunking. .lib / .so / .dll are binary and useless
# to embedding models; .ipp/.tpp are rare in the EcoOS SDK but we include
# them for completeness.
_C_EXTS = {".h", ".hpp", ".c", ".cpp", ".inc", ".ipp", ".tpp"}


def _iter_source_files(cache_dir: Path) -> Iterable[tuple[str, Path]]:
    """Yield (component, file_path) pairs from ``cache_dir/<Component>/...``.

    The directory layout is uniform across all 30 components — each has a
    top-level dir matching its marketplace name (``Eco.Math.C89/``,
    ``Eco.Core1/``, …) and headers under ``SharedFiles/``. Build artefacts
    in ``BuildFiles/`` are skipped (binary).
    """
    for component_dir in sorted(cache_dir.iterdir()):
        if not component_dir.is_dir():
            continue
        # Skip eco-cli bookkeeping & profile dumps
        if component_dir.name.startswith((".", "_")):
            continue
        component = component_dir.name
        for path in component_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in _C_EXTS:
                continue
            # Skip the (already-binary) build outputs and zip artefacts
            if "BuildFiles" in path.parts:
                continue
            yield component, path


def _read_text(path: Path) -> Optional[str]:
    """Read with a few common encodings; return None on irrecoverable failure.

    EcoOS headers tend to be UTF-8 with BOM (the ``Cyrillic (UTF-8 with
    signature)`` comment marker is right there in the file header), but
    a handful of legacy files are CP1251. ``utf-8-sig`` handles both
    UTF-8 with and without BOM.
    """
    for enc in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return None


def ingest_cache(
    cache_dir: Path,
    store: RagStore,
    chunker: Chunker,
    embedder: Embedder,
    *,
    component_filter: Optional[set[str]] = None,
    file_filter: Optional[set[str]] = None,
    progress_every: int = 50,
) -> dict:
    """Run the full ingest into ``store``. Returns a stats dict.

    Stats include: components, files, chunks, dim, elapsed_s — useful for
    the eval report.
    """
    t0 = time.time()

    # ── Phase 1+2: walk + chunk (in-memory accumulation) ─────────────────
    all_chunks: list[Chunk] = []
    files_seen = 0
    components_seen: set[str] = set()
    skipped: list[tuple[Path, str]] = []  # (path, reason)

    for component, path in _iter_source_files(cache_dir):
        if component_filter and component not in component_filter:
            continue
        if file_filter and path.name not in file_filter:
            continue
        text = _read_text(path)
        if text is None:
            skipped.append((path, "decode_failed"))
            continue
        try:
            rel_file = str(path.relative_to(cache_dir / component)).replace("\\", "/")
            chunks = chunker.chunk(text, rel_file)
        except Exception as e:
            skipped.append((path, f"chunker_failed: {e}"))
            logger.exception("chunker failed on %s", path)
            continue
        for ch in chunks:
            ch.component = component
            # chunker may have set ch.file to ``rel_file`` already; ensure it.
            if not ch.file:
                ch.file = rel_file
            all_chunks.append(ch)
        files_seen += 1
        components_seen.add(component)
        if files_seen % progress_every == 0:
            logger.info(
                "[ingest] %d files, %d chunks so far (%.1fs)",
                files_seen, len(all_chunks), time.time() - t0,
            )

    chunk_time = time.time() - t0

    if not all_chunks:
        raise RuntimeError(
            f"no chunks produced — check cache_dir={cache_dir} and filters"
        )

    # ── Phase 3: embed ────────────────────────────────────────────────────
    t_embed = time.time()
    texts = [c.text for c in all_chunks]
    vectors = embedder.embed(texts)
    embed_time = time.time() - t_embed

    # ── Phase 4: store ────────────────────────────────────────────────────
    t_store = time.time()
    rowids = store.add_chunks(all_chunks, vectors)
    store_time = time.time() - t_store

    elapsed = time.time() - t0
    stats = {
        "cache_dir": str(cache_dir),
        "chunker": chunker.id,
        "chunker_repr": repr(chunker),
        "embed_model": embedder.model,
        "embed_dim": embedder.dim,
        "components": sorted(components_seen),
        "components_count": len(components_seen),
        "files": files_seen,
        "chunks": len(all_chunks),
        "skipped": [{"path": str(p), "reason": r} for p, r in skipped],
        "chunk_time_s": round(chunk_time, 2),
        "embed_time_s": round(embed_time, 2),
        "store_time_s": round(store_time, 2),
        "elapsed_s": round(elapsed, 2),
    }
    store.set_meta("ingest_stats", stats)
    logger.info(
        "[ingest] DONE: %d chunks from %d files in %d components, %.1fs (chunk=%.1f embed=%.1f store=%.1f)",
        stats["chunks"], stats["files"], stats["components_count"],
        elapsed, chunk_time, embed_time, store_time,
    )
    return stats
