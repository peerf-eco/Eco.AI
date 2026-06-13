"""`run_build` — invoke GNU Make for a project subdir.

Minimal MVP: spawns `make <target>` in the given directory, captures
stdout+stderr, returns rc. Coder loops calls (write → run_build → on
failure, read errors → edit → run_build again).

Windows MSVC integration (vcvarsall.bat preamble, MSYS path-conv guards)
lives in the caller's environment — we don't shell out through cmd.exe so
that behaviour must be set up in the parent process's env vars before the
agent starts. This keeps the tool ledger small and shell-injection-free.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import ensure_inside, resolve_inside


_BUILD_TIMEOUT_S = 300
_BUILD_OUTPUT_TRUNC = 8 * 1024  # 8 KB of build log is enough for the model


class _BuildArgs(BaseModel):
    project_subdir: str = Field(
        ..., description="Directory under project_dir that contains the Makefile",
    )
    target: str = Field("", description="Make target (default: first target)")


def _run_build(args: _BuildArgs, project_dir: Path, make_exe: Path) -> ToolResult:
    subdir = resolve_inside(project_dir, args.project_subdir)
    if not ensure_inside(project_dir, subdir):
        return ToolResult(
            content=(
                f"project_subdir '{args.project_subdir}' is outside project_dir.\n"
                f"project_dir is: {project_dir.resolve()}\n"
                f"Pass a path relative to project_dir (e.g. 'Eco.Calc/MSVC_v140')."
            ),
            is_error=True,
        )
    if not subdir.is_dir():
        return ToolResult(
            content=(
                f"project_subdir '{args.project_subdir}' is not a directory.\n"
                f"Resolved to: {subdir.resolve(strict=False)}\n"
                f"project_dir is: {project_dir.resolve()}"
            ),
            is_error=True,
        )
    if not (subdir / "Makefile").exists() and not (subdir / "makefile").exists():
        return ToolResult(
            content=(
                f"No Makefile in '{args.project_subdir}' "
                f"(resolved to {subdir.resolve(strict=False)}). Write one first."
            ),
            is_error=True,
        )

    cmd = [str(make_exe)]
    if args.target:
        cmd.append(args.target)
    try:
        # encoding="utf-8" so cl.exe/gcc error messages with non-ASCII paths
        # or russian Windows locale messages decode predictably.
        proc = subprocess.run(
            cmd, shell=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=_BUILD_TIMEOUT_S, cwd=str(subdir),
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            content=f"make timed out after {_BUILD_TIMEOUT_S}s in '{args.project_subdir}'",
            is_error=True,
        )
    except FileNotFoundError as e:
        return ToolResult(content=f"make binary not found: {e}", is_error=True)

    combined = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    if len(combined) > _BUILD_OUTPUT_TRUNC:
        combined = (
            combined[: _BUILD_OUTPUT_TRUNC // 2]
            + f"\n... (truncated, {len(combined) - _BUILD_OUTPUT_TRUNC} bytes elided) ...\n"
            + combined[-_BUILD_OUTPUT_TRUNC // 2:]
        )
    if proc.returncode != 0:
        return ToolResult(
            content=f"BUILD FAILED (rc={proc.returncode}):\n{combined}",
            is_error=True,
            details={"rc": proc.returncode, "subdir": str(subdir)},
        )
    # On success the model only needs the fact — the full compiler chatter
    # would otherwise live in the history and be replayed every iteration.
    # The log tail stays available in details (UI/debugging channel).
    return ToolResult(
        content=f"BUILD OK in '{args.project_subdir}' (rc=0).",
        details={"rc": 0, "subdir": str(subdir), "log_tail": combined[-2000:]},
    )


def make_build_tools(project_dir: Path, make_exe: Path) -> list[EcoTool]:
    return [
        EcoTool(
            name="run_build",
            description=(
                "Run GNU make in a subdirectory of project_dir that contains a Makefile. "
                "Returns truncated build log + rc. project_subdir is anchored at "
                "project_dir — pass it as project_dir-relative (e.g. 'Eco.Calc/MSVC_v140'), "
                "not '.' or '/'."
            ),
            args_schema=_BuildArgs,
            execute=lambda a: _run_build(a, project_dir, make_exe),
        ),
    ]
