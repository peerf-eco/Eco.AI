"""Universal code-exploration tools — ``grep`` / ``glob`` / ``read``.

Why these exist
---------------
These are claude-code / codex / pi-harness-style PRIMITIVES that let the
architect (and coder) treat the whole project tree — including the
read-only ``marketplace_cache/`` snapshot of every published EcoOS
component — as one searchable workspace.

Rationale: the cache is just a directory of header files. The natural
way to find "which component implements pow / sqrt" is

    grep -rn "double.*pow" --include="*.h" marketplace_cache/

— one tool call returns the file + line, then ``read`` opens it. This is
the same flow a human developer (or Claude Code itself) uses. The
domain-specific helpers (``search_marketplace``, ``read_component_profile``)
are still available for semantic queries and quick CID lookup; they are
no longer the only path.

Sandbox model
-------------
Each tool resolves the requested path against a whitelist of "allowed
roots". A path is accepted if its real resolved location lies under one
of those roots. Defaults:

  - project_dir (the per-run output dir)
  - marketplace_cache (read-only marketplace snapshot)

The whitelist is computed once per agent (closure over make_*_tools) so
adding new roots later is a one-line change.

Limits
------
``grep`` truncates output at ``_GREP_MAX_MATCHES`` lines and
``_GREP_MAX_LINE_LEN`` bytes per match. ``read`` truncates at
``_READ_MAX_BYTES``. ``glob`` truncates at ``_GLOB_MAX_RESULTS`` paths.
This stops a single tool call from eating the context window.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, Field

from agent.internal.eco_agent import EcoTool, ToolResult

logger = logging.getLogger(__name__)


# Cap each grep run so a too-broad pattern can't dump megabytes back to
# the model. Values picked to stay well under the ~30 KB tool-result soft
# cap most providers enforce.
_GREP_MAX_MATCHES = 100
_GREP_MAX_LINE_LEN = 300
_GREP_TIMEOUT_S = 30

# read() cap — calibrated for typical EcoOS headers (50-200 KB worst case).
_READ_MAX_BYTES = 200_000
_READ_DEFAULT_BYTES = 32_768  # default page; full files only by explicit limit

# glob() cap — 30 components × ~30 files each = max ~900 files; 500 is a
# generous ceiling for any sensible pattern.
_GLOB_MAX_RESULTS = 500


def _resolve_inside_any(allowed_roots: list[Path], rel_or_abs: str) -> Optional[Path]:
    """Resolve ``rel_or_abs`` and return it only if it sits under one of
    the allowed_roots. Returns None on attempted breakout.

    Resolution rules:
      1. Absolute path  → take as-is.
      2. Relative path whose FIRST segment equals the basename of one of
         the allowed roots (e.g. ``marketplace_cache/...`` when
         ``/app/marketplace_cache`` is in the whitelist) → anchor under
         that root, stripping the basename prefix.
      3. Otherwise → anchor under the first root (by convention,
         project_dir is first).

    Rule (2) is what makes ``path="marketplace_cache"`` feel natural to
    the model without forcing it to know absolute container paths.
    """
    p = Path(rel_or_abs)
    if not p.is_absolute():
        if not allowed_roots:
            return None
        # Rule (2): basename-prefix match against any allowed root.
        first_seg = p.parts[0] if p.parts else ""
        matched_root: Optional[Path] = None
        for root in allowed_roots:
            if root.name == first_seg:
                matched_root = root
                break
        if matched_root is not None:
            remainder = Path(*p.parts[1:]) if len(p.parts) > 1 else Path()
            p = matched_root / remainder
        else:
            # Rule (3): default to first allowed root.
            p = allowed_roots[0] / p
    try:
        p = p.resolve(strict=False)
    except OSError:
        return None
    for root in allowed_roots:
        try:
            root_resolved = root.resolve(strict=False)
            p.relative_to(root_resolved)
            return p
        except ValueError:
            continue
    return None


def _outside_msg(args_path: str, allowed_roots: list[Path]) -> str:
    """Standard 'outside whitelist' error message — echoes the allowed
    roots so the model can self-correct on the next iteration."""
    roots_str = "\n  ".join(str(r.resolve()) for r in allowed_roots)
    return (
        f"Path {args_path!r} resolves outside the allowed roots.\n"
        f"Allowed roots:\n  {roots_str}\n"
        f"Pass paths relative to one of these (relative paths anchor at "
        f"the first root)."
    )


# ─────────────────────────────────────────────────────────────────────
# grep
# ─────────────────────────────────────────────────────────────────────


class _GrepArgs(BaseModel):
    """Arguments for ``grep``. Mirrors POSIX grep -rnE semantics."""
    pattern: str = Field(
        ...,
        description=(
            "Extended regex (POSIX ERE — same as grep -E). Examples: "
            "'double.*sqrt', 'IEcoComponentFactory', "
            "'CID_Eco[A-Z][a-zA-Z0-9]+'."
        ),
    )
    glob: str = Field(
        "*.h",
        description=(
            "Filename glob, matched against the basename. Examples: "
            "'*.h', '*.{h,hpp}', 'Id*.h'. Default '*.h' restricts to "
            "C/C++ header files (the common case for EcoOS exploration)."
        ),
    )
    path: str = Field(
        "marketplace_cache",
        description=(
            "Root directory for the search. Relative paths anchor at "
            "project_dir. Use 'marketplace_cache' (default) to search "
            "the full marketplace snapshot."
        ),
    )
    ignore_case: bool = Field(
        False,
        description="If true, match case-insensitively (grep -i).",
    )


def _grep(args: _GrepArgs, allowed_roots: list[Path]) -> ToolResult:
    root = _resolve_inside_any(allowed_roots, args.path)
    if root is None:
        return ToolResult(
            content=_outside_msg(args.path, allowed_roots), is_error=True,
        )
    if not root.exists():
        return ToolResult(
            content=f"grep: path {root} does not exist.", is_error=True,
        )
    if not root.is_dir():
        return ToolResult(
            content=f"grep: path {root} is not a directory.", is_error=True,
        )

    cmd = ["grep", "-rnE", f"--include={args.glob}"]
    if args.ignore_case:
        cmd.append("-i")
    cmd.extend([args.pattern, str(root)])

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=_GREP_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            content=f"grep: timed out after {_GREP_TIMEOUT_S}s. "
                    f"Narrow the pattern or restrict the path.",
            is_error=True,
        )
    except FileNotFoundError:
        return ToolResult(
            content="grep: 'grep' binary not found in PATH.",
            is_error=True,
        )

    # rc=1 means "no matches", which is a valid (non-error) outcome.
    if proc.returncode not in (0, 1):
        return ToolResult(
            content=(
                f"grep: rc={proc.returncode}\n"
                f"=== stderr ===\n{proc.stderr.strip()}"
            ),
            is_error=True,
        )

    lines = (proc.stdout or "").splitlines()
    truncated_matches = len(lines) > _GREP_MAX_MATCHES
    lines = lines[:_GREP_MAX_MATCHES]
    # Per-line truncation so one giant line can't blow the budget.
    capped: list[str] = []
    for line in lines:
        if len(line) > _GREP_MAX_LINE_LEN:
            line = line[: _GREP_MAX_LINE_LEN] + " ... (line truncated)"
        capped.append(line)

    if not capped:
        return ToolResult(
            content=f"grep: 0 matches for /{args.pattern}/ in {root} "
                    f"(glob={args.glob}).",
            details={"matches": 0, "root": str(root)},
        )

    header = (
        f"grep: {len(capped)}"
        + (f"+ (truncated; original >{_GREP_MAX_MATCHES})" if truncated_matches else "")
        + f" matches for /{args.pattern}/ in {root} (glob={args.glob}):"
    )
    body = "\n".join([header, *capped])
    return ToolResult(
        content=body,
        details={
            "matches": len(capped),
            "truncated": truncated_matches,
            "root": str(root),
            "pattern": args.pattern,
        },
    )


# ─────────────────────────────────────────────────────────────────────
# glob
# ─────────────────────────────────────────────────────────────────────


class _GlobArgs(BaseModel):
    """Arguments for ``glob``."""
    pattern: str = Field(
        ...,
        description=(
            "Glob pattern with ** for recursive matching. Examples: "
            "'**/Id*.h' (all CID headers under root), "
            "'**/SharedFiles/*.h', '**/_profiles/*.json'."
        ),
    )
    path: str = Field(
        "marketplace_cache",
        description=(
            "Root directory. Relative paths anchor at project_dir. "
            "Use 'marketplace_cache' (default) to enumerate the "
            "marketplace snapshot."
        ),
    )


def _glob(args: _GlobArgs, allowed_roots: list[Path]) -> ToolResult:
    root = _resolve_inside_any(allowed_roots, args.path)
    if root is None:
        return ToolResult(
            content=_outside_msg(args.path, allowed_roots), is_error=True,
        )
    if not root.exists():
        return ToolResult(
            content=f"glob: path {root} does not exist.", is_error=True,
        )
    if not root.is_dir():
        return ToolResult(
            content=f"glob: path {root} is not a directory.", is_error=True,
        )

    try:
        matches: list[Path] = list(root.glob(args.pattern))
    except (NotImplementedError, ValueError) as e:
        return ToolResult(
            content=f"glob: invalid pattern {args.pattern!r}: {e}",
            is_error=True,
        )

    # Sort by mtime descending so the most recently touched files come
    # first — that's almost always what you want when exploring.
    try:
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        matches.sort()

    truncated = len(matches) > _GLOB_MAX_RESULTS
    matches = matches[:_GLOB_MAX_RESULTS]

    if not matches:
        return ToolResult(
            content=f"glob: 0 matches for {args.pattern!r} under {root}.",
            details={"matches": 0, "root": str(root)},
        )

    rel_lines = []
    for m in matches:
        try:
            rel_lines.append(str(m.relative_to(root)))
        except ValueError:
            rel_lines.append(str(m))

    header = (
        f"glob: {len(matches)}"
        + (f"+ (truncated; original >{_GLOB_MAX_RESULTS})" if truncated else "")
        + f" matches for {args.pattern!r} under {root}:"
    )
    body = "\n".join([header, *rel_lines])
    return ToolResult(
        content=body,
        details={
            "matches": len(matches),
            "truncated": truncated,
            "root": str(root),
        },
    )


# ─────────────────────────────────────────────────────────────────────
# read
# ─────────────────────────────────────────────────────────────────────


class _ReadArgs(BaseModel):
    """Arguments for ``read``."""
    path: str = Field(
        ...,
        description=(
            "File path. Relative paths anchor at project_dir. Absolute "
            "paths are accepted if they sit under an allowed root "
            "(project_dir or marketplace_cache)."
        ),
    )
    offset: int = Field(
        0,
        description="Skip the first `offset` bytes. 0 reads from start.",
        ge=0,
    )
    limit: int = Field(
        0,
        description=(
            f"Maximum bytes to return. 0 means the default cap "
            f"({_READ_DEFAULT_BYTES} bytes); pass an explicit limit (up to "
            f"{_READ_MAX_BYTES}) or use offset to page through large files."
        ),
        ge=0,
    )


def _read(args: _ReadArgs, allowed_roots: list[Path]) -> ToolResult:
    p = _resolve_inside_any(allowed_roots, args.path)
    if p is None:
        return ToolResult(
            content=_outside_msg(args.path, allowed_roots), is_error=True,
        )
    if not p.exists():
        return ToolResult(
            content=f"read: file {p} does not exist.", is_error=True,
        )
    if not p.is_file():
        return ToolResult(
            content=f"read: {p} is not a regular file.", is_error=True,
        )

    try:
        size = p.stat().st_size
        # Default to a small page: every byte returned here lives in the
        # history and is replayed on each later iteration. Explicit limit
        # still allows up to _READ_MAX_BYTES; truncation hints at offset.
        cap = args.limit if args.limit > 0 else _READ_DEFAULT_BYTES
        cap = min(cap, _READ_MAX_BYTES)
        with p.open("rb") as f:
            if args.offset:
                f.seek(args.offset)
            data = f.read(cap)
    except OSError as e:
        return ToolResult(
            content=f"read: failed to read {p}: {e}", is_error=True,
        )

    text = data.decode("utf-8", errors="replace")
    truncated = (args.offset + len(data)) < size
    header = (
        f"=== {p} ({size} bytes"
        + (f", showing offset {args.offset}..{args.offset + len(data)}"
           if args.offset or truncated else "")
        + ") ==="
    )
    body = text
    if truncated:
        body += (
            f"\n\n... (truncated: {size - args.offset - len(data)} bytes "
            f"remain. Pass offset={args.offset + len(data)} to continue.)"
        )
    return ToolResult(
        content=f"{header}\n{body}",
        details={
            "path": str(p),
            "bytes_returned": len(data),
            "file_size": size,
            "truncated": truncated,
        },
    )


# ─────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────


def make_code_search_tools(
    *,
    project_dir: Path,
    extra_roots: Optional[Iterable[Path]] = None,
) -> list[EcoTool]:
    """Build the (grep, glob, read) trio.

    Args:
        project_dir: Per-run output dir. Comes FIRST in the whitelist so
                     relative paths resolve there by default.
        extra_roots: Additional read-only roots. Defaults to a list
                     containing the production marketplace_cache mount
                     (/app/marketplace_cache). Override via
                     ``MARKETPLACE_CACHE_ROOT`` env or by passing your
                     own list.

    Returns:
        Three EcoTools: grep, glob, read.
    """
    if extra_roots is None:
        cache_root = Path(os.environ.get(
            "MARKETPLACE_CACHE_ROOT",
            "/app/marketplace_cache",
        ))
        extra_roots = [cache_root] if cache_root.exists() else []
    allowed: list[Path] = [project_dir, *extra_roots]

    return [
        EcoTool(
            name="grep",
            description=(
                "POSIX extended-regex content search across files. Uses "
                "grep -rnE under the hood; output is `file:line:match` "
                "as a single string. Searches marketplace_cache by "
                "default — pass path='.' to search project_dir instead. "
                "Use this FIRST to find which header / file mentions a "
                "type, function, constant, or macro."
            ),
            args_schema=_GrepArgs,
            execute=lambda a: _grep(a, allowed),
        ),
        EcoTool(
            name="glob",
            description=(
                "File-pattern matching with ** for recursive descent. "
                "Returns paths relative to the root, sorted by mtime "
                "(newest first). Use to enumerate files when you know "
                "the naming convention but not the exact location, e.g. "
                "all CID headers: glob('**/Id*.h')."
            ),
            args_schema=_GlobArgs,
            execute=lambda a: _glob(a, allowed),
        ),
        EcoTool(
            name="read",
            description=(
                "Read a UTF-8 file from project_dir OR marketplace_cache. "
                "Optional offset/limit for large files. Use this for the "
                "actual file contents after grep / glob located the path."
            ),
            args_schema=_ReadArgs,
            execute=lambda a: _read(a, allowed),
        ),
    ]

