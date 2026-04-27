"""V5 state — Three-Node Pipeline (Planner / Coder / Executor)."""

from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


Phase = Literal["planning", "coding", "executing", "done"]


class AppState(TypedDict):
    user_request: str

    planner_messages:  Annotated[list, add_messages]
    coder_messages:    Annotated[list, add_messages]
    executor_messages: Annotated[list, add_messages]

    plan_md:             str
    coder_summary_md:    str
    feedback_md:         str
    executor_summary_md: str

    phase: Phase

    project_dir:  str
    project_name: str

    iteration:      int
    max_iterations: int
    last_status:    str  # "" | "success" | "max_iterations_reached" | "parse_failure" | "user_aborted"


def make_initial_state(user_request: str, max_iterations: int = 5) -> AppState:
    return {
        "user_request": user_request,
        "planner_messages":  [{"role": "user", "content": user_request}],
        "coder_messages":    [],
        "executor_messages": [],
        "plan_md":             "",
        "coder_summary_md":    "",
        "feedback_md":         "",
        "executor_summary_md": "",
        "phase":         "planning",
        "project_dir":   "",
        "project_name":  "",
        "iteration":      0,
        "max_iterations": max_iterations,
        "last_status":    "",
    }
