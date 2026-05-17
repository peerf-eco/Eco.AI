"""Type backbone smoke tests for pi_agent_core."""
from __future__ import annotations

from pydantic import BaseModel, TypeAdapter

from agent.pi_agent_core.types import (
    AgentEndEvent, AgentEvent, AgentStartEvent, AgentTool, AgentToolResult,
    BeforeToolCallResult, ToolExecutionStartEvent, TurnEndEvent,
)
from agent.pi_ai.types import AssistantMessage, TextContent


class _DummyArgs(BaseModel):
    x: int


async def _noop_execute(call_id, params, signal, on_update):
    return AgentToolResult(content=[TextContent(text="ok")], details=None)


def test_agent_tool_construction():
    t = AgentTool(
        name="t", description="d", label="L",
        parameters=_DummyArgs, execute=_noop_execute,
    )
    assert t.name == "t"
    pi_tool = t.to_pi_ai_tool()
    assert pi_tool.name == "t"
    assert "properties" in pi_tool.parameters  # JSON schema generated


def test_agent_tool_result_default():
    r = AgentToolResult()
    assert r.content == []
    assert r.details is None


def test_before_tool_call_result_block_default_false():
    r = BeforeToolCallResult()
    assert r.block is False
    assert r.reason is None


def test_agent_event_discriminator_round_trip():
    ev = ToolExecutionStartEvent(toolCallId="c1", toolName="foo", args={"x": 1})
    adapter = TypeAdapter(AgentEvent)
    restored = adapter.validate_python(ev.model_dump())
    assert isinstance(restored, ToolExecutionStartEvent)
    assert restored.toolCallId == "c1"


def test_agent_start_end_events():
    start = AgentStartEvent()
    end = AgentEndEvent(messages=[])
    assert start.type == "agent_start"
    assert end.type == "agent_end"
    assert end.messages == []


def test_turn_end_with_assistant_message():
    msg = AssistantMessage(api="x", provider="y", model="z", timestamp=1)
    ev = TurnEndEvent(message=msg, toolResults=[])
    assert ev.message.role == "assistant"
