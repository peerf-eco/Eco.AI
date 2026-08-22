"""On-demand (Anthropic-style) skill support.

Locks in:

1. Frontmatter parsing: SKILL.md with ``name``/``description`` frontmatter is
   treated as a dynamic skill — description goes into the ON-DEMAND SKILLS
   manifest, the body stays out of the static prompt.
2. Plain ``v<N>.md`` skills keep the classic eager full-text behavior.
3. The read_skill EcoTool resolves bodies from the whitelisted roots only,
   strips frontmatter, supports version pinning, and rejects traversal /
   unknown names with an actionable listing.
4. make_role_agent wires read_skill automatically when a role references a
   dynamic skill (and leaves it out otherwise).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.config.loader import load_config
from agent.context.customization import (
    on_demand_skills,
    resolve_custom_instructions,
    split_frontmatter,
)
from agent.internal.tools.skill_reader import (
    _ReadSkillArgs,
    read_skill,
)
from agent.pi_ai import Model, ModelCost


# ── 1. Frontmatter parsing ───────────────────────────────────────────────────


def test_split_frontmatter_valid():
    meta, body = split_frontmatter(
        "---\nname: x\ndescription: does things\n---\n\nBODY TEXT"
    )
    assert meta == {"name": "x", "description": "does things"}
    assert body == "BODY TEXT"


def test_split_frontmatter_absent():
    meta, body = split_frontmatter("# Just markdown")
    assert meta is None
    assert body == "# Just markdown"


def test_split_frontmatter_requires_description():
    meta, body = split_frontmatter("---\nname: x\n---\nBODY")
    assert meta is None  # no description → not a dynamic skill
    assert body == "BODY"


# ── 2. Resolution: dynamic vs eager ──────────────────────────────────────────


@pytest.fixture()
def skill_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "config" / "skills").mkdir(parents=True)
    return root


def test_dynamic_skill_manifest_not_body(skill_root: Path):
    skill_dir = skill_root / "config" / "skills" / "fancy"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: fancy\ndescription: Builds fanciful widgets\n---\nSECRET BODY MARKER",
        encoding="utf-8",
    )
    text, refs = resolve_custom_instructions(
        project_root=skill_root,
        role="coder",
        language="C",
        skill_versions={"fancy": "1"},
    )
    assert "Builds fanciful widgets" in text
    assert "ON-DEMAND SKILLS" in text
    assert "SECRET BODY MARKER" not in text
    assert len(refs) == 1
    assert refs[0].name == "fancy"


def test_eager_v_file_still_full_text(skill_root: Path):
    skill_dir = skill_root / "config" / "skills" / "plain"
    skill_dir.mkdir(parents=True)
    (skill_dir / "v2.md").write_text("PLAIN BODY MARKER", encoding="utf-8")
    text, refs = resolve_custom_instructions(
        project_root=skill_root,
        role="coder",
        language="C",
        skill_versions={"plain": "2"},
    )
    assert "PLAIN BODY MARKER" in text
    assert refs == []
    assert "ON-DEMAND SKILLS" not in text


def test_workspace_override_of_dynamic_skill(skill_root: Path):
    repo = skill_root / "config" / "skills" / "fancy"
    repo.mkdir(parents=True)
    (repo / "SKILL.md").write_text(
        "---\ndescription: repo desc\n---\nREPO BODY", encoding="utf-8"
    )
    ws = skill_root / ".eco-harness" / "skills" / "fancy"
    ws.mkdir(parents=True)
    (ws / "SKILL.md").write_text(
        "---\ndescription: workspace desc\n---\nWORKSPACE BODY", encoding="utf-8"
    )
    text, refs = resolve_custom_instructions(
        project_root=skill_root,
        role="coder",
        language="C",
        skill_versions={"fancy": "1"},
    )
    assert "workspace desc" in text
    assert "repo desc" not in text
    assert refs[0].path.parent == ws


# ── 3. read_skill tool ───────────────────────────────────────────────────────


def test_read_skill_returns_body_without_frontmatter(tmp_path: Path):
    skill_dir = tmp_path / "config" / "skills" / "comp"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: comp\ndescription: d\n---\nREAL CONTENT", encoding="utf-8"
    )
    result = read_skill(_ReadSkillArgs(name="comp"), project_root=tmp_path)
    assert result.is_error is False
    assert "REAL CONTENT" in result.content
    assert "---" not in result.content.split("\n")[1]


def test_read_skill_version_pinning_prefers_pinned_file(tmp_path: Path):
    skill_dir = tmp_path / "config" / "skills" / "comp"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\ndescription: d\n---\nSKILLMD", encoding="utf-8")
    (skill_dir / "v1.md").write_text("V1BODY", encoding="utf-8")
    result = read_skill(_ReadSkillArgs(name="comp", version="v1"), project_root=tmp_path)
    assert "V1BODY" in result.content


def test_read_skill_rejects_traversal_and_unknown(tmp_path: Path):
    skill_dir = tmp_path / "config" / "skills" / "known"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("x", encoding="utf-8")

    bad = read_skill(_ReadSkillArgs(name="../escape"), project_root=tmp_path)
    assert bad.is_error is True
    assert "invalid skill name" in bad.content

    missing = read_skill(_ReadSkillArgs(name="nope"), project_root=tmp_path)
    assert missing.is_error is True
    assert "Available skills: known" in missing.content


def test_read_skill_cannot_escape_via_symlink_name(tmp_path: Path):
    # Name validation happens before resolution; ensure no root escape path
    # can be constructed from a legal-looking name either.
    outside = tmp_path / "outside.md"
    outside.write_text("SECRET", encoding="utf-8")
    result = read_skill(_ReadSkillArgs(name="outside"), project_root=tmp_path)
    assert result.is_error is True
    assert "SECRET" not in result.content


# ── 4. Automatic tool wiring in make_role_agent ──────────────────────────────


def test_coder_gets_read_skill_for_component_author(tmp_path: Path):
    """Real repo config: coder references the dynamic component_author skill."""
    cfg = load_config()
    model = Model(
        id="scripted", name="scripted", api="faux-scripted",
        provider="scripted", baseUrl="", cost=ModelCost(),
    )
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    agent_obj = _make_coder(cfg, model, project_dir)
    assert "read_skill" in agent_obj.tools
    assert "ON-DEMAND SKILLS" in agent_obj.system_prompt
    assert "component_author" in agent_obj.system_prompt
    # Body must stay out of the static prompt…
    assert "ID COMPONENT TEMPLATE" not in agent_obj.system_prompt
    # …and be retrievable through the tool.
    fetched = agent_obj.tools["read_skill"].execute(
        _ReadSkillArgs(name="component_author")
    )
    assert "ID COMPONENT TEMPLATE" in fetched.content


def test_tester_has_no_read_skill_without_dynamic_skills(tmp_path: Path):
    cfg = load_config()
    model = Model(
        id="scripted", name="scripted", api="faux-scripted",
        provider="scripted", baseUrl="", cost=ModelCost(),
    )
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    agent_obj = _make_role("tester", cfg, model, project_dir)
    assert "read_skill" not in agent_obj.tools
    assert "ON-DEMAND SKILLS" not in agent_obj.system_prompt


def _make_coder(cfg, model, project_dir):
    return _make_role("coder", cfg, model, project_dir)


def _make_role(role, cfg, model, project_dir):
    from eco_harness.roles import make_role_agent

    return make_role_agent(
        role,
        config=cfg,
        model=model,
        cli_path=None,
        project_dir=project_dir,
        make_exe=Path("make"),
        language="C",
        marketplace_cache_root=cfg.root / "marketplace_cache",
        mode="auto",
    )


def test_on_demand_helper_matches_resolution():
    cfg = load_config()
    refs = on_demand_skills(
        project_root=cfg.root,
        skill_versions={"acom_framework": "1", "component_author": "1"},
    )
    assert [r.name for r in refs] == ["component_author"]
