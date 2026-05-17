"""Stateful Agent class wrapping the low-level agent loop.

Mirrors @mariozechner/pi-mono/packages/agent/src/agent.ts (543 LOC TS).

Provides:
- Agent class with subscribe(), prompt(), continue_run(), abort(), reset()
- Steering + follow-up message queues with "all" or "one-at-a-time" modes
- Active-run lifecycle: at most one prompt in flight at a time
- Default convertToLlm filter (keeps only user/assistant/toolResult roles)
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal, Optional, Union

from agent.pi_ai import stream_simple
from agent.pi_ai.types import (
    AssistantMessage, Cost, ImageContent, Message, Model, ModelCost,
    TextContent, ThinkingBudgets, Transport, Usage,
)
from agent.pi_agent_core.agent_loop import (
    AgentEventSink, run_agent_loop, run_agent_loop_continue,
)
from agent.pi_agent_core.types import (
    AfterToolCallContext, AfterToolCallHook, AfterToolCallResult,
    AgentContext, AgentEndEvent, AgentEvent, AgentLoopConfig, AgentMessage,
    AgentState, AgentTool, BeforeToolCallContext, BeforeToolCallHook,
    BeforeToolCallResult, ConvertToLlmHook, GetApiKeyHook, StreamFn,
    ToolExecutionMode, TransformContextHook,
)


QueueMode = Literal["all", "one-at-a-time"]


# Default model used when caller doesn't supply one (mirrors agent.ts:42-53).
_DEFAULT_MODEL = Model(
    id="unknown", name="unknown", api="unknown", provider="unknown",
    baseUrl="", reasoning=False, input=[], cost=ModelCost(),
    contextWindow=0, maxTokens=0,
)

# Zero-filled usage used in synthesized failure messages (agent.ts:33-40).
_EMPTY_USAGE = Usage(
    input=0, output=0, cacheRead=0, cacheWrite=0, totalTokens=0,
    cost=Cost(input=0, output=0, cacheRead=0, cacheWrite=0, total=0),
)


def default_convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    """Default convertToLlm: filter to roles the LLM understands.

    Drops any custom message types (which Phase 2 doesn't define anyway).
    """
    return [m for m in messages if getattr(m, "role", None) in ("user", "assistant", "toolResult")]


class _PendingMessageQueue:
    """Internal queue for steering and follow-up messages.

    mode="all" drains the whole queue at once.
    mode="one-at-a-time" drains just the first message per drain() call.
    """

    def __init__(self, mode: QueueMode) -> None:
        self.mode: QueueMode = mode
        self._messages: list[AgentMessage] = []

    def enqueue(self, message: AgentMessage) -> None:
        self._messages.append(message)

    def has_items(self) -> bool:
        return len(self._messages) > 0

    def drain(self) -> list[AgentMessage]:
        if self.mode == "all":
            drained = list(self._messages)
            self._messages = []
            return drained
        if not self._messages:
            return []
        first = self._messages[0]
        self._messages = self._messages[1:]
        return [first]

    def clear(self) -> None:
        self._messages = []


@dataclass
class _ActiveRun:
    """Tracks an in-flight agent run.

    - future: resolves when the run + agent_end listeners complete.
    - abort_event: signal raised by Agent.abort() to cancel.
    """
    future: asyncio.Future[None]
    abort_event: asyncio.Event


@dataclass
class AgentOptions:
    """Constructor options for Agent (agent.ts:94-111)."""
    initial_state: Optional[dict] = None  # {systemPrompt, model, thinkingLevel, tools, messages}
    convert_to_llm: Optional[ConvertToLlmHook] = None
    transform_context: Optional[TransformContextHook] = None
    stream_fn: Optional[StreamFn] = None
    get_api_key: Optional[GetApiKeyHook] = None
    on_payload: Optional[Callable[..., Any]] = None
    on_response: Optional[Callable[..., Any]] = None
    before_tool_call: Optional[BeforeToolCallHook] = None
    after_tool_call: Optional[AfterToolCallHook] = None
    steering_mode: QueueMode = "one-at-a-time"
    follow_up_mode: QueueMode = "one-at-a-time"
    session_id: Optional[str] = None
    thinking_budgets: Optional[ThinkingBudgets] = None
    transport: Transport = "sse"
    max_retry_delay_ms: Optional[int] = None
    tool_execution: ToolExecutionMode = "parallel"


class Agent:
    """Stateful wrapper around the low-level agent loop (agent.ts:158-543).

    At most one run can be active at a time. Listeners receive events in
    subscription order; awaited listeners are part of run settlement.

    Note: TS uses TypeScript get/set accessors for state.tools and state.messages
    to copy-on-assign. In Python we expose state.tools and state.messages as
    plain attributes - callers should treat them as immutable from outside.
    Use Agent.set_tools / set_messages helpers for copy-on-assign semantics.
    """

    def __init__(self, options: Optional[AgentOptions] = None) -> None:
        options = options or AgentOptions()
        initial = options.initial_state or {}
        self._state = AgentState(
            systemPrompt=initial.get("systemPrompt", ""),
            model=initial.get("model") or _DEFAULT_MODEL,
            thinkingLevel=initial.get("thinkingLevel", "off"),
            tools=list(initial.get("tools") or []),
            messages=list(initial.get("messages") or []),
        )
        self._listeners: list[Callable[[AgentEvent, asyncio.Event], Awaitable[None]]] = []
        self._steering = _PendingMessageQueue(options.steering_mode)
        self._follow_up = _PendingMessageQueue(options.follow_up_mode)
        self._active_run: Optional[_ActiveRun] = None

        self.convert_to_llm: ConvertToLlmHook = options.convert_to_llm or default_convert_to_llm
        self.transform_context: Optional[TransformContextHook] = options.transform_context
        self.stream_fn: StreamFn = options.stream_fn or stream_simple
        self.get_api_key: Optional[GetApiKeyHook] = options.get_api_key
        self.on_payload = options.on_payload
        self.on_response = options.on_response
        self.before_tool_call: Optional[BeforeToolCallHook] = options.before_tool_call
        self.after_tool_call: Optional[AfterToolCallHook] = options.after_tool_call
        self.session_id: Optional[str] = options.session_id
        self.thinking_budgets: Optional[ThinkingBudgets] = options.thinking_budgets
        self.transport: Transport = options.transport
        self.max_retry_delay_ms: Optional[int] = options.max_retry_delay_ms
        self.tool_execution: ToolExecutionMode = options.tool_execution

    @property
    def state(self) -> AgentState:
        """Current agent state. Do not mutate fields directly - use set_tools/set_messages."""
        return self._state

    def set_tools(self, tools: list[AgentTool]) -> None:
        """Copy-on-assign semantics for tools list (matches TS state.tools setter)."""
        self._state.tools = list(tools)

    def set_messages(self, messages: list[AgentMessage]) -> None:
        """Copy-on-assign semantics for messages list."""
        self._state.messages = list(messages)

    def subscribe(
        self, listener: Callable[[AgentEvent, asyncio.Event], Awaitable[None]],
    ) -> Callable[[], None]:
        """Subscribe to agent events. Returns an unsubscribe function.

        Listener gets (event, abort_event). Awaited promises are part of run
        settlement - agent stays in "active" state until all agent_end listeners
        finish.
        """
        self._listeners.append(listener)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    @property
    def steering_mode(self) -> QueueMode:
        return self._steering.mode

    @steering_mode.setter
    def steering_mode(self, mode: QueueMode) -> None:
        self._steering.mode = mode

    @property
    def follow_up_mode(self) -> QueueMode:
        return self._follow_up.mode

    @follow_up_mode.setter
    def follow_up_mode(self, mode: QueueMode) -> None:
        self._follow_up.mode = mode

    def steer(self, message: AgentMessage) -> None:
        """Queue a message to be injected after the current assistant turn."""
        self._steering.enqueue(message)

    def follow_up(self, message: AgentMessage) -> None:
        """Queue a message to run after the agent would otherwise stop."""
        self._follow_up.enqueue(message)

    def clear_steering_queue(self) -> None:
        self._steering.clear()

    def clear_follow_up_queue(self) -> None:
        self._follow_up.clear()

    def clear_all_queues(self) -> None:
        self.clear_steering_queue()
        self.clear_follow_up_queue()

    def has_queued_messages(self) -> bool:
        return self._steering.has_items() or self._follow_up.has_items()

    @property
    def signal(self) -> Optional[asyncio.Event]:
        """Active abort event for the current run, if any."""
        if self._active_run is None:
            return None
        return self._active_run.abort_event

    def abort(self) -> None:
        """Signal the current run to abort. Does nothing if no run is active."""
        if self._active_run is not None:
            self._active_run.abort_event.set()

    async def wait_for_idle(self) -> None:
        """Resolve when the current run + agent_end listeners have finished."""
        if self._active_run is None:
            return
        await self._active_run.future

    def reset(self) -> None:
        """Clear transcript state, runtime state, and queued messages."""
        self._state.messages = []
        self._state.isStreaming = False
        self._state.streamingMessage = None
        self._state.pendingToolCalls = set()
        self._state.errorMessage = None
        self.clear_steering_queue()
        self.clear_follow_up_queue()

    async def prompt(
        self,
        input: Union[str, AgentMessage, list[AgentMessage]],
        images: Optional[list[ImageContent]] = None,
    ) -> None:
        """Start a new prompt from text, a single message, or a batch.

        Raises RuntimeError if a run is already active.
        """
        if self._active_run is not None:
            raise RuntimeError(
                "Agent is already processing a prompt. Use steer() or follow_up() "
                "to queue messages, or wait for completion."
            )
        messages = self._normalize_prompt_input(input, images)
        await self._run_prompt_messages(messages)

    async def continue_run(self) -> None:
        """Continue from the current transcript. Last message must be user
        or toolResult (or a steering/follow-up message was queued).

        Python rename: TS `continue` is `continue_run` (Python keyword conflict).
        """
        if self._active_run is not None:
            raise RuntimeError("Agent is already processing.")

        last = self._state.messages[-1] if self._state.messages else None
        if last is None:
            raise RuntimeError("No messages to continue from")

        if getattr(last, "role", None) == "assistant":
            queued_steering = self._steering.drain()
            if queued_steering:
                await self._run_prompt_messages(
                    queued_steering, skip_initial_steering_poll=True,
                )
                return
            queued_follow_up = self._follow_up.drain()
            if queued_follow_up:
                await self._run_prompt_messages(queued_follow_up)
                return
            raise RuntimeError("Cannot continue from message role: assistant")

        await self._run_continuation()

    def _normalize_prompt_input(
        self,
        input: Union[str, AgentMessage, list[AgentMessage]],
        images: Optional[list[ImageContent]] = None,
    ) -> list[AgentMessage]:
        if isinstance(input, list):
            return input
        if not isinstance(input, str):
            return [input]
        content: list = [TextContent(text=input)]
        if images:
            content.extend(images)
        return [{
            "role": "user", "content": content, "timestamp": int(time.time() * 1000),
        }]  # type: ignore[list-item]

    async def _run_prompt_messages(
        self,
        messages: list[AgentMessage],
        skip_initial_steering_poll: bool = False,
    ) -> None:
        async def executor(signal: asyncio.Event) -> None:
            await run_agent_loop(
                messages,
                self._create_context_snapshot(),
                self._create_loop_config(skip_initial_steering_poll),
                self._process_events,
                signal,
                self.stream_fn,
            )

        await self._run_with_lifecycle(executor)

    async def _run_continuation(self) -> None:
        async def executor(signal: asyncio.Event) -> None:
            await run_agent_loop_continue(
                self._create_context_snapshot(),
                self._create_loop_config(),
                self._process_events,
                signal,
                self.stream_fn,
            )

        await self._run_with_lifecycle(executor)

    def _create_context_snapshot(self) -> AgentContext:
        return AgentContext(
            systemPrompt=self._state.systemPrompt,
            messages=list(self._state.messages),
            tools=list(self._state.tools),
        )

    def _create_loop_config(self, skip_initial_steering_poll: bool = False) -> AgentLoopConfig:
        skip_flag = {"skip": skip_initial_steering_poll}

        async def steering_getter() -> list[AgentMessage]:
            if skip_flag["skip"]:
                skip_flag["skip"] = False
                return []
            return self._steering.drain()

        async def follow_up_getter() -> list[AgentMessage]:
            return self._follow_up.drain()

        model = self._state.model or _DEFAULT_MODEL
        reasoning = self._state.thinkingLevel if self._state.thinkingLevel != "off" else None

        return AgentLoopConfig(
            model=model,
            reasoning=reasoning,
            sessionId=self.session_id,
            onPayload=self.on_payload,
            onResponse=self.on_response,
            transport=self.transport,
            thinkingBudgets=self.thinking_budgets,
            maxRetryDelayMs=self.max_retry_delay_ms or 60000,
            toolExecution=self.tool_execution,
            beforeToolCall=self.before_tool_call,
            afterToolCall=self.after_tool_call,
            convertToLlm=self.convert_to_llm,
            transformContext=self.transform_context,
            getApiKey=self.get_api_key,
            getSteeringMessages=steering_getter,
            getFollowUpMessages=follow_up_getter,
        )

    async def _run_with_lifecycle(
        self, executor: Callable[[asyncio.Event], Awaitable[None]],
    ) -> None:
        if self._active_run is not None:
            raise RuntimeError("Agent is already processing.")

        abort_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[None] = loop.create_future()
        self._active_run = _ActiveRun(future=future, abort_event=abort_event)

        self._state.isStreaming = True
        self._state.streamingMessage = None
        self._state.errorMessage = None

        try:
            await executor(abort_event)
        except asyncio.CancelledError:
            await self._handle_run_failure(asyncio.CancelledError(), aborted=True)
            raise
        except Exception as e:  # noqa: BLE001 - capture all
            await self._handle_run_failure(e, aborted=abort_event.is_set())
        finally:
            self._finish_run()

    async def _handle_run_failure(self, error: Any, aborted: bool) -> None:
        model = self._state.model or _DEFAULT_MODEL
        failure = AssistantMessage(
            content=[TextContent(text="")],
            api=model.api, provider=model.provider, model=model.id,
            usage=_EMPTY_USAGE,
            stopReason="aborted" if aborted else "error",
            errorMessage=str(error),
            timestamp=int(time.time() * 1000),
        )
        self._state.messages.append(failure)
        self._state.errorMessage = failure.errorMessage
        await self._process_events(AgentEndEvent(messages=[failure]))

    def _finish_run(self) -> None:
        self._state.isStreaming = False
        self._state.streamingMessage = None
        self._state.pendingToolCalls = set()
        if self._active_run is not None and not self._active_run.future.done():
            self._active_run.future.set_result(None)
        self._active_run = None

    async def _process_events(self, event: AgentEvent) -> None:
        """Reduce internal state for a loop event, then await listeners.

        agent_end means no further loop events - but the run is idle only after
        listeners settle and _finish_run() runs.
        """
        et = event.type

        if et == "message_start":
            self._state.streamingMessage = event.message
        elif et == "message_update":
            self._state.streamingMessage = event.message
        elif et == "message_end":
            self._state.streamingMessage = None
            self._state.messages.append(event.message)
        elif et == "tool_execution_start":
            pending = set(self._state.pendingToolCalls)
            pending.add(event.toolCallId)
            self._state.pendingToolCalls = pending
        elif et == "tool_execution_end":
            pending = set(self._state.pendingToolCalls)
            pending.discard(event.toolCallId)
            self._state.pendingToolCalls = pending
        elif et == "turn_end":
            msg = event.message
            err = getattr(msg, "errorMessage", None)
            if getattr(msg, "role", None) == "assistant" and err:
                self._state.errorMessage = err
        elif et == "agent_end":
            self._state.streamingMessage = None

        if self._active_run is None:
            raise RuntimeError("Agent listener invoked outside active run")
        signal = self._active_run.abort_event
        for listener in self._listeners:
            await listener(event, signal)
