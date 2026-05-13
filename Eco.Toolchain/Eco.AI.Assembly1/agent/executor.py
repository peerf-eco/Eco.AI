"""V5 Executor node — build + test, with bounded retry loop."""

import json
import logging
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command

from .tools import build_makefile, run_tests

logger = logging.getLogger(__name__)


EXECUTOR_SYSTEM_PROMPT = """\
You are the EcoOS Executor. You receive a coder summary and must:
1. Run build() to compile and link the project.
2. If build fails, immediately call back_to_code(feedback_md) with structured errors.
3. If build succeeds, call run_tests().
4. If tests fail, call back_to_code(feedback_md) with the failures.
5. If everything passes, call success(summary_md) with a short user-facing report.

Feedback Markdown format (use EXACTLY these headers):

## Stage: build|test
## Status: FAIL

## Errors
- {file}:{line}: {message}

## Test failures
- {test_name}: expected {expected}, got {actual}

## Suggested focus
- {short hint, optional}

You DO NOT modify files. Just build, test, and hand off.
"""


def build_executor_tools(project_dir: str, iteration: int, max_iterations: int):

    @tool
    def build() -> str:
        """Compile and link the project. Returns full compiler/linker output."""
        return build_makefile.invoke({"project_dir": project_dir})

    @tool
    def run_tests_tool() -> str:
        """Run tests against the built executable. Returns full test output."""
        # Locate the built exe in the project output dir
        project_path = Path(project_dir)
        exe_candidates = list(project_path.rglob("*.exe")) + list(project_path.rglob("*.out"))
        if not exe_candidates:
            return "ERROR: No built executable found in project directory"
        exe_path = str(exe_candidates[0])
        # Run with empty test cases to validate the exe at least launches
        test_cases_json = json.dumps({"strategy": "stdin_stdout", "tests": []})
        result = run_tests(exe_path, test_cases_json)
        if result.get("error") and not result.get("total"):
            return f"ERROR: {result['error']}"
        passed = result.get("passed", False)
        total = result.get("total", 0)
        failed = result.get("failed", 0)
        return f"{'OK' if passed else 'FAIL'}: {total - failed}/{total} tests passed"

    @tool
    def success(summary_md: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        """HANDOFF (success path): everything green. Pass a user-facing summary."""
        from langchain_core.messages import ToolMessage
        return Command(
            graph=Command.PARENT,
            update={
                "phase": "done",
                "last_status": "success",
                "executor_summary_md": summary_md,
                "executor_messages": [ToolMessage("Execution succeeded.", tool_call_id=tool_call_id)],
            },
        )

    @tool
    def back_to_code(feedback_md: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        """HANDOFF (failure path): pass structured Markdown feedback to the Coder.

        If max_iterations is reached, this transitions to 'done' with status
        'max_iterations_reached' instead of looping back.
        """
        from langchain_core.messages import ToolMessage
        next_iter = iteration + 1
        if next_iter > max_iterations:
            return Command(
                graph=Command.PARENT,
                update={
                    "phase": "done",
                    "last_status": "max_iterations_reached",
                    "feedback_md": feedback_md,
                    "executor_messages": [ToolMessage("Max iterations reached.", tool_call_id=tool_call_id)],
                },
            )
        return Command(
            graph=Command.PARENT,
            update={
                "phase": "coding",
                "iteration": next_iter,
                "feedback_md": feedback_md,
                "executor_messages": [ToolMessage(f"Build/test failed. Sending back to coder (iteration {next_iter}/{max_iterations}).", tool_call_id=tool_call_id)],
            },
        )

    # rename to match contract; ReAct discovers tools by .name
    run_tests_tool.name = "run_tests"
    return [build, run_tests_tool, success, back_to_code]


def create_executor_node(llm):
    """V5 Executor node — receives coder_summary_md, builds, tests, handoffs."""
    from langgraph.prebuilt import create_react_agent

    def executor_node(state):
        project_dir = state.get("project_dir") or "output/_v5_default"
        tools = build_executor_tools(project_dir, state["iteration"], state["max_iterations"])
        ctx = (
            EXECUTOR_SYSTEM_PROMPT
            + "\n\n## Coder summary\n"
            + state.get("coder_summary_md", "")
        )
        react = create_react_agent(llm, tools=tools, prompt=ctx)
        # Always seed fresh — replaying prior executor_messages (which end with a
        # ToolMessage from success/back_to_code) confuses some providers and
        # produces malformed message sequences (HTTP 400).
        seed = [{"role": "user", "content": "Build the project and run tests, then hand off via success() or back_to_code()."}]
        result = react.invoke({"messages": seed})
        new_msgs = result["messages"][len(seed):]
        return {"executor_messages": new_msgs}

    return executor_node
