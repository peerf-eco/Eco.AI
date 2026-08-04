"""Raw eco-cli passthrough — one tool, full CLI surface.

Replaces the marketplace.py / components.py specialised wrappers. The architect
calls eco_cli(args=[...]) directly:
  marketplace_list  == eco_cli(args=["find", "-p"])
  marketplace_get   == eco_cli(args=["find", "-c", CID])
  pull              == two CLI calls: find then pull, architect threads file_id

Why raw instead of wrappers:
  - Wrappers froze the CLI surface at one moment in time; new subcommands or
    flags required code edits to the architect's tool list.
  - Wrappers reformatted output to compact markdown to save tokens. With raw
    CLI we still truncate big stdout/stderr but keep the original JSON
    structure — the model parses it itself.
  - One tool to maintain across CLI releases instead of three.

What we keep from the old wrappers:
  - ECO_CLI_PATH env: absolute path to the binary (Linux ELF on Linux hosts,
    Windows .exe on Windows hosts; selected once at container start).
  - ECO_CLI_PREFIX env: optional wrapper command (e.g. "wine64" when running
    the .exe under Linux via wine).
  - Subcommand whitelist on the first arg — narrow blast radius if upstream
    adds destructive commands; update the whitelist deliberately, not by LLM.
  - Truncation of large stdout/stderr to bound agent history.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from agent.v6.eco_agent import EcoTool, ToolResult


_TIMEOUT_S = 180
_OUTPUT_TRUNC = 8192

_ALLOWED_SUBCOMMANDS = frozenset({
    "find", "pull", "help", "--help", "version", "--version",
})


class _EcoCliArgs(BaseModel):
    args: list[str] = Field(
        ...,
        description=(
            "Argument list passed to eco-cli (binary path and wine prefix are "
            "injected automatically). Examples: "
            "['find','-p'] to list all marketplace components; "
            "['find','-c','<CID>'] to fetch one component's full profile; "
            "['pull','-c','<CID>','-v','N.N.N.N','-fid=<FID>'] to download a "
            "DEVKIT (file_id comes from a prior 'find' call)."
        ),
    )


def _truncate(text: str, label: str) -> str:
    if len(text) <= _OUTPUT_TRUNC:
        return text
    head = text[: _OUTPUT_TRUNC // 2]
    tail = text[-_OUTPUT_TRUNC // 2:]
    elided = len(text) - _OUTPUT_TRUNC
    return f"{head}\n\n... ({label} truncated, {elided} bytes elided) ...\n\n{tail}"


def _eco_cli(
    args: _EcoCliArgs,
    cli_path: Optional[Path],
    project_dir: Optional[Path],
) -> ToolResult:
    if cli_path is None:
        return ToolResult(
            content="eco_cli: ECO_CLI_PATH unset — no CLI binary configured.",
            is_error=True,
        )

    raw_args = list(args.args)
    if not raw_args:
        return ToolResult(
            content=(
                "eco_cli: args is empty. First arg must be a subcommand from "
                f"{sorted(_ALLOWED_SUBCOMMANDS)}."
            ),
            is_error=True,
        )
    sub = raw_args[0]
    if sub not in _ALLOWED_SUBCOMMANDS:
        return ToolResult(
            content=(
                f"eco_cli: subcommand {sub!r} is not in the whitelist "
                f"{sorted(_ALLOWED_SUBCOMMANDS)}. If you genuinely need it, "
                "ask the operator to extend tools/eco_cli.py:"
                "_ALLOWED_SUBCOMMANDS — do not retry with a different spelling."
            ),
            is_error=True,
        )

    prefix = (
        os.getenv("ECO_CLI_PREFIX")
        or os.getenv("V6_CLI_PREFIX", "")
    ).split()
    cmd = [*prefix, str(cli_path), *raw_args]
    cwd = str(project_dir) if project_dir is not None else None

    try:
        proc = subprocess.run(
            cmd, shell=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=_TIMEOUT_S, cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            content=f"eco_cli {sub} timed out after {_TIMEOUT_S}s.",
            is_error=True,
            details={"argv": cmd, "rc": None, "timed_out": True},
        )
    except FileNotFoundError as e:
        return ToolResult(
            content=f"eco_cli binary not found: {e}",
            is_error=True,
            details={"argv": cmd},
        )

    stdout = _truncate(proc.stdout or "", "stdout")
    stderr = _truncate(proc.stderr or "", "stderr")

    parts = [f"rc: {proc.returncode}"]
    if stdout:
        parts.append("=== stdout ===")
        parts.append(stdout)
    if stderr:
        parts.append("=== stderr ===")
        parts.append(stderr)
    body = "\n".join(parts)

    return ToolResult(
        content=body,
        is_error=proc.returncode != 0,
        details={
            "argv": cmd,
            "rc": proc.returncode,
            "stdout_bytes": len(proc.stdout or ""),
            "stderr_bytes": len(proc.stderr or ""),
        },
    )


def make_eco_cli_tool(
    *,
    cli_path: Optional[Path],
    project_dir: Optional[Path] = None,
) -> EcoTool:
    """Raw eco-cli passthrough. Binary path + wine prefix come from env.

    Args:
        cli_path: ECO_CLI_PATH resolved to a concrete file. None if unset
                  (every call then returns is_error).
        project_dir: cwd for invocations that write artefacts (`pull` writes
                     the DEVKIT archive into cwd). Pass None for read-only
                     callers (find / help / version).
    """
    return EcoTool(
        name="eco_cli",
        description=(
            "Run eco-cli with the given argument list. Binary path (Linux ELF "
            "or Windows .exe under wine) and any wine prefix come from server "
            "env — you only pass the args. Allowed subcommands: find, pull, "
            "help, version. Common patterns: "
            "['find','-p'] lists every marketplace component as a JSON stream; "
            "['find','-c','<CID>'] returns one component's full JSON profile; "
            "['pull','-c','<CID>','-v','<VER>','-fid=<FID>'] downloads its "
            "DEVKIT into project_dir (file_id comes from a prior 'find' call's "
            "versions[].files[] entry with contentType=='DEVKIT'). Returns "
            "raw stdout/stderr/rc — you parse the JSON yourself."
        ),
        args_schema=_EcoCliArgs,
        execute=lambda a: _eco_cli(a, cli_path, project_dir),
    )
