def test_success_tool_returns_command_to_done():
    from agent.executor import build_executor_tools
    from langgraph.types import Command

    tools = build_executor_tools(project_dir="/tmp/p", iteration=1, max_iterations=5)
    success = next(t for t in tools if t.name == "success")
    result = success.invoke({"summary_md": "all green"})
    assert isinstance(result, Command)
    assert result.update["phase"] == "done"
    assert result.update["last_status"] == "success"


def test_back_to_code_returns_command_to_coding_with_increment():
    from agent.executor import build_executor_tools
    from langgraph.types import Command

    tools = build_executor_tools(project_dir="/tmp/p", iteration=2, max_iterations=5)
    back = next(t for t in tools if t.name == "back_to_code")
    result = back.invoke({"feedback_md": "## Stage: build\n## Status: FAIL\n## Errors\n- a.c:1: bad"})
    assert isinstance(result, Command)
    assert result.update["phase"] == "coding"
    assert result.update["iteration"] == 3
    assert "FAIL" in result.update["feedback_md"]


def test_back_to_code_at_max_iterations_marks_done():
    from agent.executor import build_executor_tools
    from langgraph.types import Command

    tools = build_executor_tools(project_dir="/tmp/p", iteration=5, max_iterations=5)
    back = next(t for t in tools if t.name == "back_to_code")
    result = back.invoke({"feedback_md": "## Stage: test\n## Status: FAIL"})
    assert result.update["phase"] == "done"
    assert result.update["last_status"] == "max_iterations_reached"
