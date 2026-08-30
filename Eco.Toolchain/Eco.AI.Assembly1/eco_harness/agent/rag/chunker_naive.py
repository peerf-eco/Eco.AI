"""Naive char-based chunkers (A and B).

These are the baselines the AST chunker has to beat.

- ``NaiveChunker`` (A): every chunk is exactly ``target_chars`` non-whitespace
  characters, hard split, no overlap. Tutorial-grade and the cheapest possible.
- ``NaiveOverlapChunker`` (B): same, but adjacent chunks share ``overlap_chars``
  non-whitespace characters at the boundary. This is what most "vector DB
  quickstart" tutorials produce.

Neither chunker understands C. They count non-whitespace characters so a chunk
of 400 non-ws chars is comparable across files regardless of indentation
style — the same convention cAST uses.
"""
from __future__ import annotations

from agent.rag.chunker_base import Chunk, ChunkKind, Chunker


def _split_by_nonws(text: str, target_chars: int, overlap_chars: int) -> list[tuple[int, int]]:
    """Walk ``text`` and yield (start, end) byte offsets such that each slice
    contains ``target_chars`` non-whitespace characters (last slice may be
    shorter). When ``overlap_chars > 0``, the next slice rewinds by that many
    non-ws chars before continuing — producing the classic overlap pattern.

    Returns
    -------
    list[(int, int)]
        Character offsets into ``text``. Indexing ``text[start:end]`` gives
        the chunk's raw content (including leading/trailing whitespace).
    """
    spans: list[tuple[int, int]] = []
    n = len(text)
    i = 0
    while i < n:
        chunk_start = i
        nonws = 0
        j = i
        while j < n and nonws < target_chars:
            if not text[j].isspace():
                nonws += 1
            j += 1
        spans.append((chunk_start, j))
        if j >= n:
            break
        if overlap_chars <= 0:
            i = j
            continue
        # rewind j by overlap_chars non-ws characters
        rewound = 0
        k = j
        while k > chunk_start and rewound < overlap_chars:
            k -= 1
            if not text[k].isspace():
                rewound += 1
        # Safety: never let the next chunk start before the current one
        i = max(k, chunk_start + 1)
    return spans


def _line_range(text: str, char_start: int, char_end: int) -> tuple[int, int]:
    """Convert character offsets to 1-based inclusive line numbers."""
    start_line = text.count("\n", 0, char_start) + 1
    # If char_end points to the start of a line, the chunk really ends on the
    # previous line — so we look one char back. Handle empty slices defensively.
    last = max(char_end - 1, char_start)
    end_line = text.count("\n", 0, last) + 1
    return start_line, end_line


class NaiveChunker(Chunker):
    """Fixed-char chunking, no overlap (Variant A in the experiment)."""

    id = "naive"

    def __init__(self, target_chars: int = 400) -> None:
        super().__init__(target_chars=target_chars, overlap_chars=0)

    def chunk(self, text: str, file_path: str) -> list[Chunk]:
        result: list[Chunk] = []
        for start, end in _split_by_nonws(text, self.target_chars, 0):
            ls, le = _line_range(text, start, end)
            result.append(Chunk(
                text=text[start:end],
                file=file_path,
                line_start=ls,
                line_end=le,
                kind=ChunkKind.UNKNOWN,
                chunker_id=self.id,
            ))
        return result


class NaiveOverlapChunker(Chunker):
    """Fixed-char chunking with 20% overlap by default (Variant B)."""

    id = "naive_overlap"

    def __init__(self, target_chars: int = 400, overlap_chars: int = 80) -> None:
        super().__init__(target_chars=target_chars, overlap_chars=overlap_chars)

    def chunk(self, text: str, file_path: str) -> list[Chunk]:
        result: list[Chunk] = []
        for start, end in _split_by_nonws(text, self.target_chars, self.overlap_chars):
            ls, le = _line_range(text, start, end)
            result.append(Chunk(
                text=text[start:end],
                file=file_path,
                line_start=ls,
                line_end=le,
                kind=ChunkKind.UNKNOWN,
                chunker_id=self.id,
            ))
        return result
