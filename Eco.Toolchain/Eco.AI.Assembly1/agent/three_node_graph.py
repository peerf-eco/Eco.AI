"""V5 Three-Node Graph: Planner → Coder → Executor."""

import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state_v5 import AppState
from .planner import create_planner_node
from .coder import create_coder_node_v5
from .executor import create_executor_node

logger = logging.getLogger(__name__)


def _route_by_phase(state) -> str:
    return state["phase"]


def _route_after_planner(state) -> str:
    return "coding" if state["phase"] == "coding" else "wait_user"


def _route_after_coder(state) -> str:
    return "executing" if state["phase"] == "executing" else "wait_user"


def _route_after_executor(state) -> str:
    if state["phase"] == "coding":
        return "coding"
    return "done"


def create_v5_graph(llm):
    """Compile the V5 three-node graph with MemorySaver checkpointer."""
    builder = StateGraph(AppState)
    builder.add_node("planner",  create_planner_node(llm))
    builder.add_node("coder",    create_coder_node_v5(llm))
    builder.add_node("executor", create_executor_node(llm))

    builder.add_conditional_edges(START, _route_by_phase, {
        "planning":  "planner",
        "coding":    "coder",
        "executing": "executor",
        "done":      END,
    })
    builder.add_conditional_edges("planner", _route_after_planner, {
        "coding":   "coder",
        "wait_user": END,
    })
    builder.add_conditional_edges("coder", _route_after_coder, {
        "executing": "executor",
        "wait_user": END,
    })
    builder.add_conditional_edges("executor", _route_after_executor, {
        "coding":  "coder",
        "done":    END,
    })

    return builder.compile(checkpointer=MemorySaver())
