"""Tests for TESTER node."""
import subprocess
from pathlib import Path
from agent.v6.nodes.tester import tester_node, _build_tester_seed
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


def test_tester_seed_does_not_include_coder_summary():
    state = make_initial_v6_state("calc")
    state["plan_md"] = "# Plan\n## Acceptance criteria\n- prints 5"
    state["coder_summary_md"] = "I wrote main.c with broken logic"
    state["build_artifact"] = "/tmp/app.exe"
    seed = _build_tester_seed(state)
    assert "broken logic" not in seed
    assert "Acceptance criteria" in seed
    assert "/tmp/app.exe" in seed


def test_tester_node_pass(monkeypatch, project_dir):
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "5", "stderr": ""})())
    state = make_initial_v6_state("calc")
    state["build_artifact"] = str(artifact)
    state["plan_md"] = "# Plan\n## Acceptance criteria\n- prints 5"
    state["retry_count"] = 0
    state["max_retries"] = 3

    llm = ScriptedChatModel(script=[
        ai_tool("run_artifact", {"timeout_s": 5}, "c1"),
        ai_tool("report_test_pass", {"reason_md": "stdout contains 5"}, "c2"),
    ])
    delta = tester_node(state, llm=llm)
    assert delta["phase"] == "done"
    assert delta["last_status"] == "success"


def test_tester_node_fail_returns_to_coding(monkeypatch, project_dir):
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "8", "stderr": ""})())
    state = make_initial_v6_state("calc")
    state["build_artifact"] = str(artifact)
    state["plan_md"] = "# Plan\n## Acceptance criteria\n- prints 5"
    state["retry_count"] = 0
    state["max_retries"] = 3

    llm = ScriptedChatModel(script=[
        ai_tool("run_artifact", {"timeout_s": 5}, "c1"),
        ai_tool("report_test_fail", {"reason_md": "expected 5, got 8"}, "c2"),
    ])
    delta = tester_node(state, llm=llm)
    assert delta["phase"] == "coding"
    assert delta["retry_count"] == 1
    assert delta["last_failure_origin"] == "tester"
    assert "expected 5" in delta["tester_report_md"]
