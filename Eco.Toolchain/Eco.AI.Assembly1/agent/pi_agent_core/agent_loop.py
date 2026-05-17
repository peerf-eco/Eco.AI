"""Agent loop - low-level turn loop with tool execution and hooks.

Mirrors @mariozechner/pi-mono/packages/agent/src/agent-loop.ts (636 LOC TS).

Architecture:
- run_agent_loop(prompts, context, config, emit, signal, stream_fn) - entry point.
- _run_loop(...) - inner loop (turn-by-turn).
- _stream_assistant_response(...) - one LLM call + event accumulation.
- _execute_tool_calls(...) - dispatches sequential|parallel based on config.
- _prepare_tool_call(...) - args validation + beforeToolCall hook.
- _execute_prepared_tool_call(...) - calls tool.execute, captures updates.
- _finalize_executed_tool_call(...) - afterToolCall hook + emits.

Contract: NEVER raises. All failures encoded as events + AssistantMessage with
stopReason in {"error", "aborted"}.
"""
from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Union

from pydantic import BaseModel

from agent.pi_ai import stream_simple
from agent.pi_ai.types import (
    AssistantMessage, Context, DoneEvent, ErrorEvent, StartEvent,
    TextContent, TextDeltaEvent, TextEndEvent, TextStartEvent,
    ThinkingDeltaEvent, ThinkingEndEvent, ThinkingStartEvent,
    ToolCallDeltaEvent, ToolCallEndEvent, ToolCallStartEvent,
    ToolResultMessage,
)
from agent.pi_ai.utils.validation import validate_args
from agent.pi_agent_core.types import (
    AfterToolCallContext, AgentContext, AgentEndEvent, AgentEvent,
    AgentLoopConfig, AgentMessage, AgentStartEvent, AgentTool, AgentToolCall,
    AgentToolResult, BeforeToolCallContext, MessageEndEvent, MessageStartEvent,
    MessageUpdateEvent, StreamFn, ToolExecutionEndEvent,
    ToolExecutionStartEvent, ToolExecutionUpdateEvent, TurnEndEvent,
    TurnStartEvent,
)


AgentEventSink = Callable[[AgentEvent], Awaitable[None]]


def _create_error_tool_result(message: str) -> AgentToolResult:
    """Build an AgentToolResult representing an error (agent-loop.ts:602-607)."""
    return AgentToolResult(
        content=[TextContent(text=message)],
        details={},
    )


async def _maybe_await(value: Any) -> Any:
    """Await value if it's awaitable, else return as-is.

    Used for hooks declared sync-or-async (TS allows either via union return).
    """
    if inspect.isawaitable(value):
        return await value
    return value


# ── Prepared/Immediate tool-call result dataclasses (agent-loop.ts:440-456) ──
@dataclass
class _PreparedToolCall:
    """Tool call that has passed validation + beforeToolCall, ready to execute."""
    tool_call: AgentToolCall
    tool: AgentTool
    args: BaseModel  # validated pydantic instance for tool.parameters


@dataclass
class _ImmediateToolCallOutcome:
    """Tool call that bypasses execute (not-found, blocked, validation-failed)."""
    result: AgentToolResult
    is_error: bool


@dataclass
class _ExecutedToolCallOutcome:
    """Result of tool.execute() - may itself be an error if the tool raised."""
    result: AgentToolResult
    is_error: bool


# ── prepare_arguments + validation helpers (agent-loop.ts:458-470) ───────────
def _prepare_tool_call_arguments(
    tool: AgentTool, tool_call: AgentToolCall,
) -> AgentToolCall:
    """If tool.prepare_arguments is set, transform raw LLM args before validation.
    Returns a (possibly new) AgentToolCall with prepared arguments dict."""
    if tool.prepare_arguments is None:
        return tool_call
    prepared = tool.prepare_arguments(tool_call.arguments)
    if prepared is tool_call.arguments:
        return tool_call
    return tool_call.model_copy(update={"arguments": prepared})


