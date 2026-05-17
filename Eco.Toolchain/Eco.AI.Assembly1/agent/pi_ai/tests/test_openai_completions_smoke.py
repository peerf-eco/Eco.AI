"""openai_completions provider smoke test via respx mocked SSE.

★ The core test: confirms `delta.reasoning` from a mocked Kimi-style stream
reaches us as a ThinkingDeltaEvent. This is the regression test for the
single bug the entire pi-port exists to fix.
"""
from __future__ import annotations

import httpx
import pytest
import respx

from agent.pi_ai import Context, Model, ModelCost, stream_simple
from agent.pi_ai.types import (
    DoneEvent, ErrorEvent, OpenAICompletionsCompat, TextDeltaEvent,
    ThinkingDeltaEvent, ToolCallDeltaEvent,
)


URL = "https://openrouter.ai/api/v1/chat/completions"


def _sse(*payloads: str) -> str:
    """Build a mock SSE response body from a list of JSON payload strings."""
    parts = [f"data: {p}\n\n" for p in payloads]
    parts.append("data: [DONE]\n\n")
    return "".join(parts)


def _model(thinking_fmt: str = "openrouter") -> Model:
    return Model(
        id="moonshotai/kimi-k2-thinking", name="kimi",
        api="openai-completions", provider="openrouter",
        baseUrl="https://openrouter.ai/api/v1",
        cost=ModelCost(),
        compat=OpenAICompletionsCompat(thinkingFormat=thinking_fmt),
    )


@pytest.mark.asyncio
@respx.mock
async def test_text_only_stream():
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","content":"Hi"}}]}',
        '{"choices":[{"delta":{"content":" there"}}]}',
        '{"choices":[{"delta":{},"finish_reason":"stop"}]}',
        '{"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}',
    )
    respx.post(URL).mock(return_value=httpx.Response(
        200, content=body, headers={"content-type": "text/event-stream"},
    ))
    events = []
    async for ev in stream_simple(_model(), Context(systemPrompt="sys", messages=[])):
        events.append(ev)
    text_pieces = [e.delta for e in events if isinstance(e, TextDeltaEvent)]
    assert "".join(text_pieces) == "Hi there"
    assert isinstance(events[-1], DoneEvent)
    assert events[-1].message.usage.input == 5


@pytest.mark.asyncio
@respx.mock
async def test_reasoning_passthrough_via_reasoning_field():
    """★ This is the regression test for the bug pi-port exists to fix."""
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","reasoning":"Let me think..."}}]}',
        '{"choices":[{"delta":{"reasoning":" still thinking..."}}]}',
        '{"choices":[{"delta":{"content":"42"}}]}',
        '{"choices":[{"delta":{},"finish_reason":"stop"}]}',
    )
    respx.post(URL).mock(return_value=httpx.Response(
        200, content=body, headers={"content-type": "text/event-stream"},
    ))
    events = []
    async for ev in stream_simple(_model(), Context()):
        events.append(ev)
    thinking_deltas = [e.delta for e in events if isinstance(e, ThinkingDeltaEvent)]
    assert "".join(thinking_deltas) == "Let me think... still thinking..."
    text_deltas = [e.delta for e in events if isinstance(e, TextDeltaEvent)]
    assert "".join(text_deltas) == "42"


@pytest.mark.asyncio
@respx.mock
async def test_reasoning_passthrough_via_reasoning_content_field():
    """Some providers use `reasoning_content` instead of `reasoning`."""
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","reasoning_content":"thinking"}}]}',
        '{"choices":[{"delta":{"content":"done"}}]}',
        '{"choices":[{"delta":{},"finish_reason":"stop"}]}',
    )
    respx.post(URL).mock(return_value=httpx.Response(
        200, content=body, headers={"content-type": "text/event-stream"},
    ))
    events = []
    async for ev in stream_simple(_model(), Context()):
        events.append(ev)
    thinking = [e.delta for e in events if isinstance(e, ThinkingDeltaEvent)]
    assert thinking == ["thinking"]


@pytest.mark.asyncio
@respx.mock
async def test_tool_call_accumulation():
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","tool_calls":[{"index":0,"id":"call_1","function":{"name":"search","arguments":"{\\"q\\":"}}]}}]}',
        '{"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"hello\\"}"}}]}}]}',
        '{"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
    )
    respx.post(URL).mock(return_value=httpx.Response(
        200, content=body, headers={"content-type": "text/event-stream"},
    ))
    events = []
    async for ev in stream_simple(_model(), Context()):
        events.append(ev)
    deltas = [e.delta for e in events if isinstance(e, ToolCallDeltaEvent)]
    assert "".join(deltas) == '{"q":"hello"}'
    assert isinstance(events[-1], DoneEvent)
    tc = [c for c in events[-1].message.content if c.type == "toolCall"][0]
    assert tc.name == "search"
    assert tc.arguments == {"q": "hello"}


@pytest.mark.asyncio
@respx.mock
async def test_http_error_yields_error_event_not_exception():
    respx.post(URL).mock(return_value=httpx.Response(429, content=b'{"error":"rate limit"}'))
    events = []
    async for ev in stream_simple(_model(), Context()):
        events.append(ev)
    assert any(isinstance(e, ErrorEvent) for e in events)
    err = [e for e in events if isinstance(e, ErrorEvent)][0]
    assert "429" in (err.error.errorMessage or "")
