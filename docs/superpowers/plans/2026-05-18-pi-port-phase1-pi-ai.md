# pi-mono → Python port — Phase 1: pi_ai layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port `@mariozechner/pi-ai` (TypeScript, ~2700 LOC) to Python as `agent/pi_ai/` package, supporting only `openai-completions` provider for OpenRouter+Kimi/GLM/MiMo/MiniMax/Nemotron. Async-first. Code-first with smoke-tests per submodule.

**Architecture:** Two-layer split — `pi_ai` (provider abstraction, this plan) + `pi_agent_core` (agent loop, separate plan). Direct `httpx.AsyncClient` (NOT openai Python SDK — to avoid Pydantic wrapper that drops `delta.reasoning` like langchain_openai 1.2.1 does). All hooks/streams async. Pydantic v2 for types with `extra="allow"`.

**Tech Stack:** Python 3.11 (project already on it), `pydantic>=2.12`, `httpx`, `pytest`, `pytest-asyncio`, `respx` (for tests). Optional: `partial-json-parser` pip pkg (fallback: custom implementation).

**Spec:** `docs/superpowers/specs/2026-05-18-pi-port-design.md` (commit `1481b5f`)

**Phase 1 scope:** Layer 1 only (pi_ai). Phase 2-4 (pi_agent_core, integration, cutover) in separate plans after Phase 1 ships.

**Convention notes:**
- Working dir: `H:\ai-hse-diploma-agent\Eco.Toolchain\Eco.AI.Assembly1\`
- All commands assume `cd Eco.Toolchain/Eco.AI.Assembly1` is done (orchestrator/server.py work from this CWD)
- Branch: `feat/v6-five-node-pipeline` (no new branch needed — same ongoing v7 work)
- TS source paths use `F:/pi-harness/pi-mono/packages/ai/src/` prefix
- Code-first: smoke-tests written **after** implementation in each task, not before

---

## Task 1: Create pi_ai package skeleton

**Files:**
- Create: `agent/pi_ai/__init__.py`
- Create: `agent/pi_ai/providers/__init__.py`
- Create: `agent/pi_ai/utils/__init__.py`
- Create: `agent/pi_ai/tests/__init__.py`
- Create: `agent/pi_ai/tests/conftest.py`

- [ ] **Step 1: Create directories and empty __init__.py files**

```bash
cd Eco.Toolchain/Eco.AI.Assembly1
mkdir -p agent/pi_ai/providers agent/pi_ai/utils agent/pi_ai/tests
```

Create empty `agent/pi_ai/__init__.py`:
```python
"""pi_ai — Python port of @mariozechner/pi-ai (openai-completions only).

This package provides a unified async streaming abstraction over OpenAI-compatible
LLM providers (OpenRouter, Kimi, GLM, MiMo, MiniMax, Nemotron, etc.) with correct
reasoning content passthrough that langchain_openai 1.2.1 drops silently.

See docs/superpowers/specs/2026-05-18-pi-port-design.md for design.
"""
```

Create empty `agent/pi_ai/providers/__init__.py`:
```python
"""Provider implementations. Each provider exposes an async function matching
the StreamFunction protocol from `pi_ai.types`."""
```

Create empty `agent/pi_ai/utils/__init__.py`:
```python
"""Internal utilities: SSE parsing, partial-JSON accumulation, schema validation,
hashing, context-window helpers."""
```

Create empty `agent/pi_ai/tests/__init__.py` (empty file).

- [ ] **Step 2: Create pytest fixtures file**

Create `agent/pi_ai/tests/conftest.py`:
```python
"""Shared fixtures for pi_ai tests."""
import pytest


@pytest.fixture
def httpx_mock_url():
    """Standard fake URL for respx-mocked OpenAI-compat endpoints."""
    return "https://openrouter.ai/api/v1/chat/completions"
```

- [ ] **Step 3: Add pytest-asyncio + respx to dev deps (if absent)**

Check `requirements.txt` or `requirements-dev.txt`:
```bash
grep -E "respx|pytest-asyncio|partial-json" requirements*.txt 2>/dev/null
```

If missing, append to `requirements-dev.txt` (or whichever the project uses for dev/test deps — verify by `cat requirements*.txt`):
```
respx>=0.21
pytest-asyncio>=0.23
partial-json-parser>=0.2
```

Then install:
```bash
pip install respx pytest-asyncio partial-json-parser
```

- [ ] **Step 4: Verify imports work**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "import agent.pi_ai; import agent.pi_ai.providers; import agent.pi_ai.utils; print('ok')"
```

Expected: `ok` on stdout, no errors.

- [ ] **Step 5: Commit**

```bash
git add agent/pi_ai/ requirements-dev.txt
git commit -m "feat(pi_ai): scaffold pi_ai package skeleton"
```

---

## Task 2: pi_ai/types.py — central type definitions

**Files:**
- Create: `agent/pi_ai/types.py`
- Reference: `F:/pi-harness/pi-mono/packages/ai/src/types.ts` (412 LOC TS)

**Background:** This file is the type backbone. Every other pi_ai module imports from here. Port discriminated unions via `pydantic.Field(discriminator="type")`. Use `model_config = ConfigDict(extra="allow")` everywhere — provider responses contain unknown fields we must not reject.

- [ ] **Step 1: Port enums and base aliases (types.ts:5-58)**

Create `agent/pi_ai/types.py` with imports + enums section:
```python
"""pi_ai type backbone. Mirrors @mariozechner/pi-ai/src/types.ts.

Discriminated unions use pydantic's discriminator pattern. All BaseModels use
extra="allow" so provider responses with unknown fields parse cleanly.
"""
from __future__ import annotations

from typing import Annotated, Any, Callable, Literal, Optional, Protocol, Union
from typing import runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


# ── API and provider identifiers (types.ts:5-43) ──────────────────────────────
KnownApi = Literal[
    "openai-completions",
    # other apis omitted — only openai-completions is ported in Phase 1
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
    # other providers omitted — only openai-compat ones used in Phase 1
]
Provider = Union[KnownProvider, str]

ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]
CacheRetention = Literal["none", "short", "long"]
Transport = Literal["sse", "websocket", "auto"]
StopReason = Literal["stop", "length", "toolUse", "error", "aborted"]
```

- [ ] **Step 2: Port Usage and ThinkingBudgets (types.ts:46-53, 177-190)**

Append to `agent/pi_ai/types.py`:
```python
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
```

- [ ] **Step 3: Port content types (types.ts:141-175)**

Append:
```python
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
```

- [ ] **Step 4: Port Message types (types.ts:194-223)**

Append:
```python
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
```

- [ ] **Step 5: Port Tool + Context (types.ts:225-237)**

Append:
```python
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
```

- [ ] **Step 6: Port AssistantMessageEvent discriminated union (types.ts:247-259)**

Append:
```python
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
```

- [ ] **Step 7: Port StreamOptions + SimpleStreamOptions (types.ts:65-125)**

Append:
```python
class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: int
    headers: dict[str, str] = Field(default_factory=dict)


class StreamOptions(BaseModel):
    """Base options for all providers (types.ts:65-116)."""
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    signal: Optional[Any] = None  # asyncio.Event, but kept Any to avoid import cycles in tests
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
```

