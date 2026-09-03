"""pi_ai type backbone. Mirrors @mariozechner/pi-ai/src/types.ts.

Discriminated unions use pydantic's discriminator pattern. All BaseModels use
extra="allow" so provider responses with unknown fields parse cleanly.
"""
from __future__ import annotations

from typing import (
    Annotated, Any, AsyncIterator, Callable, Literal, Optional, Protocol,
    Union, runtime_checkable,
)

from pydantic import BaseModel, ConfigDict, Field


# ── API and provider identifiers (types.ts:5-43) ──────────────────────────────
KnownApi = Literal[
    "openai-completions",
    # other apis omitted - only openai-completions is ported in Phase 1
]
Api = Union[KnownApi, str]  # KnownApi or arbitrary string

KnownProvider = Literal[
    "openai",
    "openrouter",
    "xai", "groq", "cerebras",
    "zai",
    "minimax", "minimax-cn",
    "huggingface",
    "opencode", "opencode-go",
    "kimi-coding",
    "vercel-ai-gateway",
    # other providers omitted - only openai-compat ones used in Phase 1
]
Provider = Union[KnownProvider, str]

ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]
CacheRetention = Literal["none", "short", "long"]
Transport = Literal["sse", "websocket", "auto"]
StopReason = Literal["stop", "length", "toolUse", "error", "aborted"]


# ── Usage and cost (types.ts:46-53, 177-190) ──────────────────────────────────
class ThinkingBudgets(BaseModel):
    """Token budgets per thinking level (token-based providers)."""
    model_config = ConfigDict(extra="allow")
    minimal: Optional[int] = None
    low: Optional[int] = None
    medium: Optional[int] = None
    high: Optional[int] = None


class Cost(BaseModel):
    model_config = ConfigDict(extra="allow")
    input: float = 0.0
    output: float = 0.0
    cacheRead: float = 0.0
    cacheWrite: float = 0.0
    total: float = 0.0


class Usage(BaseModel):
    model_config = ConfigDict(extra="allow")
    input: int = 0
    output: int = 0
    cacheRead: int = 0
    cacheWrite: int = 0
    totalTokens: int = 0
    cost: Cost = Field(default_factory=Cost)


# ── Content blocks (types.ts:141-175) ─────────────────────────────────────────
class TextContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["text"] = "text"
    text: str
    textSignature: Optional[str] = None


class ThinkingContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["thinking"] = "thinking"
    thinking: str
    thinkingSignature: Optional[str] = None
    redacted: Optional[bool] = None


