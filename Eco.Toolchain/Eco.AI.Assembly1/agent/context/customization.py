from __future__ import annotations

from pathlib import Path


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def load_custom_instructions(
    *,
    project_root: Path,
    role: str,
    language: str,
    skill_versions: dict[str, str],
) -> str:
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

    skill_roots = [
        project_root / "config" / "skills",
        project_root / ".eco-harness" / "skills",
        project_root / "agent" / "skills",
    ]
    for skill_name, version in sorted(skill_versions.items()):
        version_name = f"v{version}" if not str(version).startswith("v") else str(version)
        found = False
        for root in skill_roots:
            candidates = [
                root / skill_name / f"{version_name}.md",
                root / skill_name / "SKILL.md",
                root / f"{skill_name}.md",
            ]
            for path in candidates:
                content = _read(path)
                if content:
                    sections.append(
                        f"=== SKILL {skill_name} {version_name} ({path.as_posix()}) ===\n"
                        f"{content}",
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
    return "\n\n".join(sections)