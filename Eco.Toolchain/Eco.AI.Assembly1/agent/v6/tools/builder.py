"""BUILDER tools — run_make + report_build_pass/fail.

Cross-platform:
- Windows: spawn `cmd.exe /c "vcvarsall.bat x64 && make <target>"`.
- Linux/macOS: spawn `make <target>` directly (assumes gcc + make on PATH).
The build itself is identical because the SDK Makefile already supports gcc
(see memory: "Linux: gcc + ar argv (PR #10)").
"""
from __future__ import annotations
import os
import re
import subprocess
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import ensure_inside


_MAKE_TARGET_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,40}$")
_IS_WINDOWS = sys.platform == "win32"


class RunMakeArgs(BaseModel):
    target: str = Field(default="all")


class ReadFileArgs(BaseModel):
    path: str


class ListDirArgs(BaseModel):
    path: str


class ReportBuildPassArgs(BaseModel):
    artifact_path: str = Field(..., description="Absolute path to the built executable")


class ReportBuildFailArgs(BaseModel):
    error_md: str = Field(..., description="Markdown summary of the key error(s) — NOT raw log")


def _run_make(args: RunMakeArgs, project_dir: Path, vcvarsall: Path | None, make_exe: Path) -> ToolResult:
    if not _MAKE_TARGET_RE.match(args.target):
        return ToolResult(
            content=f"invalid make target: {args.target!r} (allowed: ^[A-Za-z0-9_.-]{{1,40}}$)",
            is_error=True,
        )
    env = dict(os.environ)
    if _IS_WINDOWS:
        if vcvarsall is None:
            return ToolResult(
                content="run_make: vcvarsall path is required on Windows",
                is_error=True,
            )
        env["MSYS_NO_PATHCONV"] = "1"
        env["MSYS2_ARG_CONV_EXCL"] = "*"
        cmd_line = f'"{vcvarsall}" x64 && "{make_exe}" {args.target}'
        cmd: list[str] = ["cmd.exe", "/c", cmd_line]
    else:
        # Linux/macOS: gcc + make are on PATH (or make_exe is an absolute path).
        cmd = [str(make_exe), args.target]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(project_dir),
            env=env,
            shell=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content="build timed out after 300s", is_error=True)
    except FileNotFoundError as e:
        return ToolResult(content=f"build tool not found: {e}", is_error=True)
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    if proc.returncode != 0:
        return ToolResult(content=f"build failed (exit {proc.returncode}):\n{out}",
                          is_error=True, details={"exit_code": proc.returncode})
    return ToolResult(content=f"build succeeded:\n{out}",
                      details={"exit_code": 0})


def _read_file(args: ReadFileArgs, project_dir: Path) -> ToolResult:
    p = Path(args.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"'{args.path}' is outside project_dir", is_error=True)
    if not p.exists():
        return ToolResult(content=f"'{args.path}' does not exist", is_error=True)
    return ToolResult(content=p.read_text(errors="replace"))


def _list_dir(args: ListDirArgs, project_dir: Path) -> ToolResult:
    p = Path(args.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"'{args.path}' is outside project_dir", is_error=True)
    if not p.exists() or not p.is_dir():
        return ToolResult(content=f"'{args.path}' is not a directory", is_error=True)
    return ToolResult(content="\n".join(sorted(e.name for e in p.iterdir())))


def make_builder_tools(*, project_dir: Path, vcvarsall: Path | None, make_exe: Path) -> list[EcoTool]:
    return [
        EcoTool("run_make", "Build the project: vcvarsall.bat x64 && make <target>.",
                RunMakeArgs, lambda a: _run_make(a, project_dir, vcvarsall, make_exe)),
        EcoTool("read_file", "Read a file under project_dir (e.g. Makefile or log).",
                ReadFileArgs, lambda a: _read_file(a, project_dir)),
        EcoTool("list_dir", "List a directory under project_dir.",
                ListDirArgs, lambda a: _list_dir(a, project_dir)),
        EcoTool("report_build_pass", "Stop tool. Call on successful build.",
                ReportBuildPassArgs, lambda _a: ToolResult(content="(stop)")),
        EcoTool("report_build_fail", "Stop tool. Call on failed build with error_md.",
                ReportBuildFailArgs, lambda _a: ToolResult(content="(stop)")),
    ]
