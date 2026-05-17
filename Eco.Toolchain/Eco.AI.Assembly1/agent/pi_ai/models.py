"""Model factory and known-model registry.

This is a slim Phase 1 implementation - only the handful of OpenRouter models
we need are pre-registered. The full pi-mono models.generated.ts (~20k LOC)
is auto-generated from models.dev API; we'll fetch it dynamically in a future
phase if needed.

Custom models can be constructed by callers directly without going through
get_model() - Model is a public pydantic class.
"""
from __future__ import annotations

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
