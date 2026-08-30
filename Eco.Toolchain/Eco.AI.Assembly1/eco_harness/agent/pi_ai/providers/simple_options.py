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
    if opts is None or opts.reasoning is None:
        return body

    # "minimal" = disable thinking entirely. Used by cheap routing gates that
    # need a short, token-clean answer. OpenRouter honours `reasoning: false`;
    # other formats simply get no thinking field.
    if opts.reasoning == "minimal":
        if (_compat(model).thinkingFormat or "openai") == "openrouter":
            body["reasoning"] = {"enabled": False}
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
