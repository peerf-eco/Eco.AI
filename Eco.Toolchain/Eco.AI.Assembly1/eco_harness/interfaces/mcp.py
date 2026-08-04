from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class McpToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


class ToolProvider(Protocol):
    def list_tools(self) -> list[McpToolDefinition]:
        ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        ...