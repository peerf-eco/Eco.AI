"""EcoAgent — claude-code-style agent loop for V6 nodes."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Literal, Optional, Union
from pydantic import BaseModel
from langchain_core.messages import BaseMessage


@dataclass(frozen=True)
class ToolResult:
    """Outcome of a single tool execution.

    `content` is sent to the LLM as ToolMessage.content. `details` is for
    UI/logs and is NOT sent to the model.
    """
    content: str
    details: Optional[dict] = None
    is_error: bool = False


@dataclass(frozen=True)
class EcoTool:
    """A tool the agent can call. Mirrors pi-harness `Tool`."""
    name: str
    description: str
    args_schema: type[BaseModel]
    execute: Callable[[BaseModel], ToolResult]


class EventType(str, Enum):
    START         = "start"
    TEXT_DELTA    = "text_delta"        # reserved for future streaming
    TOOL_START    = "tool_call_start"
    TOOL_END      = "tool_call_end"
    TOOL_UPDATE   = "tool_update"
    ITERATION     = "iteration"
    DONE          = "done"
    NO_TOOL_CALL  = "no_tool_call"
    MAX_ITERS     = "max_iters"
    ERROR         = "error"


@dataclass(frozen=True)
class EcoAgentEvent:
    type: EventType
    data: dict


@dataclass(frozen=True)
class EcoAgentResult:
    status: Literal["done", "no_tool_call", "max_iters", "error"]
    stop_tool_name: str
    stop_payload: dict
    history: list[BaseMessage]
    error: str