# ── _prepare_tool_call - validation + beforeToolCall hook (agent-loop.ts:472-522) ──
async def _prepare_tool_call(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_call: AgentToolCall,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
) -> Union[_PreparedToolCall, _ImmediateToolCallOutcome]:
    """Validate args, then call beforeToolCall hook (if any).
    Returns Prepared (ready to execute) or Immediate (error / blocked)."""
    tool = next(
        (t for t in (current_context.tools or []) if t.name == tool_call.name),
        None,
    )
    if tool is None:
        return _ImmediateToolCallOutcome(
            result=_create_error_tool_result(f"Tool {tool_call.name} not found"),
            is_error=True,
        )

    try:
        prepared_call = _prepare_tool_call_arguments(tool, tool_call)
        validated, err = validate_args(tool.parameters, prepared_call.arguments)
        if err is not None:
            return _ImmediateToolCallOutcome(
                result=_create_error_tool_result(err),
                is_error=True,
            )
        if config.beforeToolCall is not None:
            before_result = await config.beforeToolCall(
                BeforeToolCallContext(
                    assistantMessage=assistant_message,
                    toolCall=tool_call,
                    args=validated,
                    context=current_context,
                ),
                signal,
            )
            if before_result is not None and before_result.block:
                return _ImmediateToolCallOutcome(
                    result=_create_error_tool_result(
                        before_result.reason or "Tool execution was blocked",
                    ),
                    is_error=True,
                )
        return _PreparedToolCall(tool_call=tool_call, tool=tool, args=validated)
    except Exception as e:  # noqa: BLE001 - mirror TS try/catch
        return _ImmediateToolCallOutcome(
            result=_create_error_tool_result(str(e)),
            is_error=True,
        )


# ── _execute_prepared_tool_call (agent-loop.ts:524-559) ──────────────────────
async def _execute_prepared_tool_call(
    prepared: _PreparedToolCall,
    signal: Optional[asyncio.Event],
    emit: AgentEventSink,
) -> _ExecutedToolCallOutcome:
    """Invoke tool.execute with an on_update bridge that schedules emit() calls.

    on_update is a sync callable (Python lambdas inside tool code may be sync).
    We capture the updates as awaitable tasks and await them all after execute
    returns, matching TS Promise.all(updateEvents) semantics.
    """
    update_tasks: list[asyncio.Task[None]] = []

    def _on_update(partial: AgentToolResult) -> None:
        coro = emit(ToolExecutionUpdateEvent(
            toolCallId=prepared.tool_call.id,
            toolName=prepared.tool_call.name,
            args=prepared.tool_call.arguments,
            partialResult=partial,
        ))
        update_tasks.append(asyncio.create_task(coro))

    try:
        result = await prepared.tool.execute(
            prepared.tool_call.id,
            prepared.args,
            signal,
            _on_update,
        )
        if update_tasks:
            await asyncio.gather(*update_tasks)
        return _ExecutedToolCallOutcome(result=result, is_error=False)
    except Exception as e:  # noqa: BLE001 - per TS contract, capture all
        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)
        return _ExecutedToolCallOutcome(
            result=_create_error_tool_result(str(e)),
            is_error=True,
        )


# ── _finalize_executed_tool_call (agent-loop.ts:561-600) ─────────────────────
async def _finalize_executed_tool_call(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    prepared: _PreparedToolCall,
    executed: _ExecutedToolCallOutcome,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    emit: AgentEventSink,
) -> ToolResultMessage:
    """Apply afterToolCall hook overrides, then emit tool_execution_end + the
    ToolResultMessage events."""
    result = executed.result
    is_error = executed.is_error

    if config.afterToolCall is not None:
        try:
            after = await config.afterToolCall(
                AfterToolCallContext(
                    assistantMessage=assistant_message,
                    toolCall=prepared.tool_call,
                    args=prepared.args,
                    result=result,
                    isError=is_error,
                    context=current_context,
                ),
                signal,
            )
            if after is not None:
                result = AgentToolResult(
                    content=after.content if after.content is not None else result.content,
                    details=after.details if after.details is not None else result.details,
                )
                if after.isError is not None:
                    is_error = after.isError
        except Exception as e:  # noqa: BLE001
            result = _create_error_tool_result(str(e))
            is_error = True

    return await _emit_tool_call_outcome(prepared.tool_call, result, is_error, emit)


# ── _emit_tool_call_outcome (agent-loop.ts:609-636) ──────────────────────────
async def _emit_tool_call_outcome(
    tool_call: AgentToolCall,
    result: AgentToolResult,
    is_error: bool,
    emit: AgentEventSink,
) -> ToolResultMessage:
    """Emit tool_execution_end + message_start + message_end for the tool result."""
    await emit(ToolExecutionEndEvent(
        toolCallId=tool_call.id,
        toolName=tool_call.name,
        result=result,
        isError=is_error,
    ))
    tr = ToolResultMessage(
        toolCallId=tool_call.id,
        toolName=tool_call.name,
        content=result.content,
        details=result.details,
        isError=is_error,
        timestamp=int(time.time() * 1000),
    )
    await emit(MessageStartEvent(message=tr))
    await emit(MessageEndEvent(message=tr))
    return tr


