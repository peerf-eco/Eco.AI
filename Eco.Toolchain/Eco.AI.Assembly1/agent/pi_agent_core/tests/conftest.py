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
