"""AST chunker (Variant D) — tree-sitter-c + cAST split-then-merge.

Algorithm
---------
1. Parse the C source with ``tree-sitter-c``.
2. Build a list of **top-level structural units** — but with a twist: when the
   "top level" is dominated by a single include-guard ``preproc_ifdef``
   (the classic ``#ifndef __FOO_H__ ... #endif`` wrapper around the entire
   file), descend inside it. Otherwise we'd produce one giant chunk per
   file, defeating the point.
3. For each unit, decide its ``ChunkKind`` and ``name`` via lightweight
   structural inspection (interface = typedef struct with function-pointer
   fields; struct = typedef struct without; macro = preproc_def; etc.).
4. **Split** any unit larger than ``target_chars`` by recursing into its
   children (cAST split phase).
5. **Merge** adjacent units that fit together under ``target_chars`` (cAST
   merge phase), preserving kind heterogeneity in a ``MIXED`` chunk.

Fallback
--------
If tree-sitter-c is unavailable (ABI mismatch, missing native binary),
``ASTChunker.__init__`` raises ``ImportError``; the evaluation harness then
skips this variant. There is also a ``RegexFallbackChunker`` in this module
that approximates AST chunking by greedy regex over typedef/struct/define/
function patterns — used as a portability safety net.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional, Tuple

from agent.rag.chunker_base import Chunk, ChunkKind, Chunker


# Top-level node types we treat as candidate "units" inside an include-guard.
# Anything else gets passed through (kind=UNKNOWN) so we never lose source.
_KIND_BY_NODE_TYPE = {
    "preproc_def": ChunkKind.MACRO,
    "preproc_function_def": ChunkKind.MACRO,
    "preproc_include": ChunkKind.INCLUDE,
    "type_definition": ChunkKind.STRUCT,           # refined later if vtbl
    "function_definition": ChunkKind.FUNCTION,
    "declaration": ChunkKind.FUNCTION,             # function decls live here
    "struct_specifier": ChunkKind.STRUCT,
    "enum_specifier": ChunkKind.ENUM,
    "comment": ChunkKind.COMMENT,
}


def _node_text(text_bytes: bytes, node) -> str:
    """Slice the original source for a tree-sitter node."""
    return text_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _nonws_len(s: str) -> int:
    return sum(1 for c in s if not c.isspace())


def _find_identifier(node) -> Optional[str]:
    """Best-effort: walk children to find the first ``identifier`` /
    ``type_identifier`` token. Used as the chunk's ``name``."""
    for ch in node.children:
        if ch.type in ("identifier", "type_identifier"):
            return ch.text.decode("utf-8", errors="replace")
        nested = _find_identifier(ch)
        if nested:
            return nested
    return None


def _classify_typedef(text_slice: str) -> ChunkKind:
    """Refine STRUCT → INTERFACE when the typedef defines a struct with
    function-pointer fields (the ACOM vtbl pattern).

    Heuristic: presence of ``(ECOCALLMETHOD *`` or ``)(.*me``  inside the
    typedef body. Both are reliable markers in the EcoOS codebase.
    """
    if "ECOCALLMETHOD" in text_slice or re.search(r"\)\s*\(\s*[A-Za-z_]+Ptr_t", text_slice):
        return ChunkKind.INTERFACE
    return ChunkKind.STRUCT


def _is_include_guard(node, text_bytes: bytes) -> bool:
    """A ``preproc_ifdef`` is an include-guard when its condition is
    ``!defined(__FOO_H__)`` / ``ifndef __FOO_H__`` AND it covers most of
    the file. We use it as a signal to descend rather than emit one chunk.

    Recognises ``.h``, ``.hpp``, ``.hh``, ``.hxx``, ``.inc``, ``.inl``
    suffixes. The earlier regex only matched ``_H_`` — Codex (2026-05-24)
    pointed out this silently disabled descent for every ``.hpp`` file
    in the corpus, leaving HPP top-level as
    ``[comment, preproc_ifdef, comment]`` and degrading parse quality.
    """
    if node.type != "preproc_ifdef":
        return False
    # The condition lives in the first identifier child after the ifdef token.
    snippet = _node_text(text_bytes, node)[:80]
    return bool(re.match(
        r"#\s*ifndef\s+__\w+_(?:H|HPP|HH|HXX|INC|INL)_+_?\s*", snippet
    ))


