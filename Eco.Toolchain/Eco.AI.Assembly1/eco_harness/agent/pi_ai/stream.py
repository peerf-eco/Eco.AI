"""Top-level streaming entry points.

stream_simple(model, context, opts) - async iter of AssistantMessageEvent.
complete(model, context, opts) - convenience: drains the stream, returns final
AssistantMessage (or raises if the stream ended with error/aborted).
"""
from __future__ import annotations

import time as _t
from typing import AsyncIterator, Optional

from agent.pi_ai.api_registry import get_provider, known_apis
from agent.pi_ai.types import (
    AssistantMessage, AssistantMessageEvent, Context, DoneEvent, ErrorEvent,
    Model, SimpleStreamOptions, StartEvent,
)


async def stream_simple(
    model: Model,
    context: Context,
    options: Optional[SimpleStreamOptions] = None,
) -> AsyncIterator[AssistantMessageEvent]:
    """Look up provider by model.api and delegate."""
    provider = get_provider(model.api)
    if provider is None:
        # Encode the error in the stream per StreamFunction contract
        partial = AssistantMessage(
            api=model.api, provider=model.provider, model=model.id,
            timestamp=int(_t.time() * 1000),
            stopReason="error",
            errorMessage=f"Unknown api {model.api!r}. Registered: {list(known_apis())}",
        )
        yield StartEvent(partial=partial.model_copy(deep=True))
        yield ErrorEvent(reason="error", error=partial)
        return
    async for ev in provider(model, context, options):
        yield ev


async def complete(
    model: Model,
    context: Context,
    options: Optional[SimpleStreamOptions] = None,
) -> AssistantMessage:
    """Drain stream and return the final AssistantMessage. Raises RuntimeError
    on stream error (errors are encoded inside, so callers wanting silent
    handling should use stream_simple directly)."""
    final: Optional[AssistantMessage] = None
    async for ev in stream_simple(model, context, options):
        if isinstance(ev, DoneEvent):
            final = ev.message
        elif isinstance(ev, ErrorEvent):
            raise RuntimeError(ev.error.errorMessage or "stream error")
    if final is None:
        raise RuntimeError("stream ended without done event")
    return final
