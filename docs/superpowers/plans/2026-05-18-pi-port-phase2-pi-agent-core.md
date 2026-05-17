# pi-mono → Python port — Phase 2: pi_agent_core layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port `@mariozechner/pi-mono/packages/agent` (TypeScript, ~1520 LOC) to Python as `agent/pi_agent_core/` package. Wraps the Phase 1 `pi_ai` layer with: Agent class (stateful), run_agent_loop (turn loop), AgentTool (with pydantic schema + async execute), AgentEvent (discriminated union), hooks (beforeToolCall/afterToolCall/transformContext/convertToLlm), parallel|sequential tool execution, steering+follow-up message queues, abort via `asyncio.Event`.

**Architecture:** Two files do the heavy lifting — `agent_loop.py` (~480 LOC, low-level turn loop, ports `agent-loop.ts`) and `agent.py` (~430 LOC, stateful facade, ports `agent.ts`). `types.py` (~270 LOC) defines the data backbone. `proxy.py` is a 20-LOC stub (web-UI proxy is out of scope per spec). All hooks/tools are async-native.

**Tech Stack:** Python 3.11, `pydantic>=2.12`, `pytest`, `pytest-asyncio` (Phase 1 deps already installed). Builds directly on Phase 1 `agent/pi_ai/` (commits `d7b5954`..`5dbcbac`).

**Spec:** `docs/superpowers/specs/2026-05-18-pi-port-design.md` (commit `1481b5f`).

**Phase 2 scope:** Layer 2 only (pi_agent_core). Phase 3 (integration into v7: orchestrator/architect/coder/tester/server) is a separate plan. Phase 4 (cutover with real OpenRouter + UI smoke) is a separate plan.

**Convention notes:**
- Working dir: `H:\ai-hse-diploma-agent\Eco.Toolchain\Eco.AI.Assembly1\`
- All Python commands assume `cd Eco.Toolchain/Eco.AI.Assembly1`; all `git` commands assume `cd /h/ai-hse-diploma-agent`.
- Branch: `feat/v6-five-node-pipeline` (same ongoing v7 work — Phase 1 landed there).
- TS source paths use `F:/pi-harness/pi-mono/packages/agent/src/` prefix.
- Code-first: smoke-tests after implementation in each task, not before.
- `continue` is a Python keyword; the TS `Agent.continue()` method is renamed `Agent.continue_run()` in the Python port.

---

## Task 1: Create pi_agent_core package skeleton

**Files:**
- Create: `agent/pi_agent_core/__init__.py`
- Create: `agent/pi_agent_core/tests/__init__.py`
- Create: `agent/pi_agent_core/tests/conftest.py`

- [ ] **Step 1: Create directories and empty __init__.py files**

```bash
mkdir -p Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/tests
```

Create empty `agent/pi_agent_core/__init__.py`:
```python
"""pi_agent_core - Python port of @mariozechner/pi-mono/packages/agent.

This package wraps the Phase 1 pi_ai layer with:
- Agent class (stateful conversation handler, message queues, event subscribers)
- run_agent_loop (low-level turn loop with hooks)
- AgentTool (pydantic-schema tool definition with async execute callback)
- AgentEvent (discriminated union of lifecycle events)

See docs/superpowers/specs/2026-05-18-pi-port-design.md for design.
"""
```

Create empty `agent/pi_agent_core/tests/__init__.py` (empty file).

- [ ] **Step 2: Create pytest fixtures file**

Create `agent/pi_agent_core/tests/conftest.py`:
```python
"""Shared fixtures for pi_agent_core tests."""
from __future__ import annotations

import pytest

from agent.pi_ai import Model, ModelCost
from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.providers.faux import make_faux_provider


@pytest.fixture
def faux_text_model():
    """Model wired to a faux provider that emits text 'hello' and stop."""
    register_provider("faux-hello", make_faux_provider(text="hello"))
    return Model(
        id="m", name="m", api="faux-hello", provider="faux",
        baseUrl="", cost=ModelCost(),
    )
```

- [ ] **Step 3: Verify imports work**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "import agent.pi_agent_core; print('ok')"
```

Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
cd /h/ai-hse-diploma-agent
git add Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/
git commit -m "feat(pi_agent_core): scaffold pi_agent_core package skeleton"
```

---

## Task 2: pi_agent_core/types.py — type backbone

**Files:**
- Create: `agent/pi_agent_core/types.py`
- Reference: `F:/pi-harness/pi-mono/packages/agent/src/types.ts` (341 LOC)

**Background:** This file defines every type the agent layer consumes. Discriminated unions use `pydantic.Field(discriminator="type")`. `AgentMessage` is an alias for `pi_ai.Message` (no custom messages in scope per spec). `AgentTool` extends `pi_ai.Tool` and adds the executable callback; `parameters` is a pydantic schema class (subclass of `BaseModel`), not a JSON schema dict, because we want pydantic-native validation.

All `BaseModel` subclasses use `extra="allow"` to match Phase 1 convention.

- [ ] **Step 1: Imports + type aliases (types.ts:1-40)**

Create `agent/pi_agent_core/types.py`:
```python
"""pi_agent_core type backbone. Mirrors @mariozechner/pi-mono/packages/agent/src/types.ts.

AgentMessage is an alias for pi_ai.Message (no custom messages in Phase 2 scope).
AgentTool extends pi_ai.Tool with an async execute callback and a pydantic
parameters class. AgentEvent is a discriminated union for all lifecycle events.
"""
from __future__ import annotations

import asyncio
from typing import (
    Annotated, Any, Awaitable, Callable, Literal, Optional, Protocol,
    Union, runtime_checkable,
)

from pydantic import BaseModel, ConfigDict, Field

from agent.pi_ai.types import (
    AssistantMessage, ImageContent, Message, Model, SimpleStreamOptions,
    TextContent, ThinkingLevel, ToolCall, ToolResultMessage, Tool,
)


# ── Public type aliases (types.ts:35-38, 240-245) ─────────────────────────────
ToolExecutionMode = Literal["sequential", "parallel"]
AgentMessage = Message  # Phase 2: no custom messages (per spec out-of-scope)
AgentToolCall = ToolCall  # alias for clarity in the agent layer
```

- [ ] **Step 2: Port AgentToolResult + AgentTool (types.ts:280-307)**

Append:
```python
class AgentToolResult(BaseModel):
    """Final or partial result produced by a tool (types.ts:281-286)."""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    content: list[Union[TextContent, ImageContent]] = Field(default_factory=list)
    details: Any = None


# Type alias for the streaming-update callback a tool's execute() may receive.
# Sync-callable (the agent loop converts it into an async emit internally).
AgentToolUpdateCallback = Callable[[AgentToolResult], None]


