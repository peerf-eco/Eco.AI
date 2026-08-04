"""Tests for entry.py — topology declaration and pipeline assembly."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.internal.entry import V7_EDGES, V7_ENTRY, build_v7_pipeline
from agent.internal.orchestrator import Orchestrator
from agent.internal.tests.conftest import make_scripted_model_pair, ai_tool


# ── 1. Topology shape ──────────────────────────────────────────────────────
def test_topology_entry_is_architect():
    assert V7_ENTRY == "architect"
    assert V7_ENTRY in V7_EDGES


def test_topology_has_three_agents():
    assert set(V7_EDGES.keys()) == {"architect", "coder", "tester"}


def test_topology_forward_path_architect_coder_tester_done():
    """The happy path must traverse architect → coder → tester → done."""
    assert V7_EDGES["architect"]["to_coder"] == "coder"
    assert V7_EDGES["coder"]["to_tester"] == "tester"
    assert V7_EDGES["tester"]["done"] is None  # terminal


def test_topology_has_backward_edges():
    """Backward handoffs are what let the pipeline self-correct without
    bouncing all the way back to a separate retry-router."""
    # Tester can send the artifact back to coder for fixes.
    assert V7_EDGES["tester"]["to_coder"] == "coder"
    # Coder can escalate plan-level problems back to architect.
    assert V7_EDGES["coder"]["to_architect"] == "architect"


def test_topology_every_agent_can_fail_terminally():
    """Honest-failure stop is available from every node."""
    for agent in ("architect", "coder", "tester"):
        assert "fail" in V7_EDGES[agent]
        assert V7_EDGES[agent]["fail"] is None


def test_topology_only_tester_can_declare_done():
    """`done` is the success terminal — only the tester (which evaluates the
    artifact against acceptance criteria) is authorised to call it."""
    assert "done" in V7_EDGES["tester"]
    assert "done" not in V7_EDGES["architect"]
    assert "done" not in V7_EDGES["coder"]


# ── 2. Assembly: build_v7_pipeline returns a valid Orchestrator ───────────
@pytest.fixture
def model():
    m, _stream_fn = make_scripted_model_pair([ai_tool("fail", {"reason": "smoke"}, "c0")])
    return m


def test_build_v7_pipeline_returns_orchestrator(model, project_dir, tmp_path):
    orch = build_v7_pipeline(
        model=model,
        cli_path=tmp_path / "eco-cli.exe",
        project_dir=project_dir,
        make_exe=tmp_path / "make",
    )
    assert isinstance(orch, Orchestrator)
    assert orch.entry == "architect"
    assert orch.max_hops == 8
    assert set(orch.agents.keys()) == {"architect", "coder", "tester"}


def test_build_v7_pipeline_passes_through_max_hops(model, project_dir, tmp_path):
    orch = build_v7_pipeline(
        model=model,
        cli_path=tmp_path / "eco-cli.exe",
        project_dir=project_dir,
        make_exe=tmp_path / "make",
        max_hops=3,
    )
    assert orch.max_hops == 3


def test_build_v7_pipeline_works_without_cli_path(model, project_dir, tmp_path):
    """cli_path can be None — marketplace tools will return is_error, but
    the pipeline still assembles cleanly. Tested separately because of
    the Optional[Path] type."""
    orch = build_v7_pipeline(
        model=model,
        cli_path=None,
        project_dir=project_dir,
        make_exe=tmp_path / "make",
    )
    assert isinstance(orch, Orchestrator)


# ── 3. Topology + agents are wired correctly: every declared edge name
#       matches one of the corresponding agent's stop_tools.
def test_every_topology_edge_matches_an_agent_stop_tool(model, project_dir, tmp_path):
    orch = build_v7_pipeline(
        model=model,
        cli_path=tmp_path / "eco-cli.exe",
        project_dir=project_dir,
        make_exe=tmp_path / "make",
    )
    for agent_name, edges in V7_EDGES.items():
        agent = orch.agents[agent_name]
        for edge_name in edges:
            assert edge_name in agent.stop_tools, (
                f"Topology declares edge {edge_name!r} for agent {agent_name!r}, "
                f"but the agent's stop_tools are {sorted(agent.stop_tools)}. "
                "Topology and agent factory are out of sync."
            )


def test_no_agent_stop_tool_is_an_unknown_topology_edge(model, project_dir, tmp_path):
    """Inverse: every stop-tool the agent might call must have a topology
    entry. Otherwise the orchestrator would surface `unknown_edge` for a
    legitimate-but-undeclared handoff — a silent contract bug."""
    orch = build_v7_pipeline(
        model=model,
        cli_path=tmp_path / "eco-cli.exe",
        project_dir=project_dir,
        make_exe=tmp_path / "make",
    )
    for agent_name, agent in orch.agents.items():
        declared = set(V7_EDGES[agent_name].keys())
        for stop_name in agent.stop_tools:
            assert stop_name in declared, (
                f"Agent {agent_name!r} has stop-tool {stop_name!r} but topology "
                f"declares only {sorted(declared)}. Add the edge to V7_EDGES or "
                "remove the stop-tool from the agent factory."
            )

