"""EcoAgent - claude-code-style agent loop for V6 nodes.

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
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel, ValidationError

from agent.pi_ai import (
    AssistantMessage, Context, Model, SimpleStreamOptions,
    StreamOptions, TextContent, Tool, ToolCall, ToolResultMessage, UserMessage,
    stream_simple,
)
from agent.pi_ai.types import (
    DoneEvent, ErrorEvent, StreamFunction, TextDeltaEvent, ThinkingDeltaEvent,
)


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
        max_iters: int = 25,
        prepare_arguments: Optional[Callable[[str, dict], dict]] = None,
        before_tool_call:  Optional[Callable[[str, BaseModel], Optional[dict]]] = None,
        after_tool_call:   Optional[Callable[[str, BaseModel, ToolResult], ToolResult]] = None,
        on_event:          Optional[Callable[[EcoAgentEvent], None]] = None,
        stream_options:    Optional[SimpleStreamOptions] = None,
        stream_fn:         Optional[StreamFunction] = None,
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
        self.max_iters = max_iters
        self.prepare_arguments = prepare_arguments
        self.before_tool_call = before_tool_call
        self.after_tool_call = after_tool_call
        self.on_event = on_event or (lambda _e: None)
        self.stream_options = stream_options
        self.stream_fn: StreamFunction = stream_fn or stream_simple

        self._pi_tools = _eco_tools_to_pi_tools(tools)

    # ── helpers ────────────────────────────────────────────────────────────
    def _emit(self, event_type: EventType, data: Optional[dict] = None):
        self.on_event(EcoAgentEvent(type=event_type, data=data or {}))

    def _build_context(self, history: list) -> Context:
        return Context(
            systemPrompt=self.system_prompt,
            messages=history,
            tools=self._pi_tools or None,
        )

    def _stream_llm(self, history: list) -> AssistantMessage:
        """Stream one LLM turn through pi_ai, emit deltas, return final AssistantMessage.

        This is sync — orchestrator/server invoke EcoAgent.run from
        asyncio.to_thread, so creating a fresh event loop here via
        asyncio.run() is safe.
        """
        context = self._build_context(history)
        return asyncio.run(_drain_stream(
            self.stream_fn, self.model, context, self.stream_options,
            on_text_delta=lambda d: self._emit(EventType.TEXT_DELTA, {"content": d}),
            on_thinking_delta=lambda d: self._emit(EventType.THINKING_DELTA, {"content": d}),
        ))

    # ── main entrypoint ────────────────────────────────────────────────────
    def run(self, seed) -> EcoAgentResult:
        self._emit(EventType.START)
        history: list = list(_normalize_seed(seed))

        for i in range(self.max_iters):
            self._emit(EventType.ITERATION, {"i": i})

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
                        continue

                # 4. stop tool — short-circuit return
                if name in self.stop_tools:
                    payload = args_obj.model_dump() if hasattr(args_obj, "model_dump") else dict(cooked)
                    self._emit(EventType.DONE, {"stop_tool": name, "payload": payload})
                    return EcoAgentResult(
                        status="done", stop_tool_name=name,
                        stop_payload=payload, history=history, error="",
                    )

                # 5. execute
                try:
                    result = tool.execute(args_obj)
                except Exception as e:
                    history.append(ToolResultMessage(
                        toolCallId=call_id, toolName=name,
                        content=[TextContent(text=f"TOOL ERROR: {e}")],
                        isError=True, timestamp=_now_ms(),
                    ))
                    continue

                # 6. after_tool_call hook
                if self.after_tool_call:
                    result = self.after_tool_call(name, args_obj, result)

                self._emit(EventType.TOOL_END, {
                    "name": name, "is_error": result.is_error, "details": result.details,
                })
                history.append(ToolResultMessage(
                    toolCallId=call_id, toolName=name,
                    content=[TextContent(text=result.content)],
                    isError=result.is_error,
                    timestamp=_now_ms(),
                ))

        self._emit(EventType.MAX_ITERS)
        return EcoAgentResult(
            status="max_iters", stop_tool_name="", stop_payload={},
            history=history, error="",
        )
