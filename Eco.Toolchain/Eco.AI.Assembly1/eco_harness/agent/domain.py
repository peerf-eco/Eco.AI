from __future__ import annotations

from pathlib import Path

from eco_harness.agent.internal.tools.paths import config_dir


def load_acom_domain(root: Path | None = None) -> str:
    path = config_dir(root) / "prompts" / "acom_domain.md"
    return path.read_text(encoding="utf-8")


def load_tool_contract(root: Path | None = None) -> str:
    path = config_dir(root) / "prompts" / "tool_contract.md"
    return path.read_text(encoding="utf-8")
