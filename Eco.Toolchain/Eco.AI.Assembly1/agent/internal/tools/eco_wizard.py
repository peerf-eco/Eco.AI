"""Minimal-output eco-wizard tool for generated project structure."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from agent.internal.eco_agent import EcoTool, ToolResult


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
        description="eco-wizard options such as pn, cp, ut, or ts",
    )
    use_env_framework: bool = Field(
        True,
        description="Use the ECO_FRAMEWORK environment path",
    )


def _resolve_wizard() -> str | None:
    configured = os.getenv("ECO_WIZARD_PATH")
    if configured:
        if Path(configured).is_file():
            return configured
        return None
    for name in ("eco-wizard", "eco-wizard.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


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
    command = [
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
    return ToolResult(
        content=f"eco_wizard created {args.name} ({args.language}/{args.project_type}).",
        details={
            "returncode": process.returncode,
            "stdout_tail": (process.stdout or "")[-1200:],
            "out_dir": str(out_dir),
        },
    )


def make_eco_wizard_tool(project_dir: Path) -> EcoTool:
    return EcoTool(
        name="eco_wizard",
        description=(
            "Generate project or component boilerplate with the locally installed "
            "eco-wizard CLI. Always use this tool instead of writing templates "
            "or generated structure directly. Returns only a minimal structural "
            "summary; details contain a bounded output tail."
        ),
        args_schema=_WizardArgs,
        execute=lambda args: _run_wizard(args, project_dir),
    )