# ── _execute_tool_calls_sequential | _parallel (agent-loop.ts:350-438) ───────
async def _execute_tool_calls_sequential(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_calls: list[AgentToolCall],
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    emit: AgentEventSink,
) -> list[ToolResultMessage]:
    """One tool at a time: prepare -> execute -> finalize -> next."""
    results: list[ToolResultMessage] = []
    for tool_call in tool_calls:
        await emit(ToolExecutionStartEvent(
            toolCallId=tool_call.id, toolName=tool_call.name,
            args=tool_call.arguments,
        ))
        preparation = await _prepare_tool_call(
            current_context, assistant_message, tool_call, config, signal,
        )
        if isinstance(preparation, _ImmediateToolCallOutcome):
            results.append(await _emit_tool_call_outcome(
                tool_call, preparation.result, preparation.is_error, emit,
            ))
        else:
            executed = await _execute_prepared_tool_call(preparation, signal, emit)
            results.append(await _finalize_executed_tool_call(
                current_context, assistant_message, preparation,
                executed, config, signal, emit,
            ))
    return results


async def _execute_tool_calls_parallel(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_calls: list[AgentToolCall],
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    emit: AgentEventSink,
) -> list[ToolResultMessage]:
    """Preflight sequentially (so beforeToolCall hooks see deterministic order),
    then execute allowed tools concurrently. Final results emitted in source order."""
    results: list[ToolResultMessage] = []
    runnable: list[_PreparedToolCall] = []

    for tool_call in tool_calls:
        await emit(ToolExecutionStartEvent(
            toolCallId=tool_call.id, toolName=tool_call.name,
            args=tool_call.arguments,
        ))
        preparation = await _prepare_tool_call(
            current_context, assistant_message, tool_call, config, signal,
        )
        if isinstance(preparation, _ImmediateToolCallOutcome):
            results.append(await _emit_tool_call_outcome(
                tool_call, preparation.result, preparation.is_error, emit,
            ))
        else:
            runnable.append(preparation)

    running = [
        (prep, asyncio.create_task(_execute_prepared_tool_call(prep, signal, emit)))
        for prep in runnable
    ]
    for prep, task in running:
        executed = await task
        results.append(await _finalize_executed_tool_call(
            current_context, assistant_message, prep,
            executed, config, signal, emit,
        ))
    return results


async def _execute_tool_calls(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    emit: AgentEventSink,
) -> list[ToolResultMessage]:
    """Dispatch to sequential|parallel per config.toolExecution (agent-loop.ts:336-348)."""
    tool_calls = [c for c in assistant_message.content if isinstance(c, AgentToolCall)]
    if config.toolExecution == "sequential":
        return await _execute_tool_calls_sequential(
            current_context, assistant_message, tool_calls, config, signal, emit,
        )
    return await _execute_tool_calls_parallel(
        current_context, assistant_message, tool_calls, config, signal, emit,
    )


# ── _stream_assistant_response (agent-loop.ts:238-331) ───────────────────────
async def _stream_assistant_response(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    emit: AgentEventSink,
    stream_fn: Optional[StreamFn] = None,
) -> AssistantMessage:
    """One LLM call. Streams pi_ai events, accumulates the partial AssistantMessage,
    bridges each event into a MessageUpdateEvent. Returns the final AssistantMessage.

    Differences from TS upstream:
    - TS's EventStream.result() lets it await the final message separately.
      We don't have that - we read final_message from DoneEvent.message or
      ErrorEvent.error (whichever terminates the stream).
    """
    messages = context.messages
    if config.transformContext is not None:
        messages = await config.transformContext(messages, signal)

    converted = config.convertToLlm(messages)
    llm_messages = await _maybe_await(converted)

    llm_context = Context(
        systemPrompt=context.systemPrompt,
        messages=llm_messages,
        tools=[t.to_pi_ai_tool() for t in (context.tools or [])] or None,
    )

    resolved_api_key: Optional[str] = None
    if config.getApiKey is not None:
        resolved_api_key = await _maybe_await(config.getApiKey(config.model.provider))
    if not resolved_api_key:
        resolved_api_key = config.apiKey

    call_opts = config.model_copy(update={"apiKey": resolved_api_key, "signal": signal})

    stream = (stream_fn or stream_simple)(config.model, llm_context, call_opts)

    partial_message: Optional[AssistantMessage] = None
    added_partial = False
    final_message: Optional[AssistantMessage] = None

    async for event in stream:
        if isinstance(event, StartEvent):
            partial_message = event.partial
            context.messages.append(partial_message)
            added_partial = True
            await emit(MessageStartEvent(message=partial_message.model_copy(deep=True)))
        elif isinstance(event, (
            TextStartEvent, TextDeltaEvent, TextEndEvent,
            ThinkingStartEvent, ThinkingDeltaEvent, ThinkingEndEvent,
            ToolCallStartEvent, ToolCallDeltaEvent, ToolCallEndEvent,
        )):
            if partial_message is not None:
                partial_message = event.partial
                context.messages[-1] = partial_message
                await emit(MessageUpdateEvent(
                    message=partial_message.model_copy(deep=True),
                    assistantMessageEvent=event,
                ))
        elif isinstance(event, DoneEvent):
            final_message = event.message
            break
        elif isinstance(event, ErrorEvent):
            final_message = event.error
            break

    if final_message is None:
        final_message = AssistantMessage(
            api=config.model.api, provider=config.model.provider,
            model=config.model.id, timestamp=int(time.time() * 1000),
            stopReason="error",
            errorMessage="stream ended without done event",
        )

    if added_partial:
        context.messages[-1] = final_message
    else:
        context.messages.append(final_message)
        await emit(MessageStartEvent(message=final_message.model_copy(deep=True)))
    await emit(MessageEndEvent(message=final_message))
    return final_message


