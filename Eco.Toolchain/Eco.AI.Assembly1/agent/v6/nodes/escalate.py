"""ESCALATE — interrupt() asking user to continue or abort.

The payload carries an explicit `reason` so the UI can render the true cause
of the stop (planner timeout, setup verification failure, builder retry ceiling,
...) rather than always saying "Max retries reached".
"""
from __future__ import annotations
from langgraph.types import interrupt
from agent.v6.state import V6State


def _derive_reason(state: V6State) -> str:
    """Pick the most specific reason string available on state.

    Builder/tester nodes set last_status to `<node>_retry_limit` when their
    retry counter exceeds max_retries, and to `<node>_<agent-status>` (e.g.
    `builder_no_tool_call`, `planner_max_iters`) when the agent loop itself
    failed on the first attempt. We surface whichever was set; if nothing
    was set we degrade to a generic 'unknown' rather than lying about retries.
    """
    last_status = (state.get("last_status") or "").strip()
    if last_status:
        return last_status
    origin = state.get("last_failure_origin", "") or ""
    return f"{origin}_unknown" if origin else "unknown"


def escalate_node(state: V6State) -> dict:
    reason = _derive_reason(state)
    resume = interrupt({
        "reason":           reason,
        "failure_origin":   state.get("last_failure_origin", ""),
        "retry_count":      state.get("retry_count", 0),
        "max_retries":      state.get("max_retries", 0),
        "build_log":        state.get("build_log", ""),
        "tester_report_md": state.get("tester_report_md", ""),
        "plan_md":          state.get("plan_md", ""),
        "coder_summary_md": state.get("coder_summary_md", ""),
    })
    # resume value: {"continue": bool}
    if resume.get("continue", False):
        return {
            "retry_count": 0,
            "last_status": "user_continue",
            "phase": "coding",
        }
    return {"phase": "done", "last_status": "user_aborted"}
