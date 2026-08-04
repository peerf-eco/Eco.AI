#!/usr/bin/env python3
"""Import source documents into the shared marketplace RAG index."""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.rag.chunker_ast import ASTChunker, RegexFallbackChunker
from agent.rag.embedder import Embedder
from agent.rag.ingest import ingest_cache
from agent.rag.store import RagStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("import_rag")

SUPPORTED_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".idl", ".inc", ".ipp", ".tpp", ".md", ".markdown", ".txt",
}


def _copy_inputs(inputs: list[Path], staging_root: Path) -> int:
    copied = 0
    for source in inputs:
        source = source.resolve()
        if source.is_file():
            candidates = [source]
        elif source.is_dir():
            candidates = [path for path in source.rglob("*") if path.is_file()]
        else:
            continue
        for path in candidates:
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            relative = path.name if source.is_file() else path.relative_to(source)
            destination = staging_root / source.stem / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            copied += 1
    return copied


def _import_sqlite_dump(path: Path, destination: Path) -> int:
    """Copy textual chunks from a compatible SQLite RAG dump into staging."""
    import sqlite3

    connection = sqlite3.connect(path)
    try:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(chunks)").fetchall()
        }
        if "text" not in columns:
            return 0
        rows = connection.execute(
            "SELECT component, file, text FROM chunks ORDER BY id",
        ).fetchall()
    finally:
        connection.close()
    count = 0
    for index, (component, file_name, text) in enumerate(rows):
        if not text:
            continue
        relative = Path(str(component or "imported")) / (
            f"{Path(str(file_name or 'chunk')).name}.{index}.txt"
        )
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(str(text), encoding="utf-8")
        count += 1
    return count


def import_inputs(
    inputs: list[Path],
    *,
    index_path: Path,
    staging_root: Path | None = None,
    rebuild: bool = False,
) -> dict:
    staging = staging_root or Path(tempfile.mkdtemp(prefix="eco-rag-import-"))
    staging.mkdir(parents=True, exist_ok=True)
    files = 0
    sqlite_rows = 0
    for item in inputs:
        if item.suffix.lower() in {".sqlite", ".sqlite3", ".db"} and item.is_file():
            sqlite_rows += _import_sqlite_dump(item, staging)
        else:
            files += _copy_inputs([item], staging)
    if not files and not sqlite_rows:
        raise RuntimeError("No supported documents were found in the import set.")

    embedder = Embedder()
    embedder.embed_one("warmup")
    store = RagStore.create(index_path, embed_dim=embedder.dim, reset=rebuild)
    try:
        try:
            chunker = ASTChunker(target_chars=400)
        except ImportError:
            chunker = RegexFallbackChunker(target_chars=400)
        stats = ingest_cache(staging, store, chunker, embedder)
        stats.update({
            "input_count": len(inputs),
            "imported_files": files,
            "imported_sqlite_chunks": sqlite_rows,
            "index_path": str(index_path),
        })
        store.set_meta("last_import", stats)
    finally:
        store.close()
        embedder.close()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "--index",
        type=Path,
        default=PROJECT_ROOT / "marketplace_index.sqlite",
    )
    parser.add_argument("--staging-root", type=Path)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    stats = import_inputs(
        args.inputs,
        index_path=args.index,
        staging_root=args.staging_root,
        rebuild=args.rebuild,
    )
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())