"""Workspace + skill instruction resolution for role system prompts.

Three eager layers are concatenated (repo root AGENTS.md, role AGENTS.md
layers, selected skill bodies, language skill) exactly as before. On top of
that this module now understands **on-demand (Anthropic-style) skills**:

A ``SKILL.md`` whose body starts with a YAML frontmatter block
(``---`` … ``---`` with at least a ``description:`` key) is NOT injected as
full text. Instead its one-line description is collected into an
``ON-DEMAND SKILLS`` manifest that is appended to the instructions; the agent
fetches the full body only when relevant:

  - internal backends: via the ``read_skill`` EcoTool
    (:mod:`agent.internal.tools.skill_reader`), wired automatically by
    :mod:`eco_harness.roles` whenever the manifest is non-empty;
  - external CLI backends: they have no tool API, so each manifest entry also
    carries the source file path for their own file tools.

Plain ``v<N>.md`` files and frontmatter-less ``SKILL.md`` files keep the
classic eager behavior unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SkillRef:
    """One on-demand skill discovered during resolution."""

    name: str
    description: str
    path: Path  # absolute; shown to external CLIs, resolved by read_skill


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Split a leading ``---`` YAML frontmatter block from ``text``.

    Returns ``(meta_dict_or_None, body)``. A block without at least a
    string ``description`` is reported as ``None`` (treated as no
    frontmatter) while still returning the stripped body.
    """
    if not text.startswith("---"):
        return None, text
    lines = text.splitlines()
    try:
        close = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None, text
    block = "\n".join(lines[1:close])
    body = "\n".join(lines[close + 1:]).strip()
    try:
        meta = yaml.safe_load(block)
    except yaml.YAMLError:
        return None, body
    if not isinstance(meta, dict):
        return None, body
    if not isinstance(meta.get("description"), str) or not meta["description"].strip():
        return None, body
    return meta, body


def _skill_candidates(root: Path, skill_name: str, version_name: str) -> list[Path]:
    return [
        root / skill_name / f"{version_name}.md",
        root / skill_name / "SKILL.md",
        root / f"{skill_name}.md",
    ]


def _resolve_skill(
    project_root: Path,
    skill_name: str,
    version_name: str,
) -> Path | None:
    """Winning candidate across roots: .eco-harness/skills → config/skills.

    Workspace overrides repo (harness-wide precedence: environment >
    workspace > config). The historical order was inverted — a same-name
    workspace skill never actually won; fixed alongside the on-demand work.
    """
    skill_roots = [
        project_root / ".eco-harness" / "skills",
        project_root / "config" / "skills",
    ]
    for root in skill_roots:
        for path in _skill_candidates(root, skill_name, version_name):
            content = _read(path)
            if content:
                return path
    return None


def on_demand_skills(
    *,
    project_root: Path,
    skill_versions: dict[str, str],
) -> list[SkillRef]:
    """Which entries of ``skill_versions`` resolve to dynamic SKILL.md files."""
    refs: list[SkillRef] = []
    for skill_name, version in sorted(skill_versions.items()):
        version_name = f"v{version}" if not str(version).startswith("v") else str(version)
        path = _resolve_skill(project_root, skill_name, version_name)
        if path is None or path.name != "SKILL.md":
            continue
        meta, _body = split_frontmatter(_read(path))
        if meta is None:
            continue
        name = meta.get("name") if isinstance(meta.get("name"), str) else skill_name
        description = " ".join(meta["description"].split())
        refs.append(SkillRef(name=name, description=description, path=path))
    return refs


def _manifest_section(refs: list[SkillRef]) -> str:
    lines = [
        "=== ON-DEMAND SKILLS ===",
        "Full bodies are NOT loaded. When a task matches a description, fetch it:",
        "- internal agent tool: call read_skill with args {\"name\": \"<skill>\"}",
        "- external CLI agents: read the listed file yourself",
        "Do not fetch skills whose descriptions do not match the task.",
        "",
    ]
    for ref in refs:
        lines.append(
            f"- {ref.name}: {ref.description}\n"
            f"  source: {ref.path.as_posix()}"
        )
    return "\n".join(lines)


def resolve_custom_instructions(
    *,
    project_root: Path,
    role: str,
    language: str,
    skill_versions: dict[str, str],
) -> tuple[str, list[SkillRef]]:
    """Resolve AGENTS.md layers + skills. Returns (text, on_demand_refs).

    Eager layers are joined into ``text``; on-demand skills appear only as
    manifest entries appended to ``text`` and are returned in
    ``on_demand_refs`` so callers can wire the ``read_skill`` tool.
    """
    sections: list[str] = []
    candidates = [
        project_root / "AGENTS.md",
        project_root / "config" / "agents" / role / "AGENTS.md",
        project_root / ".eco-harness" / "agents" / role / "AGENTS.md",
    ]
    for path in candidates:
        content = _read(path)
        if content:
            sections.append(f"=== AGENTS.md: {path.as_posix()} ===\n{content}")

    # Workspace overrides repo (see _resolve_skill). The legacy `agent/skills`
    # root was retired in PRD_2 Phase 2
    # (agent/skills/c.md → config/skills/component_author/SKILL.md).
    skill_roots = [
        project_root / ".eco-harness" / "skills",
        project_root / "config" / "skills",
    ]
    dynamic: list[SkillRef] = []
    for skill_name, version in sorted(skill_versions.items()):
        version_name = f"v{version}" if not str(version).startswith("v") else str(version)
        found = False
        for root in skill_roots:
            for path in _skill_candidates(root, skill_name, version_name):
                raw = _read(path)
                if not raw:
                    continue
                if path.name == "SKILL.md":
                    meta, body = split_frontmatter(raw)
                    if meta is not None:
                        name = (
                            meta["name"]
                            if isinstance(meta.get("name"), str)
                            else skill_name
                        )
                        dynamic.append(
                            SkillRef(
                                name=name,
                                description=" ".join(meta["description"].split()),
                                path=path,
                            )
                        )
                        found = True
                        break
                    # Frontmatter-less SKILL.md stays eager (legacy form).
                sections.append(
                    f"=== SKILL {skill_name} {version_name} ({path.as_posix()}) ===\n"
                    f"{raw}",
                )
                found = True
                break
            if found:
                break

    language_path = project_root / "config" / "skills" / "languages" / f"{language}.md"
    language_content = _read(language_path)
    if language_content:
        sections.append(
            f"=== LANGUAGE SKILL {language} ({language_path.as_posix()}) ===\n"
            f"{language_content}",
        )

    if dynamic:
        sections.append(_manifest_section(dynamic))
    return "\n\n".join(sections), dynamic


def load_custom_instructions(
    *,
    project_root: Path,
    role: str,
    language: str,
    skill_versions: dict[str, str],
) -> str:
    """Backward-compatible wrapper returning only the text part."""
    text, _refs = resolve_custom_instructions(
        project_root=project_root,
        role=role,
        language=language,
        skill_versions=skill_versions,
    )
    return text
