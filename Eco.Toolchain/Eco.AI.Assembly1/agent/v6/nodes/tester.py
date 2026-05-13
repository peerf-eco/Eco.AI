"""TESTER node — LLM-judge isolated from coder_summary."""
from __future__ import annotations
import re
from pathlib import Path
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.tester import make_tester_tools
from agent.v6.state import V6State
from langgraph.config import get_stream_writer
from agent.v6.stream_events import make_on_event


TESTER_SYSTEM_PROMPT = """\
You are the EcoOS Tester. You CANNOT see the source code or any coder notes — \
only the user's original request, the plan's acceptance criteria, and the \
built artifact at a given path.

Call `run_artifact` to execute the binary and capture stdout/stderr/exit. \
Compare the runtime behavior against the acceptance criteria. Decide pass/fail \
based on OBSERVABLE behavior only — not assumptions about what the code might do.

Then call either `report_test_pass(reason_md)` or `report_test_fail(reason_md)`. \
On fail, be specific: what did you expect, what did you see, what should be fixed."""


def _extract_acceptance(plan_md: str) -> str:
    """Extract the '## Acceptance criteria' section if present."""
    match = re.search(r"##\s+Acceptance\s+criteria.*?(?=\n##\s|\Z)",
                      plan_md, re.IGNORECASE | re.DOTALL)
    return match.group(0).strip() if match else "(no acceptance criteria section found)"


def _build_tester_seed(state: V6State) -> str:
    return (
        f"User request:\n{state['user_request']}\n\n"
        f"Acceptance criteria from plan:\n{_extract_acceptance(state['plan_md'])}\n\n"
        f"Built artifact: {state['build_artifact']}\n\n"
        "Run the artifact and judge by behavior only. You cannot read source files."
    )


def tester_node(state: V6State, *, llm, max_iters: int = 10) -> dict:
    artifact = Path(state["build_artifact"])
    tools = make_tester_tools(build_artifact=artifact)

    try:
        writer = get_stream_writer()
    except RuntimeError:
        # No active LangGraph stream context (e.g. node called from a unit test).
        writer = None
    on_event = make_on_event("tester", writer)
    agent = EcoAgent(
        llm=llm,
        system_prompt=TESTER_SYSTEM_PROMPT,
        tools=tools,
        stop_tool=["report_test_pass", "report_test_fail"],
        max_iters=max_iters,
        on_event=on_event,
    )
    result = agent.run(_build_tester_seed(state))

    if result.status != "done":
        return {
            "phase": "failed_escalated",
            "last_failure_origin": "tester",
            "last_status": f"tester_{result.status}",
            "tester_messages": result.history,
        }

    if result.stop_tool_name == "report_test_pass":
        return {
            "phase": "done",
            "last_status": "success",
            "tester_report_md": result.stop_payload["reason_md"],
            "tester_messages": result.history,
        }

    new_retry = state.get("retry_count", 0) + 1
    hit_ceiling = new_retry >= state.get("max_retries", 3)
    return {
        "tester_report_md": result.stop_payload["reason_md"],
        "retry_count": new_retry,
        "last_failure_origin": "tester",
        "last_status": "tester_retry_limit" if hit_ceiling else "tester_retry",
        "phase": "failed_escalated" if hit_ceiling else "coding",
        "tester_messages": result.history,
    }


tester_node.__test__ = False  # don't let pytest collect this as a test function
