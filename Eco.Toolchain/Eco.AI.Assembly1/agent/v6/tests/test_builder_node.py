"""Tests for BUILDER node — pass/fail routing + retry counter."""
import subprocess
from pathlib import Path

import pytest

from agent.v6.nodes.builder import builder_node
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


def test_builder_node_pass_transitions_to_testing(monkeypatch, project_dir):
    """On successful build (returncode=0), builder calls report_build_pass and routes to testing."""
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
    )
    state = make_initial_v6_state("x")
    state["project_dir"] = str(project_dir)
    state["coder_summary_md"] = "x"
    state["retry_count"] = 0
    state["max_retries"] = 3

    llm = ScriptedChatModel(
        script=[
            ai_tool("run_make", {}, "c1"),
            ai_tool("report_build_pass", {"artifact_path": str(project_dir / "app.exe")}, "c2"),
        ]
    )
    delta = builder_node(
        state,
        llm=llm,
        vcvarsall=Path("C:/vc.bat"),
        make_exe=Path("C:/make.exe"),
    )
    assert delta["phase"] == "testing"
    assert delta["build_artifact"].endswith("app.exe")


def test_builder_node_fail_increments_retry_and_returns_to_coding(monkeypatch, project_dir):
    """On failed build (returncode!=0), builder calls report_build_fail, increments retry, routes to coding."""
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "boom", "stderr": ""})(),
    )
    state = make_initial_v6_state("x")
    state["project_dir"] = str(project_dir)
    state["retry_count"] = 0
    state["max_retries"] = 3

    llm = ScriptedChatModel(
        script=[
            ai_tool("run_make", {}, "c1"),
            ai_tool("report_build_fail", {"error_md": "## Error\nboom"}, "c2"),
        ]
    )
    delta = builder_node(
        state,
        llm=llm,
        vcvarsall=Path("C:/vc.bat"),
        make_exe=Path("C:/make.exe"),
    )
    assert delta["phase"] == "coding"
    assert delta["retry_count"] == 1
    assert delta["last_failure_origin"] == "builder"
    assert "boom" in delta["build_log"]


def test_builder_node_fail_at_max_retries_escalates(monkeypatch, project_dir):
    """On failed build when retry_count reaches max_retries, phase becomes failed_escalated."""
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})(),
    )
    state = make_initial_v6_state("x")
    state["project_dir"] = str(project_dir)
    state["retry_count"] = 2  # one away from max
    state["max_retries"] = 3

    llm = ScriptedChatModel(
        script=[
            ai_tool("run_make", {}, "c1"),
            ai_tool("report_build_fail", {"error_md": "## Err"}, "c2"),
        ]
    )
    delta = builder_node(
        state,
        llm=llm,
        vcvarsall=Path("C:/vc.bat"),
        make_exe=Path("C:/make.exe"),
    )
    assert delta["phase"] == "failed_escalated"
    assert delta["retry_count"] == 3


def test_builder_no_tool_call_sets_failure_origin(project_dir):
    """Builder agent that emits a bare text reply (no tool_calls) must set
    last_failure_origin='builder' so escalate_node can label the cause."""
    from agent.v6.tests.conftest import ai_text

    state = make_initial_v6_state("x")
    state["project_dir"] = str(project_dir)
    state["coder_summary_md"] = "fake summary"

    # First (and only) LLM reply has no tool_calls → status=no_tool_call.
    llm = ScriptedChatModel(script=[ai_text("I don't know what to build")])

    out = builder_node(state, llm=llm, vcvarsall=None, make_exe=None, max_iters=2)
    assert out["phase"] == "failed_escalated"
    assert out["last_failure_origin"] == "builder"
    assert out["last_status"] == "builder_no_tool_call"
