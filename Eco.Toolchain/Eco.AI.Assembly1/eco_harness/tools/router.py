from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RoutedTool:
    name: str
    description: str
    schema: dict[str, Any]
    execute: Callable[[dict[str, Any]], Any]


class ToolRouter:
    def __init__(self) -> None:
        self._tools: dict[str, RoutedTool] = {}

    def register(self, tool: RoutedTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def list_tools(self) -> list[RoutedTool]:
        return [self._tools[name] for name in sorted(self._tools)]

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        try:
            tool = self._tools[name]
        except KeyError as error:
            raise KeyError(f"Unknown tool: {name}") from error
        return tool.execute(arguments)