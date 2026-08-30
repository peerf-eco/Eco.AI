"""Chunker abstract base + chunk dataclass.

All four chunkers (naive / naive+overlap / recursive / AST) implement the same
single method:

    chunk(text: str, file_path: str) -> list[Chunk]

so the ingest pipeline and the evaluation harness can swap them freely.

A ``Chunk`` is plain text + structural metadata (component, file, lines, kind,
name). ``kind`` and ``name`` are optional — only the AST chunker fills them
reliably; naive chunkers leave them as ``ChunkKind.UNKNOWN`` / ``None``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ChunkKind(str, Enum):
    """What kind of C declaration this chunk represents.

    Strings are stable identifiers used in the search tool's ``kind`` filter
    — do not rename without coordinating with the active RAG tool adapter.
    """
    INTERFACE = "interface"   # typedef struct ... + vtbl or ACOM interface
    STRUCT = "struct"         # plain typedef struct
    FUNCTION = "function"     # free-standing function declaration/definition
    MACRO = "macro"           # #define
    ENUM = "enum"             # typedef enum
    INCLUDE = "include"       # #include block
    COMMENT = "comment"       # standalone block comment (file header etc.)
    MIXED = "mixed"           # multiple kinds merged by the chunker
    UNKNOWN = "unknown"       # naive chunker has no clue


@dataclass
class Chunk:
    """A piece of source text with location and structural metadata.

    Attributes
    ----------
    text:
        Raw chunk content. Embedded as-is (chunker decides what to include in
        each chunk's text — e.g. AST chunker may prepend a one-line breadcrumb
        ``"// <component>::<file>::<kind> <name>"`` for context).
    component:
        Marketplace component name, e.g. ``"Eco.Core1"``. Set by the ingest
        loop based on the file's path — chunkers don't need to fill it.
    file:
        File path relative to the component root, e.g.
        ``"SharedFiles/IEcoBase1.h"``. Same — ingest fills, chunker doesn't.
    line_start, line_end:
        1-based inclusive line range in the original file. Used for both
        display (``"L42-L88"``) and click-through during evaluation.
    kind:
        Best-effort classification. AST chunker uses the parser; naive
        chunkers leave UNKNOWN. Used by the search tool's ``kind`` filter.
    name:
        Best-effort canonical identifier (interface name, struct tag, macro
        name). Same as ``kind`` — only AST fills reliably.
    chunker_id:
        Identifier of the chunker that produced this chunk
        (``"naive"`` / ``"naive_overlap"`` / ``"recursive"`` / ``"ast"``).
        Stored so the evaluation harness can verify which run a row came
        from when sharing one DB across experiments (we don't share — but
        the field is cheap to carry).
    """
    text: str
    component: str = ""
    file: str = ""
    line_start: int = 0
    line_end: int = 0
    kind: ChunkKind = ChunkKind.UNKNOWN
    name: Optional[str] = None
    chunker_id: str = ""

    def location(self) -> str:
        """Human-friendly location label like ``"Eco.Core1/IEcoBase1.h:L42-L88"``."""
        if self.line_start and self.line_end:
            return f"{self.component}/{self.file}:L{self.line_start}-L{self.line_end}"
        return f"{self.component}/{self.file}"

    @property
    def char_count(self) -> int:
        """Non-whitespace character count — the metric cAST recommends for sizing."""
        return sum(1 for c in self.text if not c.isspace())


class Chunker(ABC):
    """Abstract base for all chunkers.

    Concrete chunkers receive a ``target_chars`` (non-whitespace) and produce
    chunks that *aim* for that size — they may exceed it when a single
    indivisible unit (a long macro, a multi-line struct) is larger.
    """

    #: Stable identifier used in chunker_id of produced chunks AND in the
    #: experiment harness as a column name. Subclasses MUST override.
    id: str = "abstract"

    def __init__(self, target_chars: int = 400, overlap_chars: int = 0) -> None:
        """
        Parameters
        ----------
        target_chars:
            Soft target for chunk size in **non-whitespace** characters.
            ~400 non-ws ≈ ~250-300 tokens for C — comfortable for embedding
            and within the sweet-spot from RAG benchmarks 2025-26.
        overlap_chars:
            How many non-ws characters to repeat between adjacent chunks.
            Only meaningful for naive-overlap / recursive variants;
            AST chunker uses a different overlap semantics (1 sibling).
        """
        self.target_chars = target_chars
        self.overlap_chars = overlap_chars

    @abstractmethod
    def chunk(self, text: str, file_path: str) -> list[Chunk]:
        """Split ``text`` into a list of chunks.

        Parameters
        ----------
        text:
            Full file contents (UTF-8 decoded).
        file_path:
            Source file path — used by the AST chunker to pick the parser
            and by all chunkers for tagging Chunk.file. The ingest loop will
            replace it with a project-relative path before storage.

        Returns
        -------
        list[Chunk]
            In document order. Every chunk has ``chunker_id == self.id`` and
            non-empty ``text``. ``component`` / ``file`` may be left blank —
            the ingest loop fills them.
        """

    def __repr__(self) -> str:  # pragma: no cover — debug aid
        return f"{type(self).__name__}(target={self.target_chars}, overlap={self.overlap_chars})"
