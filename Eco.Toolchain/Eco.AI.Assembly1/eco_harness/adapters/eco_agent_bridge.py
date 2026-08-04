from __future__ import annotations

from pathlib import Path
from typing import Optional

from agent.v6.eco_agent import EcoAgentResult, EcoAgentEvent
from eco_harness.adapters.external_cli import ExternalCliBackend


class ExternalEcoAgent:
    """Adapt a local coding CLI to the internal orchestrator contract."""

    def __init__(
        self,
        *,
        backend: ExternalCliBackend,
        role: str,
        max_wall_s: int,
        system_prompt: str = "",
        on_event=None,
    ) -> None:
        self.backend = backend
        self.role = role
        self.max_wall_s = max_wall_s
        self.system_prompt = system_prompt
        self.on_event = on_event

    def run(self, seed) -> EcoAgentResult:
        if isinstance(seed, list):
            seed = "\n\n".join(str(item) for item in seed)

        def emit(event: dict):
            if self.on_event is None:
                return
            event_type = event.get("type", "error")
            try:
                from agent.v6.eco_agent import EventType
                event_enum = EventType(event_type)
            except ValueError:
                from agent.v6.eco_agent import EventType
                event_enum = EventType.ERROR
            self.on_event(EcoAgentEvent(type=event_enum, data=event))

        result = self.backend.run(
            role=self.role,
            seed=f"{self.system_prompt}\n\n=== DYNAMIC SEED ===\n{seed}",
            budget=type("Budget", (), {"max_wall_s": self.max_wall_s})(),
            on_event=emit,
        )
        if result.status != "done":
            return EcoAgentResult(
                status=result.status,
                stop_tool_name="",
                stop_payload={},
                history=[],
                error=result.error or result.message,
            )
        return EcoAgentResult(
            status="done",
            stop_tool_name=result.edge or "",
            stop_payload={"message": result.message},
            history=[],
            error="",
        )