def _enumerate_units(root, text_bytes: bytes) -> list:
    """Return the working list of nodes the chunker will operate on.

    If the root has exactly one big ``preproc_ifdef`` child that looks like
    an include-guard, descend into it and re-enumerate. Otherwise return the
    root's direct children.
    """
    units = list(root.children)
    # Repeat descent up to 2 levels — covers ``#ifndef OUTER`` + ``#ifndef INNER``
    # which appears in a handful of EcoOS headers.
    for _ in range(2):
        # The "dominant guard" pattern: top level is [comment*, guard, comment*]
        non_trivial = [u for u in units if u.type != "comment"]
        if (len(non_trivial) == 1
                and _is_include_guard(non_trivial[0], text_bytes)):
            keep_comments = [u for u in units if u.type == "comment"]
            units = keep_comments + list(non_trivial[0].children)
            continue
        break
    return units


def _unit_to_chunk(node, text_bytes: bytes, file_path: str) -> Optional[Chunk]:
    """Build a Chunk from a single tree-sitter node, classifying its kind."""
    text = _node_text(text_bytes, node)
    if not text.strip():
        return None
    kind = _KIND_BY_NODE_TYPE.get(node.type, ChunkKind.UNKNOWN)
    if kind == ChunkKind.STRUCT and node.type == "type_definition":
        kind = _classify_typedef(text)
    name = _find_identifier(node)
    return Chunk(
        text=text,
        file=file_path,
        line_start=node.start_point[0] + 1,
        line_end=node.end_point[0] + 1,
        kind=kind,
        name=name,
        chunker_id="ast",
    )


# Strong structural kinds: when the *parent* chunk has one of these kinds,
# its child sub-chunks inherit it during ``_split_oversized``. This is the
# fix for the bug Codex (2026-05-24) reported as CRITICAL: previously, the
# vtbl-struct of a large interface was correctly classified as INTERFACE
# at the parent level, but when split into child nodes (``field_declaration``,
# etc.), each child got UNKNOWN or FUNCTION, and the parent's INTERFACE
# kind was lost. After this fix, every sub-chunk of an INTERFACE typedef
# stays tagged ``INTERFACE`` (with the same ``name``) — so ``kind=interface``
# search actually finds them. Without inheritance, ``ast.sqlite`` had only
# 3 INTERFACE rows across the entire 30-component corpus.
_INHERITABLE_KINDS = frozenset({
    ChunkKind.INTERFACE,
    ChunkKind.STRUCT,
    ChunkKind.ENUM,
    ChunkKind.MACRO,
})


def _split_oversized(chunk: Chunk, node, text_bytes: bytes, target_chars: int) -> list[Chunk]:
    """Recursive split: if ``chunk`` exceeds ``target_chars``, recurse into
    the node's children and re-emit. A single indivisible large unit (e.g.
    one 1200-char ``IsEqualUGUID`` macro) returns as-is — we don't break
    inside a declaration.

    When splitting a chunk whose ``kind`` is one of ``_INHERITABLE_KINDS``,
    every child sub-chunk inherits the parent's ``kind`` and ``name``. This
    preserves structural identity through recursive descent — a vtbl-typedef
    split into 5 field-declaration chunks still reads as 5 INTERFACE chunks
    of the same named interface, not 5 anonymous FUNCTION fragments.
    """
    if chunk.char_count <= target_chars or not node.children:
        return [chunk]

    inherit = chunk.kind in _INHERITABLE_KINDS
    out: list[Chunk] = []
    for child in node.children:
        sub = _unit_to_chunk(child, text_bytes, chunk.file)
        if sub is None:
            continue
        if inherit:
            # Propagate the parent's structural identity. The child keeps its
            # own line range and text, just gets re-tagged.
            sub.kind = chunk.kind
            sub.name = chunk.name or sub.name
        if sub.char_count > target_chars:
            out.extend(_split_oversized(sub, child, text_bytes, target_chars))
        else:
            out.append(sub)
    # If recursion produced nothing useful (e.g. only braces / punctuation),
    # fall back to the original — better one big chunk than zero.
    return out or [chunk]


