"""openai-completions provider - async streaming via direct httpx.

Mirrors @mariozechner/pi-ai/src/providers/openai-completions.ts (894 LOC TS).

Why httpx directly instead of the openai SDK:
  The openai Python SDK wraps response chunks in its own Pydantic models.
  Those models silently drop unknown fields like `delta.reasoning` - exactly
  the same bug as langchain_openai 1.2.1. Going direct lets us read the raw
  dict before any wrapper touches it.

Critical line: see _extract_reasoning() - the one feature this whole port exists for.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator, Optional

import httpx

from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.env_api_keys import get_api_key
from agent.pi_ai.providers.simple_options import apply_reasoning
from agent.pi_ai.providers.transform_messages import transform_messages
from agent.pi_ai.types import (
    AssistantMessage, AssistantMessageEvent, Context, Cost,
    DoneEvent, ErrorEvent, Model, OpenAICompletionsCompat, SimpleStreamOptions,
    StartEvent, StreamOptions, TextContent, TextDeltaEvent, TextEndEvent,
    TextStartEvent, ThinkingContent, ThinkingDeltaEvent, ThinkingEndEvent,
    ThinkingStartEvent, Tool, ToolCall, ToolCallDeltaEvent, ToolCallEndEvent,
    ToolCallStartEvent, Usage,
)
from agent.pi_ai.utils.event_stream import parse_sse
from agent.pi_ai.utils.json_parse import parse_strict


# Conservative margin kept free of the context window (system overhead,
# tool schemas, reasoning scratch, etc.) when clamping max_tokens.
_CTX_SAFETY_MARGIN = 4_000


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token). Good enough for a safety clamp
    that only ever *reduces* the requested output budget."""
    return max(1, len(text or "") // 4)


# ── Request body assembly ────────────────────────────────────────────────────
def _build_request_body(
    model: Model,
    context: Context,
    opts: Optional[StreamOptions],
) -> dict:
    """Assemble the OpenAI chat-completions request body."""
    body: dict[str, Any] = {
        "model": model.id,
        "messages": _prepend_system(
            transform_messages(context.messages, model),
            context.systemPrompt,
        ),
        "stream": True,
    }
    compat = model.compat or OpenAICompletionsCompat()

    # max-tokens field name varies by provider
    max_field = compat.maxTokensField or "max_tokens"
    if isinstance(opts, StreamOptions) and opts.maxTokens:
        body[max_field] = opts.maxTokens
    elif model.maxTokens:
        body[max_field] = model.maxTokens

    # Clamp the requested output tokens so they fit the model's context
    # window *after* the (often very large, stitched-source) system prompt is
    # included. Without this, a role whose per_query_tokens budget exceeds the
    # remaining context (e.g. 200k requested vs ~80k of injected source inside
    # a 262k window) triggers HTTP 400 "maximum context length exceeded".
    if max_field in body and model.contextWindow:
        # body["messages"] already includes the system prompt as its first
        # message (see _prepend_system), so estimate from there alone to avoid
        # double-counting it.
        est_input = 0
        for _msg in body.get("messages", []):
            _content = _msg.get("content")
            if isinstance(_content, str):
                est_input += _estimate_tokens(_content)
            elif isinstance(_content, list):
                for _part in _content:
                    if isinstance(_part, dict) and isinstance(_part.get("text"), str):
                        est_input += _estimate_tokens(_part["text"])
        headroom = model.contextWindow - est_input - _CTX_SAFETY_MARGIN
        if headroom < 0:
            headroom = 0
        body[max_field] = min(int(body[max_field]), headroom)

    if opts and opts.temperature is not None:
        body["temperature"] = opts.temperature

    # Tools
    if context.tools:
        body["tools"] = _format_tools(context.tools, compat)

    # Usage in streaming (most providers support it; some don't)
    if compat.supportsUsageInStreaming is not False:
        body["stream_options"] = {"include_usage": True}

    # OpenRouter cost accounting: adds usage.cost + cached_tokens to the
    # final stream chunk (no-op fields for other providers, so gate on URL).
    if "openrouter" in (model.baseUrl or ""):
        body["usage"] = {"include": True}

    # Reasoning (delegates to simple_options.apply_reasoning)
    if isinstance(opts, SimpleStreamOptions):
        apply_reasoning(body, model, opts)

    # OpenRouter provider routing
    if compat.openRouterRouting:
        body["provider"] = compat.openRouterRouting.model_dump(exclude_none=True)

    return body


def _prepend_system(messages: list[dict], system_prompt: Optional[str]) -> list[dict]:
    if not system_prompt:
        return messages
    return [{"role": "system", "content": system_prompt}, *messages]


def _format_tools(tools: list[Tool], compat: OpenAICompletionsCompat) -> list[dict]:
    """Render Tool[] in OpenAI tool-calling format."""
    out = []
    for t in tools:
        entry = {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        if compat.supportsStrictMode is not False:
            entry["function"]["strict"] = False  # default off
        out.append(entry)
    return out


# ── URL + headers ────────────────────────────────────────────────────────────
def _build_url(model: Model) -> str:
    base = model.baseUrl.rstrip("/")
    # OpenRouter and most OpenAI-compat endpoints use /chat/completions
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _build_headers(model: Model, opts: Optional[StreamOptions]) -> dict[str, str]:
    api_key = (
        opts.apiKey if (opts and opts.apiKey)
        else get_api_key(model.provider)
    )
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if model.headers:
        headers.update(model.headers)
    if opts and opts.headers:
        headers.update(opts.headers)
    # OpenRouter wants HTTP-Referer + X-Title for analytics; harmless elsewhere
    headers.setdefault("HTTP-Referer", "https://github.com/eco-toolchain/pi-ai-py")
    headers.setdefault("X-Title", "pi-ai-py")
    return headers


# ── Reasoning extraction (★ THE critical helpers) ────────────────────────────
def _extract_reasoning(delta: dict) -> Optional[str]:
    """★ The one line this entire port exists for.

    OpenAI-compat reasoning models (Kimi/GLM/DeepSeek/MiMo/...) send their
    chain-of-thought in `delta.reasoning` or `delta.reasoning_content`.
    langchain_openai 1.2.1 drops both. We read both directly from the raw dict.

    Replicates hermes-agent/run_agent.py:5673.
    """
    val = delta.get("reasoning") or delta.get("reasoning_content")
    if isinstance(val, str) and val:
        return val
    return None


def _extract_reasoning_from_details(message_dict: dict) -> Optional[str]:
    """Some providers (OpenRouter unified format) put reasoning in an array
    of {summary|content|text} dicts under message.reasoning_details. Read it
    on the final message if present."""
    details = message_dict.get("reasoning_details")
    if not isinstance(details, list):
        return None
    parts = []
    for d in details:
        if not isinstance(d, dict):
            continue
        v = d.get("text") or d.get("summary") or d.get("content")
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    return "\n\n".join(parts) if parts else None


# ── Usage normalization (OpenAI shape -> pi_ai Usage) ────────────────────────
def _normalize_usage(raw: dict) -> Usage:
    """Map OpenAI usage chunk {prompt_tokens, completion_tokens, total_tokens,
    prompt_tokens_details{cached_tokens}, ...} -> pi_ai Usage.

    extra="allow" preserves the original raw fields too, so callers that need
    OpenAI-shape can still read them off the model.
    """
    prompt = int(raw.get("prompt_tokens") or 0)
    completion = int(raw.get("completion_tokens") or 0)
    total = int(raw.get("total_tokens") or (prompt + completion))
    cache_read = 0
    details = raw.get("prompt_tokens_details")
    if isinstance(details, dict):
        cache_read = int(details.get("cached_tokens") or 0)
    kwargs: dict = {}
    # OpenRouter accounting (usage:{include:true}) sends "cost" as a plain
    # float — fold it into the structured Cost field instead of letting the
    # raw passthrough collide with it.
    raw_cost = raw.get("cost")
    if isinstance(raw_cost, (int, float)):
        kwargs["cost"] = Cost(total=float(raw_cost))
    return Usage(
        input=prompt,
        output=completion,
        totalTokens=total,
        cacheRead=cache_read,
        **kwargs,
        **{k: v for k, v in raw.items() if k not in (
            "prompt_tokens", "completion_tokens", "total_tokens",
            "prompt_tokens_details", "cost",
        )},
    )


# ── Tool-call accumulator (delta -> ToolCall) ────────────────────────────────
class _ToolCallAcc:
    """Accumulates streaming tool-call deltas. OpenAI sends them as:
      delta.tool_calls = [{index, id?, function: {name?, arguments?}}]
    where each chunk extends a previous one (matched by index)."""

    def __init__(self) -> None:
        self._by_idx: dict[int, dict[str, Any]] = {}

    def feed(self, tc_deltas: list[dict]) -> list[tuple[int, str]]:
        """Apply a batch of tool-call deltas. Returns list of (index, arg_delta_str)
        so caller can emit toolcall_delta events with the raw JSON fragment."""
        emitted: list[tuple[int, str]] = []
        for tc in tc_deltas:
            idx = tc.get("index", 0)
            slot = self._by_idx.setdefault(idx, {
                "id": "",
                "name": "",
                "arguments_raw": "",
            })
            if tc.get("id"):
                slot["id"] = tc["id"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                slot["name"] += fn["name"]
            if fn.get("arguments"):
                slot["arguments_raw"] += fn["arguments"]
                emitted.append((idx, fn["arguments"]))
        return emitted

    def finalize(self) -> list[ToolCall]:
        """Build complete ToolCall objects. Argument strings are parsed strict;
        on failure we fall back to {} so the agent sees malformed calls explicitly."""
        out: list[ToolCall] = []
        for idx in sorted(self._by_idx.keys()):
            slot = self._by_idx[idx]
            try:
                args = parse_strict(slot["arguments_raw"]) if slot["arguments_raw"] else {}
            except ValueError:
                args = {}
            out.append(ToolCall(
                id=slot["id"] or f"call_{idx}",
                name=slot["name"],
                arguments=args if isinstance(args, dict) else {},
            ))
        return out

    def indices(self) -> list[int]:
        return sorted(self._by_idx.keys())


# ── Stream-state container ───────────────────────────────────────────────────
class _StreamState:
    """Mutable state assembled across stream chunks. Yields AssistantMessageEvent
    objects via emit_* methods."""

    def __init__(self, model: Model) -> None:
        self.partial = AssistantMessage(
            api=model.api,
            provider=model.provider,
            model=model.id,
            timestamp=int(time.time() * 1000),
        )
        self.tool_acc = _ToolCallAcc()
        self.text_buf = ""
        self.thinking_buf = ""
        self.text_started = False
        self.thinking_started = False
        self.tool_started: set[int] = set()
        self.content_idx = -1  # advanced as new content blocks open

    def _next_content_idx(self) -> int:
        self.content_idx += 1
        return self.content_idx

    def finalize_text(self) -> Optional[TextEndEvent]:
        if not self.text_started:
            return None
        ev = TextEndEvent(
            contentIndex=self.content_idx,
            content=self.text_buf,
            partial=self.partial.model_copy(deep=True),
        )
        self.partial.content.append(TextContent(text=self.text_buf))
        self.text_buf = ""
        self.text_started = False
        return ev

    def finalize_thinking(self) -> Optional[ThinkingEndEvent]:
        if not self.thinking_started:
            return None
        ev = ThinkingEndEvent(
            contentIndex=self.content_idx,
            content=self.thinking_buf,
            partial=self.partial.model_copy(deep=True),
        )
        self.partial.content.append(ThinkingContent(thinking=self.thinking_buf))
        self.thinking_buf = ""
        self.thinking_started = False
        return ev


# ── Main stream function (entry point) ───────────────────────────────────────
async def stream_openai_completions(
    model: Model,
    context: Context,
    options: Optional[StreamOptions] = None,
) -> AsyncIterator[AssistantMessageEvent]:
    """Async stream from an OpenAI-compat /chat/completions endpoint.

    Contract: NEVER raises (per pi_ai StreamFunction protocol). All errors are
    emitted as ErrorEvent + AssistantMessage(stopReason="error"|"aborted")."""
    state = _StreamState(model)
    yield StartEvent(partial=state.partial.model_copy(deep=True))

    try:
        async for event in _stream_inner(model, context, options, state):
            yield event
    except asyncio.CancelledError:
        # Async cancellation translates to aborted
        yield _build_error_event(state, reason="aborted", err_msg="cancelled")
        raise  # re-raise so caller's cancellation semantics still work
    except Exception as e:  # noqa: BLE001 - last-resort safety net
        yield _build_error_event(state, reason="error", err_msg=f"{type(e).__name__}: {e}")


async def _stream_inner(
    model: Model,
    context: Context,
    options: Optional[StreamOptions],
    state: _StreamState,
) -> AsyncIterator[AssistantMessageEvent]:
    body = _build_request_body(model, context, options)
    url = _build_url(model)
    headers = _build_headers(model, options)
    signal: Optional[asyncio.Event] = getattr(options, "signal", None) if options else None

    timeout = httpx.Timeout(connect=30.0, read=120.0, write=120.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=body, headers=headers) as response:
            if options and options.onResponse:
                try:
                    options.onResponse(response, model)
                except Exception:  # noqa: BLE001 - user hook must not break stream
                    pass

            if response.status_code >= 400:
                err_body = await response.aread()
                yield _build_error_event(
                    state, reason="error",
                    err_msg=f"HTTP {response.status_code}: {err_body.decode('utf-8', errors='replace')[:500]}",
                )
                return

            async for chunk in parse_sse(response):
                if signal is not None and signal.is_set():
                    yield _build_error_event(state, reason="aborted", err_msg="abort signal set")
                    return

                async for event in _handle_chunk(chunk, state):
                    yield event

    # Stream ended cleanly - close out any unfinished blocks and emit done
    closing = state.finalize_text()
    if closing:
        yield closing
    closing = state.finalize_thinking()
    if closing:
        yield closing

    # Promote accumulated tool calls onto the partial message
    tool_calls = state.tool_acc.finalize()
    for tc in tool_calls:
        state.partial.content.append(tc)
    state.partial.stopReason = "toolUse" if tool_calls else "stop"
    yield DoneEvent(
        reason=("toolUse" if tool_calls else "stop"),
        message=state.partial.model_copy(deep=True),
    )


# ── Per-chunk handler (where reasoning passthrough fires) ────────────────────
async def _handle_chunk(chunk: dict, state: _StreamState) -> AsyncIterator[AssistantMessageEvent]:
    """Process one SSE chunk and emit zero or more AssistantMessageEvents."""
    choices = chunk.get("choices") or []
    # Usage may arrive in a dedicated empty-choices chunk (OpenAI) OR in the
    # final chunk together with choices (OpenRouter puts it next to the
    # finish_reason=stop delta) — capture it wherever it shows up.
    usage = chunk.get("usage")
    if usage:
        state.partial.usage = _normalize_usage(usage)
    if not choices:
        return
    choice = choices[0]
    delta = choice.get("delta") or {}

    # ★ REASONING - the headline feature
    reasoning = _extract_reasoning(delta)
    if reasoning:
        # Close text block if open (thinking can't interleave with text)
        closing = state.finalize_text()
        if closing:
            yield closing
        if not state.thinking_started:
            idx = state._next_content_idx()
            state.thinking_started = True
            yield ThinkingStartEvent(contentIndex=idx, partial=state.partial.model_copy(deep=True))
        state.thinking_buf += reasoning
        yield ThinkingDeltaEvent(
            contentIndex=state.content_idx,
            delta=reasoning,
            partial=state.partial.model_copy(deep=True),
        )

    # TEXT content
    content = delta.get("content")
    if isinstance(content, str) and content:
        # Close thinking if open
        closing = state.finalize_thinking()
        if closing:
            yield closing
        if not state.text_started:
            idx = state._next_content_idx()
            state.text_started = True
            yield TextStartEvent(contentIndex=idx, partial=state.partial.model_copy(deep=True))
        state.text_buf += content
        yield TextDeltaEvent(
            contentIndex=state.content_idx,
            delta=content,
            partial=state.partial.model_copy(deep=True),
        )

    # TOOL CALLS
    tc_deltas = delta.get("tool_calls")
    if isinstance(tc_deltas, list) and tc_deltas:
        # Close text/thinking first
        closing = state.finalize_text()
        if closing:
            yield closing
        closing = state.finalize_thinking()
        if closing:
            yield closing
        emitted = state.tool_acc.feed(tc_deltas)
        for idx in state.tool_acc.indices():
            if idx not in state.tool_started:
                state.tool_started.add(idx)
                content_idx = state._next_content_idx()
                yield ToolCallStartEvent(
                    contentIndex=content_idx,
                    partial=state.partial.model_copy(deep=True),
                )
        for _idx, frag in emitted:
            yield ToolCallDeltaEvent(
                contentIndex=state.content_idx,
                delta=frag,
                partial=state.partial.model_copy(deep=True),
            )

    # finish_reason hints stop - we honor it on the trailing chunk in caller


# ── Error helper + registration ──────────────────────────────────────────────
def _build_error_event(
    state: _StreamState, *, reason: str, err_msg: str,
) -> ErrorEvent:
    state.partial.stopReason = "aborted" if reason == "aborted" else "error"
    state.partial.errorMessage = err_msg
    return ErrorEvent(reason=reason, error=state.partial.model_copy(deep=True))


# Module-level registration
register_provider("openai-completions", stream_openai_completions)
