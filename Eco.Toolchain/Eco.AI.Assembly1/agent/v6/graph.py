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


def route_after_plan_gate(s: V6State) -> str:
    """Route after plan_gate node. Setup or End."""
    return "setup" if s["phase"] == "setup" else END


def route_after_builder(s: V6State) -> str:
    """Route after builder node. Tester, coder retry, escalate, or End."""
    return {"testing": "tester", "coding": "coder", "failed_escalated": "escalate"}.get(s["phase"], END)


def route_after_tester(s: V6State) -> str:
    """Route after tester node. Done, coder retry, or escalate."""
    return {"done": END, "coding": "coder", "failed_escalated": "escalate"}.get(s["phase"], END)


def route_after_escalate(s: V6State) -> str:
    """Route after escalate node. Coder retry or End."""
    return "coder" if s.get("last_status") == "user_continue" else END


def create_v6_graph(
    llm,
    *,
    sdk_root: Path,
    cli_path: Path,
    vcvarsall: Path,
    make_exe: Path,
    checkpointer=None,
):
    """Build the V6 graph. All node-specific config (paths) is captured by closures.

    Args:
        llm: Language model instance
        sdk_root: Path to SDK packages directory
        cli_path: Path to eco-cli executable
        vcvarsall: Path to vcvarsall.bat
        make_exe: Path to GNU Make executable
        checkpointer: Optional LangGraph checkpointer for persistence

    Returns:
        Compiled LangGraph StateGraph
    """
    g = StateGraph(V6State)

    # Add all 7 nodes
    g.add_node("planner",   lambda s: planner_node(s, llm=llm, sdk_root=sdk_root))
    g.add_node("plan_gate", plan_gate_node)
    g.add_node("setup",     lambda s: setup_node(s, llm=llm, cli_path=cli_path))
    g.add_node("coder",     lambda s: coder_node(s, llm=llm))
    g.add_node("builder",   lambda s: builder_node(s, llm=llm, vcvarsall=vcvarsall, make_exe=make_exe))
    g.add_node("tester",    lambda s: tester_node(s, llm=llm))
    g.add_node("escalate",  escalate_node)

    # Entry point
    g.set_entry_point("planner")

    # Fixed edges
    g.add_edge("planner", "plan_gate")
    g.add_edge("setup", "coder")

    # Conditional edges
    g.add_conditional_edges(
        "plan_gate",
        route_after_plan_gate,
        {"setup": "setup", END: END}
    )
    g.add_conditional_edges(
        "builder",
        route_after_builder,
        {"tester": "tester", "coder": "coder", "escalate": "escalate", END: END}
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
