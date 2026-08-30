"""Regression tests for ``RagStore.vector_search`` against a real vec0 table.

Context (2026-08-24 production incident): the KNN query was written as
``WHERE embedding MATCH ? ORDER BY distance LIMIT ?``. That form only works
when the runtime SQLite passes the SQLITE_INDEX_CONSTRAINT_LIMIT
pseudo-constraint to the vtab's xBestIndex — true on dev hosts (SQLite 3.45)
but NOT inside the api container (python:3.11-slim-bookworm ships SQLite
3.40.1), where every ``search_marketplace`` call died at prepare time with
"A LIMIT or 'k = ?' constraint is required on vec0 knn queries." The query
now constrains the hidden ``k`` column instead, which every sqlite-vec /
SQLite combination supports (and which cannot be combined with LIMIT).

These tests open a REAL sqlite-vec vec0 table (tiny, dim=8) so the exact SQL
form is exercised end-to-end — unlike test_tool_rag.py, which mocks the
retriever. They fail if anyone reintroduces a LIMIT-only KNN form on an
old-SQLite runtime.
"""
from __future__ import annotations

import pytest

pytest.importorskip("sqlite_vec")

from eco_harness.agent.rag.chunker_base import Chunk, ChunkKind
from eco_harness.agent.rag.store import RagStore

DIM = 8


def _graded_vec(i: int) -> list[float]:
    """Deterministic vectors with pairwise-distinct L2 distances.

    All vectors lie on one axis with magnitude (i+1)/10; a unit query vector
    then ranks chunk i by |1 - (i+1)/10| — no ties, fully deterministic order.
    """
    v = [0.0] * DIM
    v[0] = (i + 1) / 10.0
    return v


@pytest.fixture
def store(tmp_path):
    """Store with 8 chunks whose nearest-first order is known exactly.

    Insert order i=0..7 → autoincrement ids 1..8. With q=[1,0,...]:
    id8 (0.2) < id7 (0.3) < id6 (0.4) < ... < id1 (0.9).
    Components: ids 1-6 Eco.Math.C89, ids 7-8 Eco.InterfaceBus1.
    Kinds: all function except id8 = macro.
    """
    s = RagStore.create(tmp_path / "idx.sqlite", embed_dim=DIM)
    chunks, vectors = [], []
    for i in range(8):
        chunks.append(Chunk(
            text=f"declaration {i}",
            component="Eco.Math.C89" if i < 6 else "Eco.InterfaceBus1",
            file=f"SharedFiles/F{i}.h",
            line_start=i * 10 + 1,
            line_end=i * 10 + 9,
            kind=ChunkKind.MACRO if i == 7 else ChunkKind.FUNCTION,
            name=f"MACRO_{i}" if i == 7 else f"fn_{i}",
            chunker_id="test",
        ))
        vectors.append(_graded_vec(i))
    s.add_chunks(chunks, vectors)
    yield s
    s.close()


def _query() -> list[float]:
    v = [0.0] * DIM
    v[0] = 1.0
    return v


def test_vector_search_returns_k_nearest_in_distance_order(store):
    hits = store.vector_search(_query(), k=3)
    assert len(hits) == 3
    distances = [d for _, d in hits]
    assert distances == sorted(distances)  # nearest-first
    # Graded vectors → exact expected ranking: id8, id7, id6.
    assert [rid for rid, _ in hits] == [8, 7, 6]


def test_vector_search_without_filter_returns_all_when_k_large(store):
    hits = store.vector_search(_query(), k=100)
    assert [rid for rid, _ in hits] == [8, 7, 6, 5, 4, 3, 2, 1]


def test_vector_search_kind_filter_overfetches_and_truncates(store):
    # Nearest chunk overall is the macro id8; a kind=function search must
    # overfetch past it and return only function rows, still nearest-first.
    hits = store.vector_search(_query(), k=2, kind="function")
    assert len(hits) == 2
    kinds_ok = all(store.get_chunk(rid)["kind"] == "function" for rid, _ in hits)
    assert kinds_ok
    assert [rid for rid, _ in hits] == [7, 6]


def test_vector_search_component_filter_excludes_nearer_foreign_rows(store):
    # Bus rows are the two NEAREST overall (ids 7, 8); filtering to
    # Eco.Math.C89 must skip them and return Math rows only.
    hits = store.vector_search(_query(), k=2, component="Eco.Math.C89")
    assert len(hits) == 2
    comps = {store.get_chunk(rid)["component"] for rid, _ in hits}
    assert comps == {"Eco.Math.C89"}
    assert [rid for rid, _ in hits] == [6, 5]