class AgentTool(BaseModel):
    """Tool definition used by the agent runtime (types.ts:292-307).

    Differences from pi_ai.Tool:
    - parameters is a pydantic BaseModel subclass, not a JSON-schema dict
      (the agent layer validates with pydantic, not AJV).
    - execute is an async callable: (toolCallId, params, signal, on_update)
      -> AgentToolResult
    - label is the human-readable UI label.
    - prepare_arguments is an optional pre-validation shim for raw LLM args.
    """
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    name: str
    description: str
    label: str
    parameters: type[BaseModel]
    prepare_arguments: Optional[Callable[[Any], Any]] = None
    execute: Callable[
        [str, BaseModel, Optional[asyncio.Event], Optional[AgentToolUpdateCallback]],
        Awaitable[AgentToolResult],
    ]

    def to_pi_ai_tool(self) -> Tool:
        """Convert to pi_ai.Tool (JSON-schema form) for the LLM request body."""
        return Tool(
            name=self.name,
            description=self.description,
            parameters=self.parameters.model_json_schema(),
        )
```

- [ ] **Step 3: Port AgentContext + hook contexts (types.ts:46-94, 309-317)**

Append:
```python
class AgentContext(BaseModel):
    """Context snapshot passed into the low-level agent loop (types.ts:310-317)."""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    systemPrompt: str = ""
    messages: list[AgentMessage] = Field(default_factory=list)
    tools: Optional[list[AgentTool]] = None


class BeforeToolCallResult(BaseModel):
    """Result returned from beforeToolCall hook (types.ts:46-49).

    block=True prevents execution; reason becomes the error text shown to the model.
    """
    model_config = ConfigDict(extra="allow")
    block: bool = False
    reason: Optional[str] = None


class AfterToolCallResult(BaseModel):
    """Partial override returned from afterToolCall (types.ts:62-66).

    Field-by-field merge (no deep merge). None means: keep original.
    """
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    content: Optional[list[Union[TextContent, ImageContent]]] = None
    details: Any = None
    isError: Optional[bool] = None


class BeforeToolCallContext(BaseModel):
    """Context passed to beforeToolCall hook (types.ts:69-78)."""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    assistantMessage: AssistantMessage
    toolCall: AgentToolCall
    args: Any  # validated args (pydantic instance for that tool's schema)
    context: AgentContext


class AfterToolCallContext(BaseModel):
    """Context passed to afterToolCall hook (types.ts:81-94)."""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    assistantMessage: AssistantMessage
    toolCall: AgentToolCall
    args: Any
    result: AgentToolResult
    isError: bool
    context: AgentContext
```

- [ ] **Step 4: Port StreamFn protocol (types.ts:16-26)**

Append:
```python
@runtime_checkable
class StreamFn(Protocol):
    """Async stream function contract (types.ts:24-26).

    Matches the signature of agent.pi_ai.stream_simple. May either be a coroutine
    that returns an AsyncIterator, or the AsyncIterator-returning function directly.
    Implementations must NOT raise — failures must be encoded as ErrorEvent
    in the stream.
    """
    def __call__(
        self,
        model: Model,
        context: Any,  # pi_ai.Context
        options: Optional[SimpleStreamOptions] = None,
    ) -> Any: ...  # AsyncIterator[pi_ai.AssistantMessageEvent]
```

- [ ] **Step 5: Port AgentLoopConfig (types.ts:96-214)**

Append:
```python
# Hook callable type aliases for readability
BeforeToolCallHook = Callable[
    [BeforeToolCallContext, Optional[asyncio.Event]],
    Awaitable[Optional[BeforeToolCallResult]],
]
AfterToolCallHook = Callable[
    [AfterToolCallContext, Optional[asyncio.Event]],
    Awaitable[Optional[AfterToolCallResult]],
]
ConvertToLlmHook = Callable[
    [list[AgentMessage]],
    Union[list[Message], Awaitable[list[Message]]],
]
TransformContextHook = Callable[
    [list[AgentMessage], Optional[asyncio.Event]],
    Awaitable[list[AgentMessage]],
]
GetApiKeyHook = Callable[
    [str],
    Union[Optional[str], Awaitable[Optional[str]]],
]
GetMessagesHook = Callable[[], Awaitable[list[AgentMessage]]]


class AgentLoopConfig(SimpleStreamOptions):
    """Low-level agent-loop configuration (types.ts:96-214).

    Inherits all SimpleStreamOptions fields (temperature, maxTokens, signal, apiKey,
    reasoning, thinkingBudgets, transport, headers, sessionId, onPayload, onResponse, ...).
    Adds: model, convertToLlm, transformContext, getApiKey, hooks, toolExecution.
    """
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    model: Model
    convertToLlm: ConvertToLlmHook
    transformContext: Optional[TransformContextHook] = None
    getApiKey: Optional[GetApiKeyHook] = None
    getSteeringMessages: Optional[GetMessagesHook] = None
    getFollowUpMessages: Optional[GetMessagesHook] = None
    toolExecution: ToolExecutionMode = "parallel"
    beforeToolCall: Optional[BeforeToolCallHook] = None
    afterToolCall: Optional[AfterToolCallHook] = None
```

- [ ] **Step 6: Port AgentEvent discriminated union (types.ts:326-341)**

Append:
```python
class _AgentEvBase(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)


class AgentStartEvent(_AgentEvBase):
    type: Literal["agent_start"] = "agent_start"


class AgentEndEvent(_AgentEvBase):
    type: Literal["agent_end"] = "agent_end"
    messages: list[AgentMessage] = Field(default_factory=list)


class TurnStartEvent(_AgentEvBase):
    type: Literal["turn_start"] = "turn_start"


class TurnEndEvent(_AgentEvBase):
    type: Literal["turn_end"] = "turn_end"
    message: AgentMessage
    toolResults: list[ToolResultMessage] = Field(default_factory=list)


class MessageStartEvent(_AgentEvBase):
    type: Literal["message_start"] = "message_start"
    message: AgentMessage


class MessageUpdateEvent(_AgentEvBase):
    """Emitted only for assistant messages during streaming. Wraps a raw
    pi_ai AssistantMessageEvent so subscribers can read inner deltas."""
    type: Literal["message_update"] = "message_update"
    message: AgentMessage
    assistantMessageEvent: Any  # pi_ai.AssistantMessageEvent (avoid circular validation cost)


class MessageEndEvent(_AgentEvBase):
    type: Literal["message_end"] = "message_end"
    message: AgentMessage


class ToolExecutionStartEvent(_AgentEvBase):
    type: Literal["tool_execution_start"] = "tool_execution_start"
    toolCallId: str
    toolName: str
    args: Any


class ToolExecutionUpdateEvent(_AgentEvBase):
    type: Literal["tool_execution_update"] = "tool_execution_update"
    toolCallId: str
    toolName: str
    args: Any
    partialResult: Any


class ToolExecutionEndEvent(_AgentEvBase):
    type: Literal["tool_execution_end"] = "tool_execution_end"
    toolCallId: str
    toolName: str
    result: Any
    isError: bool


