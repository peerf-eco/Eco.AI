"""PLANNER node — produces plan_md + components."""
from __future__ import annotations

from pathlib import Path

from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.planner import make_planner_tools
from agent.v6.state import V6State


PLANNER_SYSTEM_PROMPT = """\
You are the EcoOS Planner.

Read available SDK components via `list_components` and `read_component`. \
Then design an application that satisfies the user request using ONLY existing \
SDK components.

Produce a final plan via `submit_plan` (stop tool). The plan MUST contain:
- a `## Acceptance criteria` section listing observable behaviors (stdout strings, \
  exit codes, what the tester will check)
- a `components` list with cid, version, base name, and a one-sentence reason for each
- a narrative `plan_md` describing the application

Always use `list_components` first if you don't know what's available."""


def planner_node(state: V6State, *, llm, sdk_root: Path, max_iters: int = 30) -> dict:
    """Run the planner agent.

    Args:
        state: V6 state with user_request
        llm: Language model instance
        sdk_root: Path to SDK packages directory
        max_iters: Maximum agent loop iterations

    Returns:
        Delta dict with phase, plan_md, components, project_name, or error status
    """
    tools = make_planner_tools(sdk_root=sdk_root)
    agent = EcoAgent(
        llm=llm,
        system_prompt=PLANNER_SYSTEM_PROMPT,
        tools=tools,
        stop_tool="submit_plan",
        max_iters=max_iters,
    )
    result = agent.run(state["user_request"])

    if result.status == "done":
        return {
            "phase": "awaiting_approval",
            "plan_md":      result.stop_payload["plan_md"],
            "components":   result.stop_payload["components"],
            "project_name": result.stop_payload["project_name"],
            "planner_messages": result.history,
        }
    # max_iters or no_tool_call or error
    return {
        "phase": "failed_escalated",
        "last_status": f"planner_{result.status}",
        "planner_messages": result.history,
    }
