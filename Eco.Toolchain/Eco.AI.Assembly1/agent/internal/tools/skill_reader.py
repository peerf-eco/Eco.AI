"""On-demand skill reader — fetches a single skill body by name.

Companion to the ``ON-DEMAND SKILLS`` manifest that
:mod:`agent.context.customization` injects when a role references a
``SKILL.md`` carrying YAML frontmatter. The manifest deliberately keeps full
bodies out of the static prompt (token cost / KV-cache prefix); this tool is
the internal agent's fetch path. External CLI backends read the manifest's
source paths with their own file tools instead.

Security/containment:

  - lookup is restricted to ``<project_root>/config/skills`` and
    ``<project_root>/.eco-harness/skills``
  - ``name`` must be a single path segment (no separators, no ``..``)
  - the resolved file must live under one of the roots (defense in depth)
  - output is size-capped like every other tool
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from agent.internal.eco_agent import EcoTool, ToolResult
from agent.internal.tools.paths import repo_root

_MAX_BODY_BYTES = 65_536


def _roots(project_root: Path | None) -> list[Path]:
    """Skill roots in override order: .eco-harness/skills → config/skills."""
    base = project_root if project_root is not None else repo_root()
    return [base / ".eco-harness" / "skills", base / "config" / "skills"]


def _candidate_files(skill_dir: Path, name: str, version: str | None) -> list[Path]:
    candidates: list[Path] = [skill_dir / "SKILL.md"]
    if version:
        candidates.insert(0, skill_dir / f"v{version}.md")
        candidates.insert(0, skill_dir / f"{version}.md")
    # Any other versioned body, newest-ish first.
    try:
        versioned = sorted(
            (p for p in skill_dir.glob("v*.md") if p.is_file()),
            key=lambda p: p.name,
            reverse=True,
        )
    except OSError:
        versioned = []
    candidates.extend(versioned)
    candidates.append(skill_dir.parent / f"{name}.md")
    return candidates


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


class _ReadSkillArgs(BaseModel):
    name: str = Field(
        ...,
        description="Skill folder name from the ON-DEMAND SKILLS manifest "
        "(single segment, e.g. 'component_author').",
    )
    version: str | None = Field(
        None,
        description="Optional pinned version such as 'v1' or '1'. Omit to "
        "get the default resolution.",
    )


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text.strip()
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:]).strip()
    return text.strip()


def read_skill(
    args: _ReadSkillArgs,
    *,
    project_root: Path | None = None,
) -> ToolResult:
    name = args.name.strip().strip("/")
    if (
        not name
        or "/" in name
        or "\\" in name
        or ".." in name
        or name in {".", ".."}
    ):
        return ToolResult(
            content=(
                "read_skill: invalid skill name. Pass the folder name exactly "
                "as listed in the ON-DEMAND SKILLS manifest."
            ),
            is_error=True,
        )

    available: list[str] = []
    for root in _roots(project_root):
        try:
            if root.is_dir():
                available.extend(p.name for p in root.iterdir() if p.is_dir())
        except OSError:
            continue

        for candidate in _candidate_files(root / name, name, args.version):
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if not _is_within(resolved, root):
                continue
            raw = resolved.read_text(encoding="utf-8", errors="replace")
            body = _strip_frontmatter(raw)
            encoded = body.encode("utf-8")
            note = ""
            if len(encoded) > _MAX_BODY_BYTES:
                head = encoded[:_MAX_BODY_BYTES].decode("utf-8", errors="ignore")
                body = (
                    f"{head}\n\n... (truncated at {_MAX_BODY_BYTES} bytes; "
                    f"{len(encoded) - _MAX_BODY_BYTES} bytes elided)"
                )
                note = "truncated"
            return ToolResult(
                content=(
                    f"=== SKILL {name} ({resolved.as_posix()}) ===\n{body}"
                ),
                details={
                    "skill": name,
                    "path": resolved.as_posix(),
                    "bytes": len(encoded),
                    "truncated": bool(note),
                },
            )

    listing = ", ".join(sorted(set(available))) or "(no skills installed)"
    return ToolResult(
        content=(
            f"read_skill: no skill named {name!r}. Available skills: "
            f"{listing}. Names come from the ON-DEMAND SKILLS manifest of "
            "this prompt — do not guess others."
        ),
        is_error=True,
    )


def make_read_skill_tool(*, project_root: Path | None = None) -> EcoTool:
    """Fetch one on-demand skill body by name (see module docstring)."""
    return EcoTool(
        name="read_skill",
        description=(
            "Load the full body of one ON-DEMAND skill listed in your system "
            "prompt manifest. Call it only when the task matches that "
            "skill's description; do not call it speculatively. Returns the "
            "markdown body (frontmatter stripped), size-capped."
        ),
        args_schema=_ReadSkillArgs,
        execute=lambda a: read_skill(a, project_root=project_root),
    )
