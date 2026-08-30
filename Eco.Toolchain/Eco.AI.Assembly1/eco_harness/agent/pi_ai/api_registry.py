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
