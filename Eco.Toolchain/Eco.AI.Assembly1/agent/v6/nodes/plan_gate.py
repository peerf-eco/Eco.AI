"""PLAN_GATE — pure interrupt() wrapper. No agent."""
from __future__ import annotations

from langgraph.types import interrupt

from agent.v6.state import V6State


def plan_gate_node(state: V6State) -> dict:
    """Interrupt to let user review and approve the plan.

    Raises GraphInterrupt with plan and components payload. When resumed,
    expects {"approved": bool, "modified_plan_md"?: str, "reason"?: str}.

    Args:
        state: V6 state with plan_md, components, project_name

    Returns:
        Delta dict with phase and optional plan_md update, or done+user_aborted
    """
    resume = interrupt({
        "plan_md":     state["plan_md"],
        "components":  state["components"],
        "project_name": state.get("project_name", ""),
    })
    # resume value: {"approved": bool, "modified_plan_md"?: str, "reason"?: str}
    if not resume.get("approved", False):
        return {"phase": "done", "last_status": "user_aborted"}
    delta = {"phase": "setup"}
    if "modified_plan_md" in resume and resume["modified_plan_md"]:
        delta["plan_md"] = resume["modified_plan_md"]
    return delta
