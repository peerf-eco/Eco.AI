"""Regression test for the pi_ai bridge in EcoAgent.

The whole point of this bridge: when llm is a ChatOpenAI pointed at an
OpenAI-compat endpoint that streams `delta.reasoning`, the agent must
emit THINKING_DELTA events. langchain_openai 1.2.1 dropped that field
silently — pi_ai reads it raw.

This is the END-TO-END regression test for the bug pi-port exists to fix,
exercised through the real EcoAgent loop (not just pi_ai in isolation).
"""
from __future__ import annotations

import httpx
import respx
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from agent.v6.eco_agent import EcoAgent, EcoTool, EventType, ToolResult


URL = "https://openrouter.ai/api/v1/chat/completions"


def _sse(*payloads: str) -> str:
    parts = [f"data: {p}\n\n" for p in payloads]
    parts.append("data: [DONE]\n\n")
    return "".join(parts)


class _StopArgs(BaseModel):
    message: str


def _make_stop_tool() -> EcoTool:
    return EcoTool(
        name="done",
        description="stop the run",
        args_schema=_StopArgs,
        execute=lambda a: ToolResult(content="never executed - it is the stop tool"),
    )


def _make_chat_openai() -> ChatOpenAI:
    return ChatOpenAI(
        model="moonshotai/kimi-k2-thinking",
        openai_api_key="sk-test",
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0,
    )


@respx.mock
def test_reasoning_delta_emitted_as_thinking_event():
    """★ THE regression test: SSE with delta.reasoning -> THINKING_DELTA event."""
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","reasoning":"thinking step one..."}}]}',
        '{"choices":[{"delta":{"reasoning":" thinking step two..."}}]}',
        '{"choices":[{"delta":{"content":"answer"}}]}',
        # Provider emits the final stop tool call
        '{"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1","type":"function","function":{"name":"done","arguments":"{\\"message\\":\\"ok\\"}"}}]}}]}',
        '{"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
    )
    respx.post(URL).mock(return_value=httpx.Response(
        200, content=body, headers={"content-type": "text/event-stream"},
    ))

    seen_events = []
    agent = EcoAgent(
        llm=_make_chat_openai(),
        system_prompt="sys",
        tools=[_make_stop_tool()],
        stop_tool="done",
        max_iters=3,
        on_event=seen_events.append,
    )
    result = agent.run("hi")

    # Bridge must have produced the THINKING_DELTA events.
    thinking_events = [e for e in seen_events if e.type == EventType.THINKING_DELTA]
    assert len(thinking_events) == 2
    assert thinking_events[0].data["content"] == "thinking step one..."
    assert thinking_events[1].data["content"] == " thinking step two..."

    # And the regular TEXT_DELTA still fires.
    text_events = [e for e in seen_events if e.type == EventType.TEXT_DELTA]
    assert any(e.data["content"] == "answer" for e in text_events)

    # And the stop-tool flow still produces a proper "done" result.
    assert result.status == "done"
    assert result.stop_tool_name == "done"
    assert result.stop_payload == {"message": "ok"}


@respx.mock
def test_reasoning_content_field_also_supported():
    """Some providers use `reasoning_content` instead of `reasoning`. Both work."""
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","reasoning_content":"alt-field thinking"}}]}',
        '{"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1","type":"function","function":{"name":"done","arguments":"{\\"message\\":\\"x\\"}"}}]}}]}',
        '{"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
    )
    respx.post(URL).mock(return_value=httpx.Response(
        200, content=body, headers={"content-type": "text/event-stream"},
    ))

    seen = []
    agent = EcoAgent(
        llm=_make_chat_openai(),
        system_prompt="sys",
        tools=[_make_stop_tool()],
        stop_tool="done",
        max_iters=3,
        on_event=seen.append,
    )
    result = agent.run("hi")
    thinking = [e.data["content"] for e in seen if e.type == EventType.THINKING_DELTA]
    assert thinking == ["alt-field thinking"]
    assert result.status == "done"


@respx.mock
def test_text_only_no_reasoning_still_works():
    """When the provider sends no reasoning, the loop still terminates normally."""
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","content":"just text"}}]}',
        '{"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c1","type":"function","function":{"name":"done","arguments":"{\\"message\\":\\"ok\\"}"}}]}}]}',
        '{"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
    )
    respx.post(URL).mock(return_value=httpx.Response(
        200, content=body, headers={"content-type": "text/event-stream"},
    ))

    seen = []
    agent = EcoAgent(
        llm=_make_chat_openai(),
        system_prompt="sys",
        tools=[_make_stop_tool()],
        stop_tool="done",
        max_iters=3,
        on_event=seen.append,
    )
    result = agent.run("hi")
    assert not any(e.type == EventType.THINKING_DELTA for e in seen)
    text = [e.data["content"] for e in seen if e.type == EventType.TEXT_DELTA]
    assert text == ["just text"]
    assert result.status == "done"
