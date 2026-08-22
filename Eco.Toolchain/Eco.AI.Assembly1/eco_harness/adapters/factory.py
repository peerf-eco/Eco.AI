from __future__ import annotations

from pathlib import Path

import yaml

from agent.internal.tools.binaries import resolve_binary
from eco_harness.adapters.external_cli import ExternalCliBackend


def _load_external_agent_config(name: str) -> dict:
    """config/agents/external/<name>.yaml: executable, flag, supports_tools.

    These files were dead config until PRD_2 Phase 2 wired the ``flag`` and
    ``executable`` keys into ExternalCliBackend. Missing file → empty dict.
    """
    path = Path(__file__).resolve().parents[2] / "config" / "agents" / "external" / f"{name}.yaml"
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError:
        return {}
    return value if isinstance(value, dict) else {}


def make_external_backend(
    name: str,
    *,
    cwd: Path | None = None,
    timeout_s: int = 900,
):
    agent_config = _load_external_agent_config(name)
    resolved = resolve_binary(
        name,
        explicit=agent_config.get("executable") if agent_config.get("executable") else None,
    )
    return ExternalCliBackend(
        name,
        executable=str(resolved) if resolved else (agent_config.get("executable") or name),
        flag=agent_config.get("flag"),
        cwd=cwd,
        timeout_s=timeout_s,
    )
