"""SETUP tools — ecoos_pull, list_dir, read_file, mark_setup_done.

Cross-platform:
- Windows: `ecoos_pull` calls eco-cli.exe to fetch a component from marketplace.
- Linux/macOS: eco-cli is Windows-only. We fall back to copying the matching
  `<name>_DK_v.<version>/` directory from `sdk_root` (a local SDK mirror,
  mounted read-only in Docker) into `project_dir`. The observable result —
  the package landing inside project_dir — is the same.
"""
from __future__ import annotations
import re
import shutil
import subprocess
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import is_valid_cid, is_valid_version, ensure_inside
from agent.v6.tools.sdk_layout import resolve_component_root


_IS_WINDOWS = sys.platform == "win32"

# Matches any directory whose name ends with the versioned DK suffix,
# e.g. "Eco.X_DK_v.1.0.1.2". Used to guard the no-version fallback so we
# do NOT silently substitute a wrong-versioned package.
_VERSIONED_RE = re.compile(r"^.+_DK_v\.\d+\.\d+\.\d+\.\d+$")


class EcoosPullArgs(BaseModel):
    cid: str = Field(..., description="32-char uppercase hex component CID")
    version: str = Field(..., description="Version in N.N.N.N format")


class ListDirArgs(BaseModel):
    path: str


class ReadFileArgs(BaseModel):
    path: str


class MarkSetupDoneArgs(BaseModel):
    downloaded_paths: list[str] = Field(..., description="Verified package directories under project_dir")


def _ecoos_pull(args: EcoosPullArgs, cli_path: Path | None, project_dir: Path,
                allowed_components: list[dict], sdk_root: Path | None) -> ToolResult:
    if not is_valid_cid(args.cid):
        return ToolResult(content=f"Invalid CID: must be 32-char uppercase hex, got '{args.cid}'", is_error=True)
    if not is_valid_version(args.version):
        return ToolResult(content=f"Invalid version: must be N.N.N.N, got '{args.version}'", is_error=True)

    component = next(
        (c for c in allowed_components
         if c.get("cid") == args.cid and c.get("version") == args.version),
        None,
    )
    if component is None:
        return ToolResult(content=f"Component {args.cid} v{args.version} not in plan", is_error=True)

    if _IS_WINDOWS and cli_path is not None:
        cmd = [str(cli_path), "pull", "-c", args.cid, "-v", args.version, "-d", str(project_dir)]
        try:
            proc = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            return ToolResult(content=f"eco-cli pull timed out after 60s", is_error=True)
        except FileNotFoundError as e:
            return ToolResult(content=f"eco-cli not found: {e}", is_error=True)
        if proc.returncode != 0:
            return ToolResult(
                content=f"eco-cli failed (exit {proc.returncode}):\n{proc.stderr}",
                is_error=True,
                details={"stdout": proc.stdout, "stderr": proc.stderr},
            )
        return ToolResult(content=f"pulled {args.cid} v{args.version}", details={"stdout": proc.stdout})

    # Linux/macOS or no eco-cli: copy the INNER root from local sdk_root mirror.
    if sdk_root is None:
        return ToolResult(
            content="ecoos_pull: neither eco-cli nor sdk_root configured",
            is_error=True,
        )
    name = component.get("name") or ""
    if not name:
        return ToolResult(
            content=f"Component {args.cid} v{args.version} has no `name` in plan — cannot resolve in sdk_root",
            is_error=True,
        )

    inner = resolve_component_root(Path(sdk_root), name, version=args.version)
    if inner is None:
        # Fallback ONLY for flat packages (Eco.MemoryManager1-style) whose
        # version pin is conventional, not encoded in the dirname. We must NOT
        # silently substitute a different versioned package — that would have
        # the tool report "v2.0.0.0 copied" when only v1.0.1.2 was on disk.
        candidate = resolve_component_root(Path(sdk_root), name)
        if candidate is not None \
                and not _VERSIONED_RE.match(candidate.name) \
                and not _VERSIONED_RE.match(candidate.parent.name):
            inner = candidate
    if inner is None:
        return ToolResult(
            content=f"Component '{name}' v{args.version} not found in local sdk_root: {sdk_root}",
            is_error=True,
        )

    dst = Path(project_dir) / inner.name
    try:
        shutil.copytree(inner, dst, dirs_exist_ok=True)
    except Exception as e:
        return ToolResult(
            content=f"copy from sdk_root failed: {type(e).__name__}: {e}",
            is_error=True,
        )
    dst_posix = dst.as_posix()
    return ToolResult(
        content=(
            f"copied {name} v{args.version} from sdk_root.\n"
            f"Inner root inside project_dir: {dst_posix}\n"
            f"Verify with `list_dir('{dst_posix}')` — you should see SharedFiles/ and BuildFiles/."
        ),
        details={
            "source": str(inner),
            "target": str(dst),
            "inner_root": dst_posix,
        },
    )


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


def make_setup_tools(*, cli_path: Path | None, project_dir: Path,
                     allowed_components: list[dict],
                     sdk_root: Path | None = None) -> list[EcoTool]:
    return [
        EcoTool(
            name="ecoos_pull",
            description="Pull an EcoOS SDK component into project_dir. Uses eco-cli on Windows, or copies from local sdk_root mirror elsewhere.",
            args_schema=EcoosPullArgs,
            execute=lambda a: _ecoos_pull(a, cli_path, project_dir, allowed_components, sdk_root),
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
