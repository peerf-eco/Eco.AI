"""Hybrid store: sqlite-vec for vector search + sqlite FTS5 for BM25.

One file (``*.sqlite``), three tables:

    chunks       — id + component + file + kind + name + line range + text
    vec_chunks   — id-aligned vector column (sqlite-vec vec0 virtual table)
    fts_chunks   — id-aligned FTS5 virtual table for BM25 ranking

Why all three in one sqlite file:
    Portability. Mount one ``./marketplace_index.sqlite`` into the container,
    no extra services (no Chroma server, no Qdrant). Backups = file copy.
    The whole index for our ~26 MB corpus is ~50-100 MB and reads cold in
    a few hundred ms.

Why sqlite-vec, not FAISS:
    FAISS is fast but doesn't ship with BM25. Maintaining two indexes
    (FAISS .bin + sqlite chunks) doubles the failure modes. sqlite-vec is
    a single SQLite extension (.dll/.so loaded with one line) and the
    schema lives next to the chunks table — no synchronisation drift
    possible.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import sqlite3
import struct
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Optional

import sqlite_vec

from agent.rag.chunker_base import Chunk, ChunkKind

logger = logging.getLogger(__name__)


class IndexMismatchError(RuntimeError):
    """Raised when the runtime embedding config doesn't match the index.

    The classic trigger: the index was built with model A (dim N) but the
    runtime embedder defaults to / is configured for model B (dim M). With a
    mismatch, ``lazy_open`` succeeds (warmup embed works), but the vec0 KNN
    ``MATCH`` fails cryptically *at query time* — surfacing as a meaningless
    "retrieval error". We catch it eagerly at open with an actionable message.
    """


def _vec_dim_from_schema(sql: str) -> Optional[int]:
    """Extract the vector width declared in a ``vec0`` CREATE statement."""
    m = re.search(r"float\[(\d+)\]", sql or "")
    return int(m.group(1)) if m else None


def _serialize_vec(v: list[float]) -> bytes:
    """sqlite-vec vec0 wants vectors as little-endian float32 blobs."""
    return struct.pack(f"<{len(v)}f", *v)


class RagStore:
    """Open / create a hybrid sqlite-vec + FTS5 store.

    Usage
    -----
        store = RagStore.create(Path("idx.sqlite"), embed_dim=3584)
        store.add_chunks(chunks, vectors)
        results = store.vector_search(query_vec, k=100)
        results = store.bm25_search("IEcoMath sqrt", k=100)

    The store is *content-aware* about chunk kinds via the ``kind`` column,
    so ``kind`` filters in the retrieval tool are a cheap SQL WHERE clause
    rather than a post-filter.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS chunks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        component   TEXT    NOT NULL,
        file        TEXT    NOT NULL,
        kind        TEXT    NOT NULL,
        name        TEXT,
        line_start  INTEGER NOT NULL,
        line_end    INTEGER NOT NULL,
        chunker_id  TEXT    NOT NULL,
        text        TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_chunks_component ON chunks(component);
    CREATE INDEX IF NOT EXISTS idx_chunks_kind ON chunks(kind);
    CREATE INDEX IF NOT EXISTS idx_chunks_chunker ON chunks(chunker_id);
    """

    def __init__(self, db_path: Path, embed_dim: int, expected_model: Optional[str] = None) -> None:
        self.db_path = Path(db_path)
        self.embed_dim = embed_dim
        self.expected_model = expected_model
        self._conn = self._open(self.db_path)
        self.index_dim: Optional[int] = None
        self.index_model: Optional[str] = None
        self._validate_index()

    def _validate_index(self) -> None:
        """Fail fast (with a clear message) if the runtime embedder's
        dimension doesn't match the index the vec0 table was built with.

        A fresh DB (no ``vec_chunks`` yet) is a build-in-progress — skip.
        """
        cur = self._conn.cursor()
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='vec_chunks'"
        )
        if cur.fetchone() is None:
            self.index_dim = self.embed_dim
            self.index_model = self.expected_model
            return

        row = cur.execute(
            "SELECT sql FROM sqlite_master WHERE name='vec_chunks'"
        ).fetchone()
        vec_dim = _vec_dim_from_schema(row[0]) if row else None
        meta = self.get_meta("ingest_stats") or {}
        index_dim = meta.get("embed_dim") or vec_dim
        index_model = meta.get("embed_model")

        if index_dim is not None and self.embed_dim != index_dim:
            raise IndexMismatchError(
                f"index built with dim={index_dim} (model={index_model or 'unknown'}) "
                f"but the runtime embedder produces dim={self.embed_dim} "
                f"(model={self.expected_model or 'default'}). "
                f"Rebuild the index with `scripts/build_marketplace_index.py "
                f"--rebuild` using the SAME EMBEDDINGS_MODEL as the runtime, or "
                f"set EMBEDDINGS_MODEL to match the existing index "
                f"(model={index_model})."
            )
        if vec_dim is not None and self.embed_dim != vec_dim:
            raise IndexMismatchError(
                f"vec_chunks declares float[{vec_dim}] but the runtime embedder "
                f"produces dim={self.embed_dim}. Rebuild the index with a matching "
                f"embedding model."
            )
        self.index_dim = index_dim or self.embed_dim
        self.index_model = index_model

    @classmethod
    def create(cls, db_path: Path, embed_dim: int, *, reset: bool = False) -> "RagStore":
        db_path = Path(db_path)
        if reset and db_path.exists():
            if db_path.is_dir():
                shutil.rmtree(db_path)
            else:
                db_path.unlink()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        s = cls(db_path, embed_dim)
        s._init_schema()
        return s

    @staticmethod
    def _open(path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(path)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(self.SCHEMA)
        # vec0 virtual table — embed_dim is a hard part of the schema, can't
        # change without recreating. Test for existence before creating.
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='vec_chunks'"
        )
        if cur.fetchone() is None:
            cur.execute(
                f"CREATE VIRTUAL TABLE vec_chunks USING vec0("
                f"id INTEGER PRIMARY KEY, embedding float[{self.embed_dim}])"
            )
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='fts_chunks'"
        )
        if cur.fetchone() is None:
            cur.execute(
                "CREATE VIRTUAL TABLE fts_chunks USING fts5("
                "text, content='chunks', content_rowid='id', "
                "tokenize='porter unicode61')"
            )
        # Metadata table for provenance — useful in eval reports.
        cur.execute(
            "CREATE TABLE IF NOT EXISTS meta ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._conn.commit()

    # ── Ingestion ────────────────────────────────────────────────────────
    def add_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> list[int]:
        """Insert chunks + vectors, keeping rowids aligned across all 3 tables.

        Returns
        -------
        list[int]
            The rowids assigned to each chunk (in input order).
        """
        if len(chunks) != len(vectors):
            raise ValueError(f"chunks ({len(chunks)}) != vectors ({len(vectors)})")
        cur = self._conn.cursor()
        rowids: list[int] = []
        for ch, vec in zip(chunks, vectors):
            existing = cur.execute(
                "SELECT id FROM chunks WHERE component=? AND file=? "
                "AND line_start=? AND line_end=? AND text=? LIMIT 1",
                (
                    ch.component,
                    ch.file,
                    ch.line_start,
                    ch.line_end,
                    ch.text,
                ),
            ).fetchone()
            if existing is not None:
                rowids.append(int(existing[0]))
                continue
            cur.execute(
                "INSERT INTO chunks (component, file, kind, name, line_start, "
                "line_end, chunker_id, text) VALUES (?,?,?,?,?,?,?,?)",
                (
                    ch.component, ch.file, ch.kind.value, ch.name,
                    ch.line_start, ch.line_end, ch.chunker_id, ch.text,
                ),
            )
            rowid = cur.lastrowid
            assert rowid is not None
            rowids.append(rowid)
            cur.execute(
                "INSERT INTO vec_chunks (id, embedding) VALUES (?, ?)",
                (rowid, _serialize_vec(vec)),
            )
            # FTS5 is content='chunks' so it indexes the chunks.text column —
            # we need to push the rowid + text into the shadow table.
            cur.execute(
                "INSERT INTO fts_chunks (rowid, text) VALUES (?, ?)",
                (rowid, ch.text),
            )
        self._conn.commit()
        return rowids

    def set_meta(self, key: str, value) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
        self._conn.commit()

    def get_meta(self, key: str):
        cur = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,))
        row = cur.fetchone()
        return json.loads(row[0]) if row else None

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    # ── Retrieval ────────────────────────────────────────────────────────
    def vector_search(
        self,
        query_vec: list[float],
        k: int = 100,
        kind: Optional[str] = None,
        component: Optional[str] = None,
    ) -> list[tuple[int, float]]:
        """K-NN by L2 distance. Returns (rowid, distance) — *smaller is closer*.

        The sqlite-vec vec0 virtual table doesn't support a WHERE-clause join
        directly in the KNN query for filters; we overfetch and post-filter
        instead. Overfetch factor is 3× when a filter is requested, capped
        at 500 to bound latency.
        """
        if kind or component:
            limit = min(k * 3, 500)
        else:
            limit = k
        cur = self._conn.execute(
            "SELECT id, distance FROM vec_chunks "
            "WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (_serialize_vec(query_vec), limit),
        )
        rows = cur.fetchall()
        if not (kind or component):
            return [(r[0], r[1]) for r in rows]
        # Post-filter
        ids = [r[0] for r in rows]
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        conds = ["id IN (" + placeholders + ")"]
        params: list = list(ids)
        if kind:
            conds.append("kind = ?")
            params.append(kind)
        if component:
            conds.append("component = ?")
            params.append(component)
        keep = set(
            r[0] for r in self._conn.execute(
                f"SELECT id FROM chunks WHERE {' AND '.join(conds)}", params,
            ).fetchall()
        )
        # Preserve original (nearest-first) order
        return [(rid, dist) for rid, dist in rows if rid in keep][:k]

    def bm25_search(
        self,
        query: str,
        k: int = 100,
        kind: Optional[str] = None,
        component: Optional[str] = None,
    ) -> list[tuple[int, float]]:
        """BM25 lexical search via FTS5. Returns (rowid, score) sorted by
        descending score (FTS5's ``rank`` is *negative*, smaller = better —
        we flip the sign to follow vector-search convention).
        """
        # FTS5 MATCH syntax is fragile with special chars; sanitise a bit.
        safe = _fts5_escape(query)
        if not safe.strip():
            return []
        conds = ["fts_chunks MATCH ?"]
        params: list = [safe]
        # FTS5 with content='chunks' supports filtering via JOIN; we use a CTE
        # so the FTS query stays simple and SQLite picks an efficient plan.
        sql = (
            "SELECT c.id, bm25(fts_chunks) AS score "
            "FROM fts_chunks JOIN chunks c ON c.id = fts_chunks.rowid "
            "WHERE " + " AND ".join(conds)
        )
        if kind:
            sql += " AND c.kind = ?"
            params.append(kind)
        if component:
            sql += " AND c.component = ?"
            params.append(component)
        sql += " ORDER BY score LIMIT ?"
        params.append(k)
        try:
            rows = self._conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError as e:
            logger.warning("FTS5 query failed for %r: %s", query, e)
            return []
        # bm25() returns negative — closer to 0 == better. Flip sign so a
        # higher score means more relevant (standard convention).
        return [(rowid, -score) for rowid, score in rows]

    def get_chunk(self, rowid: int) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT component, file, kind, name, line_start, line_end, "
            "chunker_id, text FROM chunks WHERE id=?", (rowid,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": rowid,
            "component": row[0], "file": row[1], "kind": row[2],
            "name": row[3], "line_start": row[4], "line_end": row[5],
            "chunker_id": row[6], "text": row[7],
        }

    def close(self) -> None:
        self._conn.close()


# Common English stopwords that show up in agent queries but carry zero
# information for retrieval. FTS5 BM25 already weights by IDF, but with a
# 1217-chunk corpus these still leak through and *anti-rank* good matches.
# Kept short — fancy NLP stopword lists overfilter (we want "vector" to stay).
_FTS5_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "for", "from",
    "has", "have", "he", "how", "i", "in", "is", "it", "its", "me", "of",
    "on", "or", "out", "should", "that", "the", "this", "to", "was", "what",
    "when", "where", "which", "who", "will", "with", "you",
})


def _fts5_escape(query: str) -> str:
    """Make a query safe for FTS5 MATCH and useful for BM25 ranking.

    Two non-obvious choices here, each addressing a real bug discovered
    on 2026-05-23:

    1. **Join tokens with ``OR``, not whitespace.** FTS5 treats whitespace
       as implicit AND. A natural-language query like "IEcoMath1 interface
       for power and sqrt" → 7 ANDed phrases → no 400-char chunk contains
       *all* 7 → zero hits. Explicit OR + BM25 ranking finds chunks with
       *any* token and orders them by term-frequency × IDF.

    2. **Filter stopwords.** Without filtering, words like "for"/"is"/"how"
       match every chunk and waste both query budget and downstream RRF
       rank slots. Short stopword list — fancy NLP lists over-filter
       (e.g. removing "vector" or "list" which ARE meaningful identifiers
       in our corpus).

    Special chars inside identifiers (``:``, ``(``, ``)``, ``*``) are
    replaced with whitespace to prevent FTS5 syntax errors; we keep
    word chars + ``._-`` so identifiers like ``Eco.Math.C89`` survive.
    """
    safe_tokens: list[str] = []
    for tok in query.split():
        clean = "".join(c if c.isalnum() or c in "._-" else " " for c in tok)
        for piece in clean.split():
            piece_l = piece.lower()
            if piece_l in _FTS5_STOPWORDS:
                continue
            safe_tokens.append(f'"{piece}"')
    if not safe_tokens:
        return ""
    return " OR ".join(safe_tokens)
