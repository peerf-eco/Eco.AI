"""SETUP tools — ecoos_pull, list_dir, read_file, mark_setup_done."""
from __future__ import annotations
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import is_valid_cid, is_valid_version, ensure_inside


class EcoosPullArgs(BaseModel):
    cid: str = Field(..., description="32-char uppercase hex component CID")
    version: str = Field(..., description="Version in N.N.N.N format")


class ListDirArgs(BaseModel):
    path: str


class ReadFileArgs(BaseModel):
    path: str


class MarkSetupDoneArgs(BaseModel):
    downloaded_paths: list[str] = Field(..., description="Verified package directories under project_dir")


def _ecoos_pull(args: EcoosPullArgs, cli_path: Path, project_dir: Path,
                allowed_components: list[dict]) -> ToolResult:
    if not is_valid_cid(args.cid):
        return ToolResult(content=f"Invalid CID: must be 32-char uppercase hex, got '{args.cid}'", is_error=True)
    if not is_valid_version(args.version):
        return ToolResult(content=f"Invalid version: must be N.N.N.N, got '{args.version}'", is_error=True)
    in_plan = any(c.get("cid") == args.cid and c.get("version") == args.version
                  for c in allowed_components)
    if not in_plan:
        return ToolResult(content=f"Component {args.cid} v{args.version} not in plan", is_error=True)

    cmd = [str(cli_path), "pull", "-c", args.cid, "-v", args.version, "-d", str(project_dir)]
    try:
        proc = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return ToolResult(content=f"eco-cli pull timed out after 60s", is_error=True)
    if proc.returncode != 0:
        return ToolResult(
            content=f"eco-cli failed (exit {proc.returncode}):\n{proc.stderr}",
            is_error=True,
            details={"stdout": proc.stdout, "stderr": proc.stderr},
        )
    return ToolResult(content=f"pulled {args.cid} v{args.version}", details={"stdout": proc.stdout})


def _list_dir(args: ListDirArgs, project_dir: Path) -> ToolResult:
    p = Path(args.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"Path '{args.path}' is outside project_dir", is_error=True)
    if not p.exists():
        return ToolResult(content=f"Path '{args.path}' does not exist", is_error=True)
    if not p.is_dir():
        return ToolResult(content=f"Path '{args.path}' is not a directory", is_error=True)
    entries = sorted([e.name for e in p.iterdir()])
    return ToolResult(content="\n".join(entries))


def _read_file(args: ReadFileArgs, project_dir: Path) -> ToolResult:
    p = Path(args.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"Path '{args.path}' is outside project_dir", is_error=True)
    if not p.exists():
        return ToolResult(content=f"File '{args.path}' does not exist", is_error=True)
    return ToolResult(content=p.read_text(errors="replace"))


def make_setup_tools(*, cli_path: Path, project_dir: Path,
                     allowed_components: list[dict]) -> list[EcoTool]:
    return [
        EcoTool(
            name="ecoos_pull",
            description="Pull an EcoOS SDK component into project_dir via eco-cli.",
            args_schema=EcoosPullArgs,
            execute=lambda a: _ecoos_pull(a, cli_path, project_dir, allowed_components),
        ),
        EcoTool(
            name="list_dir",
            description="List entries under a directory inside project_dir.",
            args_schema=ListDirArgs,
            execute=lambda a: _list_dir(a, project_dir),
        ),
        EcoTool(
            name="read_file",
            description="Read a file under project_dir.",
            args_schema=ReadFileArgs,
            execute=lambda a: _read_file(a, project_dir),
        ),
        EcoTool(
            name="mark_setup_done",
            description="Stop tool. Call when all components are verified.",
            args_schema=MarkSetupDoneArgs,
            execute=lambda _a: ToolResult(content="(stop tool — never executed)"),
        ),
    ]
