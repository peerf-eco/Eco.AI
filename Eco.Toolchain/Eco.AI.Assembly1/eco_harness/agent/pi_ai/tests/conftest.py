"""Shared fixtures for pi_ai tests."""
import pytest


@pytest.fixture
def httpx_mock_url():
    """Standard fake URL for respx-mocked OpenAI-compat endpoints."""
    return "https://openrouter.ai/api/v1/chat/completions"
