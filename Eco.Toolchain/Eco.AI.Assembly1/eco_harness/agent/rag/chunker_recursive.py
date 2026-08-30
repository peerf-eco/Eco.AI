"""Recursive separator chunker (Variant C).

Mimics LangChain's RecursiveCharacterTextSplitter logic but without the
dependency. The idea:

    Try to split at the largest semantic boundary first. If a chunk is still
    too big, recurse with a smaller separator. Stop when chunks fit the size.

Separators are ordered from "most semantic" to "least semantic":

    ["\\n\\n", "\\n", " ", ""]

For C code, the ``\\n\\n`` separator is surprisingly effective — most
well-formatted headers put blank lines between major declarations. The
``""`` last-resort separator means "split at any character", and is the
guarantee that we always make progress.

Crucially, this chunker is **structure-aware-ish** without being a real parser:
no tree-sitter binding needed, no language-specific logic. It's the cheap
middle ground between naive and AST chunking.
"""
from __future__ import annotations

from agent.rag.chunker_base import Chunk, ChunkKind, Chunker


def _nonws_len(s: str) -> int:
    return sum(1 for c in s if not c.isspace())


def _split_by_separator(text: str, sep: str) -> list[str]:
    """Split keeping the separator attached to the *left* of each cut.

    ``"foo\\n\\nbar"`` with sep=``"\\n\\n"`` gives ``["foo\\n\\n", "bar"]``,
    not ``["foo", "bar"]``. This preserves blank-line spacing across joins.
    """
    if sep == "":
        # No separator — degrade to per-character. Caller only reaches this
        # when previous separators failed; we rely on the size limit to stop.
        return list(text)
    parts: list[str] = []
    start = 0
    sep_len = len(sep)
    while True:
        idx = text.find(sep, start)
        if idx < 0:
            parts.append(text[start:])
            return parts
        parts.append(text[start:idx + sep_len])
        start = idx + sep_len


def _recursive_split(
    text: str,
    separators: list[str],
    target_chars: int,
) -> list[str]:
    """Recursively split ``text`` until every piece is <= ``target_chars`` non-ws."""
    if _nonws_len(text) <= target_chars:
        return [text]
    # Try every separator in order; first one that produces multiple parts wins.
    for sep_idx, sep in enumerate(separators):
        parts = _split_by_separator(text, sep)
        if len(parts) <= 1:
            continue
        # Each part may still be too big — recurse with the *remaining*
        # separators (smaller granularity).
        remaining = separators[sep_idx + 1:]
        out: list[str] = []
        for p in parts:
            if _nonws_len(p) <= target_chars:
                out.append(p)
            else:
                out.extend(_recursive_split(p, remaining, target_chars))
        return out
    # Should not reach here — the "" separator always splits.
    return [text]


def _merge_small_adjacent(parts: list[str], target_chars: int) -> list[str]:
    """Greedy merge: combine adjacent small parts into chunks <= target.

    Mirrors cAST's merge step in spirit — the recursive split tends to
    over-fragment around tight separators (e.g. lots of single-line ``\\n``
    splits when no blank lines exist), and naive concatenation pulls those
    fragments back into useful units.
    """
    out: list[str] = []
    buffer = ""
    buffer_nonws = 0
    for p in parts:
        p_nonws = _nonws_len(p)
        if buffer_nonws + p_nonws <= target_chars:
            buffer += p
            buffer_nonws += p_nonws
        else:
            if buffer:
                out.append(buffer)
            buffer = p
            buffer_nonws = p_nonws
    if buffer:
        out.append(buffer)
    return out


class RecursiveChunker(Chunker):
    """Recursive separator-based chunker (Variant C).

    Uses ``["\\n\\n", "\\n", " ", ""]`` separators by default. With C code,
    this usually splits cleanly between top-level declarations (which are
    blank-line-separated) before falling back to per-line or per-char.
    """

    id = "recursive"

    DEFAULT_SEPARATORS = ["\n\n", "\n", " ", ""]

    def __init__(
        self,
        target_chars: int = 400,
        separators: list[str] | None = None,
    ) -> None:
        super().__init__(target_chars=target_chars, overlap_chars=0)
        self.separators = list(separators or self.DEFAULT_SEPARATORS)

    def chunk(self, text: str, file_path: str) -> list[Chunk]:
        parts = _recursive_split(text, self.separators, self.target_chars)
        parts = _merge_small_adjacent(parts, self.target_chars)

        # Convert string parts back to Chunks with line ranges. Since we
        # preserved order and concatenation, char offsets are recoverable
        # by walking through ``text``.
        result: list[Chunk] = []
        cursor = 0
        for p in parts:
            if not p:
                continue
            # find(p, cursor) is safe because parts are taken in document
            # order and never reordered — successive matches will only move
            # forward.
            idx = text.find(p, cursor)
            if idx < 0:
                # Degraded mode: the recursive split produced text that
                # doesn't exactly appear in the source (shouldn't happen
                # since we never modify content, only slice). Fall back to
                # using cursor as start.
                idx = cursor
            char_start = idx
            char_end = idx + len(p)
            cursor = char_end
            start_line = text.count("\n", 0, char_start) + 1
            last = max(char_end - 1, char_start)
            end_line = text.count("\n", 0, last) + 1
            result.append(Chunk(
                text=p,
                file=file_path,
                line_start=start_line,
                line_end=end_line,
                kind=ChunkKind.UNKNOWN,
                chunker_id=self.id,
            ))
        return result