- [ ] **Step 8: Port OpenAICompletionsCompat + OpenRouterRouting (types.ts:265-374)**

Append:
```python
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
```

- [ ] **Step 9: Port Model (types.ts:389-412)**

Append:
```python
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
```

- [ ] **Step 10: Port StreamFunction protocol (types.ts:127-139)**

Append:
```python
@runtime_checkable
class StreamFunction(Protocol):
    """Async stream function contract. Implementations:
    - Must NOT raise for request/model/runtime errors. Encode them in the stream
      via ErrorEvent + AssistantMessage(stopReason="error"|"aborted").
    - Must return an AsyncIterator[AssistantMessageEvent].
    """
    def __call__(
        self,
        model: "Model",
        context: "Context",
        options: Optional[StreamOptions] = None,
    ) -> "AsyncIterator[AssistantMessageEvent]": ...


# Re-export AsyncIterator for downstream importers
from typing import AsyncIterator  # noqa: E402  (intentional after-Protocol import)
```

- [ ] **Step 11: Verify file imports cleanly**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "from agent.pi_ai import types; print(sorted(n for n in dir(types) if not n.startswith('_'))[:20])"
```

Expected: list of exported names starting with `Annotated, Api, ...` printed cleanly.

- [ ] **Step 12: Commit**

```bash
git add agent/pi_ai/types.py
git commit -m "feat(pi_ai): port types.ts — Message, AssistantMessageEvent, Model, Tool"
```

---

## Task 3: pi_ai/utils/ — SSE parser, partial-JSON, validation, hash, overflow

**Files:**
- Create: `agent/pi_ai/utils/event_stream.py`
- Create: `agent/pi_ai/utils/json_parse.py`
- Create: `agent/pi_ai/utils/validation.py`
- Create: `agent/pi_ai/utils/hash.py`
- Create: `agent/pi_ai/utils/overflow.py`
- Reference: `F:/pi-harness/pi-mono/packages/ai/src/utils/`

- [ ] **Step 1: event_stream.py — async SSE parser for httpx responses**

Create `agent/pi_ai/utils/event_stream.py`:
```python
"""Server-Sent Events (SSE) parser for httpx async streams.

OpenAI-compat providers send chunks as `data: <json>\\n\\n` lines. We split
on blank lines, parse each `data:` payload as JSON, and yield dicts. The
special sentinel `data: [DONE]` terminates the stream (we yield nothing for it).
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx


async def parse_sse(response: httpx.Response) -> AsyncIterator[dict]:
    """Yield parsed JSON dicts from an httpx streaming response.

    Errors:
    - Lines that don't start with `data: ` are skipped (typically SSE comments).
    - JSON decode errors are skipped silently (some providers send keep-alive
      pings as non-JSON; logging would be too noisy).
    """
    buffer = b""
    async for chunk in response.aiter_bytes():
        buffer += chunk
        while b"\n\n" in buffer:
            block, buffer = buffer.split(b"\n\n", 1)
            for line in block.split(b"\n"):
                line = line.strip()
                if not line.startswith(b"data:"):
                    continue
                payload = line[5:].strip()  # strip "data:" prefix
                if payload == b"[DONE]":
                    return
                if not payload:
                    continue
                try:
                    yield json.loads(payload)
                except json.JSONDecodeError:
                    continue
```

- [ ] **Step 2: json_parse.py — partial-JSON accumulator**

Create `agent/pi_ai/utils/json_parse.py`:
```python
"""Partial-JSON accumulator for streaming tool_call.arguments deltas.

Tool-call argument strings are streamed character-by-character in OpenAI-compat
delta chunks. We accumulate the raw string and attempt to parse it at each step.
The result is "best-effort partial dict" — if the JSON is incomplete, we use
`partial_json_parser` to coerce. On final completion we use stdlib json.loads
for strict validation.

This replaces TypeScript's `partial-json` package (utils/json-parse.ts).
"""
from __future__ import annotations

import json
from typing import Any

try:
    from partial_json_parser import loads as _partial_loads
    _HAS_PARTIAL = True
except ImportError:
    _HAS_PARTIAL = False


def parse_partial(raw: str) -> Any:
    """Parse a (possibly incomplete) JSON string. Returns a dict if at all
    parseable, else {}."""
    if not raw or not raw.strip():
        return {}
    # Try strict parse first — fastest when the chunk is complete
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Partial path
    if _HAS_PARTIAL:
        try:
            return _partial_loads(raw)
        except Exception:
            pass
    # Fallback: nothing parseable yet
    return {}


def parse_strict(raw: str) -> Any:
    """Parse a complete JSON string, raising ValueError on any failure."""
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e
```

- [ ] **Step 3: validation.py — pydantic wrapper for tool-args validation**

Create `agent/pi_ai/utils/validation.py`:
```python
"""Tool-argument validation against pydantic schemas.

In pi_agent_core, AgentTool defines parameters as a pydantic BaseModel subclass.
Before invoking execute(), we validate raw dict args against that schema. This
file provides a thin helper that returns (validated_obj, error_str_or_None).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ValidationError


def validate_args(
    schema: type[BaseModel],
    raw_args: dict,
) -> tuple[Optional[BaseModel], Optional[str]]:
    """Validate raw dict against pydantic schema.

    Returns:
      (instance, None) on success
      (None, error_message) on failure
    """
    try:
        return schema.model_validate(raw_args), None
    except ValidationError as e:
        # Compact error message — provider sees this, must be model-friendly
        msgs = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            msgs.append(f"  - {loc}: {err['msg']}")
        return None, "Schema validation failed:\n" + "\n".join(msgs)
```

- [ ] **Step 4: hash.py — sha256 helper for cache keys**

Create `agent/pi_ai/utils/hash.py`:
```python
"""Stable hashing for cache hints and session IDs."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_hex(data: Any) -> str:
    """Hash any JSON-serializable value as hex sha256."""
    if isinstance(data, (str, bytes)):
        raw = data.encode("utf-8") if isinstance(data, str) else data
    else:
        raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
```

- [ ] **Step 5: overflow.py — context-window arithmetic helpers**

Create `agent/pi_ai/utils/overflow.py`:
```python
"""Helpers for detecting/anticipating context-window overflow.