# Kind priority during merges. When two adjacent chunks combine, the
# **higher-priority** kind wins — only when *both* are structural and
# *different* do we fall back to MIXED.
#
# Rationale: COMMENT and INCLUDE are "transparent" — they document or
# import code, not structure it. ``macro + comment`` should stay ``macro``,
# not become ``mixed``. Otherwise ``ErrEcoCodes.h`` (whose every #define
# has a leading /* comment */) gets 100% of chunks tagged ``mixed``, and
# the ``kind=macro`` filter never sees it. This was a real bug
# discovered on 2026-05-23 in the demo run.
_KIND_PRIORITY: dict[ChunkKind, int] = {
    ChunkKind.INTERFACE: 100,
    ChunkKind.STRUCT:    90,
    ChunkKind.FUNCTION:  80,
    ChunkKind.ENUM:      70,
    ChunkKind.MACRO:     60,
    ChunkKind.MIXED:     50,
    ChunkKind.UNKNOWN:   10,
    # Transparent — never override anything structural during merge.
    ChunkKind.INCLUDE:    1,
    ChunkKind.COMMENT:    1,
}


def _merge_kind(a: ChunkKind, b: ChunkKind) -> ChunkKind:
    """Pick the kind for a merged chunk.

    - One transparent (comment/include) + one anything → take the non-transparent.
    - Both transparent → COMMENT (rare; happens at file headers).
    - Both structural, same → that kind.
    - Both structural, different → MIXED.
    """
    pa, pb = _KIND_PRIORITY.get(a, 0), _KIND_PRIORITY.get(b, 0)
    if pa <= 1 and pb <= 1:
        return ChunkKind.COMMENT
    if pa <= 1:
        return b
    if pb <= 1:
        return a
    if a == b:
        return a
    return ChunkKind.MIXED


def _merge_adjacent(chunks: list[Chunk], target_chars: int) -> list[Chunk]:
    """Greedy merge: combine adjacent small chunks into ones <= target_chars.

    Kind resolution uses ``_merge_kind`` so transparent kinds (COMMENT,
    INCLUDE) don't poison the structural classification of the merged unit.
    """
    out: list[Chunk] = []
    for ch in chunks:
        if not out:
            out.append(ch)
            continue
        last = out[-1]
        combined = last.char_count + ch.char_count
        if combined <= target_chars:
            new_kind = _merge_kind(last.kind, ch.kind)
            # Pick the most "named" of the two — prefer the structural one's
            # name, fall back to the other. This way a macro+comment merge
            # keeps the macro's name, not the (always None) comment's name.
            last_prio = _KIND_PRIORITY.get(last.kind, 0)
            ch_prio = _KIND_PRIORITY.get(ch.kind, 0)
            if last_prio >= ch_prio:
                new_name = last.name or ch.name
            else:
                new_name = ch.name or last.name
            out[-1] = Chunk(
                text=last.text + ch.text,
                file=last.file,
                line_start=last.line_start,
                line_end=ch.line_end,
                kind=new_kind,
                name=new_name,
                chunker_id=last.chunker_id,
            )
        else:
            out.append(ch)
    return out


