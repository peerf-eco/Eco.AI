from __future__ import annotations

import os
from pathlib import Path

from eco_harness.adapters.external_cli import ExternalCliBackend


def make_external_backend(name: str, *, cwd: Path | None = None, timeout_s: int = 900):
    env_path = os.getenv(f"ECO_{name.upper()}_PATH")
    return ExternalCliBackend(name, executable=env_path or name, cwd=cwd, timeout_s=timeout_s)