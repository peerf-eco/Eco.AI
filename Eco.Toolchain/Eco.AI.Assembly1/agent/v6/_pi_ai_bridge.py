"""Bridge between EcoAgent (langchain-style) and pi_ai (raw httpx streaming).

Purpose: when the EcoAgent is constructed with a langchain_openai.ChatOpenAI
instance pointing at an OpenAI-compat endpoint (OpenRouter, etc.), divert
the LLM call through pi_ai.stream_simple. This fixes the reasoning-passthrough
bug — langchain_openai 1.2.1 drops delta.reasoning silently from reasoning
models (Kimi K2.6, GLM, MiMo, ...) because of how its Pydantic wrapper
discards unknown chunk fields.

When the supplied llm is NOT a ChatOpenAI-shaped object (e.g. ScriptedChatModel
in tests), is_chat_openai_like() returns False and EcoAgent falls back to
its old llm.stream() path. This keeps the existing 119-test suite green.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from langchain_core.messages import (
    AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage,
    ToolMessage,
)
from pydantic import SecretStr

from agent.pi_ai import (
    AssistantMessage, Context, Model, ModelCost, OpenAICompletionsCompat,
    SimpleStreamOptions, TextContent, Tool, stream_simple,
)
from agent.pi_ai.types import (
    DoneEvent, ErrorEvent, StartEvent, TextDeltaEvent, ThinkingDeltaEvent,
    ToolCall as PiToolCall, ToolCallDeltaEvent, ToolResultMessage,
    UserMessage,
)


def is_chat_openai_like(llm: Any) -> bool:
    """Duck-type check: does this look like a langchain ChatOpenAI pointed at
    an OpenAI-compat endpoint? We use it to decide whether to route through
    pi_ai (which passes reasoning through) or the old llm.stream() path."""
    return (
        hasattr(llm, "model_name")
        and hasattr(llm, "openai_api_base")
        and hasattr(llm, "openai_api_key")
        and getattr(llm, "openai_api_base", None) is not None
    )


def _resolve_api_key(llm: Any) -> Optional[str]:
    raw = getattr(llm, "openai_api_key", None)
    if raw is None:
        return None
    if isinstance(raw, SecretStr):
        return raw.get_secret_value()
    return str(raw)


def build_pi_model_from_chat_openai(llm: Any) -> Model:
    """Build a pi_ai Model from a langchain_openai ChatOpenAI instance.

    Defaults compat.thinkingFormat to "openrouter" since the dominant use case
    here is the OpenRouter gateway. Future improvement: detect from base URL
    (e.g. zai.com -> "zai", api.openai.com -> "openai")."""
    model_id = getattr(llm, "model_name", None) or getattr(llm, "model", "unknown")
    base_url = (getattr(llm, "openai_api_base", "") or "").rstrip("/")
    return Model(
        id=model_id,
        name=model_id,
        api="openai-completions",
        provider="openrouter",  # safe default for our use case
        baseUrl=base_url,
        reasoning=True,
        cost=ModelCost(),
        compat=OpenAICompletionsCompat(thinkingFormat="openrouter"),
    )


def _content_to_str(content: Any) -> str:
    """Flatten langchain BaseMessage.content (str or list of dicts) to a string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and p.get("type") == "text":
                parts.append(str(p.get("text", "")))
        return "".join(parts)
    return ""


def convert_history_to_pi_context(
    history: list[BaseMessage],
    pi_tools: Optional[list[Tool]] = None,
) -> Context:
    """Convert a langchain history list (SystemMessage/HumanMessage/AIMessage/
    ToolMessage) to a pi_ai Context (systemPrompt + Message[] + tools).

    The system prompt comes from the first SystemMessage; subsequent
    SystemMessages are inlined as user messages (rare in our flow).
    """
    import time as _t

    system_prompt = ""
    messages: list = []

    for i, m in enumerate(history):
        if isinstance(m, SystemMessage):
            if i == 0 and not system_prompt:
                system_prompt = _content_to_str(m.content)
            else:
                # Promote stray SystemMessage to user role (rare).
                messages.append(UserMessage(
                    content=_content_to_str(m.content),
                    timestamp=int(_t.time() * 1000),
                ))
        elif isinstance(m, HumanMessage):
            messages.append(UserMessage(
                content=_content_to_str(m.content),
                timestamp=int(_t.time() * 1000),
            ))
        elif isinstance(m, AIMessage):
            content_blocks = []
            text = _content_to_str(m.content)
            if text:
                content_blocks.append(TextContent(text=text))
            for tc in (getattr(m, "tool_calls", None) or []):
                content_blocks.append(PiToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("name", ""),
                    arguments=tc.get("args") or {},
                ))
            messages.append(AssistantMessage(
                api="openai-completions", provider="openrouter",
                model="unknown",  # post-hoc echo; provider doesn't read it back
                content=content_blocks,
                timestamp=int(_t.time() * 1000),
            ))
        elif isinstance(m, ToolMessage):
            messages.append(ToolResultMessage(
                toolCallId=m.tool_call_id,
                toolName=getattr(m, "name", "") or "",
                content=[TextContent(text=_content_to_str(m.content))],
                isError=(getattr(m, "status", "") == "error"),
                timestamp=int(_t.time() * 1000),
            ))
        # else: silently skip unknown message types (e.g. FunctionMessage from older code paths)

    return Context(systemPrompt=system_prompt, messages=messages, tools=pi_tools)