AgentEvent = Annotated[
    Union[
        AgentStartEvent, AgentEndEvent,
        TurnStartEvent, TurnEndEvent,
        MessageStartEvent, MessageUpdateEvent, MessageEndEvent,
        ToolExecutionStartEvent, ToolExecutionUpdateEvent, ToolExecutionEndEvent,
    ],
    Field(discriminator="type"),
]
```

- [ ] **Step 7: Port AgentState (types.ts:248-278)**

Append:
```python
class AgentState(BaseModel):
    """Public agent state (types.ts:253-278).

    Unlike the TS version (accessor properties for tools/messages), Python
    pydantic doesn't natively support get/set with copy-on-assign. The Agent
    class assigns these as plain attributes after copying — the contract is
    enforced in agent.py, not here.
    """
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    systemPrompt: str = ""
    model: Optional[Model] = None
    thinkingLevel: Union[ThinkingLevel, Literal["off"]] = "off"
    tools: list[AgentTool] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    isStreaming: bool = False
    streamingMessage: Optional[AgentMessage] = None
    pendingToolCalls: set[str] = Field(default_factory=set)
    errorMessage: Optional[str] = None
```

- [ ] **Step 8: Verify imports**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
from agent.pi_agent_core.types import (
    AgentMessage, AgentTool, AgentToolResult, AgentContext,
    AgentEvent, AgentLoopConfig, AgentState,
    BeforeToolCallContext, AfterToolCallContext,
    BeforeToolCallResult, AfterToolCallResult,
    ToolExecutionMode, StreamFn,
)
print('ok')
"
```

Expected: `ok`.

- [ ] **Step 9: Commit**

```bash
cd /h/ai-hse-diploma-agent
git add Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/types.py
git commit -m "feat(pi_agent_core): port types.ts - AgentMessage, AgentTool, AgentEvent, AgentLoopConfig"
```

---

## Task 3: pi_agent_core/agent_loop.py — tool execution helpers

**Files:**
- Create: `agent/pi_agent_core/agent_loop.py` (partial — Tasks 3 + 4 build it together)
- Reference: `F:/pi-harness/pi-mono/packages/agent/src/agent-loop.ts` (636 LOC, focus this task on lines 333-636)

**Background:** Build the file bottom-up. This task implements the leaf helpers (tool preparation, sequential/parallel execution, hook orchestration). Task 4 wires them into the main turn loop.

- [ ] **Step 1: File header + imports**

Create `agent/pi_agent_core/agent_loop.py`:
```python
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
from typing import Any, AsyncIterator, Awaitable, Callable, Optional, Union

from pydantic import BaseModel

from agent.pi_ai import stream_simple
from agent.pi_ai.types import (
    AssistantMessage, AssistantMessageEvent, Context, DoneEvent, ErrorEvent,
    ImageContent, MessageStartEvent as _PiMessageStart,  # unused, here for clarity
    StartEvent, TextContent, TextDeltaEvent, TextEndEvent, TextStartEvent,
    ThinkingDeltaEvent, ThinkingEndEvent, ThinkingStartEvent,
    ToolCallDeltaEvent, ToolCallEndEvent, ToolCallStartEvent,
    ToolResultMessage,
)
from agent.pi_ai.utils.validation import validate_args
from agent.pi_agent_core.types import (
    AfterToolCallContext, AgentContext, AgentEvent, AgentLoopConfig,
    AgentMessage, AgentStartEvent, AgentEndEvent, AgentTool, AgentToolCall,
    AgentToolResult, BeforeToolCallContext, MessageEndEvent, MessageStartEvent,
    MessageUpdateEvent, StreamFn, ToolExecutionEndEvent, ToolExecutionStartEvent,
    ToolExecutionUpdateEvent, TurnEndEvent, TurnStartEvent,
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
```

- [ ] **Step 2: Prepared/Immediate tool-call result dataclasses (agent-loop.ts:440-456)**

Append:
```python
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
    """Result of tool.execute() — may itself be an error if the tool raised."""
    result: AgentToolResult
    is_error: bool
```

- [ ] **Step 3: prepare_arguments + validation helper (agent-loop.ts:458-470)**

Append:
```python
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
    # Construct a fresh ToolCall with the prepared arguments dict.
    return tool_call.model_copy(update={"arguments": prepared})
```

- [ ] **Step 4: _prepare_tool_call — validation + beforeToolCall hook (agent-loop.ts:472-522)**

Append:
```python
async def _prepare_tool_call(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_call: AgentToolCall,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
) -> Union[_PreparedToolCall, _ImmediateToolCallOutcome]:
    """Validate args, then call beforeToolCall hook (if any).
    Returns Prepared (ready to execute) or Immediate (error / blocked)."""
    tool = next((t for t in (current_context.tools or []) if t.name == tool_call.name), None)
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
```

- [ ] **Step 5: _execute_prepared_tool_call — runs tool.execute, captures onUpdate (agent-loop.ts:524-559)**

Append:
```python
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
        # Schedule an emit; don't block tool execution on it.
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
```

- [ ] **Step 6: _finalize_executed_tool_call — afterToolCall hook + emit (agent-loop.ts:561-600)**

Append:
```python
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
```

- [ ] **Step 7: _emit_tool_call_outcome — final emits + ToolResultMessage (agent-loop.ts:609-636)**

Append:
```python
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
```

- [ ] **Step 8: _execute_tool_calls_sequential / _execute_tool_calls_parallel (agent-loop.ts:350-438)**

Append:
```python
async def _execute_tool_calls_sequential(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_calls: list[AgentToolCall],
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    emit: AgentEventSink,
) -> list[ToolResultMessage]:
    """One tool at a time: prepare → execute → finalize → next."""
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

    # Launch all in parallel
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
```

- [ ] **Step 9: Verify syntax — import only**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "from agent.pi_agent_core import agent_loop; print('ok')"
```

Expected: `ok` (no NameError or import error). Task 4 will add the missing top-level entry points.

- [ ] **Step 10: Commit (partial, locks down the helpers)**

```bash
cd /h/ai-hse-diploma-agent
git add Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/agent_loop.py
git commit -m "feat(pi_agent_core): agent_loop tool execution helpers (prepare/execute/finalize)"
```

---

## Task 4: pi_agent_core/agent_loop.py — main loop + assistant streaming

**Files:**
- Modify: `agent/pi_agent_core/agent_loop.py` (append to file from Task 3)
- Reference: `F:/pi-harness/pi-mono/packages/agent/src/agent-loop.ts` (lines 1-331)

- [ ] **Step 1: _stream_assistant_response — one LLM call + event bridging (agent-loop.ts:238-331)**

Append to `agent/pi_agent_core/agent_loop.py`:
```python
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
      We don't have that — we read final_message from DoneEvent.message or
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

    # Resolve API key (mostly relevant for OAuth tokens; for our Phase 1 it falls
    # through to env). config.apiKey is the static fallback.
    resolved_api_key: Optional[str] = None
    if config.getApiKey is not None:
        resolved_api_key = await _maybe_await(config.getApiKey(config.model.provider))
    if not resolved_api_key:
        resolved_api_key = config.apiKey

    # Build per-call options. signal goes via SimpleStreamOptions.signal (Any field).
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
        # Stream ended without done/error — synthesize an error message so the
        # loop above us can record it and end the turn cleanly.
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
```

- [ ] **Step 2: _run_loop — outer/inner turn loop (agent-loop.ts:152-232)**

Append:
```python
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

        # Agent would stop here — check for follow-up messages.
        follow_ups: list[AgentMessage] = []
        if config.getFollowUpMessages is not None:
            follow_ups = await config.getFollowUpMessages()
        if follow_ups:
            pending = follow_ups
            continue
        break

    await emit(AgentEndEvent(messages=new_messages))
