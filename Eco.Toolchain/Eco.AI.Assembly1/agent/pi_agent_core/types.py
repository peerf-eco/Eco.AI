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
    TextContent, ThinkingLevel, Tool, ToolCall, ToolResultMessage,
)


# ── Public type aliases (types.ts:35-38, 240-245) ─────────────────────────────
ToolExecutionMode = Literal["sequential", "parallel"]
AgentMessage = Message  # Phase 2: no custom messages (per spec out-of-scope)
AgentToolCall = ToolCall  # alias for clarity in the agent layer


# ── AgentToolResult + AgentTool (types.ts:280-307) ────────────────────────────
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


# ── AgentContext + hook contexts (types.ts:46-94, 309-317) ────────────────────
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


# ── StreamFn protocol (types.ts:16-26) ────────────────────────────────────────
@runtime_checkable
class StreamFn(Protocol):
    """Async stream function contract (types.ts:24-26).

    Matches the signature of agent.pi_ai.stream_simple. May either be a coroutine
    that returns an AsyncIterator, or the AsyncIterator-returning function directly.
    Implementations must NOT raise - failures must be encoded as ErrorEvent
    in the stream.
    """
    def __call__(
        self,
        model: Model,
        context: Any,  # pi_ai.Context
        options: Optional[SimpleStreamOptions] = None,
    ) -> Any: ...  # AsyncIterator[pi_ai.AssistantMessageEvent]


# ── AgentLoopConfig (types.ts:96-214) ─────────────────────────────────────────
# Hook callable type aliases for readability
BeforeToolCallHook = Callable[
    ["BeforeToolCallContext", Optional[asyncio.Event]],
    Awaitable[Optional["BeforeToolCallResult"]],
]
AfterToolCallHook = Callable[
    ["AfterToolCallContext", Optional[asyncio.Event]],
    Awaitable[Optional["AfterToolCallResult"]],
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


# ── AgentEvent discriminated union (types.ts:326-341) ─────────────────────────
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


# ── AgentState (types.ts:248-278) ─────────────────────────────────────────────
class AgentState(BaseModel):
    """Public agent state (types.ts:253-278).

    Unlike the TS version (accessor properties for tools/messages), Python
    pydantic doesn't natively support get/set with copy-on-assign. The Agent
    class assigns these as plain attributes after copying - the contract is
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
