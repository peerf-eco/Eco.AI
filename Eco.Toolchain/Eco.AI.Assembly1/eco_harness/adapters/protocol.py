from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


EventSink = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class AgentResult:
    status: str
    edge: str | None
    message: str
    error: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


class AgentBackend(Protocol):
    name: str

    def run(
        self,
        *,
        role: str,
        seed: str,
        budget: Any,
        on_event: EventSink | None = None,
    ) -> AgentResult:
        ...

    def supports_tools(self) -> bool:
        ...