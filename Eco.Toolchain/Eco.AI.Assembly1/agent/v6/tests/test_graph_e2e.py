"""End-to-end graph tests with ScriptedChatModel + mocked subprocess.

These tests verify the FULL flow through the LangGraph compiled graph:
- happy path
- user rejects plan
- build fail -> retry -> success
- max retries -> escalate -> continue -> success
- max retries -> escalate -> abort
"""
from __future__ import annotations
import subprocess
from pathlib import Path
import pytest
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from agent.v6.graph import create_v6_graph
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool

# Valid 32-char uppercase hex CID (ecoos_pull validates [0-9A-F]{32})
_CID = "A" * 32


@pytest.fixture
def sdk_root(tmp_path):
    root = tmp_path / "sdk"
    pkg = root / "Eco.X_DK_v.1.0.1.2" / "SharedFiles"
    pkg.mkdir(parents=True)
    (pkg / "IEcoX.h").write_text("/*x*/")
    return root


@pytest.fixture
def fake_paths(tmp_path):
    cli = tmp_path / "eco-cli.exe"; cli.write_text("")
    vc  = tmp_path / "vcvarsall.bat"; vc.write_text("")
    mk  = tmp_path / "make.exe"; mk.write_text("")
    return {"cli_path": cli, "vcvarsall": vc, "make_exe": mk}


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Default: every subprocess.run succeeds. Tests can override via the dict."""
    state = {"runs": []}
    def fake_run(cmd, **kw):
        state["runs"].append(cmd)
        class R: returncode = 0; stdout = "ok"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    return state


def _planner_script(project_dir: Path):
    """Script: planner immediately calls submit_plan."""
    return ai_tool("submit_plan", {
        "project_name": "App",
        "plan_md": f"# Plan\n## Acceptance criteria\n- runs",
        "components": [{"cid": _CID, "version": "1.0.1.2", "name": "Eco.X", "reason": "r"}],
        "acceptance_criteria": ["runs"],
    }, "p1")


def _setup_script():
    return [
        ai_tool("ecoos_pull", {"cid": _CID, "version": "1.0.1.2"}, "s1"),
        ai_tool("mark_setup_done", {"downloaded_paths": []}, "s2"),
    ]


def _coder_script(project_dir: Path):
    target = project_dir / "EcoMain.c"
    return [
        ai_tool("write_file", {"path": str(target), "content": "int main(){return 0;}"}, "c1"),
        ai_tool("mark_code_done", {"summary_md": "wrote main"}, "c2"),
    ]


def _builder_pass_script(project_dir: Path):
    return [
        ai_tool("run_make", {}, "b1"),
        ai_tool("report_build_pass", {"artifact_path": str(project_dir / "app.exe")}, "b2"),
    ]


def _builder_fail_script():
    return [
        ai_tool("run_make", {}, "b1"),
        ai_tool("report_build_fail", {"error_md": "## Err\nundefined ref"}, "b2"),
    ]


def _tester_pass_script():
    return [
        ai_tool("run_artifact", {"timeout_s": 5}, "t1"),
        ai_tool("report_test_pass", {"reason_md": "ok"}, "t2"),
    ]


def test_happy_path(sdk_root, fake_paths, mock_subprocess, project_dir):
    script = [
        _planner_script(project_dir),
        *_setup_script(),
        *_coder_script(project_dir),
        *_builder_pass_script(project_dir),
        *_tester_pass_script(),
    ]
    llm = ScriptedChatModel(script=script)
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-happy"}}
    initial = make_initial_v6_state("build x")
    initial["project_dir"] = str(project_dir)

    # First run — should pause at plan_gate
    list(graph.stream(initial, config))
    state = graph.get_state(config).values
    assert state["phase"] == "awaiting_approval"

    # Resume with approval
    list(graph.stream(Command(resume={"approved": True}), config))
    final = graph.get_state(config).values
    assert final["last_status"] == "success"
    assert final["phase"] == "done"


def test_user_rejects_plan(sdk_root, fake_paths, mock_subprocess, project_dir):
    llm = ScriptedChatModel(script=[_planner_script(project_dir)])
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-reject"}}
    initial = make_initial_v6_state("x")
    initial["project_dir"] = str(project_dir)
    list(graph.stream(initial, config))

    list(graph.stream(Command(resume={"approved": False, "reason": "no"}), config))
    final = graph.get_state(config).values
    assert final["last_status"] == "user_aborted"


def test_build_fail_retry_success(sdk_root, fake_paths, mock_subprocess, project_dir):
    script = [
        _planner_script(project_dir),
        *_setup_script(),
        *_coder_script(project_dir),           # coder #1
        *_builder_fail_script(),               # builder fails
        *_coder_script(project_dir),           # coder #2 (retry)
        *_builder_pass_script(project_dir),    # builder passes
        *_tester_pass_script(),
    ]
    llm = ScriptedChatModel(script=script)
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-retry"}}
    initial = make_initial_v6_state("x")
    initial["project_dir"] = str(project_dir)

    list(graph.stream(initial, config))
    list(graph.stream(Command(resume={"approved": True}), config))
    final = graph.get_state(config).values
    assert final["last_status"] == "success"
    assert final["retry_count"] == 1


def test_max_retry_user_continue_then_pass(sdk_root, fake_paths, mock_subprocess, project_dir):
    script = [
        _planner_script(project_dir),
        *_setup_script(),
        *_coder_script(project_dir),  # iter 1
        *_builder_fail_script(),
        *_coder_script(project_dir),  # iter 2
        *_builder_fail_script(),
        *_coder_script(project_dir),  # iter 3
        *_builder_fail_script(),       # retry 3 -> escalate
        *_coder_script(project_dir),  # after user_continue: retry resets, iter 1
        *_builder_pass_script(project_dir),
        *_tester_pass_script(),
    ]
    llm = ScriptedChatModel(script=script)
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-max-cont"}}
    initial = make_initial_v6_state("x", max_retries=3)
    initial["project_dir"] = str(project_dir)

    list(graph.stream(initial, config))                                      # planner -> gate
    list(graph.stream(Command(resume={"approved": True}), config))           # -> escalate
    list(graph.stream(Command(resume={"continue": True}), config))           # continue -> pass
    final = graph.get_state(config).values
    assert final["last_status"] == "success"


def test_max_retry_user_aborts(sdk_root, fake_paths, mock_subprocess, project_dir):
    script = [
        _planner_script(project_dir),
        *_setup_script(),
        *_coder_script(project_dir),
        *_builder_fail_script(),
        *_coder_script(project_dir),
        *_builder_fail_script(),
        *_coder_script(project_dir),
        *_builder_fail_script(),     # -> escalate
    ]
    llm = ScriptedChatModel(script=script)
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-max-abort"}}
    initial = make_initial_v6_state("x", max_retries=3)
    initial["project_dir"] = str(project_dir)

    list(graph.stream(initial, config))
    list(graph.stream(Command(resume={"approved": True}), config))
    list(graph.stream(Command(resume={"continue": False}), config))
    final = graph.get_state(config).values
    assert final["last_status"] == "user_aborted"
