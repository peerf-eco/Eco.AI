"""V6 state schema — five-node pipeline."""
from typing import Literal
from typing_extensions import TypedDict


Phase = Literal[
    "planning",
    "awaiting_approval",
    "setup",
    "coding",
    "building",
    "testing",
    "failed_escalated",
    "done",
]


class V6State(TypedDict):
    user_request: str

    # Per-node histories. Each node returns its full history under its key,
    # which REPLACES the previous value (default LangGraph reducer). DO NOT
    # add `add_messages` here — per spec §5.4 each node's history lives
    # inside the node and is reset on entry. Cross-retry accumulation would
    # otherwise quadratically grow the checkpointer payload.
    planner_messages: list
    setup_messages:   list
    coder_messages:   list
    builder_messages: list
    tester_messages:  list

    plan_md:          str
    components:       list[dict]
    project_dir:      str
    project_name:     str
    downloaded_paths: list[str]
    coder_summary_md: str
    build_artifact:   str
    build_log:        str
    tester_report_md: str

    phase:               Phase
    retry_count:         int
    max_retries:         int
    last_failure_origin: Literal["", "planner", "setup", "coder", "builder", "tester"]
    last_status:         str


def make_initial_v6_state(user_request: str, max_retries: int = 3) -> V6State:
    return {
        "user_request": user_request,
        "planner_messages": [{"role": "user", "content": user_request}],
        "setup_messages": [],
        "coder_messages": [],
        "builder_messages": [],
        "tester_messages": [],
        "plan_md": "",
        "components": [],
        "project_dir": "",
        "project_name": "",
        "downloaded_paths": [],
        "coder_summary_md": "",
        "build_artifact": "",
        "build_log": "",
        "tester_report_md": "",
        "phase": "planning",
        "retry_count": 0,
        "max_retries": max_retries,
        "last_failure_origin": "",
        "last_status": "",
    }
