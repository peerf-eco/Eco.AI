"""SETUP tools — ecoos_pull, list_dir, read_file, mark_setup_done.

`ecoos_pull` ALWAYS calls eco-cli (the marketplace CLI) when `cli_path` is
configured. On Linux containers we invoke the Windows-only eco-cli.exe via
Wine — the prefix (e.g. `wine`) is supplied through env var V6_CLI_PREFIX.

Only when `cli_path` is None do we fall back to copying packages from the
local sdk_root mirror — this exists only as a developer-mode escape hatch
and should not be relied on in production.
"""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import is_valid_cid, is_valid_version, ensure_inside
from agent.v6.tools.sdk_layout import resolve_component_root


# `wine` adds ~5-10s startup overhead on first invocation per wineprefix;
# subsequent calls are faster but a single pull can still take 30-60s while
# downloading. Keep the hard ceiling generous.
_CLI_TIMEOUT_S = 180


def _cli_command(cli_path: Path, *args: str) -> list[str]:
    """Build the argv for an eco-cli call, prepending V6_CLI_PREFIX (e.g.
    `wine` on Linux) when set. Split on whitespace so a multi-word prefix
    like `wine64` or `xvfb-run -a wine` also works."""
    prefix = os.getenv("V6_CLI_PREFIX", "").split()
    return [*prefix, str(cli_path), *args]


