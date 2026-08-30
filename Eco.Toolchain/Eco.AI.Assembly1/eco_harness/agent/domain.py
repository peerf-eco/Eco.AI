from __future__ import annotations

from pathlib import Path


def load_acom_domain(root: Path | None = None) -> str:
    project_root = (root or Path(__file__).resolve().parent.parent).resolve()
    path = project_root / "config" / "prompts" / "acom_domain.md"
    return path.read_text(encoding="utf-8")


def load_tool_contract(root: Path | None = None) -> str:
    project_root = (root or Path(__file__).resolve().parent.parent).resolve()
    path = project_root / "config" / "prompts" / "tool_contract.md"
    return path.read_text(encoding="utf-8")