def eco_tools_to_pi_tools(eco_tools: list) -> list[Tool]:
    """Convert EcoTool[] to pi_ai Tool[] (name + description + JSON-schema params).

    We use pydantic's model_json_schema() to derive the parameters schema from
    EcoTool.args_schema (a BaseModel subclass). This matches what langchain's
    bind_tools would produce for the LLM."""
    out: list[Tool] = []
    for t in eco_tools:
        params_schema: dict = {"type": "object", "properties": {}}
        if t.args_schema is not None:
            try:
                params_schema = t.args_schema.model_json_schema()
            except Exception:  # noqa: BLE001 — be tolerant of malformed schemas
                pass
        out.append(Tool(
            name=t.name,
            description=t.description,
            parameters=params_schema,
        ))
    return out


async def _stream_via_pi_ai(
    pi_model: Model,
    pi_context: Context,
    on_text_delta: Callable[[str], None],
    on_thinking_delta: Callable[[str], None],
) -> AssistantMessage:
    """Run pi_ai.stream_simple, emit text/thinking deltas via callbacks,
    return the final AssistantMessage (DoneEvent.message or ErrorEvent.error)."""
    final_message: Optional[AssistantMessage] = None
    async for ev in stream_simple(
        pi_model, pi_context,
        SimpleStreamOptions(reasoning="medium"),  # request reasoning by default
    ):
        if isinstance(ev, TextDeltaEvent) and ev.delta:
            on_text_delta(ev.delta)
        elif isinstance(ev, ThinkingDeltaEvent) and ev.delta:
            on_thinking_delta(ev.delta)
        elif isinstance(ev, ToolCallDeltaEvent):
            pass  # tool-call arg deltas are accumulated by pi_ai; we read final ToolCall objects from DoneEvent
        elif isinstance(ev, DoneEvent):
            final_message = ev.message
            break
        elif isinstance(ev, ErrorEvent):
            final_message = ev.error
            break
    if final_message is None:
        import time as _t
        final_message = AssistantMessage(
            api=pi_model.api, provider=pi_model.provider, model=pi_model.id,
            timestamp=int(_t.time() * 1000),
            stopReason="error",
            errorMessage="stream ended without done event",
        )
    return final_message


def pi_assistant_message_to_langchain_ai(msg: AssistantMessage) -> AIMessage:
    """Convert pi_ai AssistantMessage back into a langchain AIMessage with
    the same content + tool_calls so EcoAgent's downstream logic
    (history.append, tool_calls extraction) keeps working unchanged."""
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    for c in msg.content:
        ctype = getattr(c, "type", None)
        if ctype == "text":
            text_parts.append(c.text)
        elif ctype == "thinking":
            # Don't merge thinking into AIMessage.content - thinking_delta
            # events already went to the UI via EventType.THINKING_DELTA.
            # If a downstream consumer wants the full reasoning text, they
            # can read it from additional_kwargs below.
            pass
        elif ctype == "toolCall":
            tool_calls.append({
                "name": c.name,
                "args": c.arguments,
                "id": c.id,
            })

    additional_kwargs: dict = {}
    # Surface the raw reasoning text in additional_kwargs for any legacy
    # consumer that already reads it (mirrors langchain_openai 1.2.1 behavior
    # if it had actually preserved the field).
    thinking_parts = [getattr(c, "thinking", "") for c in msg.content if getattr(c, "type", None) == "thinking"]
    if thinking_parts:
        joined = "".join(thinking_parts)
        if joined:
            additional_kwargs["reasoning_content"] = joined

    return AIMessage(
        content="".join(text_parts),
        tool_calls=tool_calls,
        additional_kwargs=additional_kwargs,
    )


def stream_eco_via_pi_ai(
    llm: Any,
    history: list[BaseMessage],
    eco_tools: list,
    on_text_delta: Callable[[str], None],
    on_thinking_delta: Callable[[str], None],
) -> AIMessage:
    """Sync wrapper around the async pi_ai stream. Called from EcoAgent._stream_llm
    inside a synchronous LangGraph node — uses asyncio.run because the agent
    loop itself is sync."""
    pi_model = build_pi_model_from_chat_openai(llm)
    api_key = _resolve_api_key(llm)
    if api_key:
        # pi_ai will fall back to env-var lookup if the model.headers lack one;
        # we set it explicitly via stream options below by building a per-call
        # SimpleStreamOptions inside _stream_via_pi_ai (apiKey field). Pass it
        # by attaching to pi_model.headers so the provider sees it.
        pi_model = pi_model.model_copy(update={
            "headers": {"Authorization": f"Bearer {api_key}"},
        })

    pi_tools = eco_tools_to_pi_tools(eco_tools)
    pi_context = convert_history_to_pi_context(history, pi_tools=pi_tools or None)

    final_msg = asyncio.run(_stream_via_pi_ai(
        pi_model, pi_context, on_text_delta, on_thinking_delta,
    ))
    return pi_assistant_message_to_langchain_ai(final_msg)
