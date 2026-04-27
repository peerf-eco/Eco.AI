def test_coder_has_done_tool():
    from agent.coder import build_coder_tools_v5

    tools = build_coder_tools_v5(work_dir="/tmp/whatever")
    names = [t.name for t in tools]
    assert "done" in names


def test_done_tool_returns_command_to_executing():
    from agent.coder import build_coder_tools_v5
    from langgraph.types import Command

    tools = build_coder_tools_v5(work_dir="/tmp/whatever")
    done = next(t for t in tools if t.name == "done")
    result = done.invoke({"args": {"summary_md": "wrote files"}, "name": "done", "type": "tool_call", "id": "test_call_id"})
    assert isinstance(result, Command)
    assert result.update["coder_summary_md"] == "wrote files"
    assert result.update["phase"] == "executing"


def test_create_coder_node_v5_seeds_with_plan_md():
    from agent.coder import create_coder_node_v5
    from langchain_core.runnables import Runnable
    from langchain_core.messages import AIMessage

    class _LLMStub(Runnable):
        def bind_tools(self, tools, **kw): return self
        def invoke(self, input, config=None, **kw): return AIMessage(content="ack")

    node = create_coder_node_v5(_LLMStub())
    state = {
        "planner_messages": [],
        "coder_messages": [],
        "executor_messages": [],
        "plan_md": "## Project: X\n\n## Components\n- **A** — source: sdk — r1",
        "feedback_md": "",
        "phase": "coding",
        "iteration": 0, "max_iterations": 5,
        "user_request": "x",
        "coder_summary_md": "",
        "executor_summary_md": "",
        "project_dir": "",
        "project_name": "",
        "last_status": "",
    }
    update = node(state)
    assert "coder_messages" in update
