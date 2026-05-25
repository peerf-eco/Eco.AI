"""Flat orchestrator with declared handoff edges + hard loop guard.

Pattern: each agent's stop-tool NAME is the edge it picks. Orchestrator
holds the topology as `{agent_name: {edge_name: next_agent_or_None}}`.
A `None` next-agent means the edge is terminal (done / fail).

This is the "declared bounded graph" pattern from Microsoft Agent Framework
and OpenAI Agents SDK — picked over stack-based push/pop (which no
production framework uses because LLMs cannot reliably reason about a
call stack and recursion blows context).

Loop guard is mandatory: documented incidents show 14-min / $9.12 mutual
handoff loops without a hard hop cap.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from agent.v6.eco_agent import EcoAgent, EcoAgentResult
from agent.v6.tools.handoff import message_from_payload


@dataclass(frozen=True)
class HopRecord:
    """One row of the run trace — which agent ran, which edge it picked."""
    hop: int
    agent: str
    edge: Optional[str]      # None if the agent failed to reach a stop-tool
    agent_status: str        # EcoAgentResult.status
    message: str             # extracted from stop_payload (message or reason)


@dataclass(frozen=True)
class OrchestratorResult:
    """Outcome of a full orchestrator run."""
    status: Literal["terminal", "agent_failed", "loop_exceeded", "unknown_edge"]
    terminal_edge: Optional[str]       # e.g. "done" / "fail" on terminal exit
    last_agent: str
    last_message: str
    hops: list[HopRecord] = field(default_factory=list)
    error: str = ""


class Orchestrator:
    """Flat orchestrator over a fixed set of EcoAgents.

    Args:
        agents: name → EcoAgent. Each agent's `stop_tool` set must list the
                edge names this orchestrator expects (e.g. "to_coder", "fail").
        edges:  topology. `edges[a][e] = b` means: when agent `a` stops via
                edge `e`, run agent `b` next. `edges[a][e] = None` means edge
                `e` terminates the run.
        entry:  name of the first agent to run.
        max_hops: hard ceiling on agent-to-agent transitions before
                  `loop_exceeded` is returned (default 8).
    """

    def __init__(
        self,
        *,
        agents: dict[str, EcoAgent],
        edges: dict[str, dict[str, Optional[str]]],
        entry: str,
        max_hops: int = 8,
    ):
        if entry not in agents:
            raise ValueError(f"entry agent {entry!r} not in agents: {list(agents)}")
        unknown_targets = []
        for src, e in edges.items():
            if src not in agents:
                raise ValueError(f"edges references unknown agent {src!r}")
            for edge_name, dst in e.items():
                if dst is not None and dst not in agents:
                    unknown_targets.append((src, edge_name, dst))
        if unknown_targets:
            raise ValueError(f"edges reference unknown destination agents: {unknown_targets}")
        self.agents = agents
        self.edges = edges
        self.entry = entry
        self.max_hops = max_hops

    def run(self, initial_message: str) -> OrchestratorResult:
        current = self.entry
        message = initial_message
        hops: list[HopRecord] = []

        for hop_i in range(self.max_hops):
            agent = self.agents[current]
            result: EcoAgentResult = agent.run(message)

            if result.status != "done":
                # Agent failed internally (max_iters / no_tool_call / error).
                # Surface this as agent_failed; the run is over, no edge to follow.
                hops.append(HopRecord(
                    hop=hop_i, agent=current, edge=None,
                    agent_status=result.status, message=result.error or "",
                ))
                return OrchestratorResult(
                    status="agent_failed",
                    terminal_edge=None,
                    last_agent=current,
                    last_message=result.error or "",
                    hops=hops,
                    error=f"{current}: {result.status} ({result.error})",
                )

            edge = result.stop_tool_name
            message = message_from_payload(result.stop_payload)
            hops.append(HopRecord(
                hop=hop_i, agent=current, edge=edge,
                agent_status=result.status, message=message,
            ))

            agent_edges = self.edges.get(current, {})
            if edge not in agent_edges:
                # Agent picked a stop-tool the orchestrator wasn't told about.
                # This is a wiring bug — refuse to guess.
                return OrchestratorResult(
                    status="unknown_edge",
                    terminal_edge=None,
                    last_agent=current,
                    last_message=message,
                    hops=hops,
                    error=f"{current} picked unknown edge {edge!r}; "
                          f"orchestrator knows: {sorted(agent_edges)}",
                )

            next_agent = agent_edges[edge]
            if next_agent is None:
                # Terminal edge — done / fail / whatever the topology defines.
                return OrchestratorResult(
                    status="terminal",
                    terminal_edge=edge,
                    last_agent=current,
                    last_message=message,
                    hops=hops,
                )

            current = next_agent

        # Reached max_hops without a terminal edge — declare loop and stop.
        return OrchestratorResult(
            status="loop_exceeded",
            terminal_edge=None,
            last_agent=current,
            last_message=message,
            hops=hops,
            error=f"exceeded max_hops={self.max_hops}",
        )