class ImageContent(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["image"] = "image"
    data: str  # base64
    mimeType: str  # e.g. "image/png"


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["toolCall"] = "toolCall"
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    thoughtSignature: Optional[str] = None


AssistantContent = Annotated[
    Union[TextContent, ThinkingContent, ToolCall],
    Field(discriminator="type"),
]
UserContent = Annotated[
    Union[TextContent, ImageContent],
    Field(discriminator="type"),
]
ToolResultContent = Annotated[
    Union[TextContent, ImageContent],
    Field(discriminator="type"),
]


# ── Messages (types.ts:194-223) ───────────────────────────────────────────────
class UserMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: Literal["user"] = "user"
    content: Union[str, list[UserContent]]
    timestamp: int  # Unix ms


class AssistantMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: Literal["assistant"] = "assistant"
    content: list[AssistantContent] = Field(default_factory=list)
    api: Api
    provider: Provider
    model: str
    responseId: Optional[str] = None
    usage: Usage = Field(default_factory=Usage)
    stopReason: StopReason = "stop"
    errorMessage: Optional[str] = None
    timestamp: int


class ToolResultMessage(BaseModel):
    model_config = ConfigDict(extra="allow")
    role: Literal["toolResult"] = "toolResult"
    toolCallId: str
    toolName: str
    content: list[ToolResultContent] = Field(default_factory=list)
    details: Any = None
    isError: bool = False
    timestamp: int


Message = Annotated[
    Union[UserMessage, AssistantMessage, ToolResultMessage],
    Field(discriminator="role"),
]


# ── Tool + Context (types.ts:225-237) ─────────────────────────────────────────
class Tool(BaseModel):
    """Provider-facing tool definition. Just name+description+JSON-schema args.
    AgentTool (with execute callback) lives in pi_agent_core, not here."""
    model_config = ConfigDict(extra="allow")
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema object


class Context(BaseModel):
    model_config = ConfigDict(extra="allow")
    systemPrompt: Optional[str] = None
    messages: list[Message] = Field(default_factory=list)
    tools: Optional[list[Tool]] = None


# ── AssistantMessageEvent discriminated union (types.ts:247-259) ──────────────
class _EvBase(BaseModel):
    model_config = ConfigDict(extra="allow")


class StartEvent(_EvBase):
    type: Literal["start"] = "start"
    partial: AssistantMessage


class TextStartEvent(_EvBase):
    type: Literal["text_start"] = "text_start"
    contentIndex: int
    partial: AssistantMessage


class TextDeltaEvent(_EvBase):
    type: Literal["text_delta"] = "text_delta"
    contentIndex: int
    delta: str
    partial: AssistantMessage


class TextEndEvent(_EvBase):
    type: Literal["text_end"] = "text_end"
    contentIndex: int
    content: str
    partial: AssistantMessage


class ThinkingStartEvent(_EvBase):
    type: Literal["thinking_start"] = "thinking_start"
    contentIndex: int
    partial: AssistantMessage


class ThinkingDeltaEvent(_EvBase):
    type: Literal["thinking_delta"] = "thinking_delta"
    contentIndex: int
    delta: str
    partial: AssistantMessage


class ThinkingEndEvent(_EvBase):
    type: Literal["thinking_end"] = "thinking_end"
    contentIndex: int
    content: str
    partial: AssistantMessage


class ToolCallStartEvent(_EvBase):
    type: Literal["toolcall_start"] = "toolcall_start"
    contentIndex: int
    partial: AssistantMessage


class ToolCallDeltaEvent(_EvBase):
    type: Literal["toolcall_delta"] = "toolcall_delta"
    contentIndex: int
    delta: str
    partial: AssistantMessage


class ToolCallEndEvent(_EvBase):
    type: Literal["toolcall_end"] = "toolcall_end"
    contentIndex: int
    toolCall: ToolCall
    partial: AssistantMessage


class DoneEvent(_EvBase):
    type: Literal["done"] = "done"
    reason: Literal["stop", "length", "toolUse"]
    message: AssistantMessage


class ErrorEvent(_EvBase):
    type: Literal["error"] = "error"
    reason: Literal["aborted", "error"]
    error: AssistantMessage


AssistantMessageEvent = Annotated[
    Union[
        StartEvent,
        TextStartEvent, TextDeltaEvent, TextEndEvent,
        ThinkingStartEvent, ThinkingDeltaEvent, ThinkingEndEvent,
        ToolCallStartEvent, ToolCallDeltaEvent, ToolCallEndEvent,
        DoneEvent, ErrorEvent,
    ],
    Field(discriminator="type"),
]


# ── StreamOptions (types.ts:65-125) ───────────────────────────────────────────
class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: int
    headers: dict[str, str] = Field(default_factory=dict)


class StreamOptions(BaseModel):
    """Base options for all providers (types.ts:65-116)."""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    signal: Optional[Any] = None  # asyncio.Event, kept Any to avoid import cycles
    apiKey: Optional[str] = None
    transport: Optional[Transport] = None
    cacheRetention: Optional[CacheRetention] = None
    sessionId: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    maxRetryDelayMs: int = 60000
    metadata: Optional[dict[str, Any]] = None
    onPayload: Optional[Callable[..., Any]] = None
    onResponse: Optional[Callable[..., Any]] = None


class SimpleStreamOptions(StreamOptions):
    """Unified options for streamSimple()/completeSimple() (types.ts:121-125)."""
    reasoning: Optional[ThinkingLevel] = None
    thinkingBudgets: Optional[ThinkingBudgets] = None


# ── OpenAI-completions compat + OpenRouter routing (types.ts:265-374) ─────────
class OpenRouterRouting(BaseModel):
    """OpenRouter provider routing (types.ts:307-374). All fields optional."""
    model_config = ConfigDict(extra="allow")
    allow_fallbacks: Optional[bool] = None
    require_parameters: Optional[bool] = None
    data_collection: Optional[Literal["allow", "deny"]] = None
    zdr: Optional[bool] = None
    enforce_distillable_text: Optional[bool] = None
    order: Optional[list[str]] = None
    only: Optional[list[str]] = None
    ignore: Optional[list[str]] = None
    quantizations: Optional[list[str]] = None
    sort: Optional[Any] = None  # string or {by, partition}
    max_price: Optional[dict[str, Any]] = None
    preferred_min_throughput: Optional[Any] = None
    preferred_max_latency: Optional[Any] = None


class OpenAICompletionsCompat(BaseModel):
    """Compat overrides for OpenAI-compat endpoints (types.ts:265-294)."""
    model_config = ConfigDict(extra="allow")
    supportsStore: Optional[bool] = None
    supportsDeveloperRole: Optional[bool] = None
    supportsReasoningEffort: Optional[bool] = None
    reasoningEffortMap: Optional[dict[str, str]] = None
    supportsUsageInStreaming: Optional[bool] = None
    maxTokensField: Optional[Literal["max_completion_tokens", "max_tokens"]] = None
    requiresToolResultName: Optional[bool] = None
    requiresAssistantAfterToolResult: Optional[bool] = None
    requiresThinkingAsText: Optional[bool] = None
    thinkingFormat: Optional[Literal["openai", "openrouter", "zai", "qwen", "qwen-chat-template"]] = None
    openRouterRouting: Optional[OpenRouterRouting] = None
    zaiToolStream: Optional[bool] = None
    supportsStrictMode: Optional[bool] = None


# ── Model (types.ts:389-412) ──────────────────────────────────────────────────
class ModelCost(BaseModel):
    model_config = ConfigDict(extra="allow")
    input: float = 0.0
    output: float = 0.0
    cacheRead: float = 0.0
    cacheWrite: float = 0.0


class Model(BaseModel):
    """Provider+model description. compat is constrained by api at construction.
    Phase 1: only api="openai-completions" supported, so compat is OpenAICompletionsCompat | None."""
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    api: Api
    provider: Provider
    baseUrl: str
    reasoning: bool = False
    input: list[Literal["text", "image"]] = Field(default_factory=lambda: ["text"])
    cost: ModelCost = Field(default_factory=ModelCost)
    contextWindow: int = 0
    maxTokens: int = 0
    headers: Optional[dict[str, str]] = None
    compat: Optional[OpenAICompletionsCompat] = None  # narrowed to openai-completions in Phase 1


# ── StreamFunction protocol (types.ts:127-139) ────────────────────────────────
@runtime_checkable
class StreamFunction(Protocol):
    """Async stream function contract. Implementations:
    - Must NOT raise for request/model/runtime errors. Encode them in the stream
      via ErrorEvent + AssistantMessage(stopReason="error"|"aborted").
    - Must return an AsyncIterator[AssistantMessageEvent].
    """
    def __call__(
        self,
        model: Model,
        context: Context,
        options: Optional[StreamOptions] = None,
    ) -> AsyncIterator[AssistantMessageEvent]: ...
