"""Tests for the flat orchestrator with declared handoff edges."""
from __future__ import annotations

import pytest

from agent.internal.eco_agent import EcoAgent
from agent.internal.orchestrator import Orchestrator
from agent.internal.tools.handoff import make_handoff_tool, make_fail_tool
from agent.internal.tests.conftest import make_scripted_model_pair, ai_tool


# ── helpers ────────────────────────────────────────────────────────────────
def _scripted_agent(
    name: str,
    *,
    edges_out: list[str],         # names of handoff/done/fail tools to bind
    edge_calls: list[tuple[str, str, str]],  # [(tool_name, field, value), ...]
) -> EcoAgent:
    """Build an EcoAgent whose scripted LLM emits the given stop-tool calls in order.

    Each tuple is (tool_name, arg_field, arg_value) — arg_field is either
    "message" or "reason" depending on the stop-tool flavour.
    """
    tools = []
    for e in edges_out:
        if e == "fail":
            tools.append(make_fail_tool())
        else:
            tools.append(make_handoff_tool(e, f"{name} edge {e}"))

    script = [
        ai_tool(tool_name, {field: value}, call_id=f"{name}-{i}")
        for i, (tool_name, field, value) in enumerate(edge_calls)
    ]
    model, stream_fn = make_scripted_model_pair(script)
    return EcoAgent(
        model=model,
        stream_fn=stream_fn,
        system_prompt=f"you are {name}",
        tools=tools,
        stop_tool=edges_out,
        max_iters=5,
    )


# ── 1. single agent, terminal "done" edge ──────────────────────────────────
def test_single_agent_terminal_done():
    architect = _scripted_agent(
        "architect",
        edges_out=["done"],
        edge_calls=[("done", "message", "all good")],
    )
    orch = Orchestrator(
        agents={"architect": architect},
        edges={"architect": {"done": None}},
        entry="architect",
    )
    r = orch.run("hello")
    assert r.status == "terminal"
    assert r.terminal_edge == "done"
    assert r.last_agent == "architect"
    assert r.last_message == "all good"
    assert len(r.hops) == 1
    assert r.hops[0].agent == "architect"
    assert r.hops[0].edge == "done"


# ── 2. forward handoff: a → b → done ───────────────────────────────────────
def test_forward_handoff_two_agents():
    architect = _scripted_agent(
        "architect",
        edges_out=["to_coder"],
        edge_calls=[("to_coder", "message", "plan: write a calc")],
    )
    coder = _scripted_agent(
        "coder",
        edges_out=["done"],
        edge_calls=[("done", "message", "code shipped")],
    )
    orch = Orchestrator(
        agents={"architect": architect, "coder": coder},
        edges={
            "architect": {"to_coder": "coder"},
            "coder":     {"done": None},
        },
        entry="architect",
    )
    r = orch.run("build me a calc")
    assert r.status == "terminal"
    assert r.terminal_edge == "done"
    assert r.last_agent == "coder"
    assert [(h.agent, h.edge) for h in r.hops] == [
        ("architect", "to_coder"),
        ("coder",     "done"),
    ]
    # Forward handoff must propagate architect's message to coder.
    # We verify indirectly via the hop record (coder did receive control).


# ── 3. backward handoff: tester → coder → tester → done ────────────────────
def test_backward_handoff_tester_to_coder():
    architect = _scripted_agent(
        "architect", edges_out=["to_coder"],
        edge_calls=[("to_coder", "message", "plan")],
    )
    # Coder is invoked TWICE — first hands off to tester, second time after
    # tester sends control back, hands off again to tester.
    coder = _scripted_agent(
        "coder", edges_out=["to_tester"],
        edge_calls=[
            ("to_tester", "message", "first attempt"),
            ("to_tester", "message", "fixed per tester feedback"),
        ],
    )
    # Tester first rejects (backward to coder), then accepts.
    tester = _scripted_agent(
        "tester", edges_out=["to_coder", "done"],
        edge_calls=[
            ("to_coder", "message", "missing edge case"),
            ("done",     "message", "all tests pass"),
        ],
    )
    orch = Orchestrator(
        agents={"architect": architect, "coder": coder, "tester": tester},
        edges={
            "architect": {"to_coder":  "coder"},
            "coder":     {"to_tester": "tester"},
            "tester":    {"to_coder":  "coder", "done": None},
        },
        entry="architect",
    )
    r = orch.run("build")
    assert r.status == "terminal"
    assert r.terminal_edge == "done"
    assert [(h.agent, h.edge) for h in r.hops] == [
        ("architect", "to_coder"),
        ("coder",     "to_tester"),
        ("tester",    "to_coder"),
        ("coder",     "to_tester"),
        ("tester",    "done"),
    ]


