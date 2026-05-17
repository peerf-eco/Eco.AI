"""Type backbone smoke tests. Discriminated unions must serialize/deserialize
without losing the discriminator. Tests round-trip via model_dump -> parse_obj."""
from __future__ import annotations

from pydantic import TypeAdapter

from agent.pi_ai.types import (
    AssistantMessage, AssistantMessageEvent, DoneEvent, Message,
    TextContent, TextDeltaEvent, ThinkingContent, ToolCall, ToolResultMessage,
    UserMessage,
)


def test_user_message_with_string_content():
    m = UserMessage(content="hi", timestamp=123)
    assert m.role == "user"
    assert m.content == "hi"
    # round-trip
    adapter = TypeAdapter(Message)
    restored = adapter.validate_python(m.model_dump())
    assert isinstance(restored, UserMessage)


def test_assistant_message_with_mixed_content():
    m = AssistantMessage(
        api="openai-completions", provider="openrouter", model="kimi",
        content=[
            ThinkingContent(thinking="hmm..."),
            TextContent(text="answer"),
            ToolCall(id="c1", name="search", arguments={"q": "x"}),
        ],
        timestamp=123,
    )
    assert len(m.content) == 3
    assert m.content[0].type == "thinking"
    assert m.content[2].type == "toolCall"


def test_assistant_message_event_discriminator_round_trip():
    ev = TextDeltaEvent(
        contentIndex=0,
        delta="hello",
        partial=AssistantMessage(
            api="x", provider="y", model="z", timestamp=1,
        ),
    )
    adapter = TypeAdapter(AssistantMessageEvent)
    restored = adapter.validate_python(ev.model_dump())
    assert isinstance(restored, TextDeltaEvent)
    assert restored.delta == "hello"


def test_done_event():
    msg = AssistantMessage(api="a", provider="b", model="c", timestamp=1, stopReason="stop")
    ev = DoneEvent(reason="stop", message=msg)
    assert ev.reason == "stop"
    assert ev.message.stopReason == "stop"


def test_tool_result_message():
    m = ToolResultMessage(
        toolCallId="c1", toolName="search",
        content=[TextContent(text="result")],
        timestamp=123,
    )
    assert m.isError is False
    assert m.content[0].text == "result"
