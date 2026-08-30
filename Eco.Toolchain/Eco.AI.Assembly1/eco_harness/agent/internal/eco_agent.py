"""EcoAgent - claude-code-style agent loop for internal nodes.

Runs entirely on pi-ai (no langchain). The agent loop owns:
- history as list[pi_ai.Message] (UserMessage / AssistantMessage / ToolResultMessage)
- LLM call via pi_ai.stream_simple (reasoning passthrough included)
- sync tool execution (EcoTool.execute is a sync callable)
- before/after_tool_call hooks, prepare_arguments shim
- stop-tool dispatch and EcoAgentResult plumbing

Public surface is preserved: EcoTool, ToolResult, EventType, EcoAgentEvent,
EcoAgentResult, EcoAgent. Existing callers (orchestrator, agents/, backend)
only need to swap their `llm: BaseChatModel` for `model: pi_ai.Model`.
"""
from __future__ import annotations

import asyncio
import json as _json
import time
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel, ValidationError

from eco_harness.agent.pi_ai import (
    AssistantMessage, Context, Model, SimpleStreamOptions,
    StreamOptions, TextContent, Tool, ToolCall, ToolResultMessage, UserMessage,
    stream_simple,
)
from eco_harness.agent.pi_ai.types import (
    DoneEvent, ErrorEvent, StreamFunction, TextDeltaEvent, ThinkingDeltaEvent,
)
from eco_harness.agent.internal.call_trace import write_call_trace


# ── Data types (public, unchanged) ────────────────────────────────────────────

@dataclass(frozen=True)
class ToolResult:
    """Outcome of a single tool execution.

    `content` is sent to the LLM as the textual tool result. `details` is for
    UI/logs and is NOT sent to the model.
    """
    content: str
    details: Optional[dict] = None
    is_error: bool = False


@dataclass(frozen=True)
class EcoTool:
    """A tool the agent can call. Mirrors pi-harness `Tool`.

    execute is a SYNC callable: (validated_args: BaseModel) -> ToolResult.
    """
    name: str
    description: str
    args_schema: type[BaseModel]
    execute: Callable[[BaseModel], ToolResult]


class EventType(str, Enum):
    START          = "start"
    TEXT_DELTA     = "text_delta"        # streaming visible content (final answer tokens)
    THINKING_DELTA = "thinking_delta"    # streaming reasoning/thinking tokens
    TOOL_START     = "tool_call_start"
    TOOL_END       = "tool_call_end"
    TOOL_UPDATE    = "tool_update"
    ITERATION      = "iteration"
    DONE           = "done"
    NO_TOOL_CALL   = "no_tool_call"
    MAX_ITERS      = "max_iters"
    USAGE          = "usage"             # per-LLM-call token accounting (data.usage)
    ERROR          = "error"


@dataclass(frozen=True)
class EcoAgentEvent:
    type: EventType
    data: dict


@dataclass(frozen=True)
class EcoAgentResult:
    status: str  # "done" | "no_tool_call" | "max_iters" | "error"
    stop_tool_name: str
    stop_payload: dict
    # History is a list of pi_ai Messages. Concrete types: UserMessage,
    # AssistantMessage, ToolResultMessage. The orchestrator only reads
    # the last assistant message's stop_payload, so the exact element
    # types are unimportant to most callers.
    history: list
    error: str


# ── Helpers (internal) ────────────────────────────────────────────────────────

def _now_ms() -> int:
    return int(time.time() * 1000)


