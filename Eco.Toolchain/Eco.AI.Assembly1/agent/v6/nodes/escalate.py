"""ESCALATE — interrupt() asking user to continue or abort."""
from __future__ import annotations
from langgraph.types import interrupt
from agent.v6.state import V6State


def escalate_node(state: V6State) -> dict:
    resume = interrupt({
        "failure_origin":   state.get("last_failure_origin", ""),
        "retry_count":      state.get("retry_count", 0),
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
