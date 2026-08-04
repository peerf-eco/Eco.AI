from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CliProfile:
    name: str
    executable: str
    prefix: tuple[str, ...] = ()
    timeout_s: int = 180
    output_limit: int = 8192
    allowed_subcommands: frozenset[str] = field(default_factory=frozenset)


def run_cli(profile: CliProfile, args: list[str], *, cwd: Path | None = None) -> dict:
    if not args or (
        profile.allowed_subcommands and args[0] not in profile.allowed_subcommands
    ):
        raise ValueError(
            f"CLI profile '{profile.name}' rejects subcommand "
            f"{args[0] if args else '(empty)'}"
        )
    executable = shutil.which(profile.executable) or profile.executable
    command = [*profile.prefix, executable, *args]
    try:
        process = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=profile.timeout_s,
            env=os.environ.copy(),
        )
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"CLI '{profile.name}' executable was not found: {profile.executable}"
        ) from error
    output = ((process.stdout or "") + "\n" + (process.stderr or "")).strip()
    return {
        "returncode": process.returncode,
        "output": output[:profile.output_limit],
        "argv": command,
    }