"""File-system tools — sandboxed to one project_dir.

All three tools refuse to touch anything outside `project_dir` via
`ensure_inside`. This is structural capability gating: a coder agent that's
only given `write_file` configured for one dir physically cannot write
elsewhere, regardless of what the prompt tells it.

`make_read_tools(project_dir)` returns (read_file, list_dir) — for any agent.
`make_write_tools(project_dir)` returns (write_file,) — coder only.

Tester gets ONLY read tools, never write_file. This is the load-bearing
distinction that prevents the test-fudging anti-pattern.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from agent.internal.eco_agent import EcoTool, ToolResult
from agent.internal.tools import paths
from agent.internal.tools.common import (
    ensure_inside,
    ensure_inside_any,
    resolve_inside_any,
    decode_text,
)


_READ_FILE_MAX_BYTES = 256 * 1024  # 256 KB — header files + small sources
_LIST_DIR_MAX_ENTRIES = 200        # beyond this the model should narrow the path


def _outside_msg(args_path: str, project_dir: Path) -> str:
    """Build the standard 'outside project_dir' error with a usable hint.

    Always echoes the absolute project_dir so the model can self-correct
    without having to discover the prefix via trial-and-error list_dir calls.
    """
    return (
        f"Path '{args_path}' is outside project_dir.\n"
        f"project_dir is: {project_dir.resolve()}\n"
        f"Pass paths relative to project_dir (e.g. "
        f"'Eco.Math.C89/SharedFiles/IEcoMathC89.h'), not '.' / '/' / "
        f"absolute paths that escape it."
    )


def _missing_msg(args_path: str, resolved: Path, project_dir: Path, kind: str) -> str:
    """Standard 'does not exist' / 'not a directory' / 'not a regular file' error.

    Echoes the resolved absolute path and project_dir so the agent sees
    *exactly* where the lookup landed — invaluable when paths get prefixed.
    """
    return (
        f"Path '{args_path}' {kind}.\n"
        f"Resolved to: {resolved.resolve(strict=False)}\n"
        f"project_dir is: {project_dir.resolve()}"
    )


class _PathArgs(BaseModel):
    path: str = Field(..., description="Path inside project_dir")


class _WriteArgs(BaseModel):
    path: str = Field(..., description="Path inside project_dir")
    content: str = Field(..., description="Full file content (overwrites existing)")


# ── Read-side tools ────────────────────────────────────────────────────────
def _list_dir(args: _PathArgs, project_dir: Path, extra_roots: Optional[list[Path]] = None) -> ToolResult:
    roots = [project_dir, *(extra_roots or [])]
    p = resolve_inside_any(roots, args.path)
    if p is None or not ensure_inside_any(roots, p):
        return ToolResult(content=_outside_msg(args.path, project_dir), is_error=True)
    if not p.exists():
        return ToolResult(content=_missing_msg(args.path, p, project_dir, "does not exist"), is_error=True)
    if not p.is_dir():
        return ToolResult(content=_missing_msg(args.path, p, project_dir, "is not a directory"), is_error=True)
    entries = []
    for e in sorted(p.iterdir()):
        suffix = "/" if e.is_dir() else ""
        entries.append(f"{e.name}{suffix}")
    if len(entries) > _LIST_DIR_MAX_ENTRIES:
        more = len(entries) - _LIST_DIR_MAX_ENTRIES
        entries = entries[:_LIST_DIR_MAX_ENTRIES]
        entries.append(f"... ({more} more entries — narrow the path)")
    return ToolResult(content="\n".join(entries) if entries else "(empty)")


def _read_file(args: _PathArgs, project_dir: Path, extra_roots: Optional[list[Path]] = None) -> ToolResult:
    roots = [project_dir, *(extra_roots or [])]
    p = resolve_inside_any(roots, args.path)
    if p is None or not ensure_inside_any(roots, p):
        return ToolResult(content=_outside_msg(args.path, project_dir), is_error=True)
    if not p.exists():
        return ToolResult(content=_missing_msg(args.path, p, project_dir, "does not exist"), is_error=True)
    if not p.is_file():
        return ToolResult(content=_missing_msg(args.path, p, project_dir, "is not a regular file"), is_error=True)
    try:
        size = p.stat().st_size
    except OSError as e:
        return ToolResult(content=f"stat failed for '{args.path}': {e}", is_error=True)
    if size > _READ_FILE_MAX_BYTES:
        return ToolResult(
            content=f"File '{args.path}' is {size} bytes — exceeds limit "
                    f"{_READ_FILE_MAX_BYTES}. Use a smaller scope or list_dir to navigate.",
            is_error=True,
        )
    try:
        return ToolResult(content=decode_text(p.read_bytes()))
    except OSError as e:
        # Catch read errors symmetrically with stat above — otherwise an
        # IO error would surface as an EcoAgent ToolMessage(error) without
        # the helpful "path: ..." context every other branch provides.
        return ToolResult(content=f"read failed for '{args.path}': {e}", is_error=True)


# ── Write-side tool ────────────────────────────────────────────────────────
def _write_file(args: _WriteArgs, project_dir: Path) -> ToolResult:
    p = resolve_inside_any([project_dir], args.path)
    if p is None or not ensure_inside(project_dir, p):
        return ToolResult(content=_outside_msg(args.path, project_dir), is_error=True)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(args.content)
    except OSError as e:
        return ToolResult(content=f"write failed for '{args.path}': {e}", is_error=True)
    return ToolResult(
        content=f"wrote {len(args.content)} bytes to {p.as_posix()}",
        details={"path": p.as_posix(), "bytes": len(args.content)},
    )


# ── Factories ──────────────────────────────────────────────────────────────
_PATH_HINT = (
    "Paths are anchored at project_dir (or at marketplace_cache when the path "
    "starts with 'marketplace_cache/'), so pass them as root-relative "
    "(e.g. 'Eco.Math.C89/SharedFiles/IEcoMathC89.h' or "
    "'marketplace_cache/Eco.System1/SharedFiles'). Absolute paths and legacy "
    "CWD-relative paths that already point inside a root are also accepted. "
    "Do NOT pass '.' / '/' / '' to discover the workspace — read the "
    "project_dir absolute path from the seed message instead."
)


def make_read_tools(project_dir: Path) -> list[EcoTool]:
    """Read-only fs tools (read_file, list_dir). Safe for any agent including tester.

    Read access is also granted to the marketplace_cache mount (read-only) so
    agents can inspect component headers there without falling back to the
    project_dir-only sandbox error. Write access stays strictly project_dir.
    """
    # Same layered resolution as code_search (env override → repo-root cache
    # → /app mount) so host runs and the nested-project container layout both
    # resolve without env vars.
    cache_root = paths.marketplace_cache_root()
    extra_roots = [cache_root] if cache_root.exists() else []
    return [
        EcoTool(
            name="read_file",
            description=(
                "Read a UTF-8 file inside project_dir OR marketplace_cache. "
                f"Refuses files larger than {_READ_FILE_MAX_BYTES // 1024} KB. "
                + _PATH_HINT
            ),
            args_schema=_PathArgs,
            execute=lambda a: _read_file(a, project_dir, extra_roots),
        ),
        EcoTool(
            name="list_dir",
            description=(
                "List the contents of a directory inside project_dir OR "
                "marketplace_cache. Directories are marked with a trailing "
                "slash. " + _PATH_HINT
            ),
            args_schema=_PathArgs,
            execute=lambda a: _list_dir(a, project_dir, extra_roots),
        ),
    ]


def make_write_tools(project_dir: Path) -> list[EcoTool]:
    """Write-side fs tool (write_file). Coder only — NEVER bind to tester."""
    return [
        EcoTool(
            name="write_file",
            description=(
                "Create or overwrite a file inside project_dir. "
                "Parent directories are created automatically. " + _PATH_HINT
            ),
            args_schema=_WriteArgs,
            execute=lambda a: _write_file(a, project_dir),
        ),
    ]


def make_architect_spec_write_tool(project_dir: Path) -> list[EcoTool]:
    """Sandboxed write for the architect: ONLY ``project_dir/docs/specs/``.

    The architect must not author source code (no pre-writing what the coder
    is supposed to write), but it does need a way to dump per-new-component
    IDL / business-logic specs to disk so the plan handoff stays small and
    a future parallel-coders orchestrator can read one spec per worker. This
    factory is the load-bearing capability gate: the tool refuses to write
    anywhere outside ``docs/specs/`` regardless of what the prompt tells the
    model.
    """
    specs_root = (project_dir / "docs" / "specs").resolve()

    def _write_spec(args: _WriteArgs) -> ToolResult:
        # Resolve under project_dir first (so relative paths anchor correctly),
        # then enforce the specs/ prefix. This mirrors the existing
        # ``ensure_inside`` double-check pattern: capability gating that
        # doesn't trust the prompt.
        p = resolve_inside_any([project_dir], args.path)
        if p is None or not ensure_inside(project_dir, p):
            return ToolResult(content=_outside_msg(args.path, project_dir), is_error=True)
        # Hard scope: must be inside docs/specs/.
        try:
            p_resolved = p.resolve()
        except OSError as e:
            return ToolResult(content=f"resolve failed for '{args.path}': {e}", is_error=True)
        if not (p_resolved == specs_root or specs_root in p_resolved.parents):
            return ToolResult(
                content=(
                    f"Path '{args.path}' is outside the architect's writable scope "
                    f"({specs_root}). The architect may ONLY write to "
                    f"project_dir/docs/specs/ — a path-anchored, capability-gated "
                    f"write, NOT a free write_file. Use this tool to author one "
                    f"markdown spec per new component; the coder reads them later."
                ),
                is_error=True,
            )
        try:
            p_resolved.parent.mkdir(parents=True, exist_ok=True)
            p_resolved.write_text(args.content, encoding="utf-8")
        except OSError as e:
            return ToolResult(content=f"write failed for '{args.path}': {e}", is_error=True)
        return ToolResult(
            content=f"wrote {len(args.content)} bytes to {p_resolved.as_posix()}",
            details={"path": p_resolved.as_posix(), "bytes": len(args.content)},
        )

    return [
        EcoTool(
            name="write_spec",
            description=(
                "Sandboxed write for the architect: create or overwrite a file "
                f"inside {specs_root}. Parent directories are created "
                "automatically. The path MUST be relative to project_dir and "
                "begin with 'docs/specs/' (e.g. 'docs/specs/Eco.MyNewThing.md'). "
                "Any other path is refused. Use this tool to author one "
                "markdown spec per new reusable component the plan introduces; "
                "the plan then lists the spec path and the coder reads the "
                "file directly. This keeps the to_coder handoff under the "
                "HARNESS_PLAN_HANDOFF_MAX_BYTES budget even when there are "
                "many new components and enables parallel coders (one spec "
                "per worker)."
            ),
            args_schema=_WriteArgs,
            execute=_write_spec,
        ),
    ]

