"""Tests for CODER node."""
from pathlib import Path
from agent.v6.nodes.coder import coder_node, _build_coder_seed
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


def test_coder_node_happy_writes_file(project_dir):
    state = make_initial_v6_state("calc")
    state["plan_md"] = "# Plan\nWrite EcoMain.c"
    state["project_dir"] = str(project_dir)
    state["downloaded_paths"] = []
    state["retry_count"] = 0

    target = project_dir / "EcoMain.c"
    llm = ScriptedChatModel(script=[
        ai_tool("write_file", {"path": str(target), "content": "int main(){return 0;}"}, "c1"),
        ai_tool("mark_code_done", {"summary_md": "wrote EcoMain.c"}, "c2"),
    ])
    delta = coder_node(state, llm=llm)
    assert delta["phase"] == "building"
    assert "wrote EcoMain.c" in delta["coder_summary_md"]
    assert target.exists()


def test_coder_seed_first_attempt_excludes_feedback():
    state = make_initial_v6_state("x")
    state["plan_md"] = "P"
    state["project_dir"] = "/tmp/p"
    state["retry_count"] = 0
    seed = _build_coder_seed(state)
    assert "retry" not in seed.lower()


def test_coder_seed_retry_includes_build_log():
    state = make_initial_v6_state("x")
    state["plan_md"] = "P"
    state["project_dir"] = "/tmp/p"
    state["retry_count"] = 1
    state["last_failure_origin"] = "builder"
    state["build_log"] = "## Error\nundefined symbol foo"
    seed = _build_coder_seed(state)
    assert "retry" in seed.lower()
    assert "undefined symbol foo" in seed


def test_coder_seed_retry_includes_tester_report():
    state = make_initial_v6_state("x")
    state["plan_md"] = "P"
    state["project_dir"] = "/tmp/p"
    state["retry_count"] = 2
    state["last_failure_origin"] = "tester"
    state["tester_report_md"] = "expected 5, got 8"
    seed = _build_coder_seed(state)
    assert "expected 5, got 8" in seed
