"""`run_artifact` — execute a built binary, capture its output.

Tester-only tool. Used to verify the compiled artifact behaves per the
acceptance criteria passed in the handoff message from coder.

Sandboxed: the artifact path must resolve inside project_dir, so a tester
running on `/usr/bin/rm -rf /` is not a possible outcome — same path-check
discipline as the read/write tools.

No timeout enforcement beyond a hard cap: an artifact that hangs is itself
a test failure (the tester reports it as such via fail/done(message)).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from agent.internal.eco_agent import EcoTool, ToolResult
from agent.internal.tools.common import ensure_inside


_RUN_TIMEOUT_S = 30
_RUN_OUTPUT_TRUNC = 16 * 1024  # 16 KB of program output


class _RunArgs(BaseModel):
    artifact_path: str = Field(..., description="Absolute path to the binary (inside project_dir)")
    stdin: str = Field("", description="Optional input piped to the program's stdin")


def _run_artifact(args: _RunArgs, project_dir: Path) -> ToolResult:
    p = Path(args.artifact_path)
    if not ensure_inside(project_dir, p):
        return ToolResult(
            content=f"artifact_path '{args.artifact_path}' is outside project_dir",
            is_error=True,
        )
    if not p.exists():
        return ToolResult(
            content=f"Artifact '{args.artifact_path}' does not exist", is_error=True,
        )
    if not p.is_file():
        return ToolResult(
            content=f"Artifact '{args.artifact_path}' is not a regular file", is_error=True,
        )

    try:
        # encoding="utf-8" so artifact's stdout/stderr decode consistently
        # across platforms — important because acceptance criteria are
        # compared as strings by the tester.
        proc = subprocess.run(
            [str(p)], shell=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=_RUN_TIMEOUT_S, input=args.stdin or None,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            content=f"Artifact ran for >{_RUN_TIMEOUT_S}s without exiting — likely hung. "
                    "This is a test failure; report it via fail() with the observed behaviour.",
            is_error=True,
        )
    except FileNotFoundError as e:
        return ToolResult(
            content=f"Artifact could not be executed: {e}", is_error=True,
        )
    except PermissionError as e:
        return ToolResult(
            content=f"Artifact is not executable: {e}. "
                    "On Linux, check that the file has the +x bit.",
            is_error=True,
        )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if len(stdout) > _RUN_OUTPUT_TRUNC:
        stdout = stdout[:_RUN_OUTPUT_TRUNC] + f"\n... (stdout truncated at {_RUN_OUTPUT_TRUNC} bytes)"
    if len(stderr) > _RUN_OUTPUT_TRUNC:
        stderr = stderr[:_RUN_OUTPUT_TRUNC] + f"\n... (stderr truncated at {_RUN_OUTPUT_TRUNC} bytes)"

    sections = [f"rc: {proc.returncode}"]
    if stdout:
        sections.append(f"--- stdout ---\n{stdout}")
    else:
        sections.append("--- stdout --- (empty)")
    if stderr:
        sections.append(f"--- stderr ---\n{stderr}")
    return ToolResult(
        content="\n".join(sections),
        details={"rc": proc.returncode, "artifact": str(p)},
    )


def make_runtime_tools(project_dir: Path) -> list[EcoTool]:
    """Runtime tools for the tester agent — read-side only, no write/edit."""
    return [
        EcoTool(
            name="run_artifact",
            description="Execute a compiled binary inside project_dir and capture stdout/stderr/rc. "
                        "Times out at 30s.",
            args_schema=_RunArgs,
            execute=lambda a: _run_artifact(a, project_dir),
        ),
    ]

