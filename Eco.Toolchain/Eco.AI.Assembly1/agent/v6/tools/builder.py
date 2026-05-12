"""BUILDER tools — run_make + report_build_pass/fail."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import ensure_inside


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


def _run_make(args: RunMakeArgs, project_dir: Path, vcvarsall: Path, make_exe: Path) -> ToolResult:
    cmd_line = f'"{vcvarsall}" x64 && "{make_exe}" {args.target}'
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    try:
        proc = subprocess.run(
            ["cmd.exe", "/c", cmd_line],
            cwd=str(project_dir),
            env=env,
            shell=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content="build timed out after 300s", is_error=True)
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


def make_builder_tools(*, project_dir: Path, vcvarsall: Path, make_exe: Path) -> list[EcoTool]:
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