# ── _run_loop (agent-loop.ts:152-232) ────────────────────────────────────────
async def _run_loop(
    current_context: AgentContext,
    new_messages: list[AgentMessage],
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    emit: AgentEventSink,
    stream_fn: Optional[StreamFn] = None,
) -> None:
    """Main loop body. Continues until no tool calls + no steering + no follow-ups."""
    first_turn = True
    pending: list[AgentMessage] = []
    if config.getSteeringMessages is not None:
        pending = await config.getSteeringMessages()

    while True:
        has_more_tool_calls = True

        while has_more_tool_calls or len(pending) > 0:
            if not first_turn:
                await emit(TurnStartEvent())
            else:
                first_turn = False

            if pending:
                for message in pending:
                    await emit(MessageStartEvent(message=message))
                    await emit(MessageEndEvent(message=message))
                    current_context.messages.append(message)
                    new_messages.append(message)
                pending = []

            assistant_message = await _stream_assistant_response(
                current_context, config, signal, emit, stream_fn,
            )
            new_messages.append(assistant_message)

            if assistant_message.stopReason in ("error", "aborted"):
                await emit(TurnEndEvent(message=assistant_message, toolResults=[]))
                await emit(AgentEndEvent(messages=new_messages))
                return

            tool_calls = [c for c in assistant_message.content if isinstance(c, AgentToolCall)]
            has_more_tool_calls = len(tool_calls) > 0

            tool_results: list[ToolResultMessage] = []
            if has_more_tool_calls:
                tool_results = await _execute_tool_calls(
                    current_context, assistant_message, config, signal, emit,
                )
                for r in tool_results:
                    current_context.messages.append(r)
                    new_messages.append(r)

            await emit(TurnEndEvent(message=assistant_message, toolResults=tool_results))

            if config.getSteeringMessages is not None:
                pending = await config.getSteeringMessages()
            else:
                pending = []

        follow_ups: list[AgentMessage] = []
        if config.getFollowUpMessages is not None:
            follow_ups = await config.getFollowUpMessages()
        if follow_ups:
            pending = follow_ups
            continue
        break

    await emit(AgentEndEvent(messages=new_messages))


# ── Public entry points (agent-loop.ts:95-143) ───────────────────────────────
async def run_agent_loop(
    prompts: list[AgentMessage],
    context: AgentContext,
    config: AgentLoopConfig,
    emit: AgentEventSink,
    signal: Optional[asyncio.Event] = None,
    stream_fn: Optional[StreamFn] = None,
) -> list[AgentMessage]:
    """Start an agent loop with new prompt message(s). Emits agent_start,
    turn_start, message_start/end for each prompt, then enters the loop.

    Returns the list of messages added during this run (prompts + assistants
    + tool results + any steered/follow-up messages)."""
    new_messages: list[AgentMessage] = list(prompts)
    current_context = AgentContext(
        systemPrompt=context.systemPrompt,
        messages=[*context.messages, *prompts],
        tools=context.tools,
    )

    await emit(AgentStartEvent())
    await emit(TurnStartEvent())
    for prompt in prompts:
        await emit(MessageStartEvent(message=prompt))
        await emit(MessageEndEvent(message=prompt))

    await _run_loop(current_context, new_messages, config, signal, emit, stream_fn)
    return new_messages


async def run_agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    emit: AgentEventSink,
    signal: Optional[asyncio.Event] = None,
    stream_fn: Optional[StreamFn] = None,
) -> list[AgentMessage]:
    """Continue from existing context (no new prompt added). The last message
    must NOT be an assistant role - convertToLlm needs a user or toolResult
    message to terminate the conversation properly."""
    if len(context.messages) == 0:
        raise ValueError("Cannot continue: no messages in context")
    last = context.messages[-1]
    if getattr(last, "role", None) == "assistant":
        raise ValueError("Cannot continue from message role: assistant")

    new_messages: list[AgentMessage] = []
    current_context = AgentContext(
        systemPrompt=context.systemPrompt,
        messages=list(context.messages),
        tools=context.tools,
    )

    await emit(AgentStartEvent())
    await emit(TurnStartEvent())

    await _run_loop(current_context, new_messages, config, signal, emit, stream_fn)
    return new_messages