```

- [ ] **Step 3: run_agent_loop + run_agent_loop_continue public entry points (agent-loop.ts:95-143)**

Append:
```python
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
    must NOT be an assistant role — convertToLlm needs a user or toolResult
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
```

- [ ] **Step 4: Verify imports**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
from agent.pi_agent_core.agent_loop import (
    run_agent_loop, run_agent_loop_continue, AgentEventSink,
)
print('ok')
"
```

Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
cd /h/ai-hse-diploma-agent
git add Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/agent_loop.py
git commit -m "feat(pi_agent_core): agent_loop main turn loop + stream_assistant_response"
```

---

## Task 5: pi_agent_core/agent.py — PendingMessageQueue + default helpers

**Files:**
- Create: `agent/pi_agent_core/agent.py` (partial — Tasks 5 + 6 build it together)
- Reference: `F:/pi-harness/pi-mono/packages/agent/src/agent.ts` (focus this task on lines 1-150)

- [ ] **Step 1: File header + imports + module constants**

Create `agent/pi_agent_core/agent.py`:
```python
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
    AgentContext, AgentEvent, AgentLoopConfig, AgentMessage, AgentState,
    AgentTool, BeforeToolCallContext, BeforeToolCallHook, BeforeToolCallResult,
    ConvertToLlmHook, GetApiKeyHook, StreamFn, ToolExecutionMode,
    TransformContextHook,
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
```

- [ ] **Step 2: default_convert_to_llm helper (agent.ts:27-31)**

Append:
```python
def default_convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    """Default convertToLlm: filter to roles the LLM understands.

    Drops any custom message types (which Phase 2 doesn't define anyway).
    """
    return [m for m in messages if getattr(m, "role", None) in ("user", "assistant", "toolResult")]
```

- [ ] **Step 3: PendingMessageQueue (agent.ts:113-144)**

Append:
```python
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
```

- [ ] **Step 4: _ActiveRun dataclass (agent.ts:146-150)**

Append:
```python
@dataclass
class _ActiveRun:
    """Tracks an in-flight agent run.

    - future: resolves when the run + agent_end listeners complete.
    - abort_event: signal raised by Agent.abort() to cancel.
    """
    future: asyncio.Future[None]
    abort_event: asyncio.Event
```

- [ ] **Step 5: Verify imports**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
from agent.pi_agent_core.agent import (
    QueueMode, _PendingMessageQueue, _ActiveRun, default_convert_to_llm,
    _DEFAULT_MODEL, _EMPTY_USAGE,
)
q = _PendingMessageQueue('all')
print('ok')
"
```

Expected: `ok`.

- [ ] **Step 6: Commit (partial)**

```bash
cd /h/ai-hse-diploma-agent
git add Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/agent.py
git commit -m "feat(pi_agent_core): agent.py - PendingMessageQueue + default helpers"
```

---

## Task 6: pi_agent_core/agent.py — Agent class

**Files:**
- Modify: `agent/pi_agent_core/agent.py` (append to file from Task 5)
- Reference: `F:/pi-harness/pi-mono/packages/agent/src/agent.ts` (lines 152-543)

**Background:** The Agent class is a stateful facade. It owns one `AgentState`, exposes a `prompt()` entry point that drives `run_agent_loop`, lets subscribers listen to events, and provides `steer()` / `follow_up()` / `abort()` / `reset()` controls. At most one run can be active at a time.

- [ ] **Step 1: AgentOptions dataclass (agent.ts:93-111)**

Append to `agent/pi_agent_core/agent.py`:
```python
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
```

- [ ] **Step 2: Agent class skeleton + constructor + state property (agent.ts:152-231)**

Append:
```python
class Agent:
    """Stateful wrapper around the low-level agent loop (agent.ts:158-543).

    At most one run can be active at a time. Listeners receive events in
    subscription order; awaited listeners are part of run settlement.

    Note: TS uses TypeScript get/set accessors for state.tools and state.messages
    to copy-on-assign. In Python we expose state.tools and state.messages as
    plain attributes — callers should treat them as immutable from outside.
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
        """Current agent state. Do not mutate fields directly — use set_tools/set_messages."""
        return self._state

    def set_tools(self, tools: list[AgentTool]) -> None:
        """Copy-on-assign semantics for tools list (matches TS state.tools setter)."""
        self._state.tools = list(tools)

    def set_messages(self, messages: list[AgentMessage]) -> None:
        """Copy-on-assign semantics for messages list."""
        self._state.messages = list(messages)
```

- [ ] **Step 3: Subscribe + queue accessors (agent.ts:219-280)**

Append:
```python
    def subscribe(
        self, listener: Callable[[AgentEvent, asyncio.Event], Awaitable[None]],
    ) -> Callable[[], None]:
        """Subscribe to agent events. Returns an unsubscribe function.

        Listener gets (event, abort_event). Awaited promises are part of run
        settlement — agent stays in "active" state until all agent_end listeners
        finish.
        """
        self._listeners.append(listener)

        def unsubscribe() -> None:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

        return unsubscribe

    # Steering and follow-up queue API
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
```

- [ ] **Step 4: Abort + waitForIdle + reset (agent.ts:282-310)**

Append:
```python
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
```

- [ ] **Step 5: prompt() + continue_run() entry points (agent.ts:312-353)**

Append:
```python
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
```

- [ ] **Step 6: _normalize_prompt_input + _run_prompt_messages + _run_continuation (agent.ts:355-400)**

Append:
```python
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
        }]  # type: ignore[list-item]  # plain dict accepted via Message discriminator

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
```

- [ ] **Step 7: _create_context_snapshot + _create_loop_config (agent.ts:402-436)**

Append:
```python
    def _create_context_snapshot(self) -> AgentContext:
        return AgentContext(
            systemPrompt=self._state.systemPrompt,
            messages=list(self._state.messages),
            tools=list(self._state.tools),
        )

    def _create_loop_config(self, skip_initial_steering_poll: bool = False) -> AgentLoopConfig:
        # Local flag flips after first poll.
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
```

