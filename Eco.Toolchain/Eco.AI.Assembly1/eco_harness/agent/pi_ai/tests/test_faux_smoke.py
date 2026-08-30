"""Faux provider smoke test. Verifies the registry -> provider -> stream_simple
plumbing works end-to-end without any real network."""
from __future__ import annotations

import pytest

from agent.pi_ai import Context, Model, ModelCost, stream_simple, ToolCall
from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.providers.faux import make_faux_provider
from agent.pi_ai.types import (
    DoneEvent, StartEvent, TextDeltaEvent, ThinkingDeltaEvent,
)


def _make_test_model(provider_name: str = "faux-test") -> Model:
    return Model(
        id="test-model", name="test", api=provider_name,
        provider="faux", baseUrl="", cost=ModelCost(),
    )


@pytest.mark.asyncio
async def test_faux_text_only():
    register_provider("faux-text-only", make_faux_provider(text="hello world"))
    model = _make_test_model("faux-text-only")
    events = []
    async for ev in stream_simple(model, Context()):
        events.append(ev)
    assert isinstance(events[0], StartEvent)
    assert any(isinstance(e, TextDeltaEvent) and e.delta == "hello world" for e in events)
    assert isinstance(events[-1], DoneEvent)
    assert events[-1].message.content[0].type == "text"
    assert events[-1].message.content[0].text == "hello world"


@pytest.mark.asyncio
async def test_faux_with_thinking():
    register_provider("faux-thinking", make_faux_provider(thinking="reasoning...", text="answer"))
    model = _make_test_model("faux-thinking")
    events = []
    async for ev in stream_simple(model, Context()):
        events.append(ev)
    thinking_deltas = [e for e in events if isinstance(e, ThinkingDeltaEvent)]
    text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
    assert len(thinking_deltas) == 1
    assert thinking_deltas[0].delta == "reasoning..."
    assert len(text_deltas) == 1
    assert text_deltas[0].delta == "answer"


@pytest.mark.asyncio
async def test_faux_with_tool_call():
    register_provider("faux-tools", make_faux_provider(
        text="",
        tool_calls=[{"name": "search", "arguments": {"q": "x"}}],
    ))
    model = _make_test_model("faux-tools")
    events = []
    async for ev in stream_simple(model, Context()):
        events.append(ev)
    assert isinstance(events[-1], DoneEvent)
    tcs = [c for c in events[-1].message.content if isinstance(c, ToolCall)]
    assert len(tcs) == 1
    assert tcs[0].name == "search"
    assert tcs[0].arguments == {"q": "x"}
    assert events[-1].reason == "toolUse"