Trivial port — we only ship the rough char→token estimator. Real token counting
is provider-specific and lives in pi_agent_core's transformContext hook.
"""
from __future__ import annotations


def estimate_tokens_from_chars(num_chars: int) -> int:
    """Rough heuristic: ~4 chars per token for English-heavy content.
    Conservative for code (which has more tokens per char) but adequate
    for first-pass overflow detection. Real tokenization belongs in
    pi_agent_core/transformContext hook with tiktoken."""
    return num_chars // 4


def would_overflow(
    estimated_input_tokens: int,
    *,
    context_window: int,
    safety_margin: int = 1024,
) -> bool:
    """Returns True if estimated input is unsafely close to context_window."""
    return estimated_input_tokens + safety_margin >= context_window
```

- [ ] **Step 6: Verify all utils import cleanly**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "from agent.pi_ai.utils import event_stream, json_parse, validation, hash as h, overflow; print('ok')"
```

Expected: `ok`.

- [ ] **Step 7: Commit**

```bash
git add agent/pi_ai/utils/
git commit -m "feat(pi_ai): port utils — SSE parser, partial-JSON, validation, hash"
```

---

## Task 4: pi_ai/env_api_keys.py + models.py + api_registry.py

**Files:**
- Create: `agent/pi_ai/env_api_keys.py`
- Create: `agent/pi_ai/models.py`
- Create: `agent/pi_ai/api_registry.py`
- Reference: `F:/pi-harness/pi-mono/packages/ai/src/{env-api-keys,models,api-registry}.ts`

- [ ] **Step 1: env_api_keys.py — resolve API key from env per provider**

Create `agent/pi_ai/env_api_keys.py`:
```python
"""Resolve API keys from environment variables per provider.

Mirrors @mariozechner/pi-ai/src/env-api-keys.ts but trimmed to providers we
actually support (Phase 1: openai-compat family only).
"""
from __future__ import annotations

import os
from typing import Optional

from agent.pi_ai.types import Provider


_KEY_MAP: dict[str, list[str]] = {
    "openai":       ["OPENAI_API_KEY"],
    "openrouter":   ["OPENROUTER_API_KEY", "OPENAI_API_KEY"],
    "xai":          ["XAI_API_KEY"],
    "groq":         ["GROQ_API_KEY"],
    "cerebras":     ["CEREBRAS_API_KEY"],
    "zai":          ["ZAI_API_KEY", "Z_AI_API_KEY"],
    "minimax":      ["MINIMAX_API_KEY"],
    "minimax-cn":   ["MINIMAX_CN_API_KEY", "MINIMAX_API_KEY"],
    "huggingface":  ["HUGGINGFACE_API_KEY", "HF_TOKEN"],
    "vercel-ai-gateway": ["VERCEL_AI_GATEWAY_API_KEY"],
    "kimi-coding":  ["KIMI_CODING_API_KEY", "MOONSHOT_API_KEY"],
}


def get_api_key(provider: Provider) -> Optional[str]:
    """Return the first non-empty env-var value from the provider's key chain,
    or None if none are set."""
    for var in _KEY_MAP.get(provider, []):
        val = os.environ.get(var)
        if val:
            return val
    return None
```

- [ ] **Step 2: models.py — get_model() factory with known model definitions**

Create `agent/pi_ai/models.py`:
```python
"""Model factory and known-model registry.

This is a slim Phase 1 implementation — only the handful of OpenRouter models
we need are pre-registered. The full pi-mono models.generated.ts (~20k LOC)
is auto-generated from models.dev API; we'll fetch it dynamically in a future
phase if needed.

Custom models can be constructed by callers directly without going through
get_model() — Model is a public pydantic class.
"""
from __future__ import annotations

from typing import Optional

from agent.pi_ai.types import (
    Model, ModelCost, OpenAICompletionsCompat, Provider,
)


# Known model registry. Pre-populated for the models from our MEMORY.md
# portability constraint (Kimi K2.6, GLM 5.1, etc).
_KNOWN: dict[tuple[str, str], Model] = {}


def _register(model: Model) -> None:
    _KNOWN[(model.provider, model.id)] = model


def _openrouter_base() -> str:
    return "https://openrouter.ai/api/v1"


# Pre-register the models we know we need.
_register(Model(
    id="moonshotai/kimi-k2-thinking",
    name="Kimi K2.6 Thinking",
    api="openai-completions",
    provider="openrouter",
    baseUrl=_openrouter_base(),
    reasoning=True,
    contextWindow=256_000,
    maxTokens=32_000,
    cost=ModelCost(input=0.6, output=2.5),
    compat=OpenAICompletionsCompat(
        thinkingFormat="openrouter",
        supportsReasoningEffort=True,
        reasoningEffortMap={"minimal": "low", "low": "low", "medium": "medium", "high": "high", "xhigh": "high"},
    ),
))

_register(Model(
    id="zai-org/glm-4.5",
    name="GLM 4.5",
    api="openai-completions",
    provider="openrouter",
    baseUrl=_openrouter_base(),
    reasoning=True,
    contextWindow=128_000,
    maxTokens=32_000,
    cost=ModelCost(input=0.5, output=2.0),
    compat=OpenAICompletionsCompat(thinkingFormat="openrouter"),
))

# Add more as needed; constructor is public so users don't need to register.


def get_model(provider: Provider, id: str) -> Model:
    """Return the registered model, or raise KeyError. Callers that need a
    custom model should instantiate Model() directly."""
    key = (provider, id)
    if key not in _KNOWN:
        raise KeyError(
            f"Unknown model {provider!r}/{id!r}. "
            f"Register it via models._register() or construct Model() directly."
        )
    return _KNOWN[key]


def register_model(model: Model) -> None:
    """Public hook to add a model to the registry."""
    _register(model)


def known_models() -> list[Model]:
    """Snapshot of all registered models."""
    return list(_KNOWN.values())
```

- [ ] **Step 3: api_registry.py — map api: str → StreamFunction**

Create `agent/pi_ai/api_registry.py`:
```python
"""Registry mapping `api` strings (e.g. "openai-completions") to their
StreamFunction implementations. Mirrors pi-mono's register-builtins.ts.

Phase 1 only registers openai-completions. Adding another provider = one
register_provider() call elsewhere.
"""
from __future__ import annotations

from typing import Optional

from agent.pi_ai.types import Api, StreamFunction


_REGISTRY: dict[str, StreamFunction] = {}


def register_provider(api: Api, stream_fn: StreamFunction) -> None:
    """Register a provider implementation under an api identifier."""
    _REGISTRY[api] = stream_fn


def get_provider(api: Api) -> Optional[StreamFunction]:
    """Look up the StreamFunction for an api. Returns None if not registered."""
    return _REGISTRY.get(api)


def known_apis() -> list[str]:
    return list(_REGISTRY.keys())
```

- [ ] **Step 4: Verify imports work**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
from agent.pi_ai.env_api_keys import get_api_key
from agent.pi_ai.models import get_model, known_models
from agent.pi_ai.api_registry import register_provider, get_provider, known_apis
print('known_models:', [m.id for m in known_models()])
print('known_apis (before registration):', known_apis())
"
```

Expected: lists print without error. `known_apis` is empty until Task 6 registers openai-completions.

- [ ] **Step 5: Commit**

```bash
git add agent/pi_ai/env_api_keys.py agent/pi_ai/models.py agent/pi_ai/api_registry.py
git commit -m "feat(pi_ai): env API keys, model registry, provider registry"
```

---

## Task 5: pi_ai/providers/transform_messages.py + simple_options.py

**Files:**
- Create: `agent/pi_ai/providers/transform_messages.py`
- Create: `agent/pi_ai/providers/simple_options.py`
- Reference: `F:/pi-harness/pi-mono/packages/ai/src/providers/{transform-messages,simple-options}.ts`

**Background:** These two files are pure-function utilities that prepare the request body sent to OpenAI-compat endpoints. They're invoked by `openai_completions.py` in Task 6 — keeping them separate makes Task 6 manageable.

- [ ] **Step 1: transform_messages.py — pi_ai Messages → OpenAI message array**

Create `agent/pi_ai/providers/transform_messages.py`:
```python
"""Transform pi_ai Message[] → OpenAI chat-completions message array.