- [ ] **Step 8: _run_with_lifecycle + _handle_run_failure + _finish_run (agent.ts:438-486)**

Append:
```python
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
        # Emit agent_end with the failure so subscribers see it.
        from agent.pi_agent_core.types import AgentEndEvent
        await self._process_events(AgentEndEvent(messages=[failure]))

    def _finish_run(self) -> None:
        self._state.isStreaming = False
        self._state.streamingMessage = None
        self._state.pendingToolCalls = set()
        if self._active_run is not None and not self._active_run.future.done():
            self._active_run.future.set_result(None)
        self._active_run = None
```

- [ ] **Step 9: _process_events — state reducer + listener dispatch (agent.ts:488-543)**

Append:
```python
    async def _process_events(self, event: AgentEvent) -> None:
        """Reduce internal state for a loop event, then await listeners.

        agent_end means no further loop events — but the run is idle only after
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
```

- [ ] **Step 10: Verify import + basic instantiation**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
from agent.pi_agent_core.agent import Agent, AgentOptions
a = Agent(AgentOptions(initial_state={'systemPrompt': 'hi'}))
print('state:', a.state.systemPrompt, 'tools:', a.state.tools)
print('ok')
"
```

Expected: `state: hi tools: []` then `ok`.

- [ ] **Step 11: Commit**

```bash
cd /h/ai-hse-diploma-agent
git add Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/agent.py
git commit -m "feat(pi_agent_core): Agent class - prompt/continue/abort/subscribe + state reducer"
```

---

## Task 7: pi_agent_core/proxy.py stub + __init__.py public re-exports

**Files:**
- Create: `agent/pi_agent_core/proxy.py`
- Modify: `agent/pi_agent_core/__init__.py`

**Background:** `proxy.py` is a deliberate stub per spec (web-UI proxy is out of scope for Phase 2). The `__init__.py` rewrite exposes the public API.

- [ ] **Step 1: Create proxy.py stub**

Create `agent/pi_agent_core/proxy.py`:
```python
"""Browser-relay proxy stub.

Per docs/superpowers/specs/2026-05-18-pi-port-design.md (Out of scope), the
browser proxy is intentionally not implemented in Phase 2. This module is a
placeholder so callers attempting to import it get a clear error rather than
ModuleNotFoundError.
"""
from __future__ import annotations


def make_proxy(*args, **kwargs):
    """Not implemented. See docs/superpowers/specs/2026-05-18-pi-port-design.md."""
    raise NotImplementedError(
        "pi_agent_core.proxy is a stub. Web-UI proxy is out of scope for Phase 2."
    )
```

- [ ] **Step 2: Overwrite __init__.py with public re-exports**

Overwrite `agent/pi_agent_core/__init__.py`:
```python
"""pi_agent_core - Python port of @mariozechner/pi-mono/packages/agent.

Public API:
    from agent.pi_agent_core import (
        # Class facades
        Agent, AgentOptions,
        # Low-level
        run_agent_loop, run_agent_loop_continue, AgentEventSink,
        # Types
        AgentMessage, AgentContext, AgentTool, AgentToolResult, AgentState,
        AgentEvent, AgentLoopConfig, ToolExecutionMode,
        # Hook contexts/results
        BeforeToolCallContext, BeforeToolCallResult,
        AfterToolCallContext, AfterToolCallResult,
        # Defaults
        default_convert_to_llm,
        # Sub-types of AgentEvent (for isinstance checks)
        AgentStartEvent, AgentEndEvent,
        TurnStartEvent, TurnEndEvent,
        MessageStartEvent, MessageUpdateEvent, MessageEndEvent,
        ToolExecutionStartEvent, ToolExecutionUpdateEvent, ToolExecutionEndEvent,
    )

See docs/superpowers/specs/2026-05-18-pi-port-design.md for design.
"""

from agent.pi_agent_core.agent import (
    Agent, AgentOptions, default_convert_to_llm,
)
from agent.pi_agent_core.agent_loop import (
    AgentEventSink, run_agent_loop, run_agent_loop_continue,
)
from agent.pi_agent_core.types import (
    AfterToolCallContext, AfterToolCallResult,
    AgentContext, AgentEndEvent, AgentEvent, AgentLoopConfig, AgentMessage,
    AgentStartEvent, AgentState, AgentTool, AgentToolResult,
    BeforeToolCallContext, BeforeToolCallResult,
    MessageEndEvent, MessageStartEvent, MessageUpdateEvent,
    ToolExecutionEndEvent, ToolExecutionMode, ToolExecutionStartEvent,
    ToolExecutionUpdateEvent, TurnEndEvent, TurnStartEvent,
)

__all__ = [
    "Agent", "AgentOptions", "default_convert_to_llm",
    "run_agent_loop", "run_agent_loop_continue", "AgentEventSink",
    "AgentMessage", "AgentContext", "AgentTool", "AgentToolResult", "AgentState",
    "AgentEvent", "AgentLoopConfig", "ToolExecutionMode",
    "BeforeToolCallContext", "BeforeToolCallResult",
    "AfterToolCallContext", "AfterToolCallResult",
    "AgentStartEvent", "AgentEndEvent",
    "TurnStartEvent", "TurnEndEvent",
    "MessageStartEvent", "MessageUpdateEvent", "MessageEndEvent",
    "ToolExecutionStartEvent", "ToolExecutionUpdateEvent", "ToolExecutionEndEvent",
]
```

- [ ] **Step 3: Verify public API**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
import agent.pi_agent_core as p
print('exports:', sorted(p.__all__))
print('Agent:', p.Agent)
print('run_agent_loop:', p.run_agent_loop.__name__)
"
```

Expected: prints the full export list, references Agent class and run_agent_loop function.

- [ ] **Step 4: Verify proxy stub**

Run:
```bash
python -c "
from agent.pi_agent_core.proxy import make_proxy
try:
    make_proxy()
    print('FAIL: should have raised')
except NotImplementedError as e:
    print('proxy stub:', str(e)[:60])
"
```

Expected: `proxy stub: pi_agent_core.proxy is a stub. ...`

- [ ] **Step 5: Commit**

```bash
cd /h/ai-hse-diploma-agent
git add Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/proxy.py Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/__init__.py
git commit -m "feat(pi_agent_core): proxy stub + public re-exports"
```

---

## Task 8: Smoke tests

**Files:**
- Create: `agent/pi_agent_core/tests/test_types_smoke.py`
- Create: `agent/pi_agent_core/tests/test_agent_loop_smoke.py`
- Create: `agent/pi_agent_core/tests/test_agent_smoke.py`

**Background:** Code-first per spec. These are safety-net tests that catch obvious regressions during Phase 3 integration. NOT TDD — code already exists.

- [ ] **Step 1: test_types_smoke — discriminated union round-trip**

