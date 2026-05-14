"""Tests for write_trace — V6 node execution trace persistence."""
import json

import pytest
from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage, ToolMessage, messages_from_dict,
)

from agent.v6.eco_agent import EcoAgentResult
from agent.v6.state import make_initial_v6_state
from agent.v6 import trace as trace_mod
from agent.v6.trace import write_trace


def _fake_history():
    return [
        SystemMessage(content="system prompt"),
        HumanMessage(content="seed request"),
        AIMessage(content="thinking...", tool_calls=[
            {"name": "read_file", "args": {"path": "x.c"}, "id": "c1"}
        ]),
        ToolMessage(content="file contents", tool_call_id="c1", status="success"),
    ]


def _result(status="done", error=""):
    return EcoAgentResult(
        status=status, stop_tool_name="", stop_payload={},
        history=_fake_history(), error=error,
    )


def test_write_trace_happy_path(monkeypatch, tmp_path):
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": "test-thread-1"}},
    )
    state = make_initial_v6_state("build a calculator")
    state["phase"] = "coding"

    path = write_trace(_result(status="max_iters"), node="coder",
                       state=state, traces_root=tmp_path)

    assert path is not None
    assert path.name == "01-coder.json"
    assert path.parent.name == "test-thread-1"

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["meta"]["thread_id"] == "test-thread-1"
    assert payload["meta"]["node"] == "coder"
    assert payload["meta"]["seq"] == 1
    assert payload["meta"]["phase"] == "coding"
    assert payload["meta"]["status"] == "max_iters"
    assert payload["meta"]["iters"] == 1  # one AIMessage in history

    # messages round-trip — proves the trace is semantically faithful
    restored = messages_from_dict(payload["messages"])
    assert len(restored) == 4
    assert restored[0].content == "system prompt"
    assert restored[2].tool_calls[0]["name"] == "read_file"


def test_write_trace_seq_increments(monkeypatch, tmp_path):
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": "test-thread-2"}},
    )
    state = make_initial_v6_state("x")

    p1 = write_trace(_result(), node="planner", state=state, traces_root=tmp_path)
    p2 = write_trace(_result(), node="setup", state=state, traces_root=tmp_path)

    assert p1 is not None
    assert p2 is not None
    assert p1.name == "01-planner.json"
    assert p2.name == "02-setup.json"


@pytest.mark.parametrize("evil_id, expected_dir", [
    ("../../evil", "evil"),
    ("..", "unknown"),
    (".", "unknown"),
    ("/abs/path", "path"),
])
def test_write_trace_sanitizes_thread_id(monkeypatch, tmp_path, evil_id, expected_dir):
    """Path-traversal / degenerate thread_ids must not escape traces_root."""
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": evil_id}},
    )
    state = make_initial_v6_state("x")

    path = write_trace(_result(), node="coder", state=state, traces_root=tmp_path)

    assert path is not None
    # real containment proof — resolve() collapses any "../" before the check
    assert path.resolve().is_relative_to(tmp_path.resolve())
    assert path.parent.name == expected_dir


def test_write_trace_no_thread_id_returns_none(monkeypatch, tmp_path):
    """Config present but thread_id missing/empty — skip silently, no file."""
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": ""}},
    )
    state = make_initial_v6_state("x")

    path = write_trace(_result(), node="coder", state=state, traces_root=tmp_path)

    assert path is None
    assert list(tmp_path.glob("**/*.json")) == []


def test_write_trace_no_graph_context_returns_none(monkeypatch, tmp_path):
    """No active LangGraph context (e.g. a unit test) — skip silently."""
    def _boom():
        raise RuntimeError("Called get_config outside of a runnable context")
    monkeypatch.setattr(trace_mod, "get_config", _boom)
    state = make_initial_v6_state("x")

    path = write_trace(_result(), node="coder", state=state, traces_root=tmp_path)

    assert path is None
    assert list(tmp_path.glob("**/*.json")) == []


def test_write_trace_never_raises_on_bad_root(monkeypatch, tmp_path):
    """A broken traces_root must not propagate an exception to the node."""
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": "t"}},
    )
    # traces_root points at a FILE, so mkdir under it will fail
    bad_root = tmp_path / "i-am-a-file"
    bad_root.write_text("not a dir")
    state = make_initial_v6_state("x")

    path = write_trace(_result(), node="coder", state=state, traces_root=bad_root)

    assert path is None  # no exception propagated


def test_write_trace_default_str_safety_net(monkeypatch, tmp_path):
    """A non-JSON-serializable object in additional_kwargs is coerced, not fatal."""
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": "t-safety"}},
    )
    history = [
        SystemMessage(content="s"),
        AIMessage(content="a", additional_kwargs={"weird": object()}),
    ]
    result = EcoAgentResult(
        status="done", stop_tool_name="", stop_payload={},
        history=history, error="",
    )
    state = make_initial_v6_state("x")

    path = write_trace(result, node="coder", state=state, traces_root=tmp_path)

    assert path is not None
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["meta"]["node"] == "coder"
