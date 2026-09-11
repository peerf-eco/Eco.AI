"""eco-wizard tool for generated project structure — v0.1.3+ JSON contract.

The wrapper speaks the deterministic PRD 7.10 contract (docs/
ECO-WIZARD_CLI_REFERENCE_NEW.md): every subcommand is invoked with ``--json``
and parsed as the manifest-v1 object. Older binaries without the
``json-output`` capability (feature-detected via ``version --json``) fall
back to the legacy text-mode path with the post-generation tree scan.

Result contract (session 8c3431c2 lesson): the result must answer the
coder's next three questions directly — where are the files, which file
holds the EcoMain entry point, and what project_subdir run_build needs.
The v0.1.3+ manifest carries all three (``files``, ``entry_file``,
``build_subdir``), so the scan is only a fallback for legacy binaries.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path, PurePosixPath
from typing import Optional

from pydantic import BaseModel, Field

from eco_harness.agent.internal.eco_agent import EcoTool, ToolResult
from eco_harness.agent.internal.tools.binaries import resolve_binary


class _WizardArgs(BaseModel):
    name: str = Field(..., description="Project or component name")
    project_type: str = Field(
        "APP",
        description=(
            "eco-wizard type: APP (application) or COM (component) generate "
            "complete scaffolds; LIB, ECOOS, LINUX and BOOT are valid input "
            "but policy-rejected by the wizard (exit 5, no templates)"
        ),
    )
    language: str = Field("C", description="C or CPP (the wizard rejects other languages)")
    out_dir: str = Field(".", description="Project-relative output directory")
    options: list[str] = Field(
        default_factory=list,
        description=(
            "Wizard option codes: pn (namespace postfix), cp (connection "
            "points), ai/ao/co (aggregation inner/outer, containment outer), "
            "ut (unit-test project), ts (thread-safe). Add only what the "
            "plan needs."
        ),
    )
    use_env_framework: bool = Field(
        True,
        description="Use the ECO_FRAMEWORK environment path",
    )
    entry: Optional[str] = Field(
        None,
        description="Base name for the generated entry file and identifiers",
    )
    registrations: list[str] = Field(
        default_factory=list,
        description="COM registration identifiers, stored in config.json",
    )
    target: Optional[str] = Field(
        None,
        description=(
            "Target triplet <os/arch/variant>, e.g. linux/x64/gcc_v132; "
            "omit to let the wizard pick the host default"
        ),
    )
    design_docs: bool = Field(
        True,
        description="False skips the localized .fodt design documents",
    )
    if_absent: bool = Field(
        False,
        description=(
            "Create only when the project dir is absent; re-runs exit 0 "
            "with status reused instead of failing"
        ),
    )
    if_exists: Optional[str] = Field(
        None,
        description=(
            "Collision policy when the project dir exists: fail, overwrite "
            "(wizard-owned trees only) or suffix. Default: fail (json mode)"
        ),
    )
    verify: bool = Field(
        True,
        description="Explicitly request the build dry-run (make -n) validation",
    )
    dry_run: bool = Field(
        False,
        description="Plan only; writes nothing and returns the planned tree",
    )


class _ValidateArgs(BaseModel):
    path: str = Field(
        ".",
        description=(
            "Scaffold directory to validate, relative to project_dir — "
            "e.g. the wizard's nested '<Name>/' directory"
        ),
    )


# Manifest-v1 exit codes (docs/ECO-WIZARD_CLI_REFERENCE_NEW.md).
_EXIT_CODE_MEANING: dict[int, str] = {
    0: "ok",
    2: "usage error",
    3: "not-found",
    4: "network/transport",
    5: "policy-denied",
}

_TIMEOUT_ENV = "ECO_WIZARD_TIMEOUT_S"
_PROBE_TTL_S = 300.0
_capability_cache: dict[str, tuple[float, dict | None]] = {}


def _resolve_wizard() -> str | None:
    resolved = resolve_binary("eco-wizard")
    return str(resolved) if resolved else None


def _wizard_prefix() -> list[str]:
    # Support wine prefix for Windows executables on Linux
    return (
        os.getenv("ECO_WIZARD_PREFIX")
        or os.getenv("internal_WIZARD_PREFIX", "")
    ).split()


def _run_subprocess(
    command: list[str],
    *,
    cwd: Path,
    timeout: float,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=timeout,
    )


def _wizard_capabilities(executable: str, prefix: list[str]) -> dict | None:
    """Feature-detect the binary via `version --json` (cached per binary).

    Returns {"version": str, "capabilities": set[str]} for contract-capable
    binaries, or None when the probe fails (old binary without the `version`
    subcommand) — callers then use the legacy text-mode path only for arguments
    that legacy binaries can honor.
    """
    try:
        prefix_key = "\x1f".join(prefix)
        key = f"{executable}:{os.stat(executable).st_mtime_ns}:{prefix_key}"
    except OSError:
        return None
    hit = _capability_cache.get(key)
    now = time.monotonic()
    if hit and now - hit[0] < _PROBE_TTL_S:
        return hit[1]
    try:
        process = _run_subprocess(
            [*prefix, executable, "version", "--json"],
            cwd=Path.cwd(),
            timeout=15.0,
        )
    except (OSError, subprocess.SubprocessError):
        _capability_cache[key] = (time.monotonic(), None)
        return None
    if process.returncode != 0:
        _capability_cache[key] = (time.monotonic(), None)
        return None
    try:
        data = json.loads(process.stdout)
    except ValueError:
        _capability_cache[key] = (time.monotonic(), None)
        return None
    if not isinstance(data, dict):
        _capability_cache[key] = (time.monotonic(), None)
        return None
    caps = data.get("capabilities")
    if not isinstance(caps, list):
        _capability_cache[key] = (time.monotonic(), None)
        return None
    info = {"version": str(data.get("version") or "?"), "capabilities": set(caps)}
    _capability_cache[key] = (now, info)
    return info


def _parse_json_payload(process: subprocess.CompletedProcess) -> dict | None:
    """Parse the single JSON object the wizard emits on stdout."""
    for stream in (process.stdout, process.stderr):
        text = (stream or "").strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _relative_to_harness(project_dir: Path, wizard_project_dir: str | None) -> str | None:
    """Manifest project_dir → path relative to the harness project_dir."""
    if not wizard_project_dir:
        return "."
    if not isinstance(wizard_project_dir, str):
        return None
    try:
        project_root = project_dir.resolve()
        candidate = Path(wizard_project_dir)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        rel = candidate.resolve().relative_to(project_root)
        return rel.as_posix() or "."
    except (ValueError, OSError):
        return None


def _safe_manifest_rel(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path.as_posix()


def _manifest_paths_valid(manifest: dict, rel_project: str) -> bool:
    if rel_project not in ("", ".") and _safe_manifest_rel(rel_project) is None:
        return False
    for key in ("entry_file", "build_subdir", "build_file", "config_file"):
        value = manifest.get(key)
        if value is not None and _safe_manifest_rel(value) is None:
            return False
    files = manifest.get("files")
    if files is None:
        return True
    if not isinstance(files, dict):
        return False
    for key in ("created", "existing", "overwritten"):
        values = files.get(key) or []
        if not isinstance(values, list):
            return False
        if any(_safe_manifest_rel(value) is None for value in values):
            return False
    return True


def _join_rel(base: str, rel: str | None) -> str | None:
    """Join two manifest-relative POSIX paths ('.'-safe)."""
    clean_rel = _safe_manifest_rel(rel)
    if clean_rel is None:
        return None
    if base in ("", "."):
        return clean_rel
    clean_base = _safe_manifest_rel(base)
    if clean_base is None:
        return None
    return str(PurePosixPath(clean_base) / clean_rel)


def _format_tree(files: list[str], limit: int = 40) -> str:
    shown = files[:limit]
    lines = [f"  {rel}" for rel in shown]
    if len(files) > limit:
        lines.append(f"  ... (+{len(files) - limit} more files)")
    return "\n".join(lines)


def _scan_generated_tree(project_dir: Path, out_dir: Path) -> dict:
    """Post-generation scan: what did the wizard actually create?

    Session 8c3431c2 lesson: the old tool result said only
    "eco_wizard created <name> (...)" with no paths, so the coder guessed
    the layout, passed a doubled path to run_build (BUILD FAIL) and burned
    4 extra LLM calls + a 13.9s marketplace-wide glob recovering. The
    result contract now answers the coder's next three questions directly:
    where are the files, which one has the EcoMain entry point, and what
    project_subdir does run_build need.
    """
    rel_root: str = "."
    try:
        rel_root = out_dir.relative_to(project_dir).as_posix() or "."
    except ValueError:
        rel_root = "."

    files: list[str] = []
    entry_candidates: list[str] = []
    makefile_candidates: list[str] = []
    stray_flagged_dirs: list[str] = []
    max_scan = 500

    def _is_stray(path: Path) -> bool:
        # Known wizard bug (pre-0.1.3): CLI flags leak as path components
        # (a literal `--app/...` tree). Everything under a `--`-prefixed
        # component is flagged and excluded from the build-path answers.
        try:
            rel = path.relative_to(project_dir)
        except ValueError:
            return True
        return any(part.startswith("--") for part in rel.parts)

    for path in sorted(out_dir.rglob("*")):
        if len(files) >= max_scan:
            break
        stray = _is_stray(path)
        if path.is_dir():
            if stray and path.name.startswith("--"):
                stray_flagged_dirs.append(
                    path.relative_to(project_dir).as_posix(),
                )
            continue
        try:
            rel = path.relative_to(project_dir).as_posix()
        except ValueError:
            continue
        if not stray:
            files.append(rel)
            if path.suffix.lower() == ".c":
                try:
                    if path.stat().st_size <= 256_000:
                        text = path.read_text(encoding="utf-8", errors="replace")
                        # eco-wizard scaffolds SourceFiles/<Name>.c with the
                        # ACOM EcoMain entry point inside — the file is NOT
                        # named EcoMain.c.
                        if "EcoMain" in text:
                            entry_candidates.append(rel)
                except OSError:
                    pass
            if path.name in ("Makefile", "MakefileExe"):
                makefile_candidates.append(
                    path.parent.relative_to(project_dir).as_posix(),
                )

    # Prefer the shallowest candidates: the top-level build tree wins over
    # anything accidentally nested deeper.
    entry_candidates.sort(key=lambda rel: (rel.count("/"), rel))
    makefile_candidates.sort(key=lambda rel: (rel.count("/"), 0 if rel.endswith("Makefile") else 1, rel))
    entry_file = entry_candidates[0] if entry_candidates else None
    build_subdir = makefile_candidates[0] if makefile_candidates else None

    files.sort(key=lambda rel: (rel.count("/"), rel))
    return {
        "rel_root": rel_root,
        "files": files,
        "entry_file": entry_file,
        "build_subdir": build_subdir,
        "stray_flagged_dirs": stray_flagged_dirs,
    }


def _build_new_command(args: _WizardArgs, out_dir: Path) -> list[str]:
    command = [
        "new",
        "--out",
        str(out_dir),
        "--name",
        args.name,
        "--type",
        args.project_type,
        "--lang",
        args.language,
    ]
    if args.use_env_framework:
        command.extend(["--env", "true"])
    if args.options:
        command.extend(["--opt", ",".join(args.options)])
    if args.entry:
        command.extend(["--entry", args.entry])
    if args.registrations:
        command.extend(["--registrations", ",".join(args.registrations)])
    if args.target:
        command.extend(["--target", args.target])
    if not args.design_docs:
        command.append("--no-design-docs")
    if args.if_absent:
        command.append("--if-absent")
    if args.if_exists:
        command.extend(["--if-exists", args.if_exists])
    if args.verify:
        command.append("--verify")
    if args.dry_run:
        command.append("--dry-run")
    return command


def _format_manifest_content(
    args: _WizardArgs,
    manifest: dict,
    rel_project: str,
) -> str:
    status = str(manifest.get("status") or "created")
    created = manifest.get("files") or {}
    file_list: list[str] = list(created.get("created") or [])
    if not file_list:
        file_list = list(created.get("existing") or [])
    # Rebase manifest-relative paths onto the harness project_dir so the
    # coder can use them verbatim with read/write/run_build.
    rebased = [
        joined
        for rel in file_list
        if (joined := _join_rel(rel_project, rel)) is not None
    ]
    entry_rel = _join_rel(rel_project, manifest.get("entry_file"))
    build_subdir_rel = _join_rel(rel_project, manifest.get("build_subdir"))

    lines = [
        f"eco_wizard {status} {args.name} ({args.language}/{args.project_type}) "
        f"— wizard v{manifest.get('wizard_version', '?')}, manifest v1.",
        f"project_dir: '{rel_project}' (relative to project_dir).",
    ]
    if status == "reused":
        lines.append(
            "The project already existed and was left untouched (--if-absent); "
            "adapt the existing files, do not regenerate.",
        )
    elif args.dry_run:
        lines.append(
            "DRY-RUN: nothing was written to disk; the file list below is the "
            "planned tree. Re-invoke without dry_run to materialize it.",
        )
    else:
        lines.append(
            "v0.1.3+ scaffolds INTO '<out_dir>/<Name>/' — a nested directory "
            "(older wizards wrote directly into out_dir).",
        )
    lines.extend([
        "",
        f"Generated files ({len(rebased)}):",
        _format_tree(sorted(rebased)),
        "",
    ])
    if entry_rel:
        lines.extend([
            f"EcoMain entry point: {entry_rel}",
            "(eco-wizard names the entry file SourceFiles/<Name>.c, NOT "
            "EcoMain.c — the file contains int16_t EcoMain(IEcoUnknown*). "
            "Open exactly this file to fill the plan's business logic.)",
        ])
    if build_subdir_rel:
        lines.extend([
            "",
            f"run_build project_subdir: '{build_subdir_rel}'",
            "(pass exactly this value to run_build — it already includes the "
            "nested project directory; do not prefix it again).",
        ])
    build_argv = manifest.get("build_command_argv")
    if isinstance(build_argv, list) and build_argv:
        lines.append(f"Build command (reference): {' '.join(map(str, build_argv))}")
    validation = manifest.get("validation") or {}
    warnings = [str(w) for w in (manifest.get("warnings") or [])]
    warnings += [str(w) for w in (validation.get("warnings") or [])]
    lines.extend([
        "",
        "Validation: "
        f"files_exist={validation.get('files_exist')} "
        f"build_dry_run={validation.get('build_dry_run')}",
    ])
    if warnings:
        lines.append("Warnings: " + "; ".join(warnings))
    collision = manifest.get("collision") or {}
    if collision.get("detected"):
        lines.append(
            f"Collision: policy={collision.get('policy')} "
            f"action={collision.get('action')}.",
        )
    return "\n".join(lines)


def _format_wizard_error(
    process: subprocess.CompletedProcess,
    payload: dict | None,
) -> str:
    if payload is not None and payload.get("error"):
        rc = payload.get("exit_code", process.returncode)
        meaning = _EXIT_CODE_MEANING.get(rc, "failure")
        lines = [
            f"eco_wizard failed (rc={rc}, {meaning}): "
            f"{payload.get('code', 'ERROR')} — {payload.get('error')}",
        ]
        hint = payload.get("hint")
        if hint:
            lines.append(f"hint: {hint}")
        return "\n".join(lines)
    meaning = _EXIT_CODE_MEANING.get(process.returncode, "failure")
    lines = [f"eco_wizard failed with rc={process.returncode} ({meaning})."]
    stderr_tail = (process.stderr or "").strip()
    if stderr_tail:
        lines.append(stderr_tail[-1200:])
    return "\n".join(lines)


def _run_wizard_new(
    args: _WizardArgs,
    project_dir: Path,
    executable: str,
    wizard_version: str,
) -> ToolResult:
    out_dir = (project_dir / args.out_dir).resolve()
    try:
        out_dir.relative_to(project_dir.resolve())
    except ValueError:
        return ToolResult(content="eco_wizard out_dir is outside project_dir.", is_error=True)
    command = [
        *_wizard_prefix(),
        executable,
        *_build_new_command(args, out_dir),
        "--json",
    ]
    try:
        process = _run_subprocess(
            command,
            cwd=project_dir,
            timeout=float(int(os.getenv(_TIMEOUT_ENV, "180"))),
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content="eco_wizard timed out.", is_error=True)
    except OSError as error:
        return ToolResult(content=f"eco_wizard failed to start: {error}", is_error=True)
    payload = _parse_json_payload(process)
    if process.returncode != 0:
        return ToolResult(
            content=_format_wizard_error(process, payload),
            details={
                "returncode": process.returncode,
                "code": (payload or {}).get("code"),
                "exit_code": (payload or {}).get("exit_code", process.returncode),
                "hint": (payload or {}).get("hint"),
                "stderr_tail": (process.stderr or "")[-1200:],
            },
            is_error=True,
        )
    if payload is None:
        return ToolResult(
            content=(
                "eco_wizard returned rc=0 without a parseable JSON manifest; "
                "generation was not retried because it may already have completed."
            ),
            details={
                "returncode": process.returncode,
                "stderr_tail": (process.stderr or "")[-1200:],
            },
            is_error=True,
        )
    if payload.get("error"):
        return ToolResult(
            content=_format_wizard_error(process, payload),
            details={"returncode": process.returncode, "payload": payload},
            is_error=True,
        )
    rel_project = _relative_to_harness(project_dir, payload.get("project_dir"))
    if rel_project is None:
        return ToolResult(
            content="eco_wizard returned a project_dir outside project_dir.",
            details={"returncode": process.returncode, "manifest": payload},
            is_error=True,
        )
    if not _manifest_paths_valid(payload, rel_project):
        return ToolResult(
            content="eco_wizard returned unsafe project-relative manifest paths.",
            details={"returncode": process.returncode, "manifest": payload},
            is_error=True,
        )
    scan_fallback = None
    if not payload.get("entry_file") and not args.dry_run:
        # Manifest missing the entry answer (unexpected): recover from disk.
        wizard_tree = (project_dir / rel_project) if rel_project not in ("", ".") else project_dir
        if wizard_tree.is_dir():
            scan_fallback = _scan_generated_tree(project_dir, wizard_tree)
    content = _format_manifest_content(args, payload, rel_project)
    if scan_fallback and scan_fallback.get("entry_file"):
        content += (
            "\n(manifest did not name the entry file; disk scan found: "
            f"{scan_fallback['entry_file']})"
        )
    return ToolResult(
        content=content,
        details={
            "returncode": process.returncode,
            "wizard_version": wizard_version,
            "manifest": payload,
            "project_dir_rel": rel_project,
            "out_dir": str(out_dir),
            "entry_file": _join_rel(rel_project, payload.get("entry_file")),
            "build_subdir": _join_rel(rel_project, payload.get("build_subdir")),
        },
    )


def _run_wizard_legacy(
    args: _WizardArgs,
    project_dir: Path,
    executable: str,
    note: str = "legacy wizard (no JSON contract)",
) -> ToolResult:
    """Pre-0.1.3 binary: text mode + post-generation tree scan."""
    out_dir = (project_dir / args.out_dir).resolve()
    try:
        out_dir.relative_to(project_dir.resolve())
    except ValueError:
        return ToolResult(content="eco_wizard out_dir is outside project_dir.", is_error=True)
    prefix = _wizard_prefix()
    command = [
        *prefix,
        executable,
        "new",
        "--out",
        str(out_dir),
        "--name",
        args.name,
        "--type",
        args.project_type,
        "--lang",
        args.language,
    ]
    if args.use_env_framework:
        command.extend(["--env", "true"])
    if args.options:
        command.extend(["--opt", ",".join(args.options)])
    try:
        process = _run_subprocess(
            command,
            cwd=project_dir,
            timeout=float(int(os.getenv(_TIMEOUT_ENV, "180"))),
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content="eco_wizard timed out.", is_error=True)
    except OSError as error:
        return ToolResult(content=f"eco_wizard failed to start: {error}", is_error=True)
    if process.returncode != 0:
        return ToolResult(
            content=_format_wizard_error(process, _parse_json_payload(process)),
            details={"returncode": process.returncode, "stderr": (process.stderr or "")[-1200:]},
            is_error=True,
        )
    scan = _scan_generated_tree(project_dir, out_dir)
    # Fallback: when the flag-leak bug swallowed the WHOLE output (no
    # clean files at all), report the stray-tree files anyway — the coder
    # still needs the real paths to work with.
    reported_files = scan["files"]
    if not reported_files and scan["stray_flagged_dirs"]:
        for path in sorted(out_dir.rglob("*")):
            if path.is_file():
                try:
                    reported_files = reported_files + [
                        path.relative_to(project_dir).as_posix(),
                    ]
                except ValueError:
                    pass
    summary_lines = [
        f"eco_wizard created {args.name} ({args.language}/{args.project_type}).",
        f"out_dir: '{scan['rel_root']}' (relative to project_dir — the "
        f"wizard scaffolds INTO this dir; it does not create a nested "
        f"'{args.name}/' subdirectory).",
        f"({note})",
        "",
        "Generated files:",
        _format_tree(reported_files),
        "",
    ]
    if scan["entry_file"]:
        summary_lines.extend([
            f"EcoMain entry point: {scan['entry_file']}",
            "(eco-wizard names the entry file SourceFiles/<Name>.c, NOT "
            "EcoMain.c — the file contains int16_t EcoMain(IEcoUnknown*). "
            "Open exactly this file to fill the plan's business logic.)",
        ])
    else:
        summary_lines.append(
            "EcoMain entry point: no .c file containing EcoMain was found "
            "under the generated tree — check SourceFiles/ manually.",
        )
    if scan["build_subdir"]:
        summary_lines.extend([
            "",
            f"run_build project_subdir: '{scan['build_subdir']}'",
            "(pass exactly this value to run_build — do not prefix it with "
            "the project name).",
        ])
    if scan["stray_flagged_dirs"]:
        summary_lines.extend([
            "",
            "WARNING: the wizard created stray directory artifact(s) whose "
            "names look like CLI flags (known wizard bug): "
            + ", ".join(scan["stray_flagged_dirs"]),
            "Ignore them; they are not part of the build path.",
        ])
    return ToolResult(
        content="\n".join(summary_lines),
        details={
            "returncode": process.returncode,
            "stdout_tail": (process.stdout or "")[-1200:],
            "out_dir": str(out_dir),
            "entry_file": scan["entry_file"],
            "build_subdir": scan["build_subdir"],
            "files": scan["files"],
            "stray_flagged_dirs": scan["stray_flagged_dirs"],
        },
    )


def _legacy_unsupported_args(args: _WizardArgs) -> list[str]:
    unsupported: list[str] = []
    if args.entry:
        unsupported.append("entry")
    if args.registrations:
        unsupported.append("registrations")
    if args.target:
        unsupported.append("target")
    if not args.design_docs:
        unsupported.append("design_docs")
    if args.if_absent:
        unsupported.append("if_absent")
    if args.if_exists:
        unsupported.append("if_exists")
    if args.dry_run:
        unsupported.append("dry_run")
    return unsupported


def _run_wizard(args: _WizardArgs, project_dir: Path) -> ToolResult:
    executable = _resolve_wizard()
    if not executable:
        return ToolResult(
            content=(
                "eco_wizard executable was not found. Install eco-wizard or set "
                "ECO_WIZARD (legacy ECO_WIZARD_PATH still works); scaffold "
                "fallback is disabled by default."
            ),
            is_error=True,
        )
    language = args.language.strip().upper()
    if language not in ("C", "CPP"):
        return ToolResult(
            content=(
                f"eco_wizard does not support language '{args.language}'. Only "
                "C and CPP generate scaffolds; for other languages follow the "
                "task spec directly instead of calling this tool."
            ),
            is_error=True,
        )
    args = args.model_copy(update={"language": language})
    if args.use_env_framework:
        framework = (os.getenv("ECO_FRAMEWORK") or "").strip()
        if not framework:
            return ToolResult(
                content=(
                    "eco_wizard: use_env_framework=true requires ECO_FRAMEWORK "
                    "to be set to the framework root directory (wizard exits 3 "
                    "ENV_NOT_SET). Set it or pass use_env_framework=false."
                ),
                is_error=True,
            )
        if not Path(framework).is_dir():
            return ToolResult(
                content=(
                    f"eco_wizard: ECO_FRAMEWORK points at a missing directory "
                    f"({framework}). Fix it or pass use_env_framework=false."
                ),
                is_error=True,
            )
    capabilities = _wizard_capabilities(executable, _wizard_prefix())
    if capabilities and (
        "json-output" in capabilities["capabilities"]
        and "manifest-v1" in capabilities["capabilities"]
    ):
        return _run_wizard_new(args, project_dir, executable, capabilities["version"])
    unsupported = _legacy_unsupported_args(args)
    if unsupported:
        return ToolResult(
            content=(
                "eco_wizard legacy binary cannot honor these arguments: "
                + ", ".join(unsupported)
                + ". Install eco-wizard v0.1.3+ for the JSON contract."
            ),
            details={"unsupported": unsupported},
            is_error=True,
        )
    return _run_wizard_legacy(args, project_dir, executable)


def _run_validate(args: _ValidateArgs, project_dir: Path) -> ToolResult:
    executable = _resolve_wizard()
    if not executable:
        return ToolResult(
            content=(
                "eco_wizard executable was not found. Install eco-wizard or set "
                "ECO_WIZARD (legacy ECO_WIZARD_PATH still works)."
            ),
            is_error=True,
        )
    target = (project_dir / args.path).resolve()
    try:
        target.relative_to(project_dir.resolve())
    except ValueError:
        return ToolResult(content="eco_wizard_validate path is outside project_dir.", is_error=True)
    command = [*_wizard_prefix(), executable, "validate", str(target), "--json"]
    try:
        process = _run_subprocess(
            command,
            cwd=project_dir,
            timeout=float(int(os.getenv(_TIMEOUT_ENV, "60"))),
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content="eco_wizard validate timed out.", is_error=True)
    except OSError as error:
        return ToolResult(content=f"eco_wizard failed to start: {error}", is_error=True)
    payload = _parse_json_payload(process)
    if payload is None:
        return ToolResult(
            content=(
                "eco_wizard validate returned no parseable JSON payload; "
                "validation cannot be treated as successful."
            ),
            details={"returncode": process.returncode, "stderr": (process.stderr or "")[-1200:]},
            is_error=True,
        )
    findings = payload.get("findings")
    if payload.get("error") or not isinstance(payload.get("ok"), bool) or not isinstance(findings, list):
        return ToolResult(
            content=_format_wizard_error(process, payload),
            details={"returncode": process.returncode, "payload": payload},
            is_error=True,
        )
    if process.returncode not in (0, 3):
        return ToolResult(
            content=_format_wizard_error(process, payload),
            details={"returncode": process.returncode, "payload": payload},
            is_error=True,
        )
    if any(not isinstance(finding, dict) for finding in findings):
        return ToolResult(
            content="eco_wizard validate returned malformed findings.",
            details={"returncode": process.returncode, "payload": payload},
            is_error=True,
        )
    errors = [f for f in findings if f.get("severity") == "error"]
    warnings = [f for f in findings if f.get("severity") != "error"]
    lines = [
        (
            f"eco_wizard_validate: OK — '{args.path}' passes the scaffold "
            "checks (0 errors)."
            if not errors
            else f"eco_wizard_validate: {len(errors)} error finding(s) in "
            f"'{args.path}' (rc={process.returncode}, not-found):"
        ),
    ]
    for finding in (errors + warnings)[:20]:
        prefix = "ERROR" if finding.get("severity") == "error" else "warn"
        lines.append(f"  [{prefix}] {finding.get('code')}: {finding.get('message')}")
    if errors:
        lines.append(
            "Fix the listed files (or regenerate with eco_wizard) — the "
            "scaffold will not build cleanly until these are resolved.",
        )
    return ToolResult(
        content="\n".join(lines),
        details={"returncode": process.returncode, "payload": payload},
        is_error=bool(errors),
    )


def make_eco_wizard_tool(project_dir: Path) -> EcoTool:
    return EcoTool(
        name="eco_wizard",
        description=(
            "Generate project or component boilerplate with the locally installed "
            "eco-wizard CLI (v0.1.3+ JSON manifest contract). Always use this tool "
            "instead of writing templates or generated structure directly. The "
            "result carries the manifest: the nested project_dir "
            "(<out_dir>/<Name>/), the exact generated file list, the "
            "SourceFiles/<Name>.c file containing the EcoMain entry point (the "
            "entry file is named after the project, NOT EcoMain.c), and the "
            "run_build project_subdir — use those values verbatim; do NOT "
            "re-explore the layout with list_dir/glob."
        ),
        args_schema=_WizardArgs,
        execute=lambda args: _run_wizard(args, project_dir),
    )


def make_eco_wizard_validate_tool(project_dir: Path) -> EcoTool:
    return EcoTool(
        name="eco_wizard_validate",
        description=(
            "Validate a generated project scaffold with the eco-wizard CLI "
            "(config.json, required directories, entry file, build files, "
            "Makefile source references, workspace files). Run it after "
            "editing or deleting generated files (e.g. before the first "
            "run_build) to catch a broken scaffold early. Exit 3 findings "
            "are reported as tool errors."
        ),
        args_schema=_ValidateArgs,
        execute=lambda args: _run_validate(args, project_dir),
    )