Create `agent/pi_agent_core/tests/test_types_smoke.py`:
```python
"""Type backbone smoke tests for pi_agent_core."""
from __future__ import annotations

import pytest
from pydantic import BaseModel, TypeAdapter

from agent.pi_agent_core.types import (
    AgentEndEvent, AgentEvent, AgentStartEvent, AgentTool, AgentToolResult,
    BeforeToolCallResult, ToolExecutionStartEvent, TurnEndEvent,
)
from agent.pi_ai.types import AssistantMessage, TextContent


class _DummyArgs(BaseModel):
    x: int


async def _noop_execute(call_id, params, signal, on_update):
    return AgentToolResult(content=[TextContent(text="ok")], details=None)


def test_agent_tool_construction():
    t = AgentTool(
        name="t", description="d", label="L",
        parameters=_DummyArgs, execute=_noop_execute,
    )
    assert t.name == "t"
    pi_tool = t.to_pi_ai_tool()
    assert pi_tool.name == "t"
    assert "properties" in pi_tool.parameters  # JSON schema generated


def test_agent_tool_result_default():
    r = AgentToolResult()
    assert r.content == []
    assert r.details is None


def test_before_tool_call_result_block_default_false():
    r = BeforeToolCallResult()
    assert r.block is False
    assert r.reason is None


def test_agent_event_discriminator_round_trip():
    ev = ToolExecutionStartEvent(toolCallId="c1", toolName="foo", args={"x": 1})
    adapter = TypeAdapter(AgentEvent)
    restored = adapter.validate_python(ev.model_dump())
    assert isinstance(restored, ToolExecutionStartEvent)
    assert restored.toolCallId == "c1"


def test_agent_start_end_events():
    start = AgentStartEvent()
    end = AgentEndEvent(messages=[])
    assert start.type == "agent_start"
    assert end.type == "agent_end"
    assert end.messages == []


def test_turn_end_with_assistant_message():
    msg = AssistantMessage(api="x", provider="y", model="z", timestamp=1)
    ev = TurnEndEvent(message=msg, toolResults=[])
    assert ev.message.role == "assistant"
```

- [ ] **Step 2: test_agent_loop_smoke — through-loop with faux provider**

Create `agent/pi_agent_core/tests/test_agent_loop_smoke.py`:
```python
"""Agent-loop smoke tests using the faux provider from pi_ai.

These exercise run_agent_loop end-to-end without a real LLM.
"""
from __future__ import annotations

import asyncio
import time

import pytest
from pydantic import BaseModel

from agent.pi_ai import Context, Model, ModelCost
from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.providers.faux import make_faux_provider
from agent.pi_agent_core import (
    Agent, AgentContext, AgentEvent, AgentLoopConfig, AgentTool, AgentToolResult,
    BeforeToolCallResult, default_convert_to_llm, run_agent_loop,
    ToolExecutionEndEvent, ToolExecutionUpdateEvent,
)
from agent.pi_ai.types import TextContent


class _SearchArgs(BaseModel):
    q: str


async def _search_exec(call_id, params: _SearchArgs, signal, on_update):
    if on_update:
        on_update(AgentToolResult(content=[TextContent(text="searching...")], details=None))
    return AgentToolResult(
        content=[TextContent(text=f"results for {params.q}")],
        details={"q": params.q},
    )


def _search_tool() -> AgentTool:
    return AgentTool(
        name="search", description="search the web", label="Search",
        parameters=_SearchArgs, execute=_search_exec,
    )


def _model(api: str) -> Model:
    return Model(id="m", name="m", api=api, provider="faux", baseUrl="", cost=ModelCost())


def _user_message(text: str) -> dict:
    return {"role": "user", "content": text, "timestamp": int(time.time() * 1000)}


def _config(model: Model) -> AgentLoopConfig:
    return AgentLoopConfig(model=model, convertToLlm=default_convert_to_llm)


@pytest.mark.asyncio
async def test_run_agent_loop_text_only_no_tools():
    register_provider("faux-loop-text", make_faux_provider(text="hi"))
    events: list[AgentEvent] = []

    async def emit(ev):
        events.append(ev)

    new_messages = await run_agent_loop(
        prompts=[_user_message("hello")],
        context=AgentContext(systemPrompt="sys"),
        config=_config(_model("faux-loop-text")),
        emit=emit,
    )
    types = [e.type for e in events]
    assert types[0] == "agent_start"
    assert types[-1] == "agent_end"
    assert "message_start" in types and "message_end" in types
    # one assistant message added, no tool results
    assistants = [m for m in new_messages if getattr(m, "role", None) == "assistant"]
    assert len(assistants) == 1
    assert assistants[0].content[0].text == "hi"


@pytest.mark.asyncio
async def test_run_agent_loop_single_tool_call():
    """Faux emits one tool_call -> we execute -> faux on next turn emits text."""
    # Faux provider emits tool_call. After we return tool result, we need to
    # set up a second faux that emits text only. We swap providers by registering
    # under different api strings and changing model.api between turns - simpler
    # to just register one provider that on its first call emits the tool, and
    # on subsequent calls emits the answer.
    call_count = {"n": 0}
    async def stateful_stream(model, ctx, opts=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            inner = make_faux_provider(
                text="",
                tool_calls=[{"name": "search", "arguments": {"q": "python"}}],
            )
        else:
            inner = make_faux_provider(text="done")
        async for ev in inner(model, ctx, opts):
            yield ev

    register_provider("faux-loop-tool", stateful_stream)
    events: list[AgentEvent] = []

    async def emit(ev):
        events.append(ev)

    new_messages = await run_agent_loop(
        prompts=[_user_message("search python")],
        context=AgentContext(systemPrompt="sys", tools=[_search_tool()]),
        config=_config(_model("faux-loop-tool")),
        emit=emit,
    )
    types = [e.type for e in events]
    assert "tool_execution_start" in types
    assert "tool_execution_end" in types
    # update event was emitted (because _search_exec called on_update)
    assert "tool_execution_update" in types
    # there should be 2 assistant messages (one with tool_call, one done) + 1 tool result
    assistants = [m for m in new_messages if getattr(m, "role", None) == "assistant"]
    tool_results = [m for m in new_messages if getattr(m, "role", None) == "toolResult"]
    assert len(assistants) == 2
    assert len(tool_results) == 1
    assert "results for python" in tool_results[0].content[0].text


@pytest.mark.asyncio
async def test_run_agent_loop_unknown_tool_immediate_error():
    """LLM calls a tool that isn't registered -> immediate error tool result."""
    call_count = {"n": 0}
    async def stateful_stream(model, ctx, opts=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            inner = make_faux_provider(
                text="",
                tool_calls=[{"name": "does_not_exist", "arguments": {}}],
            )
        else:
            inner = make_faux_provider(text="oh well")
        async for ev in inner(model, ctx, opts):
            yield ev

    register_provider("faux-loop-unknown", stateful_stream)
    events = []
    async def emit(ev):
        events.append(ev)

    new_messages = await run_agent_loop(
        prompts=[_user_message("call missing")],
        context=AgentContext(systemPrompt="sys", tools=[]),
        config=_config(_model("faux-loop-unknown")),
        emit=emit,
    )
    tool_results = [m for m in new_messages if getattr(m, "role", None) == "toolResult"]
    assert len(tool_results) == 1
    assert tool_results[0].isError is True
    assert "not found" in tool_results[0].content[0].text


@pytest.mark.asyncio
async def test_run_agent_loop_before_tool_call_blocks():
    """beforeToolCall returning block=True -> tool not executed, error result."""
    tool_executed = {"yes": False}
    async def watching_exec(call_id, params, signal, on_update):
        tool_executed["yes"] = True
        return AgentToolResult(content=[TextContent(text="ok")], details=None)

    tool = AgentTool(
        name="search", description="d", label="L",
        parameters=_SearchArgs, execute=watching_exec,
    )

    async def block_hook(ctx, signal):
        return BeforeToolCallResult(block=True, reason="nope")

    call_count = {"n": 0}
    async def stateful_stream(model, ctx, opts=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            inner = make_faux_provider(
                text="",
                tool_calls=[{"name": "search", "arguments": {"q": "x"}}],
            )
        else:
            inner = make_faux_provider(text="ok")
        async for ev in inner(model, ctx, opts):
            yield ev
    register_provider("faux-loop-block", stateful_stream)

    config = AgentLoopConfig(
        model=_model("faux-loop-block"),
        convertToLlm=default_convert_to_llm,
        beforeToolCall=block_hook,
    )
    events = []
    new_messages = await run_agent_loop(
        prompts=[_user_message("go")],
        context=AgentContext(tools=[tool]),
        config=config,
        emit=lambda ev: asyncio.sleep(0, result=events.append(ev)),
    )
    tool_results = [m for m in new_messages if getattr(m, "role", None) == "toolResult"]
    assert len(tool_results) == 1
    assert tool_results[0].isError is True
    assert "nope" in tool_results[0].content[0].text
    assert tool_executed["yes"] is False  # critical: tool NEVER ran
```

