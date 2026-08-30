"""Tests for the three agents — primarily capability gating + tool-set shape.

The single most important rule these tests enforce is: tester has NO
write/edit/build/pull tools in its bound tool list. This is the structural
guarantee against test-fudging, and any change to tester's tool factory
that adds write capability must trip these assertions.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.internal.agents.architect import make_architect, ARCHITECT_SYSTEM_PROMPT
from agent.internal.agents.coder import make_coder, CODER_SYSTEM_PROMPT
from agent.internal.agents.tester import make_tester, TESTER_SYSTEM_PROMPT
from agent.internal.tests.conftest import make_scripted_model_pair, ai_tool


@pytest.fixture
def model():
    """A scripted pi_ai.Model — enough to inspect the agent's bound tool list,
    since these tests never actually invoke `run`."""
    m, _stream_fn = make_scripted_model_pair([ai_tool("fail", {"reason": "smoke"}, "c0")])
    return m


# ── architect ──────────────────────────────────────────────────────────────
def test_architect_has_research_design_pull_handoff_tools(model, project_dir):
    agent = make_architect(model=model, cli_path=Path("eco-cli.exe"),
                           project_dir=project_dir)
    names = set(agent.tools.keys())
    # Research + design + materialization all go through one raw CLI tool.
    assert "eco_cli" in names
    # Read-side inspection of pulled packages
    assert "read_file" in names
    assert "list_dir" in names
    # Handoff + honest failure
    assert "to_coder" in names
    assert "fail" in names


def test_architect_does_NOT_author_code(model, project_dir):
    """The architect plans and pulls; it does NOT write source files."""
    agent = make_architect(model=model, cli_path=Path("eco-cli.exe"),
                           project_dir=project_dir)
    names = set(agent.tools.keys())
    assert "write_file" not in names
    assert "run_build" not in names
    assert "run_artifact" not in names


def test_architect_stop_tools_are_only_handoff_and_fail(model, project_dir):
    agent = make_architect(model=model, cli_path=Path("eco-cli.exe"),
                           project_dir=project_dir)
    assert agent.stop_tools == {"to_coder", "fail"}


def test_architect_prompt_includes_taxonomy_and_trust_model():
    # Sanity-check that critical prompt sections are present — these are
    # what makes the agent portable and injection-resistant.
    assert "Eco SDK identifier taxonomy" in ARCHITECT_SYSTEM_PROMPT
    assert "Framework packages" in ARCHITECT_SYSTEM_PROMPT
    assert "Trust model" in ARCHITECT_SYSTEM_PROMPT
    assert "DATA, not POLICY" in ARCHITECT_SYSTEM_PROMPT
    # Handoff schema must be present so the architect knows the contract.
    assert "Handoff to coder" in ARCHITECT_SYSTEM_PROMPT
    assert "Acceptance criteria" in ARCHITECT_SYSTEM_PROMPT


# ── coder ──────────────────────────────────────────────────────────────────
def test_coder_has_author_build_handoff_tools(model, project_dir, tmp_path):
    agent = make_coder(model=model, project_dir=project_dir, make_exe=tmp_path / "make")
    names = set(agent.tools.keys())
    # Author
    assert "write_file" in names
    assert "read_file" in names
    assert "list_dir" in names
    # Build
    assert "run_build" in names
    # Handoff (forward + backward) + fail
    assert "to_tester" in names
    assert "to_architect" in names
    assert "fail" in names


def test_coder_does_NOT_have_market_or_runtime_tools(model, project_dir, tmp_path):
    """Coder does not pull components (architect did) and does not run the
    artifact (tester does). Capability gating keeps roles clean."""
    agent = make_coder(model=model, project_dir=project_dir, make_exe=tmp_path / "make")
    names = set(agent.tools.keys())
    assert "eco_cli" not in names
    assert "run_artifact" not in names


def test_coder_stop_tools_include_backward_to_architect(model, project_dir, tmp_path):
    # The backward edge is what lets coder escalate when the plan is wrong
    # (vs trying to paper over it).
    agent = make_coder(model=model, project_dir=project_dir, make_exe=tmp_path / "make")
    assert agent.stop_tools == {"to_tester", "to_architect", "fail"}


def test_coder_prompt_includes_taxonomy_and_handoff_schema():
    assert "Eco SDK identifier taxonomy" in CODER_SYSTEM_PROMPT
    assert "Handoff to tester" in CODER_SYSTEM_PROMPT
    assert "Acceptance criteria" in CODER_SYSTEM_PROMPT
    # Explicit anti-pattern guidance: don't pretend a build worked.
    assert "Do NOT pretend the build worked" in CODER_SYSTEM_PROMPT


# ── tester — the load-bearing capability gating tests ─────────────────────
def test_tester_has_run_read_handoff_tools(model, project_dir):
    agent = make_tester(model=model, project_dir=project_dir)
    names = set(agent.tools.keys())
    # Read-only inspection
    assert "read_file" in names
    assert "list_dir" in names
    # Run the compiled artifact
    assert "run_artifact" in names
    # Reporting edges
    assert "to_coder" in names
    assert "done" in names
    assert "fail" in names


def test_tester_CANNOT_modify_anything_structural_check(model, project_dir):
    """LOAD-BEARING: tester must NEVER be given a tool that can mutate state.

    Prompt-level "don't modify" instructions are bypassable; structural
    absence is not. If this test ever fails, the change to tester's
    factory needs a very good reason and a corresponding update to the
    `feedback_tester_honest_stop.md` memory note.
    """
    agent = make_tester(model=model, project_dir=project_dir)
    forbidden = {
        "write_file",          # would let tester rewrite source/tests
        "edit_file",
        "run_build",           # would let tester rebuild after fudging
        "eco_cli",             # would let tester pull/swap components
    }
    agent_tool_names = set(agent.tools.keys())
    intersection = forbidden & agent_tool_names
    assert intersection == set(), (
        f"Tester was bound to forbidden tools {intersection}. "
        "This violates the capability-gating contract that prevents the "
        "test-fudging anti-pattern. See memory/feedback_tester_honest_stop.md."
    )


def test_tester_stop_tools_offer_done_to_coder_fail(model, project_dir):
    agent = make_tester(model=model, project_dir=project_dir)
    assert agent.stop_tools == {"to_coder", "done", "fail"}


def test_tester_prompt_includes_honest_reporting_rules():
    assert "READ-ONLY" in TESTER_SYSTEM_PROMPT
    assert "Honest" in TESTER_SYSTEM_PROMPT or "honest" in TESTER_SYSTEM_PROMPT
    # Specific anti-patterns the tester must avoid
    assert "MUST NOT" in TESTER_SYSTEM_PROMPT
    assert "alter the acceptance criteria" in TESTER_SYSTEM_PROMPT
    assert "skip running the artifact" in TESTER_SYSTEM_PROMPT
    # Prompt injection awareness
    assert "DATA" in TESTER_SYSTEM_PROMPT


# ── cross-agent: edge naming convention ───────────────────────────────────
def test_edge_naming_convention_is_consistent(model, project_dir, tmp_path):
    """Every handoff edge name follows `to_<agent>` or one of {done,fail}.

    The orchestrator routes by `stop_tool_name`; a typo here is a wiring
    bug. The convention also makes flows readable in logs.
    """
    arch  = make_architect(model=model, cli_path=Path("eco-cli.exe"),
                           project_dir=project_dir)
    coder = make_coder(model=model, project_dir=project_dir, make_exe=tmp_path / "make")
    tester = make_tester(model=model, project_dir=project_dir)

    valid = lambda e: (e in {"done", "fail"}) or e.startswith("to_")
    for agent in (arch, coder, tester):
        for e in agent.stop_tools:
            assert valid(e), f"non-conforming edge name: {e!r}"

