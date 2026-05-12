from pydantic import BaseModel
from agent.v6.eco_agent import (
    ToolResult, EcoTool, EventType, EcoAgentEvent, EcoAgentResult,
)


def test_tool_result_defaults():
    r = ToolResult(content="hello")
    assert r.content == "hello"
    assert r.details is None
    assert r.is_error is False


def test_tool_result_error_form():
    r = ToolResult(content="boom", is_error=True, details={"phase": "fetch"})
    assert r.is_error is True
    assert r.details == {"phase": "fetch"}


def test_eco_tool_holds_schema_and_executor():
    class Args(BaseModel):
        x: int
    def ex(a: Args) -> ToolResult:
        return ToolResult(content=str(a.x))
    t = EcoTool(name="t", description="d", args_schema=Args, execute=ex)
    assert t.name == "t"
    assert t.args_schema is Args
    assert t.execute(Args(x=5)).content == "5"


def test_event_type_values():
    assert EventType.DONE.value == "done"
    assert EventType.MAX_ITERS.value == "max_iters"
    assert EventType.TOOL_START.value == "tool_call_start"


def test_eco_agent_event_carries_payload():
    e = EcoAgentEvent(type=EventType.ITERATION, data={"i": 3})
    assert e.type == EventType.ITERATION
    assert e.data == {"i": 3}


def test_eco_agent_result_has_status_and_stop_payload():
    r = EcoAgentResult(
        status="done", stop_tool_name="submit", stop_payload={"x": 1},
        history=[], error="",
    )
    assert r.status == "done"
    assert r.stop_tool_name == "submit"
    assert r.stop_payload == {"x": 1}