- [ ] **Step 3: test_agent_smoke — Agent class facade**

Create `agent/pi_agent_core/tests/test_agent_smoke.py`:
```python
"""Agent class smoke tests."""
from __future__ import annotations

import asyncio
import time

import pytest
from pydantic import BaseModel

from agent.pi_ai import Model, ModelCost
from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.providers.faux import make_faux_provider
from agent.pi_agent_core import Agent, AgentOptions, AgentTool, AgentToolResult
from agent.pi_ai.types import TextContent


def _model(api: str) -> Model:
    return Model(id="m", name="m", api=api, provider="faux", baseUrl="", cost=ModelCost())


def _user_message(text: str) -> dict:
    return {"role": "user", "content": text, "timestamp": int(time.time() * 1000)}


class _NoArgs(BaseModel):
    pass


async def _ok_exec(call_id, params, signal, on_update):
    return AgentToolResult(content=[TextContent(text="done")], details=None)


@pytest.mark.asyncio
async def test_agent_prompt_text_only():
    register_provider("faux-agent-text", make_faux_provider(text="hello"))
    a = Agent(AgentOptions(initial_state={
        "systemPrompt": "sys",
        "model": _model("faux-agent-text"),
    }))
    events = []
    a.subscribe(lambda ev, sig: events.append(ev) or asyncio.sleep(0))
    await a.prompt("hi")
    types = [e.type for e in events]
    assert "agent_start" in types
    assert "agent_end" in types
    assert any(getattr(m, "role", None) == "assistant" for m in a.state.messages)


@pytest.mark.asyncio
async def test_agent_subscribe_unsubscribe():
    register_provider("faux-agent-sub", make_faux_provider(text="hi"))
    a = Agent(AgentOptions(initial_state={
        "model": _model("faux-agent-sub"),
    }))
    seen = []
    unsubscribe = a.subscribe(lambda ev, sig: seen.append(ev.type) or asyncio.sleep(0))
    await a.prompt("first")
    first_count = len(seen)
    unsubscribe()
    await a.prompt("second")
    assert len(seen) == first_count  # no new events after unsubscribe


@pytest.mark.asyncio
async def test_agent_rejects_concurrent_prompt():
    register_provider("faux-agent-conc", make_faux_provider(text="hi"))
    a = Agent(AgentOptions(initial_state={"model": _model("faux-agent-conc")}))

    async def slow_listener(ev, sig):
        if ev.type == "agent_start":
            await asyncio.sleep(0.05)

    a.subscribe(slow_listener)
    task = asyncio.create_task(a.prompt("first"))
    await asyncio.sleep(0.01)  # let the first prompt enter active state
    with pytest.raises(RuntimeError, match="already processing"):
        await a.prompt("second")
    await task


@pytest.mark.asyncio
async def test_agent_steer_and_followup_queues():
    a = Agent(AgentOptions())
    assert a.has_queued_messages() is False
    a.steer(_user_message("steer1"))
    assert a.has_queued_messages() is True
    a.clear_steering_queue()
    assert a.has_queued_messages() is False
    a.follow_up(_user_message("fu1"))
    a.follow_up(_user_message("fu2"))
    assert a.has_queued_messages() is True
    a.clear_all_queues()
    assert a.has_queued_messages() is False


@pytest.mark.asyncio
async def test_agent_reset_clears_state():
    register_provider("faux-agent-reset", make_faux_provider(text="hi"))
    a = Agent(AgentOptions(initial_state={"model": _model("faux-agent-reset")}))
    await a.prompt("hello")
    assert len(a.state.messages) >= 2  # user + assistant
    a.reset()
    assert a.state.messages == []
    assert a.state.isStreaming is False
    assert a.state.pendingToolCalls == set()


@pytest.mark.asyncio
async def test_agent_set_tools_copy_on_assign():
    a = Agent()
    tools_list = [
        AgentTool(name="t", description="d", label="L",
                  parameters=_NoArgs, execute=_ok_exec),
    ]
    a.set_tools(tools_list)
    tools_list.clear()
    assert len(a.state.tools) == 1  # internal copy unchanged
```