# ── 4. fail edge is terminal (honest stop) ─────────────────────────────────
def test_fail_edge_terminal():
    architect = _scripted_agent(
        "architect", edges_out=["fail"],
        edge_calls=[("fail", "reason", "marketplace empty")],
    )
    orch = Orchestrator(
        agents={"architect": architect},
        edges={"architect": {"fail": None}},
        entry="architect",
    )
    r = orch.run("go")
    assert r.status == "terminal"
    assert r.terminal_edge == "fail"
    assert r.last_message == "marketplace empty"


# ── 5. loop guard kicks in on mutual handoffs ──────────────────────────────
def test_loop_guard_mutual_handoff():
    # Two agents that bounce control between each other forever. The
    # orchestrator must stop them at max_hops without crashing.
    a_calls = [("to_b", "message", f"a says {i}") for i in range(10)]
    b_calls = [("to_a", "message", f"b says {i}") for i in range(10)]
    a = _scripted_agent("a", edges_out=["to_b"], edge_calls=a_calls)
    b = _scripted_agent("b", edges_out=["to_a"], edge_calls=b_calls)
    orch = Orchestrator(
        agents={"a": a, "b": b},
        edges={"a": {"to_b": "b"}, "b": {"to_a": "a"}},
        entry="a",
        max_hops=4,
    )
    r = orch.run("ping")
    assert r.status == "loop_exceeded"
    assert len(r.hops) == 4
    assert "max_hops=4" in r.error


# ── 6. agent internal failure surfaces as agent_failed ─────────────────────
def test_agent_failure_propagates():
    # Agent's scripted LLM exhausts before reaching a stop-tool — EcoAgent
    # returns status="max_iters". Orchestrator must surface this, not crash.
    model, stream_fn = make_scripted_model_pair([ai_tool("non_stop", {"x": "y"}, "c1")])
    # No matching tool defined — EcoAgent will record UNKNOWN TOOL and loop
    # until max_iters since the script is exhausted on the second call.
    bad = EcoAgent(
        model=model,
        stream_fn=stream_fn,
        system_prompt="broken agent",
        tools=[make_handoff_tool("to_b", "to b")],
        stop_tool=["to_b"],
        max_iters=1,  # one iteration, no stop-tool → max_iters
    )
    orch = Orchestrator(
        agents={"bad": bad, "b": _scripted_agent("b", edges_out=["done"],
                                                 edge_calls=[("done", "message", "x")])},
        edges={"bad": {"to_b": "b"}, "b": {"done": None}},
        entry="bad",
    )
    r = orch.run("go")
    assert r.status == "agent_failed"
    assert r.last_agent == "bad"
    # The hop record should still be present so users can inspect what happened.
    assert len(r.hops) == 1
    assert r.hops[0].edge is None


# ── 7. unknown_edge is surfaced when agent picks an edge orchestrator doesn't know ─
def test_unknown_edge_is_surfaced():
    # Agent declares both "to_coder" and "to_tester" as stop-tools, but
    # orchestrator only routes "to_coder". When the agent picks "to_tester",
    # the orchestrator must refuse to guess.
    rogue = _scripted_agent(
        "rogue", edges_out=["to_coder", "to_tester"],
        edge_calls=[("to_tester", "message", "wrong way")],
    )
    coder = _scripted_agent("coder", edges_out=["done"],
                            edge_calls=[("done", "message", "x")])
    orch = Orchestrator(
        agents={"rogue": rogue, "coder": coder},
        edges={
            "rogue": {"to_coder": "coder"},          # ← no "to_tester" here
            "coder": {"done": None},
        },
        entry="rogue",
    )
    r = orch.run("go")
    assert r.status == "unknown_edge"
    assert "to_tester" in r.error
    assert "to_coder" in r.error  # error lists known edges so the bug is obvious


# ── 8. constructor validation: entry must be a known agent ────────────────
def test_constructor_rejects_unknown_entry():
    a = _scripted_agent("a", edges_out=["done"],
                        edge_calls=[("done", "message", "x")])
    with pytest.raises(ValueError, match="entry"):
        Orchestrator(
            agents={"a": a},
            edges={"a": {"done": None}},
            entry="b",
        )


# ── 9. constructor validation: edges must reference known agents ──────────
def test_constructor_rejects_unknown_edge_target():
    a = _scripted_agent("a", edges_out=["to_ghost"],
                        edge_calls=[("to_ghost", "message", "x")])
    with pytest.raises(ValueError, match="unknown destination"):
        Orchestrator(
            agents={"a": a},
            edges={"a": {"to_ghost": "ghost"}},
            entry="a",
        )


# ── 10. constructor validation: edges source must be a known agent ────────
def test_constructor_rejects_unknown_edge_source():
    a = _scripted_agent("a", edges_out=["done"],
                        edge_calls=[("done", "message", "x")])
    with pytest.raises(ValueError, match="unknown agent"):
        Orchestrator(
            agents={"a": a},
            edges={"a": {"done": None}, "phantom": {"done": None}},
            entry="a",
        )