def _find_devkit(cli_path: Path, cid: str) -> dict | None:
    """Call `eco-cli find -c CID`, parse the JSON output, find the MultiOS
    DEVKIT artefact and return its metadata.

    Returns a dict shaped:
        {"version": "1.0.1.2", "file_id": "be7e1b3a3528",
         "package_name": "Eco.Math.C89"}
    or None if the response was unparseable / no DEVKIT in the listing.

    Why DEVKIT over per-OS dynamic libs: the DEVKIT zip is multi-platform
    universal — one download yields SharedFiles/ headers AND BuildFiles/
    for every OS+arch (incl. static & dynamic libs). See manual smoke
    test results in conversation history.
    """
    cmd = _cli_command(cli_path, "find", "-c", cid)
    try:
        proc = subprocess.run(
            cmd, shell=False, capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if proc.returncode != 0:
        return None

    # eco-cli prints prelude lines ("Hello, yan@..."), the JSON body, and
    # possibly trailing lines. Extract the JSON object by finding the first
    # `{` and matching braces. The body is a single nested object.
    out = proc.stdout or ""
    start = out.find("{")
    if start < 0:
        return None
    depth = 0
    end = -1
    for i in range(start, len(out)):
        ch = out[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        return None
    try:
        data = json.loads(out[start:end])
    except json.JSONDecodeError:
        return None

    package_name = data.get("name") or ""
    for version in data.get("versions") or []:
        ver_name = version.get("name") or ""
        for f in version.get("files") or []:
            if f.get("contentType") == "DEVKIT":
                return {
                    "version": ver_name,
                    "file_id": f.get("fileId") or "",
                    "package_name": package_name,
                }
    return None

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


def _allowed_components_hint(allowed_components: list[dict]) -> str:
    """Format the plan's component list as a self-teaching hint for the LLM.
    Returned on every validation/lookup error so the model can self-correct
    on the next call."""
    if not allowed_components:
        return ""
    rows = []
    for c in allowed_components:
        cid = c.get("cid", "?")
        ver = c.get("version", "?")
        name = c.get("name", "?")
        rows.append(f"  - cid='{cid}', version='{ver}'   # {name}")
    return "\n\nAllowed components (copy these values EXACTLY):\n" + "\n".join(rows)


def _normalize_cid(cid: str) -> str:
    """Accept the LLM's CID in many shapes and coerce to the canonical
    32-char uppercase hex form. Strip dashes (UUID-style and partial),
    whitespace, and quote characters; uppercase the rest. We do NOT
    enforce a strict regex here because find/pull would catch genuinely
    bad CIDs anyway, and rejecting at the validator was sending the LLM
    into format-guessing loops."""
    return re.sub(r"[^0-9A-Fa-f]", "", cid).upper()


def _normalize_version(ver: str) -> str:
    """Pad version to 4 components. Planner often emits '1.0.0' or even
    '1.0' — the marketplace uses 4-tuple but we don't actually need an
    exact match because `_find_devkit` returns the real version anyway.
    Normalisation is just so downstream string compares don't get noisy."""
    parts = [p for p in ver.strip().split(".") if p]
    while len(parts) < 4:
        parts.append("0")
    return ".".join(parts[:4])


def _ecoos_pull(args: EcoosPullArgs, cli_path: Path | None, project_dir: Path,
                allowed_components: list[dict], sdk_root: Path | None,
                target_os: str | None = None, target_arch: str | None = None) -> ToolResult:
    hint = _allowed_components_hint(allowed_components)
    # Normalise instead of reject — be liberal in what we accept. The real
    # validation is "does eco-cli find a DEVKIT for this CID?" later on.
    cid = _normalize_cid(args.cid)
    plan_version = _normalize_version(args.version)
    if len(cid) != 32 or not re.fullmatch(r"[0-9A-F]{32}", cid):
        return ToolResult(
            content=(
                f"CID '{args.cid}' is not a 32-char hex value (after stripping "
                f"dashes/whitespace). Need exactly 32 hex digits.{hint}"
            ),
            is_error=True,
        )

    # Match against plan by NORMALISED CID — accept any version string in
    # `args.version` because the planner sometimes emits 1.0.0, 1.0, etc.,
    # and the marketplace version is queried fresh via _find_devkit anyway.
    component = next(
        (c for c in allowed_components if _normalize_cid(c.get("cid", "")) == cid),
        None,
    )
    if component is None:
        return ToolResult(
            content=f"Component CID {cid} not in plan (after normalisation).{hint}",
            is_error=True,
        )
    # Re-bind args to normalised values so downstream code (logging, errors)
    # uses the canonical form.
    args = EcoosPullArgs(cid=cid, version=plan_version)

    # CLI-first strategy: find the DEVKIT via `eco find -c CID`, then pull
    # it by fileId. One DEVKIT pull yields the COMPLETE multi-platform
    # package — SharedFiles/ headers + BuildFiles/{Linux,Windows}/<arch>/
    # {Static,Dynamic}Release/{lib<CID>.a,<CID>.so,<CID>.lib,<CID>.dll}.
    # This is why the per-OS dynamic-only pull was always insufficient
    # (it returned just one .so/.dll), and why marketplace "version not
    # found" used to spuriously fail the whole run (plan-version mismatch
    # is now silently overridden by what the marketplace actually serves).
    cli_attempt: dict | None = None
    if cli_path is not None:
        project_dir.mkdir(parents=True, exist_ok=True)
        devkit = _find_devkit(cli_path, args.cid)
        if devkit and devkit.get("file_id"):
            real_version = devkit["version"] or args.version
            file_id = devkit["file_id"]
            cmd = _cli_command(
                cli_path, "pull", "-c", args.cid, "-v", real_version,
                f"-fid={file_id}",
            )
            try:
                proc = subprocess.run(
                    cmd, shell=False, capture_output=True, text=True,
                    timeout=_CLI_TIMEOUT_S, cwd=str(project_dir),
                )
                combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
                # eco-cli returns exit 0 even when nothing downloads —
                # verify by checking the package's inner root materialised.
                pkg_name = devkit.get("package_name") or ""
                inner = (project_dir / pkg_name) if pkg_name else None
                materialised = bool(inner and inner.exists() and (inner / "SharedFiles").exists())
                hard_fail = (
                    proc.returncode != 0
                    or "Не удалось загрузить" in combined
                    or not materialised
                )
                if not hard_fail and inner is not None:
                    version_note = (
                        f" (marketplace version {real_version} differs from plan {args.version})"
                        if real_version != args.version else ""
                    )
                    return ToolResult(
                        content=(
                            f"pulled {pkg_name} v{real_version} via eco-cli devkit.\n"
                            f"Inner root: {inner.as_posix()}\n"
                            f"Verify with `list_dir('{inner.as_posix()}')` — you "
                            f"should see SharedFiles/ and BuildFiles/.{version_note}"
                        ),
                        details={
                            "inner_root": inner.as_posix(),
                            "argv": cmd,
                            "via": "cli_devkit",
                            "marketplace_version": real_version,
                            "plan_version": args.version,
                        },
                    )
                cli_attempt = {
                    "argv": cmd,
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "materialised": materialised,
                }
            except subprocess.TimeoutExpired:
                cli_attempt = {"argv": cmd, "error": f"timeout after {_CLI_TIMEOUT_S}s"}
            except FileNotFoundError as e:
                cli_attempt = {"argv": cmd, "error": f"eco-cli binary not found: {e}"}
        else:
            cli_attempt = {"error": "find -c CID returned no DEVKIT entry"}

    # ── sdk_root fallback ───────────────────────────────────────────────────
    # Either no CLI configured, or CLI attempt failed. Copy the INNER root
    # from the local sdk_root mirror. This is the only reliable path when
    # the marketplace lacks a Linux build of the requested component.
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
    via = "sdk_root_fallback" if cli_attempt is not None else "sdk_root"
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
            "via": via,
            "cli_attempt": cli_attempt,
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
                     sdk_root: Path | None = None,
                     target_os: str | None = None,
                     target_arch: str | None = None) -> list[EcoTool]:
    return [
        EcoTool(
            name="ecoos_pull",
            description=(
                "Pull an EcoOS SDK component into project_dir. Tries eco-cli "
                "(real marketplace) first; on failure copies from local sdk_root mirror."
            ),
            args_schema=EcoosPullArgs,
            execute=lambda a: _ecoos_pull(
                a, cli_path, project_dir, allowed_components, sdk_root,
                target_os=target_os, target_arch=target_arch,
            ),
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
