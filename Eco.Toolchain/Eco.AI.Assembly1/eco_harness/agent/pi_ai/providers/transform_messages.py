"""Transform pi_ai Message[] -> OpenAI chat-completions message array.

The provider input has a richer shape than OpenAI's API (separate content blocks
for text/thinking/toolCall, structured ToolResult). We flatten + map per OpenAI
spec, with provider-specific quirks driven by Model.compat.

Mirrors providers/transform-messages.ts (160 LOC TS).
"""
from __future__ import annotations

import json as _json

from agent.pi_ai.types import (
    AssistantMessage, ImageContent, Message, Model, OpenAICompletionsCompat,
    TextContent, ThinkingContent, ToolCall, ToolResultMessage, UserMessage,
)


def _compat(model: Model) -> OpenAICompletionsCompat:
    return model.compat or OpenAICompletionsCompat()


def transform_user_message(msg: UserMessage) -> dict:
    """User message -> {role: user, content: ... }."""
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
    """Assistant message -> {role: assistant, content?, tool_calls?}.

    Thinking blocks: if compat.requiresThinkingAsText -> merge into content
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
            # else: drop - provider can't accept thinking blocks as input
        elif isinstance(c, ToolCall):
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
    """ToolResult message -> {role: tool, tool_call_id, content, [name]}."""
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