The provider input has a richer shape than OpenAI's API (separate content blocks
for text/thinking/toolCall, structured ToolResult). We flatten + map per OpenAI
spec, with provider-specific quirks driven by Model.compat.

Mirrors providers/transform-messages.ts (160 LOC TS).
"""
from __future__ import annotations

from typing import Any

from agent.pi_ai.types import (
    AssistantMessage, ImageContent, Message, Model, OpenAICompletionsCompat,
    TextContent, ThinkingContent, ToolCall, ToolResultMessage, UserMessage,
)


def _compat(model: Model) -> OpenAICompletionsCompat:
    return model.compat or OpenAICompletionsCompat()


def transform_user_message(msg: UserMessage) -> dict:
    """User message → {role: user, content: ... }."""
    if isinstance(msg.content, str):
        return {"role": "user", "content": msg.content}
    parts: list[dict] = []
    for c in msg.content:
        if isinstance(c, TextContent):
            parts.append({"type": "text", "text": c.text})
        elif isinstance(c, ImageContent):
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{c.mimeType};base64,{c.data}"},
            })
    return {"role": "user", "content": parts}


def transform_assistant_message(msg: AssistantMessage, model: Model) -> dict:
    """Assistant message → {role: assistant, content?, tool_calls?}.

    Thinking blocks: if compat.requiresThinkingAsText → merge into content
    as <thinking>...</thinking> text. Otherwise dropped (most providers don't
    accept them on subsequent turns, only on the originating response)."""
    compat = _compat(model)
    text_parts: list[str] = []
    tool_calls: list[dict] = []

    for c in msg.content:
        if isinstance(c, TextContent):
            text_parts.append(c.text)
        elif isinstance(c, ThinkingContent):
            if compat.requiresThinkingAsText:
                text_parts.append(f"<thinking>{c.thinking}</thinking>")
            # else: drop — provider can't accept thinking blocks as input
        elif isinstance(c, ToolCall):
            import json as _json
            tool_calls.append({
                "id": c.id,
                "type": "function",
                "function": {
                    "name": c.name,
                    "arguments": _json.dumps(c.arguments, separators=(",", ":")),
                },
            })

    out: dict = {"role": "assistant"}
    if text_parts:
        out["content"] = "\n".join(text_parts) or None
    else:
        out["content"] = None
    if tool_calls:
        out["tool_calls"] = tool_calls
    return out


def transform_tool_result_message(msg: ToolResultMessage, model: Model) -> dict:
    """ToolResult message → {role: tool, tool_call_id, content, [name]}."""
    compat = _compat(model)
    text_parts = [c.text for c in msg.content if isinstance(c, TextContent)]
    out: dict = {
        "role": "tool",
        "tool_call_id": msg.toolCallId,
        "content": "\n".join(text_parts),
    }
    if compat.requiresToolResultName:
        out["name"] = msg.toolName
    return out


def transform_messages(messages: list[Message], model: Model) -> list[dict]:
    """Flatten pi_ai Message[] into OpenAI message array.

    Handles compat.requiresAssistantAfterToolResult: if a user message follows
    tool results without an assistant message in between, inject a no-op
    assistant message."""
    compat = _compat(model)
    out: list[dict] = []

    for i, msg in enumerate(messages):
        if isinstance(msg, UserMessage):
            # Compat: ensure assistant between tool-result and user (Mistral quirk)
            if (
                compat.requiresAssistantAfterToolResult
                and i > 0
                and isinstance(messages[i - 1], ToolResultMessage)
            ):
                out.append({"role": "assistant", "content": "Continuing."})
            out.append(transform_user_message(msg))
        elif isinstance(msg, AssistantMessage):
            out.append(transform_assistant_message(msg, model))
        elif isinstance(msg, ToolResultMessage):
            out.append(transform_tool_result_message(msg, model))

    return out
```

- [ ] **Step 2: simple_options.py — map ThinkingLevel → reasoning request body**

Create `agent/pi_ai/providers/simple_options.py`:
```python
"""Translate SimpleStreamOptions.reasoning (ThinkingLevel) into provider-specific
request body fields. Mirrors providers/simple-options.ts (47 LOC TS).

Five thinkingFormat dialects:
- openai: reasoning_effort: "low"|"medium"|"high"
- openrouter: reasoning: {effort: "low"|"medium"|"high"} OR reasoning: {max_tokens: N}
- zai: enable_thinking: bool (top-level)
- qwen: enable_thinking: bool (top-level)
- qwen-chat-template: chat_template_kwargs.enable_thinking: bool
"""
from __future__ import annotations

from typing import Optional

from agent.pi_ai.types import (
    Model, OpenAICompletionsCompat, SimpleStreamOptions, ThinkingLevel,
)


def _compat(model: Model) -> OpenAICompletionsCompat:
    return model.compat or OpenAICompletionsCompat()


def _map_effort(model: Model, level: ThinkingLevel) -> str:
    """Apply compat.reasoningEffortMap override if set, else identity."""
    compat = _compat(model)
    if compat.reasoningEffortMap and level in compat.reasoningEffortMap:
        return compat.reasoningEffortMap[level]
    return level if level in ("low", "medium", "high") else "medium"


def apply_reasoning(body: dict, model: Model, opts: Optional[SimpleStreamOptions]) -> dict:
    """Mutate `body` in place: insert provider-correct thinking request based
    on model.compat.thinkingFormat. Returns body for chaining."""
    if opts is None or opts.reasoning is None or opts.reasoning == "minimal":
        return body

    compat = _compat(model)
    fmt = compat.thinkingFormat or "openai"
    level = opts.reasoning

    if fmt == "openai":
        if compat.supportsReasoningEffort is not False:
            body["reasoning_effort"] = _map_effort(model, level)
    elif fmt == "openrouter":
        body["reasoning"] = {"effort": _map_effort(model, level)}
        # Caller can override with max_tokens via opts.thinkingBudgets if needed
        if opts.thinkingBudgets:
            budget = getattr(opts.thinkingBudgets, level, None)
            if budget:
                body["reasoning"] = {"max_tokens": budget}
    elif fmt == "zai":
        body["enable_thinking"] = True
    elif fmt == "qwen":
        body["enable_thinking"] = True
    elif fmt == "qwen-chat-template":
        body.setdefault("chat_template_kwargs", {})["enable_thinking"] = True

    return body
```

- [ ] **Step 3: Verify imports**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "from agent.pi_ai.providers.transform_messages import transform_messages; from agent.pi_ai.providers.simple_options import apply_reasoning; print('ok')"
```

Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add agent/pi_ai/providers/transform_messages.py agent/pi_ai/providers/simple_options.py
git commit -m "feat(pi_ai): port transform_messages + simple_options helpers"
```

---

## Task 6: pi_ai/providers/openai_completions.py — THE CORE FILE

**Files:**
- Create: `agent/pi_ai/providers/openai_completions.py`
- Reference: `F:/pi-harness/pi-mono/packages/ai/src/providers/openai-completions.ts` (894 LOC TS)
- Reference (streaming pattern): `F:/pi-harness/hermes-agent/run_agent.py:5599-5800`

**Background:** This is the heart of Phase 1. Single async function that opens an httpx SSE stream, parses chunks, accumulates them into the partial `AssistantMessage`, and yields `AssistantMessageEvent` per the protocol. **Reasoning passthrough** (★) is the critical feature here — it's literally `getattr(delta, "reasoning", None) or getattr(delta, "reasoning_content", None)`.

This task has many steps because the file is large. Break work into logical sections that match the TS source layout.

- [ ] **Step 1: File skeleton + imports + body builder**

Create `agent/pi_ai/providers/openai_completions.py` with the structural skeleton:
```python
"""openai-completions provider — async streaming via direct httpx.

