"""Tests for setup_node."""
import subprocess
from pathlib import Path

import pytest

from agent.v6.nodes.setup import setup_node, SETUP_SYSTEM_PROMPT
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


def _fake_subprocess_run(cmd, **kw):
    """Stub subprocess.run — pretends every eco-cli invocation succeeded."""
    class R:
        returncode = 0
        stdout = "ok"
        stderr = ""
    return R()


@pytest.fixture
def fake_cli_path(tmp_path):
    """Fake eco-cli executable."""
    cli = tmp_path / "eco-cli.exe"
    cli.write_text("")
    return cli


def test_setup_node_happy_path(monkeypatch, project_dir, fake_cli_path):
    """Setup agent pulls components, verifies via list_dir, then marks done."""
    monkeypatch.setattr(subprocess, "run", _fake_subprocess_run)

    state = make_initial_v6_state("x")
    state["components"] = [{"cid": "A" * 32, "version": "1.0.1.2", "name": "Eco.X", "reason": "r"}]
    state["plan_md"] = "# Plan"
    state["project_dir"] = str(project_dir)

    llm = ScriptedChatModel(script=[
        ai_tool("ecoos_pull", {"cid": "A" * 32, "version": "1.0.1.2"}, "c1"),
        ai_tool("mark_setup_done", {"downloaded_paths": [str(project_dir)]}, "c2"),
    ])
    delta = setup_node(state, llm=llm, cli_path=fake_cli_path)
    assert delta["phase"] == "coding"
    assert str(project_dir) in delta["downloaded_paths"]


def test_setup_node_prompt_mentions_verification():
    """System prompt includes key directives."""
    assert "verify" in SETUP_SYSTEM_PROMPT.lower()
    assert "list_dir" in SETUP_SYSTEM_PROMPT


def test_setup_node_writes_trace(monkeypatch, project_dir, fake_cli_path):
    """setup_node calls write_trace with its EcoAgentResult after agent.run()."""
    monkeypatch.setattr(subprocess, "run", _fake_subprocess_run)

    calls = []
    import agent.v6.nodes.setup as setup_mod
    monkeypatch.setattr(
        setup_mod, "write_trace",
        lambda result, *, node, state: calls.append((result, node)),
    )

    state = make_initial_v6_state("x")
    state["components"] = [
        {"cid": "A" * 32, "version": "1.0.1.2", "name": "Eco.X", "reason": "r"}
    ]
    state["plan_md"] = "# Plan"
    state["project_dir"] = str(project_dir)

    llm = ScriptedChatModel(script=[
        ai_tool("ecoos_pull", {"cid": "A" * 32, "version": "1.0.1.2"}, "c1"),
        ai_tool("mark_setup_done", {"downloaded_paths": [str(project_dir)]}, "c2"),
    ])
    setup_node(state, llm=llm, cli_path=fake_cli_path)

    assert len(calls) == 1
    result, node = calls[0]
    assert node == "setup"
    assert result.status == "done"


def test_setup_node_writes_trace_on_failure_path(monkeypatch, project_dir, fake_cli_path):
    """write_trace fires even when the node exits via max_iters, not just on success."""
    monkeypatch.setattr(subprocess, "run", _fake_subprocess_run)

    calls = []
    import agent.v6.nodes.setup as setup_mod
    monkeypatch.setattr(
        setup_mod, "write_trace",
        lambda result, *, node, state: calls.append((result, node)),
    )

    state = make_initial_v6_state("x")
    state["components"] = [
        {"cid": "A" * 32, "version": "1.0.1.2", "name": "Eco.X", "reason": "r"}
    ]
    state["plan_md"] = "# Plan"
    state["project_dir"] = str(project_dir)

    # Script never calls the stop tool `mark_setup_done` → agent exhausts max_iters
    llm = ScriptedChatModel(script=[
        ai_tool("ecoos_pull", {"cid": "A" * 32, "version": "1.0.1.2"}, "c1"),
        ai_tool("ecoos_pull", {"cid": "A" * 32, "version": "1.0.1.2"}, "c2"),
        ai_tool("ecoos_pull", {"cid": "A" * 32, "version": "1.0.1.2"}, "c3"),
    ])
    setup_node(state, llm=llm, cli_path=fake_cli_path, max_iters=2)

    assert len(calls) == 1
    result, node = calls[0]
    assert node == "setup"
    assert result.status == "max_iters"