- [ ] **Step 4: Run the pi_agent_core test suite**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -m pytest agent/pi_agent_core/tests/ -v
```

Expected: all ~14 tests passing. If any fail, fix before committing.

Common pitfalls watch out for:
- `_user_message()` returns a plain dict but is annotated `AgentMessage`. Pydantic validates it via the `Message` discriminator union — it'll work as long as `role` is set.
- Faux provider registration is global. If two tests register the same api name, the second wins. Use unique api names per test.
- `Agent.prompt(str)` builds a dict from `_normalize_prompt_input` — confirm pydantic accepts it (UserMessage discriminator picks `role="user"`).

- [ ] **Step 5: Verify pre-existing tests still pass (no regression)**

Run:
```bash
python -m pytest agent/pi_ai/tests/ agent/v6/tests/test_handoff_tools.py agent/v6/tests/test_orchestrator.py agent/v6/tests/test_tools_marketplace.py agent/v6/tests/test_tools_io.py agent/v6/tests/test_tools_components.py agent/v6/tests/test_tools_build.py agent/v6/tests/test_tools_runtime.py agent/v6/tests/test_agents.py agent/v6/tests/test_entry.py
```

Expected: 137 passed (18 pi_ai + 119 v7) — same as Phase 1 completion baseline.

- [ ] **Step 6: Commit**

```bash
cd /h/ai-hse-diploma-agent
git add Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/tests/
git commit -m "test(pi_agent_core): smoke tests - types, agent_loop, Agent class"
```

---

## Task 9: Acceptance verification

**Files:** None (verification only).

- [ ] **Step 1: Package import smoke**

```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
import agent.pi_agent_core as p
print('exports:', sorted(p.__all__)[:5], '... (' + str(len(p.__all__)) + ' total)')
print('Agent class:', p.Agent)
print('run_agent_loop:', p.run_agent_loop)
"
```

Expected: prints a snippet of exports, Agent class repr, run_agent_loop function.

- [ ] **Step 2: End-to-end faux loop**

```bash
python -c "
import asyncio, time
from agent.pi_ai import Model, ModelCost
from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.providers.faux import make_faux_provider
from agent.pi_agent_core import Agent, AgentOptions

register_provider('verify', make_faux_provider(text='ok'))
async def main():
    a = Agent(AgentOptions(initial_state={
        'model': Model(id='x', name='x', api='verify', provider='faux', baseUrl='', cost=ModelCost()),
    }))
    a.subscribe(lambda ev, sig: print('event:', ev.type) or asyncio.sleep(0))
    await a.prompt('hi')
    print('done, messages:', len(a.state.messages))
asyncio.run(main())
"
```

Expected: prints `event: agent_start`, `event: turn_start`, ..., `event: agent_end`, then `done, messages: 2`.

- [ ] **Step 3: Combined pi_ai + pi_agent_core + v7 regression**

```bash
python -m pytest agent/pi_ai/tests/ agent/pi_agent_core/tests/ agent/v6/tests/test_handoff_tools.py agent/v6/tests/test_orchestrator.py agent/v6/tests/test_tools_marketplace.py agent/v6/tests/test_tools_io.py agent/v6/tests/test_tools_components.py agent/v6/tests/test_tools_build.py agent/v6/tests/test_tools_runtime.py agent/v6/tests/test_agents.py agent/v6/tests/test_entry.py
```

Expected: ≥150 tests passing (18 pi_ai + ~14 pi_agent_core + 119 v7). No regressions in v7 acceptance list.

- [ ] **Step 4: Inspect commit graph**

```bash
cd /h/ai-hse-diploma-agent
git log --oneline -15
```

Expected: see ~7-8 fresh `feat(pi_agent_core):` / `test(pi_agent_core):` commits on top of the 9 Phase 1 commits.

- [ ] **Step 5: Verify no TODO/FIXME left**

Run:
```bash
grep -rE "TODO|FIXME|XXX|HACK" Eco.Toolchain/Eco.AI.Assembly1/agent/pi_agent_core/ || echo "clean"
```

Expected: `clean`.

---

## Phase 2 acceptance criteria

After Task 9 completes, all of the following must hold:

- [ ] `python -c "import agent.pi_agent_core"` works without error.
- [ ] `agent.pi_agent_core.Agent` is constructable with no args (uses defaults).
- [ ] `python -m pytest agent/pi_agent_core/tests/ -v` shows ≥14 tests passing.
- [ ] Phase 1 pi_ai tests (18) still pass.
- [ ] Pre-existing 119 v7 tests (acceptance list) still pass.
- [ ] `git log --oneline` shows ~7-8 atomic commits with `feat(pi_agent_core):` / `test(pi_agent_core):` prefix on top of Phase 1.
- [ ] No `# TODO`, `# FIXME` left in `pi_agent_core/`.
- [ ] End-to-end smoke: `Agent.prompt(str)` with faux provider emits the full agent_start→turn_start→message_start/end→agent_end event sequence and populates `agent.state.messages` correctly.
- [ ] `Agent.subscribe()` returns an unsubscribe callable; events stop after unsubscribe.
- [ ] `Agent` rejects concurrent `prompt()` calls with a clear RuntimeError.
- [ ] `Agent.set_tools()` and `Agent.set_messages()` perform copy-on-assign (mutating the input list doesn't leak into state).
- [ ] Tool execution: `beforeToolCall` blocking prevents `execute()` from being called.
- [ ] Tool execution: unknown tool name produces an error `ToolResultMessage`, doesn't crash the loop.

## Out of scope for Phase 2 (deferred)

- Integration with v7 (`orchestrator.py`, `agents/architect.py|coder.py|tester.py`, `backend/server.py`). **Phase 3.**
- Rewriting existing 119 v7 tests under new Agent API. **Phase 3.**
- Real OpenRouter call test (currently only faux + respx). **Phase 4 cutover.**
- UI smoke through Docker for thinking-block rendering. **Phase 4 cutover.**
- Web-UI browser proxy. **Permanently out of scope** per spec.
- MCP-server integration. **Permanently out of scope** per spec.

## Reference: spec sections covered by Phase 2

| Spec section | Tasks |
|---|---|
| Architecture overview — pi_agent_core file tree | Tasks 1, 5, 6, 7 |
| pi_agent_core types (AgentMessage, AgentTool, AgentEvent, AgentLoopConfig, ...) | Task 2 |
| pi_agent_core agent_loop.py (turn loop, hook orchestration, tool execution) | Tasks 3, 4 |
| pi_agent_core agent.py (Agent facade, state, queues, lifecycle) | Tasks 5, 6 |
| pi_agent_core proxy.py (stub) | Task 7 |
| Event protocol — Layer 2 AgentEvent (10 event types) | Task 2 (types), Task 4 (loop emissions), Task 6 (state reducer) |
| Bridge between layers — `message_update` wraps `AssistantMessageEvent` | Task 2 (`MessageUpdateEvent`), Task 4 (`_stream_assistant_response`) |
| Error handling — encoded in stream, never raises | Tasks 3-6 (each error path encoded) |
| Capability gating preserved | Out of scope for Phase 2 (Phase 3 will use the Agent API to construct tester with restricted tools) |
| Stop-tools preserved | Out of scope for Phase 2 (Phase 3 will define handoff tools as AgentTool with `message: str` schema) |
| Testing strategy — smoke tests per layer | Task 8 |
| Phase 2 of migration plan | This entire plan |