Mirrors @mariozechner/pi-ai/src/providers/openai-completions.ts (894 LOC TS).

Why httpx directly instead of the openai SDK:
  The openai Python SDK wraps response chunks in its own Pydantic models.
  Those models silently drop unknown fields like `delta.reasoning` — exactly
  the same bug as langchain_openai 1.2.1. Going direct lets us read the raw
  dict before any wrapper touches it.

Critical line: see _extract_reasoning() — the one feature this whole port exists for.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator, Optional

import httpx

from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.env_api_keys import get_api_key
from agent.pi_ai.providers.simple_options import apply_reasoning
from agent.pi_ai.providers.transform_messages import transform_messages
from agent.pi_ai.types import (
    AssistantMessage, AssistantMessageEvent, Context,
    DoneEvent, ErrorEvent, Model, OpenAICompletionsCompat, SimpleStreamOptions,
    StartEvent, StreamOptions, TextContent, TextDeltaEvent, TextEndEvent,
    TextStartEvent, ThinkingContent, ThinkingDeltaEvent, ThinkingEndEvent,
    ThinkingStartEvent, Tool, ToolCall, ToolCallDeltaEvent, ToolCallEndEvent,
    ToolCallStartEvent, Usage,
)
from agent.pi_ai.utils.event_stream import parse_sse
from agent.pi_ai.utils.json_parse import parse_partial, parse_strict
```

- [ ] **Step 2: Request body builder**

Append to `agent/pi_ai/providers/openai_completions.py`:
```python
def _build_request_body(
    model: Model,
    context: Context,
    opts: Optional[StreamOptions],
) -> dict:
    """Assemble the OpenAI chat-completions request body."""
    body: dict[str, Any] = {
        "model": model.id,
        "messages": _prepend_system(transform_messages(context.messages, model), context.systemPrompt),
        "stream": True,
    }
    compat = model.compat or OpenAICompletionsCompat()

    # max-tokens field name varies by provider
    if isinstance(opts, StreamOptions) and opts.maxTokens:
        field = compat.maxTokensField or "max_tokens"
        body[field] = opts.maxTokens
    elif model.maxTokens:
        field = compat.maxTokensField or "max_tokens"
        body[field] = model.maxTokens

    if opts and opts.temperature is not None:
        body["temperature"] = opts.temperature

    # Tools
    if context.tools:
        body["tools"] = _format_tools(context.tools, compat)

    # Usage in streaming (most providers support it; some don't)
    if compat.supportsUsageInStreaming is not False:
        body["stream_options"] = {"include_usage": True}

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
            entry["function"]["strict"] = False  # default off; opt-in per tool not modelled in Phase 1
        out.append(entry)
    return out
```

- [ ] **Step 3: Headers + URL helpers**

Append:
```python
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
```

- [ ] **Step 4: Reasoning extraction (★ THE critical helper)**

Append:
```python
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
```

- [ ] **Step 5: Tool-call accumulator (delta → ToolCall)**

Append:
```python
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
```

- [ ] **Step 6: Stream-state container (accumulates partial AssistantMessage)**

Append:
```python
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
```

- [ ] **Step 7: Main stream function (entry point)**

Append:
```python
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
    except Exception as e:  # noqa: BLE001 — last-resort safety net
        yield _build_error_event(state, reason="error", err_msg=f"{type(e).__name__}: {e}")
```

- [ ] **Step 8: Inner streaming loop**

Append:
```python
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
                except Exception:  # noqa: BLE001 — user hook must not break stream
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

    # Stream ended cleanly — close out any unfinished blocks and emit done
    closing = state.finalize_text()
    if closing: yield closing
    closing = state.finalize_thinking()
    if closing: yield closing

    # Promote accumulated tool calls onto the partial message
    tool_calls = state.tool_acc.finalize()
    for tc in tool_calls:
        state.partial.content.append(tc)
    state.partial.stopReason = "toolUse" if tool_calls else "stop"
    yield DoneEvent(
        reason=("toolUse" if tool_calls else "stop"),
        message=state.partial.model_copy(deep=True),
    )
```

- [ ] **Step 9: Per-chunk handler (where reasoning passthrough fires)**

Append:
```python
async def _handle_chunk(chunk: dict, state: _StreamState) -> AsyncIterator[AssistantMessageEvent]:
    """Process one SSE chunk and emit zero or more AssistantMessageEvents."""
    choices = chunk.get("choices") or []
    # Usage chunk has empty choices
    if not choices:
        usage = chunk.get("usage")
        if usage:
            state.partial.usage = Usage.model_validate(usage)
        return
    choice = choices[0]
    delta = choice.get("delta") or {}

    # ★ REASONING — the headline feature
    reasoning = _extract_reasoning(delta)
    if reasoning:
        # Close text block if open (thinking can't interleave with text)
        closing = state.finalize_text()
        if closing: yield closing
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
        if closing: yield closing
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
        if closing: yield closing
        closing = state.finalize_thinking()
        if closing: yield closing
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

    # finish_reason hints stop — we honor it on the trailing chunk in caller
```

- [ ] **Step 10: Error builder + register provider**

Append:
```python
def _build_error_event(
    state: _StreamState, *, reason: str, err_msg: str,
) -> ErrorEvent:
    state.partial.stopReason = "aborted" if reason == "aborted" else "error"
    state.partial.errorMessage = err_msg
    return ErrorEvent(reason=reason, error=state.partial.model_copy(deep=True))


# ── module-level registration ────────────────────────────────────────────────
register_provider("openai-completions", stream_openai_completions)
```

- [ ] **Step 11: Verify syntax + import**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
from agent.pi_ai.providers import openai_completions
from agent.pi_ai.api_registry import known_apis
print('apis registered:', known_apis())
"
```

Expected: `apis registered: ['openai-completions']`.

- [ ] **Step 12: Commit**

```bash
git add agent/pi_ai/providers/openai_completions.py
git commit -m "feat(pi_ai): openai_completions provider with reasoning passthrough"
```

---

## Task 7: pi_ai/providers/faux.py — scripted provider for tests

