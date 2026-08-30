"""pi_ai - Python port of @mariozechner/pi-ai (openai-completions only).

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
    ModelCost,
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
    "get_model", "register_model", "known_models", "Model", "ModelCost",
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
