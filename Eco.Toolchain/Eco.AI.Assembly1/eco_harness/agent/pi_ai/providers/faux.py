"""faux - scripted provider for testing.

Accepts a script of events (or a list of partial messages) and emits them as
a real AsyncIterator[AssistantMessageEvent]. Use this in tests to exercise
agent loops without hitting any real LLM endpoint.

Smaller than upstream pi-mono faux.ts (we don't need its full schema-driven mode
- our tests pre-build events directly).
"""
from __future__ import annotations

import time
from typing import AsyncIterator, Optional

from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.types import (
    AssistantMessage, AssistantMessageEvent, Context, DoneEvent, Model,
    StartEvent, StreamOptions, TextContent, TextDeltaEvent, TextEndEvent,
    TextStartEvent, ThinkingContent, ThinkingDeltaEvent, ThinkingEndEvent,
    ThinkingStartEvent, ToolCall, ToolCallEndEvent, ToolCallStartEvent,
)


def make_faux_provider(
    *,
    text: Optional[str] = None,
    thinking: Optional[str] = None,
    tool_calls: Optional[list[dict]] = None,  # [{name, arguments}]
    stop_reason: str = "stop",
):
    """Build a StreamFunction-compatible callable that emits a fixed sequence.

    Example:
        provider = make_faux_provider(
            thinking="thinking...",
            text="hello world",
            tool_calls=[{"name": "search", "arguments": {"q": "x"}}],
        )
        register_provider("faux", provider)
        model.api = "faux"  # routes to this
    """
    async def _stream(
        model: Model,
        context: Context,
        options: Optional[StreamOptions] = None,
    ) -> AsyncIterator[AssistantMessageEvent]:
        partial = AssistantMessage(
            api=model.api,
            provider=model.provider,
            model=model.id,
            timestamp=int(time.time() * 1000),
        )
        yield StartEvent(partial=partial.model_copy(deep=True))
        idx = -1

        if thinking:
            idx += 1
            yield ThinkingStartEvent(contentIndex=idx, partial=partial.model_copy(deep=True))
            yield ThinkingDeltaEvent(contentIndex=idx, delta=thinking, partial=partial.model_copy(deep=True))
            partial.content.append(ThinkingContent(thinking=thinking))
            yield ThinkingEndEvent(contentIndex=idx, content=thinking, partial=partial.model_copy(deep=True))

        if text:
            idx += 1
            yield TextStartEvent(contentIndex=idx, partial=partial.model_copy(deep=True))
            yield TextDeltaEvent(contentIndex=idx, delta=text, partial=partial.model_copy(deep=True))
            partial.content.append(TextContent(text=text))
            yield TextEndEvent(contentIndex=idx, content=text, partial=partial.model_copy(deep=True))

        if tool_calls:
            for i, tc in enumerate(tool_calls):
                idx += 1
                yield ToolCallStartEvent(contentIndex=idx, partial=partial.model_copy(deep=True))
                tc_obj = ToolCall(
                    id=tc.get("id", f"faux_call_{i}"),
                    name=tc["name"],
                    arguments=tc.get("arguments", {}),
                )
                partial.content.append(tc_obj)
                yield ToolCallEndEvent(
                    contentIndex=idx, toolCall=tc_obj,
                    partial=partial.model_copy(deep=True),
                )

        reason = "toolUse" if tool_calls else stop_reason
        partial.stopReason = reason
        yield DoneEvent(reason=reason, message=partial.model_copy(deep=True))  # type: ignore[arg-type]

    return _stream


# Default registration: registers under "faux" so tests can construct Model(api="faux")
register_provider("faux", make_faux_provider(text=""))
