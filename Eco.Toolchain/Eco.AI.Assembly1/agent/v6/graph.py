"""V6 graph wiring."""
from __future__ import annotations
from pathlib import Path
from langgraph.graph import StateGraph, END
from agent.v6.state import V6State
from agent.v6.nodes.planner import planner_node
from agent.v6.nodes.plan_gate import plan_gate_node
from agent.v6.nodes.setup import setup_node
from agent.v6.nodes.coder import coder_node
from agent.v6.nodes.builder import builder_node
from agent.v6.nodes.tester import tester_node
from agent.v6.nodes.escalate import escalate_node


def route_after_planner(s: V6State) -> str:
    """Route after planner. plan_gate on success, escalate on failure."""
    if s["phase"] == "awaiting_approval":
        return "plan_gate"
    if s["phase"] == "failed_escalated":
        return "escalate"
    raise RuntimeError(f"route_after_planner: unexpected phase {s['phase']!r}")


def route_after_plan_gate(s: V6State) -> str:
    """Route after plan_gate node. Setup or End."""
    if s["phase"] == "setup":
        return "setup"
    if s["phase"] == "done":
        return END
    raise RuntimeError(f"route_after_plan_gate: unexpected phase {s['phase']!r}")


def route_after_setup(s: V6State) -> str:
    """Route after setup. coder on success, escalate on failure."""
    if s["phase"] == "coding":
        return "coder"
    if s["phase"] == "failed_escalated":
        return "escalate"
    raise RuntimeError(f"route_after_setup: unexpected phase {s['phase']!r}")


def route_after_coder(s: V6State) -> str:
    """Route after coder. builder on success, escalate on failure."""
    if s["phase"] == "building":
        return "builder"
    if s["phase"] == "failed_escalated":
        return "escalate"
    raise RuntimeError(f"route_after_coder: unexpected phase {s['phase']!r}")


def route_after_builder(s: V6State) -> str:
    """Route after builder node. Tester, coder retry, or escalate."""
    if s["phase"] == "testing":
        return "tester"
    if s["phase"] == "coding":
        return "coder"
    if s["phase"] == "failed_escalated":
        return "escalate"
    raise RuntimeError(f"route_after_builder: unexpected phase {s['phase']!r}")


def route_after_tester(s: V6State) -> str:
    """Route after tester node. Done, coder retry, or escalate."""
    if s["phase"] == "done":
        return END
    if s["phase"] == "coding":
        return "coder"
    if s["phase"] == "failed_escalated":
        return "escalate"
    raise RuntimeError(f"route_after_tester: unexpected phase {s['phase']!r}")


def route_after_escalate(s: V6State) -> str:
    """Route after escalate node. Coder retry or End."""
    return "coder" if s.get("last_status") == "user_continue" else END


def create_v6_graph(
    llm,
    *,
    sdk_root: Path,
    cli_path: Path | None,
    vcvarsall: Path | None,
    make_exe: Path,
    checkpointer=None,
):
    """Build the V6 graph. All node-specific config (paths) is captured by closures.

    Args:
        llm: Language model instance
        sdk_root: Path to SDK packages directory (used as marketplace mirror on Linux)
        cli_path: Path to eco-cli executable (Windows only; pass None on Linux)
        vcvarsall: Path to vcvarsall.bat (Windows only; pass None on Linux)
        make_exe: GNU Make executable — Windows full path or "make" on Linux
        checkpointer: Optional LangGraph checkpointer for persistence

    Returns:
        Compiled LangGraph StateGraph
    """
    g = StateGraph(V6State)

    # Add all 7 nodes
    g.add_node("planner",   lambda s: planner_node(s, llm=llm, sdk_root=sdk_root))
    g.add_node("plan_gate", plan_gate_node)
    g.add_node("setup",     lambda s: setup_node(s, llm=llm, cli_path=cli_path, sdk_root=sdk_root))
    g.add_node("coder",     lambda s: coder_node(s, llm=llm))
    g.add_node("builder",   lambda s: builder_node(s, llm=llm, vcvarsall=vcvarsall, make_exe=make_exe))
    g.add_node("tester",    lambda s: tester_node(s, llm=llm))
    g.add_node("escalate",  escalate_node)

    # Entry point
    g.set_entry_point("planner")

    # Conditional edges only — every node's exit path is phase-driven so a
    # `failed_escalated` phase from planner/setup/coder routes straight to
    # `escalate` instead of leaking into the happy-path successor.
    g.add_conditional_edges(
        "planner",
        route_after_planner,
        {"plan_gate": "plan_gate", "escalate": "escalate"}
    )
    g.add_conditional_edges(
        "plan_gate",
        route_after_plan_gate,
        {"setup": "setup", END: END}
    )
    g.add_conditional_edges(
        "setup",
        route_after_setup,
        {"coder": "coder", "escalate": "escalate"}
    )
    g.add_conditional_edges(
        "coder",
        route_after_coder,
        {"builder": "builder", "escalate": "escalate"}
    )
    g.add_conditional_edges(
        "builder",
        route_after_builder,
        {"tester": "tester", "coder": "coder", "escalate": "escalate"}
    )
    g.add_conditional_edges(
        "tester",
        route_after_tester,
        {END: END, "coder": "coder", "escalate": "escalate"}
    )
    g.add_conditional_edges(
        "escalate",
        route_after_escalate,
        {"coder": "coder", END: END}
    )

    return g.compile(checkpointer=checkpointer)
