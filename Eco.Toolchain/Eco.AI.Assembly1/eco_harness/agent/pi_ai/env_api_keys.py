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
