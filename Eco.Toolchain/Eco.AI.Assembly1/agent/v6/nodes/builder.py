"""BUILDER node — runs build via vcvarsall+make; routes on pass/fail."""
from __future__ import annotations
from pathlib import Path
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.builder import make_builder_tools
from agent.v6.state import V6State
from agent.v6.trace import write_trace
from langgraph.config import get_stream_writer
from agent.v6.stream_events import make_on_event


BUILDER_SYSTEM_PROMPT = """\
You are the EcoOS Builder.

You receive a project_dir with the source files prepared by the Coder. Invoke \
`run_make` to build it. Inspect output via `read_file` / `list_dir` if helpful.

On SUCCESS: call `report_build_pass` with the absolute path to the built \
executable.

On FAILURE: read the build output, extract the KEY error(s) (not the raw log), \
and call `report_build_fail` with a Markdown summary that the Coder can act on."""


def builder_node(
    state: V6State,
    *,
    llm,
    vcvarsall: Path | None,
    make_exe: Path,
    max_iters: int = 15,
) -> dict:
    """Build the project; route on pass/fail with retry counter."""
    project_dir = Path(state["project_dir"])
    tools = make_builder_tools(project_dir=project_dir, vcvarsall=vcvarsall, make_exe=make_exe)

    seed = (
        f"Build the project at {project_dir}.\n"
        f"Available components: {state.get('downloaded_paths', [])}\n\n"
        f"Coder summary:\n{state.get('coder_summary_md', '')}\n\n"
        "Run the build, then report pass or fail."
    )
    try:
        writer = get_stream_writer()
    except RuntimeError:
        # No active LangGraph stream context (e.g. node called from a unit test).
        writer = None
    on_event = make_on_event("builder", writer)
    agent = EcoAgent(
        llm=llm,
        system_prompt=BUILDER_SYSTEM_PROMPT,
        tools=tools,
        stop_tool=["report_build_pass", "report_build_fail"],
        max_iters=max_iters,
        on_event=on_event,
    )
    result = agent.run(seed)
    write_trace(result, node="builder", state=state)

    if result.status != "done":
        return {
            "phase": "failed_escalated",
            "last_failure_origin": "builder",
            "last_status": f"builder_{result.status}",
            "builder_messages": result.history,
        }

    if result.stop_tool_name == "report_build_pass":
        return {
            "phase": "testing",
            "build_artifact": result.stop_payload["artifact_path"],
            "builder_messages": result.history,
        }

    # report_build_fail
    new_retry = state.get("retry_count", 0) + 1
    hit_ceiling = new_retry >= state.get("max_retries", 3)
    return {
        "build_log": result.stop_payload["error_md"],
        "retry_count": new_retry,
        "last_failure_origin": "builder",
        "last_status": "builder_retry_limit" if hit_ceiling else "builder_retry",
        "phase": "failed_escalated" if hit_ceiling else "coding",
        "builder_messages": result.history,
    }
