"""CODER tools — claude-code style file I/O (no bash, no shell)."""
from __future__ import annotations
from pathlib import Path
import re
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import ensure_inside


class ReadFileArgs(BaseModel):
    path: str


class WriteFileArgs(BaseModel):
    path: str
    content: str


class EditFileArgs(BaseModel):
    path: str
    old: str = Field(..., description="Exact substring to replace (must occur exactly once)")
    new: str


class ListDirArgs(BaseModel):
    path: str


class GlobArgs(BaseModel):
    pattern: str = Field(..., description="Glob pattern relative to project_dir, e.g. '**/*.c'")


class GrepArgs(BaseModel):
    pattern: str = Field(..., description="Regex to search for")
    path: str = Field(..., description="File or directory to search in")


class MarkCodeDoneArgs(BaseModel):
    summary_md: str = Field(..., description="Markdown summary of files created/modified")


def _allowed_for_read(p: Path, project_dir: Path, downloaded_paths: list[Path]) -> bool:
    if ensure_inside(project_dir, p):
        return True
    return any(ensure_inside(dp, p) for dp in downloaded_paths)


def _read_file(a: ReadFileArgs, project_dir: Path, downloaded_paths: list[Path]) -> ToolResult:
    p = Path(a.path)
    if not _allowed_for_read(p, project_dir, downloaded_paths):
        return ToolResult(content=f"Path '{a.path}' is outside project_dir and downloaded_paths",
                          is_error=True)
    if not p.exists():
        return ToolResult(content=f"File '{a.path}' does not exist", is_error=True)
    return ToolResult(content=p.read_text(errors="replace"))


def _write_file(a: WriteFileArgs, project_dir: Path) -> ToolResult:
    p = Path(a.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"write_file: path '{a.path}' must be inside project_dir",
                          is_error=True)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(a.content)
    return ToolResult(content=f"wrote {len(a.content)} bytes to {p.name}",
                      details={"bytes": len(a.content)})


def _edit_file(a: EditFileArgs, project_dir: Path) -> ToolResult:
    p = Path(a.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"edit_file: path '{a.path}' must be inside project_dir",
                          is_error=True)
    if not p.exists():
        return ToolResult(content=f"File '{a.path}' does not exist", is_error=True)
    text = p.read_text(errors="replace")
    if a.old not in text:
        return ToolResult(content=f"old string not found in {p.name}", is_error=True)
    occurrences = text.count(a.old)
    if occurrences > 1:
        return ToolResult(content=f"old string occurs {occurrences} times in {p.name} — not unique",
                          is_error=True)
    p.write_text(text.replace(a.old, a.new))
    return ToolResult(content=f"edited {p.name}")


def _list_dir(a: ListDirArgs, project_dir: Path, downloaded_paths: list[Path]) -> ToolResult:
    p = Path(a.path)
    if not _allowed_for_read(p, project_dir, downloaded_paths):
        return ToolResult(content=f"Path '{a.path}' is outside allowed roots", is_error=True)
    if not p.exists() or not p.is_dir():
        return ToolResult(content=f"'{a.path}' is not an existing directory", is_error=True)
    return ToolResult(content="\n".join(sorted(e.name for e in p.iterdir())))


def _glob(a: GlobArgs, project_dir: Path) -> ToolResult:
    matches = sorted([str(p.relative_to(project_dir)) for p in project_dir.rglob(a.pattern)])
    if not matches:
        return ToolResult(content=f"(no matches for '{a.pattern}')")
    return ToolResult(content="\n".join(matches))


def _grep(a: GrepArgs, project_dir: Path, downloaded_paths: list[Path]) -> ToolResult:
    p = Path(a.path)
    if not _allowed_for_read(p, project_dir, downloaded_paths):
        return ToolResult(content=f"Path '{a.path}' is outside allowed roots", is_error=True)
    try:
        rx = re.compile(a.pattern)
    except re.error as e:
        return ToolResult(content=f"invalid regex: {e}", is_error=True)
    found: list[str] = []
    targets = p.rglob("*") if p.is_dir() else [p]
    for f in targets:
        if not f.is_file():
            continue
        try:
            for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                if rx.search(line):
                    found.append(f"{f}:{n}: {line}")
        except (OSError, UnicodeDecodeError):
            continue
    return ToolResult(content="\n".join(found) if found else "(no matches)")


def make_coder_tools(*, project_dir: Path, downloaded_paths: list[Path]) -> list[EcoTool]:
    return [
        EcoTool("read_file",  "Read a text file under project_dir or downloaded SDK paths.",
                ReadFileArgs,  lambda a: _read_file(a, project_dir, downloaded_paths)),
        EcoTool("write_file", "Create or overwrite a file inside project_dir.",
                WriteFileArgs, lambda a: _write_file(a, project_dir)),
        EcoTool("edit_file",  "Replace a unique substring in a file inside project_dir.",
                EditFileArgs,  lambda a: _edit_file(a, project_dir)),
        EcoTool("list_dir",   "List a directory under project_dir or downloaded SDK paths.",
                ListDirArgs,   lambda a: _list_dir(a, project_dir, downloaded_paths)),
        EcoTool("glob",       "Glob files under project_dir.",
                GlobArgs,      lambda a: _glob(a, project_dir)),
        EcoTool("grep",       "Regex-search a file or directory under allowed roots.",
                GrepArgs,      lambda a: _grep(a, project_dir, downloaded_paths)),
        EcoTool("mark_code_done", "Stop tool. Call when implementation is complete.",
                MarkCodeDoneArgs, lambda _a: ToolResult(content="(stop tool)")),
    ]