def _usage_data(response) -> dict:
    """pi_ai Usage -> plain dict for the USAGE event. Tolerates providers that
    omit usage entirely (empty dict) so the UI can ignore the event."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    if isinstance(usage, dict):
        source = usage
    else:
        model_dump = getattr(usage, "model_dump", None)
        source = model_dump() if callable(model_dump) else {
            field: getattr(usage, field, 0)
            for field in ("input", "output", "cacheRead", "cacheWrite", "totalTokens")
        }
    def _int(value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0
    input_t = _int(source.get("input"))
    output_t = _int(source.get("output"))
    if not any((_int(source.get(k)) for k in ("input", "output", "cacheRead", "cacheWrite", "totalTokens"))):
        return {}
    return {
        "input": input_t,
        "output": output_t,
        "cache_read": _int(source.get("cacheRead")),
        "cache_write": _int(source.get("cacheWrite")),
        # Some providers omit totalTokens — fall back to input+output.
        "total": _int(source.get("totalTokens")) or (input_t + output_t),
    }


def _normalize_seed(seed) -> list:
    """Seed -> list of pi_ai Messages.

    Accepts:
    - str: wrapped in a UserMessage
    - list[Message]: passed through (callers may stitch a history themselves)
    """
    if isinstance(seed, str):
        return [UserMessage(content=seed, timestamp=_now_ms())]
    return list(seed)


def _eco_tools_to_pi_tools(eco_tools: list[EcoTool]) -> list[Tool]:
    """EcoTool[] -> pi_ai Tool[] (name + description + JSON-schema)."""
    out: list[Tool] = []
    for t in eco_tools:
        params: dict = {"type": "object", "properties": {}}
        if t.args_schema is not None:
            try:
                params = t.args_schema.model_json_schema()
            except Exception:  # noqa: BLE001 — tolerate malformed schemas
                pass
        out.append(Tool(name=t.name, description=t.description, parameters=params))
    return out


async def _drain_stream(
    stream_fn: StreamFunction,
    model: Model,
    context: Context,
    options: Optional[StreamOptions],
    on_text_delta: Callable[[str], None],
    on_thinking_delta: Callable[[str], None],
) -> AssistantMessage:
    """Drive the pi_ai stream, emit text/thinking deltas via callbacks,
    return the final AssistantMessage (DoneEvent.message or ErrorEvent.error)."""
    final_message: Optional[AssistantMessage] = None
    async for ev in stream_fn(model, context, options):
        if isinstance(ev, TextDeltaEvent) and ev.delta:
            on_text_delta(ev.delta)
        elif isinstance(ev, ThinkingDeltaEvent) and ev.delta:
            on_thinking_delta(ev.delta)
        elif isinstance(ev, DoneEvent):
            final_message = ev.message
            break
        elif isinstance(ev, ErrorEvent):
            final_message = ev.error
            break
    if final_message is None:
        # No DoneEvent/ErrorEvent — synthesize an error message.
        final_message = AssistantMessage(
            api=model.api, provider=model.provider, model=model.id,
            timestamp=_now_ms(), stopReason="error",
            errorMessage="stream ended without done event",
        )
    return final_message


# ── Transient LLM-error retry policy ─────────────────────────────────────────
_LLM_TRANSIENT_RETRIES = 3
_LLM_RETRY_BACKOFF_S = 5  # 5s, 10s, 15s

# How much of a failed tool's textual result is forwarded to the UI in the
# tool_call_end event. The full content still goes to the model; this preview
# exists so the chat can surface *why* a call failed (allowlist denials,
# path rejections) without forwarding every successful payload.
_TOOL_ERROR_PREVIEW_CHARS = 500


def _is_transient_llm_error(msg: Optional[str]) -> bool:
    """Provider-side hiccups worth retrying: 5xx family, overload, timeouts.
    Auth/validation errors (4xx) are NOT transient and fail immediately.

    The chat-9257ff60 run aborted on `SSL: SSLV3_ALERT_BAD_RECORD_MAC`
    even though this is a transient transport error from openrouter — the
    upstream terminated the connection mid-handshake. Treating it as
    non-retryable and showing the user a "pipeline paused" gate is wrong:
    a single transient hiccup on a pinned provider should be retried with
    backoff, not surfaced as a terminal failure. Same class as a 5xx or
    a connection timeout. The error name itself (`ssl`, `SSLError`,
    `SSLV3_ALERT_*`, `ECONNRESET`, `ECONNREFUSED`, `EPIPE`) signals
    transport-level failure and is what the rest of the harness sees
    when the upstream goes away mid-stream.
    """
    text = (msg or "").lower()
    if not text:
        return False
    transport_markers = (
        # HTTP status family — provider returned an error
        "520", "502", "503", "504", "529",
        # Provider / openrouter / generic
        "provider returned error", "overloaded", "timeout", "timed out",
        "connection", "temporarily",
        # OpenSSL / ssl errors
        "ssl", "sslerror", "sslv3", "tlsv1", "alert_bad_record_mac",
        "wrong_version_number", "record_overflow", "certificate_verify_failed",
        # OS-level transport errors
        "econnreset", "econnrefused", "epipe", "etimedout", "enotfound",
        "network is unreachable", "connection reset", "connection refused",
    )
    return any(token in text for token in transport_markers)


# ── Main agent ────────────────────────────────────────────────────────────────

class EcoAgent:
    """Claude-code-style agent loop on pi-ai. Synchronous public API."""

    def __init__(
        self,
        *,
        model: Model,
        system_prompt: str,
        tools: list[EcoTool],
        stop_tool: Union[str, list[str], None] = None,
        max_iters: Optional[int] = None,
        trace_dir: Optional[Path] = None,
        trace_label: str = "agent",
        prepare_arguments: Optional[Callable[[str, dict], dict]] = None,
        before_tool_call:  Optional[Callable[[str, BaseModel], Optional[dict]]] = None,
        after_tool_call:   Optional[Callable[[str, BaseModel, ToolResult], ToolResult]] = None,
        dedup_tools:       Optional[set] = None,
        on_event:          Optional[Callable[[EcoAgentEvent], None]] = None,
        stream_options:    Optional[SimpleStreamOptions] = None,
        stream_fn:         Optional[StreamFunction] = None,
        max_tool_results:  int = 5,
    ):
        """Construct the agent.

        - model: pi_ai.Model. Built from env via build_default_pi_model() in
          production; tests pass a faux-api model paired with stream_fn.
        - stream_options: optional SimpleStreamOptions (reasoning level, temperature,
          maxTokens, ...). Defaults to None (provider/model defaults).
        - stream_fn: optional StreamFunction override (used by tests with a
          scripted stream). Defaults to pi_ai.stream_simple.
        """
        self.model = model
        self.system_prompt = system_prompt
        self.tools = {t.name: t for t in tools}
        self.stop_tools = (
            set() if stop_tool is None
            else {stop_tool} if isinstance(stop_tool, str)
            else set(stop_tool)
        )
        # max_iters=None → unlimited loop. Safe because every LLM call is
        # traced to disk individually (see _stream_llm), so an unbounded run
        # is still fully debuggable and produces traces incrementally.
        self.max_iters = max_iters
        self.trace_dir = trace_dir
        self.trace_label = trace_label
        self._call_no = 0   # per-instance LLM-call counter (trace metadata)
        self._iter = 0      # current run() iteration (trace metadata)
        self.prepare_arguments = prepare_arguments
        self.before_tool_call = before_tool_call
        self.after_tool_call = after_tool_call
        # Read-only tools eligible for memo-dedup: an identical repeat call
        # returns a one-line pointer instead of re-running the tool and adding
        # another full-size copy of the result to the history. Any tool NOT in
        # this set is treated as potentially mutating and clears the memo
        # (e.g. write_file invalidates earlier reads of the same path).
        self.dedup_tools = set(dedup_tools or ())
        self._dedup_memo: dict = {}
        self.on_event = on_event or (lambda _e: None)
        self.stream_options = stream_options
        self.max_tool_results = max(1, max_tool_results)
        self.stream_fn: StreamFunction = stream_fn or stream_simple

        self._pi_tools = _eco_tools_to_pi_tools(tools)

    # ── helpers ────────────────────────────────────────────────────────────
    def _emit(self, event_type: EventType, data: Optional[dict] = None):
        self.on_event(EcoAgentEvent(type=event_type, data=data or {}))

    def _build_context(self, history: list) -> Context:
        tool_result_indexes = [
            index
            for index, message in enumerate(history)
            if isinstance(message, ToolResultMessage)
        ]
        stale_indexes = set(tool_result_indexes[:-self.max_tool_results])
        context_history = []
        for index, message in enumerate(history):
            if index not in stale_indexes:
                context_history.append(message)
                continue
            context_history.append(message.model_copy(update={
                "content": [
                    TextContent(
                        text="[older tool output elided; full result is retained in trace]"
                    )
                ],
            }))
        return Context(
            systemPrompt=self.system_prompt,
            messages=context_history,
            tools=self._pi_tools or None,
        )

    def _stream_llm(self, history: list) -> AssistantMessage:
        """Stream one LLM turn through pi_ai, emit deltas, return final AssistantMessage.

        This is sync — orchestrator/server invoke EcoAgent.run from
        asyncio.to_thread, so creating a fresh event loop here via
        asyncio.run() is safe.

        Every call is persisted via write_call_trace (when trace_dir is set):
        request AND response, in a finally block — so a trace exists for a
        single call and even when the stream raises before returning.
        """
        context = self._build_context(history)
        self._call_no += 1
        call_no = self._call_no
        response: Optional[AssistantMessage] = None
        error_str = ""
        try:
            response = asyncio.run(_drain_stream(
                self.stream_fn, self.model, context, self.stream_options,
                on_text_delta=lambda d: self._emit(EventType.TEXT_DELTA, {"content": d}),
                on_thinking_delta=lambda d: self._emit(EventType.THINKING_DELTA, {"content": d}),
            ))
            return response
        except Exception as e:  # noqa: BLE001 — re-raised after the trace is written
            error_str = f"{type(e).__name__}: {e}"
            raise
        finally:
            if self.trace_dir is not None:
                write_call_trace(
                    trace_dir=self.trace_dir,
                    label=self.trace_label,
                    call_no=call_no,
                    iteration=self._iter,
                    model_id=self.model.id,
                    request_context=context,
                    response=response,
                    error=error_str,
                )

    # ── main entrypoint ────────────────────────────────────────────────────
    def run(self, seed) -> EcoAgentResult:
        self._emit(EventType.START)
        history: list = list(_normalize_seed(seed))

        i = 0
        while self.max_iters is None or i < self.max_iters:
            self._iter = i
            self._emit(EventType.ITERATION, {"i": i})

            # Transient transport errors (SSLError, ECONNRESET, 5xx, timeouts)
            # raised out of _stream_llm get the same retry-with-backoff policy
            # as the in-band resp.stopReason=="error" path. chat-9257ff60
            # proved the previous behaviour (immediate terminal return) is
            # wrong: a single openrouter mid-stream reset aborts an otherwise
            # healthy run. We unify both paths into one retry loop.
            resp = None
            for attempt in range(_LLM_TRANSIENT_RETRIES + 1):
                try:
                    resp = self._stream_llm(history)
                    break  # got a response (even one with stopReason=="error")
                except Exception as exc:
                    if attempt >= _LLM_TRANSIENT_RETRIES or not _is_transient_llm_error(str(exc)):
                        # Either non-transient (auth, validation, programmer
                        # error) or we have already retried max times.
                        self._emit(EventType.ERROR, {"reason": str(exc)})
                        return EcoAgentResult(
                            status="error", stop_tool_name="", stop_payload={},
                            history=history, error=str(exc),
                        )
                    # Transient — sleep then retry. Backoff matches the
                    # in-band retry path (5s, 10s, 15s) so the two are
                    # indistinguishable to the user and to the trace.
                    self._emit(EventType.ITERATION, {
                        "i": i, "llm_retry": attempt + 1,
                        "reason": f"{type(exc).__name__}: {str(exc)[:200]}",
                    })
                    time.sleep(_LLM_RETRY_BACKOFF_S * (attempt + 1))

            # In-band error path: response came back with stopReason=="error"
            # and the message looks transient. Same backoff policy.
            retry = 0
            while (resp is not None
                   and resp.stopReason == "error"
                   and retry < _LLM_TRANSIENT_RETRIES
                   and _is_transient_llm_error(resp.errorMessage)):
                retry += 1
                self._emit(EventType.ITERATION, {
                    "i": i, "llm_retry": retry,
                    "reason": (resp.errorMessage or "")[:200],
                })
                time.sleep(_LLM_RETRY_BACKOFF_S * retry)
                try:
                    resp = self._stream_llm(history)
                except Exception as e:
                    self._emit(EventType.ERROR, {"reason": str(e)})
                    return EcoAgentResult(
                        status="error", stop_tool_name="", stop_payload={},
                        history=history, error=str(e),
                    )

            # Append the assistant turn (even if it ended in error) to history.
            history.append(resp)

            # Per-call token accounting for the UI stepper (phase/total counters).
            self._emit(EventType.USAGE, {"usage": _usage_data(resp)})

            # Sliding-window summarization. When the cumulative input
            # token count crosses the model context window (or a
            # configurable ratio of it), compress the older turns into
            # a single digest message and keep only the last 4 turns
            # verbatim. This is the single biggest input-cost saver
            # for long runs (ses-e9b2c2ad: 22-turn coder run cost
            # 891 K input tokens; 80% was history).
            self._maybe_summarize_history(history)

            # Stream-level error (HTTP fail, abort, etc.) — surface as agent error.
            if resp.stopReason in ("error", "aborted"):
                self._emit(EventType.ERROR, {"reason": resp.errorMessage or resp.stopReason})
                return EcoAgentResult(
                    status="error", stop_tool_name="", stop_payload={},
                    history=history, error=resp.errorMessage or resp.stopReason,
                )

            # Extract tool calls from the assistant content array.
            tool_calls: list[ToolCall] = [c for c in resp.content if isinstance(c, ToolCall)]
            if not tool_calls:
                self._emit(EventType.NO_TOOL_CALL)
                return EcoAgentResult(
                    status="no_tool_call", stop_tool_name="", stop_payload={},
                    history=history, error="",
                )

            for tc in tool_calls:
                name = tc.name
                raw_args = dict(tc.arguments or {})
                call_id = tc.id
                self._emit(EventType.TOOL_START, {"name": name, "args": raw_args})

                if name not in self.tools and name not in self.stop_tools:
                    history.append(ToolResultMessage(
                        toolCallId=call_id, toolName=name,
                        content=[TextContent(text=f"UNKNOWN TOOL: {name}")],
                        isError=True, timestamp=_now_ms(),
                    ))
                    # Close the UI tool card — without TOOL_END it would spin
                    # as "running" forever (same for the other error paths
                    # below). denied=True marks policy-level rejections so the
                    # frontend can badge them distinctly.
                    self._emit(EventType.TOOL_END, {
                        "name": name, "is_error": True,
                        "details": {"denied": True, "reason": f"unknown tool {name!r}"},
                    })
                    continue

                # 1. prepare_arguments shim
                cooked = self.prepare_arguments(name, raw_args) if self.prepare_arguments else raw_args

                # 2. resolve schema (stop tool may or may not be in self.tools)
                tool = self.tools.get(name)
                schema = tool.args_schema if tool else None
                if schema is None:
                    # Stop-only tool with no schema — accept the raw dict
                    args_obj = type("StopArgs", (), {
                        "model_dump": lambda self=cooked: cooked,
                    })()
                else:
                    try:
                        args_obj = schema.model_validate(cooked)
                    except ValidationError as ve:
                        history.append(ToolResultMessage(
                            toolCallId=call_id, toolName=name,
                            content=[TextContent(text=f"ARGS ERROR: {ve}")],
                            isError=True, timestamp=_now_ms(),
                        ))
                        self._emit(EventType.TOOL_END, {
                            "name": name, "is_error": True,
                            "details": {"reason": str(ve)},
                        })
                        continue

                # 3. before_tool_call gate
                if self.before_tool_call:
                    gate = self.before_tool_call(name, args_obj)
                    if gate and gate.get("block"):
                        history.append(ToolResultMessage(
                            toolCallId=call_id, toolName=name,
                            content=[TextContent(text=f"BLOCKED: {gate.get('reason', '')}")],
                            isError=True, timestamp=_now_ms(),
                        ))
                        self._emit(EventType.TOOL_END, {
                            "name": name, "is_error": True,
                            "details": {"denied": True, "reason": gate.get("reason", "")},
                        })
                        continue

                # 4. stop tool — short-circuit return
                if name in self.stop_tools:
                    payload = args_obj.model_dump() if hasattr(args_obj, "model_dump") else dict(cooked)
                    self._emit(EventType.DONE, {"stop_tool": name, "payload": payload})
                    return EcoAgentResult(
                        status="done", stop_tool_name=name,
                        stop_payload=payload, history=history, error="",
                    )

                # 4b. memo-dedup for read-only tools
                dedup_key = None
                if name in self.dedup_tools:
                    dedup_key = (name, _json.dumps(cooked, sort_keys=True,
                                                   ensure_ascii=False, default=str))
                    prior_iter = self._dedup_memo.get(dedup_key)
                    if prior_iter is not None:
                        history.append(ToolResultMessage(
                            toolCallId=call_id, toolName=name,
                            content=[TextContent(text=(
                                f"[duplicate call — identical {name} call was made "
                                f"at iteration {prior_iter}; result unchanged, "
                                f"see it above in this conversation]"))],
                            isError=False, timestamp=_now_ms(),
                        ))
                        self._emit(EventType.TOOL_END, {
                            "name": name, "is_error": False,
                            "details": {"dedup": True},
                        })
                        continue

                # 5. execute
                try:
                    result = tool.execute(args_obj)
                except Exception as e:
                    history.append(ToolResultMessage(
                        toolCallId=call_id, toolName=name,
                        content=[TextContent(text=f"TOOL ERROR: {e}")],
                        isError=True, timestamp=_now_ms(),
                    ))
                    self._emit(EventType.TOOL_END, {
                        "name": name, "is_error": True,
                        "details": {"reason": f"{type(e).__name__}: {e}"},
                    })
                    continue

                # 6. after_tool_call hook
                if self.after_tool_call:
                    result = self.after_tool_call(name, args_obj, result)

                # 6b. memo bookkeeping: remember read-only results; any other
                # (potentially mutating) tool conservatively drops the memo.
                if name in self.dedup_tools:
                    if dedup_key is not None and not result.is_error:
                        self._dedup_memo[dedup_key] = i
                elif self.dedup_tools:
                    self._dedup_memo.clear()

                end_details = dict(result.details or {})
                if result.is_error:
                    # Forward a preview of the failure text so the UI can
                    # show *why* the call failed (allowlist/path denials
                    # included).
                    end_details.setdefault(
                        "reason", result.content[:_TOOL_ERROR_PREVIEW_CHARS],
                    )
                self._emit(EventType.TOOL_END, {
                    "name": name, "is_error": result.is_error,
                    "details": end_details,
                })
                history.append(ToolResultMessage(
                    toolCallId=call_id, toolName=name,
                    content=[TextContent(text=result.content)],
                    isError=result.is_error,
                    timestamp=_now_ms(),
                ))

            i += 1

        self._emit(EventType.MAX_ITERS)
        return EcoAgentResult(
            status="max_iters", stop_tool_name="", stop_payload={},
            history=history, error="",
        )

    # ------------------------------------------------------------------
    # Conversation-history compression (sliding-window summarization).
    # ------------------------------------------------------------------
    # Without this, every LLM call re-sends the FULL conversation
    # history, which grows linearly with iteration count. The cost
    # analysis on ses-e9b2c2ad:
    #   - 22 coder turns
    #   - 38 933 tokens input on turn 0
    #   - 45 848 tokens input on turn 21 (only 7 K of growth,
    #     but the ABSOLUTE cost of turn 21 is 45 K input = $0.023 just
    #     for that one call)
    #   - 891 K total input across the run
    # With summarization, the older turns collapse to a single
    # digest message (typically 2-4 K tokens), and only the last 4
    # turns are verbatim. Net saving: ~25 K input per call after
    # turn 8 = ~$0.27 per 22-turn run.
    #
    # The digest is a USER-role message inserted between the seed and
    # the verbatim tail. The model treats it as additional context,
    # not as a directive. The digest is regenerated each time the
    # threshold is crossed (incremental summarization is left as a
    # future optimization — for now full re-summarize is cheap enough
    # and gives the best fidelity).

    _SUMMARIZE_KEEP_LAST = 4  # keep the last N messages verbatim (extended
    # back to a turn boundary so tool-call/tool-result groups stay intact)
    _SUMMARIZE_TRIGGER_RATIO = 0.6  # summarize when history > 60% of context

    def _est_history_tokens(self, history: list) -> int:
        """Rough token estimate for the dynamic part of the history.

        We use 4 chars per token (the same heuristic the openai
        provider uses for prompt budgeting). For long histories this
        is within 6% of the provider's actual count.
        """
        chars = 0
        for m in history:
            content = getattr(m, "content", None)
            if isinstance(content, str):
                chars += len(content)
            elif isinstance(content, list):
                for c in content:
                    t = getattr(c, "text", None)
                    if isinstance(t, str):
                        chars += len(t)
        return chars // 4

    def _maybe_summarize_history(self, history: list) -> None:
        # Skip if there is nothing meaningful to compress.
        if len(history) <= self._SUMMARIZE_KEEP_LAST + 2:
            return
        # Get the context window from the model profile (fallback 128 K).
        ctx = 128_000
        try:
            profile = getattr(self.model, "profile", None) or getattr(self.model, "_profile", None)
            if profile is not None and getattr(profile, "contextWindow", None):
                ctx = int(profile.contextWindow)
        except Exception:
            pass
        est = self._est_history_tokens(history)
        # Also factor in the static system prompt + tools schema. Rough
        # estimate: 12 K for the static part.
        threshold = int(ctx * self._SUMMARIZE_TRIGGER_RATIO) - 12_000
        if est < threshold:
            return
        # Compress. The most recent messages are kept verbatim; the
        # rest collapse to one digest message prepended to the tail.
        cut = len(history) - self._SUMMARIZE_KEEP_LAST
        # Never cut between an assistant tool-call message and its tool
        # results: a tail that starts with an orphaned ToolResultMessage
        # is rejected by the provider APIs ("unexpected tool_use_id" /
        # "tool message must follow assistant tool_calls"). Walk the
        # boundary back to the assistant message that owns the results.
        while 0 < cut < len(history) and getattr(history[cut], "role", "") == "toolResult":
            cut -= 1
        tail = list(history[cut:])
        head = list(history[:cut])
        # Build a structured digest of the head.
        digest = self._build_history_digest(head)
        # Replace history in place: digest + tail. We mutate the list
        # because the agent's run() uses the same reference.
        history.clear()
        history.append(digest)
        history.extend(tail)
        # Deduped read results may now live in the digested-away head;
        # stale pointers would answer a re-call with "[duplicate — see
        # it above]" for content that is no longer in context.
        self._dedup_memo.clear()
        self._emit(EventType.ITERATION, {
            "i": self._iter,
            "history_compressed": True,
            "old_tokens_est": est,
            "new_turns": len(history),
        })

    def _build_history_digest(self, head_msgs: list) -> "UserMessage":
        """Synthesize a compact summary of the older turns.

        The summary is a USER-role message that the LLM treats as
        additional context. It preserves the things the model will
        need to remember (the original user request, the architect's
        plan summary, files written, errors hit) and discards the
        things the model can re-derive from tool results (full tool
        output text, full IID bytes).
        """
        from eco_harness.agent.pi_ai.types import UserMessage
        chunks = []
        for m in head_msgs:
            role = getattr(m, "role", "?")
            content = getattr(m, "content", None)
            if isinstance(content, str):
                # Plain text message
                if len(content) > 1000:
                    content = content[:1000] + "...[truncated]"
                chunks.append(f"[{role}] {content}")
            elif isinstance(content, list):
                # Mixed: text blocks + tool calls / tool results.
                text_parts = []
                tool_parts = []
                for c in content:
                    t = getattr(c, "text", None)
                    if isinstance(t, str):
                        text_parts.append(t)
                    tool_name = getattr(c, "name", None)
                    if tool_name:
                        tool_parts.append(f"tool={tool_name}")
                body = " | ".join(text_parts[:3])[:500]
                if tool_parts:
                    body = (body + " | " if body else "") + "[" + ", ".join(tool_parts[:5]) + "]"
                if body:
                    chunks.append(f"[{role}] {body[:600]}")
        joined = "\n".join(chunks)
        # Cap the digest at ~3 K tokens (12 K chars). The LLM never
        # needs more than this for the "what was done so far" digest.
        if len(joined) > 12_000:
            joined = joined[:12_000] + "\n[...older history truncated for context budget...]"
        digest_text = (
            "[HISTORY COMPRESSED for context budget]\n"
            "The following is a digest of the older conversation turns. "
            "If you need full text of a specific tool result, re-call the "
            "tool with the same arguments and the result will be re-supplied.\n\n"
            + joined
        )
        return UserMessage(content=digest_text, timestamp=_now_ms())


