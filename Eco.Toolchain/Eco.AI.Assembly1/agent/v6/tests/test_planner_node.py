"""Tests for planner_node."""
from pathlib import Path

import pytest

from agent.v6.nodes.planner import planner_node, PLANNER_SYSTEM_PROMPT
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


def test_planner_node_writes_plan_md_and_components(tmp_path):
    """Planner agent submits plan, components, and project_name."""
    # SDK with one mock package
    sdk = tmp_path / "sdk"
    sdk.mkdir()
    pkg = sdk / "Eco.Math.C89_DK_v.1.0.1.2"
    (pkg / "SharedFiles").mkdir(parents=True)
    (pkg / "SharedFiles" / "IEcoMath.h").write_text("/*math*/")

    llm = ScriptedChatModel(script=[
        ai_tool("submit_plan", {
            "project_name": "Calc",
            "plan_md": "# Plan\n## Acceptance criteria\n- prints 5",
            "components": [{"cid": "AB"*16, "version": "1.0.1.2", "name": "Eco.Math.C89", "reason": "math"}],
            "acceptance_criteria": ["stdout contains 5"],
        })
    ])
    state = make_initial_v6_state("build a calculator")
    delta = planner_node(state, llm=llm, sdk_root=sdk)
    assert delta["phase"] == "awaiting_approval"
    assert delta["project_name"] == "Calc"
    assert "Acceptance" in delta["plan_md"]
    assert delta["components"][0]["cid"] == "AB" * 16


def test_planner_node_max_iters_escalates(tmp_path):
    """Planner escalates after max_iters without submit_plan."""
    sdk = tmp_path / "sdk"
    sdk.mkdir()
    # LLM keeps calling list_components, never submits
    llm = ScriptedChatModel(script=[
        ai_tool("list_components", {}, f"c{i}") for i in range(40)
    ])
    state = make_initial_v6_state("x")
    delta = planner_node(state, llm=llm, sdk_root=sdk, max_iters=3)
    assert delta["phase"] == "failed_escalated"
    assert delta["last_status"].startswith("planner_")


def test_planner_system_prompt_mentions_acceptance_criteria():
    """System prompt includes key directives."""
    assert "acceptance" in PLANNER_SYSTEM_PROMPT.lower()
    assert "submit_plan" in PLANNER_SYSTEM_PROMPT