**Files:**
- Create: `agent/pi_ai/providers/faux.py`
- Reference: `F:/pi-harness/pi-mono/packages/ai/src/providers/faux.ts` (499 LOC TS — we port a much smaller subset, just enough for smoke-tests)

- [ ] **Step 1: Faux provider that emits a scripted event sequence**

Create `agent/pi_ai/providers/faux.py`:
```python
"""faux — scripted provider for testing.

Accepts a script of events (or a list of partial messages) and emits them as
a real AsyncIterator[AssistantMessageEvent]. Use this in tests to exercise
agent loops without hitting any real LLM endpoint.

Smaller than upstream pi-mono faux.ts (we don't need its full schema-driven mode
— our tests pre-build events directly).
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
```

- [ ] **Step 2: Verify import + registration**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
from agent.pi_ai.providers import faux
from agent.pi_ai.api_registry import known_apis
print('apis:', sorted(known_apis()))
"
```

Expected: `apis: ['faux', 'openai-completions']` (order may differ; both present).

- [ ] **Step 3: Commit**

```bash
git add agent/pi_ai/providers/faux.py
git commit -m "feat(pi_ai): faux provider for testing"
```

---

## Task 8: pi_ai/stream.py + final __init__.py

**Files:**
- Create: `agent/pi_ai/stream.py`
- Modify: `agent/pi_ai/__init__.py`
- Reference: `F:/pi-harness/pi-mono/packages/ai/src/stream.ts` (59 LOC TS)

- [ ] **Step 1: stream.py — top-level stream_simple() and complete() wrappers**

Create `agent/pi_ai/stream.py`:
```python
"""Top-level streaming entry points.

stream_simple(model, context, opts) — async iter of AssistantMessageEvent.
complete(model, context, opts) — convenience: drains the stream, returns final
AssistantMessage (or raises if the stream ended with error/aborted).
"""
from __future__ import annotations

from typing import AsyncIterator, Optional