class ASTChunker(Chunker):
    """tree-sitter-c + cAST split-then-merge (Variant D).

    Raises
    ------
    ImportError
        If ``tree_sitter`` or ``tree_sitter_c`` is not installed / has an
        incompatible ABI. The evaluation harness catches this and falls
        back to ``RegexFallbackChunker`` so the experiment still runs.
    """

    id = "ast"

    def __init__(self, target_chars: int = 400) -> None:
        super().__init__(target_chars=target_chars, overlap_chars=0)
        # Lazy import — keep ImportError local so callers can handle it.
        try:
            import tree_sitter  # noqa: F401
            import tree_sitter_c as tsc
            from tree_sitter import Language, Parser
        except Exception as e:  # pragma: no cover — environment-specific
            raise ImportError(f"tree-sitter-c not available: {e}") from e

        self._lang = Language(tsc.language())
        self._parser = Parser(self._lang)

    def chunk(self, text: str, file_path: str) -> list[Chunk]:
        text_bytes = text.encode("utf-8")
        tree = self._parser.parse(text_bytes)
        units = _enumerate_units(tree.root_node, text_bytes)

        # Step 1: classify each unit → Chunk
        chunks: list[Chunk] = []
        for unit in units:
            ch = _unit_to_chunk(unit, text_bytes, file_path)
            if ch is None:
                continue
            # Step 2 (split): break oversized units along their children
            if ch.char_count > self.target_chars:
                chunks.extend(
                    _split_oversized(ch, unit, text_bytes, self.target_chars)
                )
            else:
                chunks.append(ch)

        # Step 3 (merge): pull adjacent small chunks together
        chunks = _merge_adjacent(chunks, self.target_chars)
        return chunks


# ── Regex fallback (used when tree-sitter unavailable) ────────────────────
# Markers strong enough to anchor C top-level declarations without a parser.
# Less precise than the AST but always works.
_RE_TOP_LEVEL = re.compile(
    r"(?ms)^(?:"
    r"(?P<comment>/\*.*?\*/)"
    r"|(?P<define>\#\s*define\s+\w+(?:\([^)]*\))?\s*(?:\\\n.*?(?<!\\)\n|.*?\n))"
    r"|(?P<include>\#\s*include\s+[<\"][^>\"]+[>\"]\s*\n)"
    r"|(?P<typedef>typedef\s+(?:struct|enum|union)?[^;{]*?\{[^}]*\}\s*\w+\s*;)"
    r"|(?P<plain_typedef>typedef\s+[^;]+;)"
    r"|(?P<function>(?:[A-Za-z_]\w*\s+){1,4}[A-Za-z_]\w*\s*\([^)]*\)\s*\{[^{}]*\})"
    r")"
)


class RegexFallbackChunker(Chunker):
    """Regex-based approximation of AST chunking — used when tree-sitter
    can't be installed. Produces structure-aware-ish chunks without any
    native dependency.
    """

    id = "regex_fallback"

    def chunk(self, text: str, file_path: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        last_end = 0
        for m in _RE_TOP_LEVEL.finditer(text):
            # Capture any "gap" between matches as UNKNOWN — better than
            # losing characters.
            if m.start() > last_end:
                gap = text[last_end:m.start()]
                if gap.strip():
                    ls = text.count("\n", 0, last_end) + 1
                    le = text.count("\n", 0, m.start() - 1) + 1
                    chunks.append(Chunk(
                        text=gap, file=file_path,
                        line_start=ls, line_end=le,
                        kind=ChunkKind.UNKNOWN, chunker_id=self.id,
                    ))
            kind_str = next(k for k, v in m.groupdict().items() if v is not None)
            kind = {
                "comment": ChunkKind.COMMENT,
                "define": ChunkKind.MACRO,
                "include": ChunkKind.INCLUDE,
                "typedef": ChunkKind.STRUCT,
                "plain_typedef": ChunkKind.STRUCT,
                "function": ChunkKind.FUNCTION,
            }[kind_str]
            ls = text.count("\n", 0, m.start()) + 1
            le = text.count("\n", 0, m.end() - 1) + 1
            chunks.append(Chunk(
                text=m.group(0), file=file_path,
                line_start=ls, line_end=le,
                kind=kind, chunker_id=self.id,
            ))
            last_end = m.end()
        # tail
        if last_end < len(text) and text[last_end:].strip():
            ls = text.count("\n", 0, last_end) + 1
            le = text.count("\n") + 1
            chunks.append(Chunk(
                text=text[last_end:], file=file_path,
                line_start=ls, line_end=le,
                kind=ChunkKind.UNKNOWN, chunker_id=self.id,
            ))
        # Same merge pass as AST chunker
        return _merge_adjacent(chunks, self.target_chars)
