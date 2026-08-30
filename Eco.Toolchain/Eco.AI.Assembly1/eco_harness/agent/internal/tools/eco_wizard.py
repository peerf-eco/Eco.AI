"""Minimal-output eco-wizard tool for generated project structure."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from eco_harness.agent.internal.eco_agent import EcoTool, ToolResult
from eco_harness.agent.internal.tools.binaries import resolve_binary


class _WizardArgs(BaseModel):
    name: str = Field(..., description="Project or component name")
    project_type: str = Field(
        "APP",
        description="eco-wizard type: APP, LIB, COM, ECOOS, LINUX, or BOOT",
    )
    language: str = Field("C", description="C, CPP, Python, or Java")
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


def _resolve_wizard() -> str | None:
    resolved = resolve_binary("eco-wizard")
    return str(resolved) if resolved else None


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
        # Known wizard bug: CLI flags leak as path components (a literal
        # `--app/...` tree). Everything under a `--`-prefixed component is
        # flagged and excluded from the build-path answers.
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


def _format_tree(files: list[str], limit: int = 40) -> str:
    shown = files[:limit]
    lines = [f"  {rel}" for rel in shown]
    if len(files) > limit:
        lines.append(f"  ... (+{len(files) - limit} more files)")
    return "\n".join(lines)


def _run_wizard(args: _WizardArgs, project_dir: Path) -> ToolResult:
    executable = _resolve_wizard()
    if not executable:
        return ToolResult(
            content=(
                "eco_wizard executable was not found. Install eco-wizard or set "
                "ECO_WIZARD_PATH; scaffold fallback is disabled by default."
            ),
            is_error=True,
        )
    out_dir = (project_dir / args.out_dir).resolve()
    try:
        out_dir.relative_to(project_dir.resolve())
    except ValueError:
        return ToolResult(content="eco_wizard out_dir is outside project_dir.", is_error=True)
    # Support wine prefix for Windows executables on Linux
    prefix = (
        os.getenv("ECO_WIZARD_PREFIX")
        or os.getenv("internal_WIZARD_PREFIX", "")
    ).split()
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
        process = subprocess.run(
            command,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=int(os.getenv("ECO_WIZARD_TIMEOUT_S", "180")),
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content="eco_wizard timed out.", is_error=True)
    except OSError as error:
        return ToolResult(content=f"eco_wizard failed to start: {error}", is_error=True)
    if process.returncode != 0:
        return ToolResult(
            content=f"eco_wizard failed with rc={process.returncode}.",
            details={"stderr": (process.stderr or "")[-1200:]},
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


def make_eco_wizard_tool(project_dir: Path) -> EcoTool:
    return EcoTool(
        name="eco_wizard",
        description=(
            "Generate project or component boilerplate with the locally installed "
            "eco-wizard CLI. Always use this tool instead of writing templates "
            "or generated structure directly. The result lists the exact "
            "generated file tree, the SourceFiles/<Name>.c file containing the "
            "EcoMain entry point (the entry file is named after the project, "
            "NOT EcoMain.c), and the run_build project_subdir — use those "
            "values verbatim; do NOT re-explore the layout with list_dir/glob."
        ),
        args_schema=_WizardArgs,
        execute=lambda args: _run_wizard(args, project_dir),
    )