from agent.pi_ai.api_registry import get_provider
from agent.pi_ai.types import (
    AssistantMessage, AssistantMessageEvent, Context, DoneEvent, ErrorEvent,
    Model, SimpleStreamOptions, StreamOptions,
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
        from agent.pi_ai.types import StartEvent, ErrorEvent
        import time as _t
        partial = AssistantMessage(
            api=model.api, provider=model.provider, model=model.id,
            timestamp=int(_t.time() * 1000),
            stopReason="error",
            errorMessage=f"Unknown api {model.api!r}. Registered: {list(_known())}",
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


def _known() -> list[str]:
    from agent.pi_ai.api_registry import known_apis
    return known_apis()
```

- [ ] **Step 2: Re-export public API from __init__.py**

Overwrite `agent/pi_ai/__init__.py`:
```python
"""pi_ai — Python port of @mariozechner/pi-ai (openai-completions only).

This package provides a unified async streaming abstraction over OpenAI-compatible
LLM providers (OpenRouter, Kimi, GLM, MiMo, MiniMax, Nemotron, etc.) with correct
reasoning content passthrough that langchain_openai 1.2.1 drops silently.

See docs/superpowers/specs/2026-05-18-pi-port-design.md for design.

Public API:
    from agent.pi_ai import (
        # Stream entrypoints
        stream_simple, complete,
        # Model + registry
        get_model, register_model, known_models, Model,
        # Types
        AssistantMessage, AssistantMessageEvent, Message, Context, Tool,
        UserMessage, ToolResultMessage,
        # Content
        TextContent, ThinkingContent, ImageContent, ToolCall,
        # Options
        StreamOptions, SimpleStreamOptions, ThinkingLevel,
        # Compat
        OpenAICompletionsCompat, OpenRouterRouting,
        # Provider registration (for custom providers)
        register_provider, get_provider, known_apis,
    )
"""

# Register built-in providers as a side effect of import (mirrors pi-mono's
# register-builtins.ts). Importing pi_ai must Just Work without further setup.
from agent.pi_ai.providers import faux, openai_completions  # noqa: F401

from agent.pi_ai.api_registry import (
    get_provider, known_apis, register_provider,
)
from agent.pi_ai.models import get_model, known_models, register_model
from agent.pi_ai.stream import complete, stream_simple
from agent.pi_ai.types import (
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    ImageContent,
    Message,
    Model,
    OpenAICompletionsCompat,
    OpenRouterRouting,
    SimpleStreamOptions,
    StreamOptions,
    TextContent,
    ThinkingContent,
    ThinkingLevel,
    Tool,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)

__all__ = [
    # Stream entrypoints
    "stream_simple", "complete",
    # Model + registry
    "get_model", "register_model", "known_models", "Model",
    # Types
    "AssistantMessage", "AssistantMessageEvent", "Message", "Context", "Tool",
    "UserMessage", "ToolResultMessage",
    # Content
    "TextContent", "ThinkingContent", "ImageContent", "ToolCall",
    # Options
    "StreamOptions", "SimpleStreamOptions", "ThinkingLevel",
    # Compat
    "OpenAICompletionsCompat", "OpenRouterRouting",
    # Provider registration
    "register_provider", "get_provider", "known_apis",
]
```

- [ ] **Step 3: Verify public API works**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "
import agent.pi_ai as p
print('exports:', sorted(p.__all__))
print('known_apis:', sorted(p.known_apis()))
print('known_models:', [m.id for m in p.known_models()])
"
```

Expected:
- `exports:` shows the full list above
- `known_apis: ['faux', 'openai-completions']`
- `known_models:` shows the registered models

- [ ] **Step 4: Commit**

```bash
git add agent/pi_ai/stream.py agent/pi_ai/__init__.py
git commit -m "feat(pi_ai): top-level stream_simple/complete + public re-exports"
```

---

## Task 9: Smoke-tests for pi_ai layer

**Files:**
- Create: `agent/pi_ai/tests/test_types_smoke.py`
- Create: `agent/pi_ai/tests/test_partial_json.py`
- Create: `agent/pi_ai/tests/test_faux_smoke.py`
- Create: `agent/pi_ai/tests/test_openai_completions_smoke.py`

**Background:** Code-first dictated by spec. These are safety-net tests that catch obvious regressions when we touch pi_ai during Phase 2+ integration. NOT TDD — we already have code.

- [ ] **Step 1: types_smoke — discriminated union round-trip**

Create `agent/pi_ai/tests/test_types_smoke.py`:
```python
"""Type backbone smoke tests. Discriminated unions must serialize/deserialize
without losing the discriminator. Tests round-trip via model_dump → parse_obj."""
from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from agent.pi_ai.types import (
    AssistantMessage, AssistantMessageEvent, DoneEvent, Message,
    TextContent, TextDeltaEvent, ThinkingContent, ToolCall, ToolResultMessage,
    UserMessage,
)


def test_user_message_with_string_content():
    m = UserMessage(content="hi", timestamp=123)
    assert m.role == "user"
    assert m.content == "hi"
    # round-trip
    adapter = TypeAdapter(Message)
    restored = adapter.validate_python(m.model_dump())
    assert isinstance(restored, UserMessage)


def test_assistant_message_with_mixed_content():
    m = AssistantMessage(
        api="openai-completions", provider="openrouter", model="kimi",
        content=[
            ThinkingContent(thinking="hmm..."),
            TextContent(text="answer"),
            ToolCall(id="c1", name="search", arguments={"q": "x"}),
        ],
        timestamp=123,
    )
    assert len(m.content) == 3
    assert m.content[0].type == "thinking"
    assert m.content[2].type == "toolCall"


def test_assistant_message_event_discriminator_round_trip():
    ev = TextDeltaEvent(
        contentIndex=0,
        delta="hello",
        partial=AssistantMessage(
            api="x", provider="y", model="z", timestamp=1,
        ),
    )
    adapter = TypeAdapter(AssistantMessageEvent)
    restored = adapter.validate_python(ev.model_dump())
    assert isinstance(restored, TextDeltaEvent)
    assert restored.delta == "hello"


def test_done_event():
    msg = AssistantMessage(api="a", provider="b", model="c", timestamp=1, stopReason="stop")
    ev = DoneEvent(reason="stop", message=msg)
    assert ev.reason == "stop"
    assert ev.message.stopReason == "stop"


def test_tool_result_message():
    m = ToolResultMessage(
        toolCallId="c1", toolName="search",
        content=[TextContent(text="result")],
        timestamp=123,
    )
    assert m.isError is False
    assert m.content[0].text == "result"
```

- [ ] **Step 2: partial_json — accumulation test**

Create `agent/pi_ai/tests/test_partial_json.py`:
```python
"""Partial-JSON accumulator smoke tests."""
from __future__ import annotations

import pytest

from agent.pi_ai.utils.json_parse import parse_partial, parse_strict


def test_parse_partial_complete_json():
    assert parse_partial('{"a": 1}') == {"a": 1}


def test_parse_partial_incremental():
    # Incremental accumulation (simulating streaming tool-call args)
    chunks = ['{"a":', ' 1, "b":', ' "x"}']
    acc = ""
    for c in chunks:
        acc += c
        parse_partial(acc)  # must not raise
    # Final
    assert parse_partial(acc) == {"a": 1, "b": "x"}


def test_parse_partial_empty():
    assert parse_partial("") == {}
    assert parse_partial("   ") == {}


def test_parse_strict_complete():
    assert parse_strict('{"x": 42}') == {"x": 42}


def test_parse_strict_invalid_raises():
    with pytest.raises(ValueError):
        parse_strict('{not json')
```

- [ ] **Step 3: faux_smoke — verify the faux provider works through stream_simple**

Create `agent/pi_ai/tests/test_faux_smoke.py`:
```python
"""Faux provider smoke test. Verifies the registry → provider → stream_simple
plumbing works end-to-end without any real network."""
from __future__ import annotations

import pytest

from agent.pi_ai import Context, Model, ModelCost, stream_simple, ToolCall
from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.providers.faux import make_faux_provider
from agent.pi_ai.types import (
    DoneEvent, StartEvent, TextDeltaEvent, ThinkingDeltaEvent,
)


def _make_test_model(provider_name: str = "faux-test") -> Model:
    return Model(
        id="test-model", name="test", api=provider_name,
        provider="faux", baseUrl="", cost=ModelCost(),
    )


@pytest.mark.asyncio
async def test_faux_text_only():
    register_provider("faux-text-only", make_faux_provider(text="hello world"))
    model = _make_test_model("faux-text-only")
    events = []
    async for ev in stream_simple(model, Context()):
        events.append(ev)
    assert isinstance(events[0], StartEvent)
    assert any(isinstance(e, TextDeltaEvent) and e.delta == "hello world" for e in events)
    assert isinstance(events[-1], DoneEvent)
    assert events[-1].message.content[0].type == "text"
    assert events[-1].message.content[0].text == "hello world"


@pytest.mark.asyncio
async def test_faux_with_thinking():
    register_provider("faux-thinking", make_faux_provider(thinking="reasoning...", text="answer"))
    model = _make_test_model("faux-thinking")
    events = []
    async for ev in stream_simple(model, Context()):
        events.append(ev)
    thinking_deltas = [e for e in events if isinstance(e, ThinkingDeltaEvent)]
    text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
    assert len(thinking_deltas) == 1
    assert thinking_deltas[0].delta == "reasoning..."
    assert len(text_deltas) == 1
    assert text_deltas[0].delta == "answer"


@pytest.mark.asyncio
async def test_faux_with_tool_call():
    register_provider("faux-tools", make_faux_provider(
        text="",
        tool_calls=[{"name": "search", "arguments": {"q": "x"}}],
    ))
    model = _make_test_model("faux-tools")
    events = []
    async for ev in stream_simple(model, Context()):
        events.append(ev)
    assert isinstance(events[-1], DoneEvent)
    tcs = [c for c in events[-1].message.content if isinstance(c, ToolCall)]
    assert len(tcs) == 1
    assert tcs[0].name == "search"
    assert tcs[0].arguments == {"q": "x"}
    assert events[-1].reason == "toolUse"
```

- [ ] **Step 4: openai_completions_smoke — respx-mocked SSE end-to-end**

Create `agent/pi_ai/tests/test_openai_completions_smoke.py`:
```python
"""openai_completions provider smoke test via respx mocked SSE.

★ The core test: confirms `delta.reasoning` from a mocked Kimi-style stream
reaches us as a ThinkingDeltaEvent. This is the regression test for the
single bug the entire pi-port exists to fix.
"""
from __future__ import annotations

import httpx
import pytest
import respx

from agent.pi_ai import Context, Model, ModelCost, stream_simple
from agent.pi_ai.types import (
    DoneEvent, ErrorEvent, OpenAICompletionsCompat, TextDeltaEvent,
    ThinkingDeltaEvent, ToolCallDeltaEvent,
)


URL = "https://openrouter.ai/api/v1/chat/completions"


def _sse(*payloads: str) -> str:
    """Build a mock SSE response body from a list of JSON payload strings."""
    parts = [f"data: {p}\n\n" for p in payloads]
    parts.append("data: [DONE]\n\n")
    return "".join(parts)


def _model(thinking_fmt: str = "openrouter") -> Model:
    return Model(
        id="moonshotai/kimi-k2-thinking", name="kimi",
        api="openai-completions", provider="openrouter",
        baseUrl="https://openrouter.ai/api/v1",
        cost=ModelCost(),
        compat=OpenAICompletionsCompat(thinkingFormat=thinking_fmt),
    )


@pytest.mark.asyncio
@respx.mock
async def test_text_only_stream():
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","content":"Hi"}}]}',
        '{"choices":[{"delta":{"content":" there"}}]}',
        '{"choices":[{"delta":{},"finish_reason":"stop"}]}',
        '{"usage":{"prompt_tokens":5,"completion_tokens":2,"total_tokens":7}}',
    )
    respx.post(URL).mock(return_value=httpx.Response(200, content=body, headers={"content-type": "text/event-stream"}))
    events = []
    async for ev in stream_simple(_model(), Context(systemPrompt="sys", messages=[])):
        events.append(ev)
    text_pieces = [e.delta for e in events if isinstance(e, TextDeltaEvent)]
    assert "".join(text_pieces) == "Hi there"
    assert isinstance(events[-1], DoneEvent)
    assert events[-1].message.usage.input == 5


@pytest.mark.asyncio
@respx.mock
async def test_reasoning_passthrough_via_reasoning_field():
    """★ This is the regression test for the bug pi-port exists to fix."""
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","reasoning":"Let me think..."}}]}',
        '{"choices":[{"delta":{"reasoning":" still thinking..."}}]}',
        '{"choices":[{"delta":{"content":"42"}}]}',
        '{"choices":[{"delta":{},"finish_reason":"stop"}]}',
    )
    respx.post(URL).mock(return_value=httpx.Response(200, content=body, headers={"content-type": "text/event-stream"}))
    events = []
    async for ev in stream_simple(_model(), Context()):
        events.append(ev)
    thinking_deltas = [e.delta for e in events if isinstance(e, ThinkingDeltaEvent)]
    assert "".join(thinking_deltas) == "Let me think... still thinking..."
    text_deltas = [e.delta for e in events if isinstance(e, TextDeltaEvent)]
    assert "".join(text_deltas) == "42"


@pytest.mark.asyncio
@respx.mock
async def test_reasoning_passthrough_via_reasoning_content_field():
    """Some providers use `reasoning_content` instead of `reasoning`."""
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","reasoning_content":"thinking"}}]}',
        '{"choices":[{"delta":{"content":"done"}}]}',
        '{"choices":[{"delta":{},"finish_reason":"stop"}]}',
    )
    respx.post(URL).mock(return_value=httpx.Response(200, content=body, headers={"content-type": "text/event-stream"}))
    events = []
    async for ev in stream_simple(_model(), Context()):
        events.append(ev)
    thinking = [e.delta for e in events if isinstance(e, ThinkingDeltaEvent)]
    assert thinking == ["thinking"]


@pytest.mark.asyncio
@respx.mock
async def test_tool_call_accumulation():
    body = _sse(
        '{"choices":[{"delta":{"role":"assistant","tool_calls":[{"index":0,"id":"call_1","function":{"name":"search","arguments":"{\\"q\\":"}}]}}]}',
        '{"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"\\"hello\\"}"}}]}}]}',
        '{"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
    )
    respx.post(URL).mock(return_value=httpx.Response(200, content=body, headers={"content-type": "text/event-stream"}))
    events = []
    async for ev in stream_simple(_model(), Context()):
        events.append(ev)
    deltas = [e.delta for e in events if isinstance(e, ToolCallDeltaEvent)]
    assert "".join(deltas) == '{"q":"hello"}'
    assert isinstance(events[-1], DoneEvent)
    tc = [c for c in events[-1].message.content if c.type == "toolCall"][0]
    assert tc.name == "search"
    assert tc.arguments == {"q": "hello"}


@pytest.mark.asyncio
@respx.mock
async def test_http_error_yields_error_event_not_exception():
    respx.post(URL).mock(return_value=httpx.Response(429, content=b'{"error":"rate limit"}'))
    events = []
    async for ev in stream_simple(_model(), Context()):
        events.append(ev)
    assert any(isinstance(e, ErrorEvent) for e in events)
    err = [e for e in events if isinstance(e, ErrorEvent)][0]
    assert "429" in (err.error.errorMessage or "")
```

- [ ] **Step 5: Run the full test suite**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -m pytest agent/pi_ai/tests/ -v
```

Expected output:
```
agent/pi_ai/tests/test_types_smoke.py::test_user_message_with_string_content PASSED
... (5 tests)
agent/pi_ai/tests/test_partial_json.py::test_parse_partial_complete_json PASSED
... (5 tests)
agent/pi_ai/tests/test_faux_smoke.py::test_faux_text_only PASSED
... (3 tests)
agent/pi_ai/tests/test_openai_completions_smoke.py::test_text_only_stream PASSED
... (5 tests)

=== 18 passed in <1s ===
```

If any test fails, fix it before committing. Common pitfalls:
- `pytest-asyncio` mode not set: add to `pyproject.toml` or `pytest.ini`:
  ```
  [pytest]
  asyncio_mode = auto
  ```
- respx version mismatch: pin to `>=0.21` (per Task 1 dep install).

- [ ] **Step 6: Verify pre-existing v7 tests still pass (no regression)**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -m pytest agent/v6/tests/test_handoff_tools.py agent/v6/tests/test_orchestrator.py agent/v6/tests/test_tools_marketplace.py agent/v6/tests/test_tools_io.py agent/v6/tests/test_tools_components.py agent/v6/tests/test_tools_build.py agent/v6/tests/test_tools_runtime.py agent/v6/tests/test_agents.py agent/v6/tests/test_entry.py
```

Expected: `119 passed`.

- [ ] **Step 7: Commit**

```bash
git add agent/pi_ai/tests/
git commit -m "test(pi_ai): smoke tests — types, partial-json, faux, openai-completions"
```

---

## Phase 1 acceptance criteria

After Task 9 commits, verify all of the following:

- [ ] `python -c "import agent.pi_ai"` works without error.
- [ ] `python -c "import agent.pi_ai; print(agent.pi_ai.known_apis())"` shows `['faux', 'openai-completions']`.
- [ ] `python -m pytest agent/pi_ai/tests/ -v` shows ≥18 tests passing.
- [ ] Pre-existing 119 v7 tests still pass (no regression in `agent/v6/`).
- [ ] `git log --oneline` shows ~9 atomic commits, each with `feat(pi_ai):` or `test(pi_ai):` prefix.
- [ ] No dead-code remaining (no `# TODO`, `# FIXME` left unaddressed in pi_ai/).
- [ ] Reasoning passthrough verified via `test_reasoning_passthrough_via_reasoning_field` and `test_reasoning_passthrough_via_reasoning_content_field` (both green).

## Out of scope for Phase 1 (deferred to Phase 2+)

- `pi_agent_core/` package (Agent class, agent_loop, AgentEvent, AgentTool, hooks). **Phase 2.**
- Any integration with v7 (`orchestrator.py`, `agents/architect.py|coder.py|tester.py`, `backend/server.py`). **Phase 3.**
- Rewriting any existing 119 v7 tests under new API. **Phase 3.**
- Real OpenRouter call test (not just respx-mocked). **Phase 4 cutover.**
- UI smoke through Docker for thinking-block rendering. **Phase 4 cutover.**

## Reference: spec sections covered

| Spec section | Tasks |
|---|---|
| Architecture overview — pi_ai file tree | Tasks 1-8 |
| pi_ai types (Message, AssistantMessageEvent, Model, Tool, Context, ...) | Task 2 |
| pi_ai utils (event_stream, json_parse, validation, hash, overflow) | Task 3 |
| pi_ai providers/openai_completions (★ reasoning passthrough) | Task 6 |
| pi_ai providers/transform_messages + simple_options | Task 5 |
| pi_ai providers/faux | Task 7 |
| pi_ai stream.py + __init__ exports | Task 8 |
| Testing strategy — smoke tests per layer | Task 9 |
| Phase 1 of migration plan | This entire plan |
