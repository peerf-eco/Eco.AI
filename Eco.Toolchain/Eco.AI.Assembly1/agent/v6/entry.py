"""v7 entry point — assemble the three-agent pipeline and run it.

Topology (declared edges):

  architect ──to_coder──→ coder ──to_tester──→ tester ──done──→ END
       │                    │                      │
       │                    │                      └─to_coder──→ coder (backward retry)
       │                    │
       │                    └─to_architect──→ architect (escalation: plan was wrong)
       │
       └─fail──→ END (any agent can fail honestly at any time)

Loop guard: max_hops=8 by default — enough for 2-3 coder/tester retry
cycles, hard ceiling on mutual-handoff infinite loops.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional
import os

from agent.pi_ai import Model
from agent.v6.agents.architect import make_architect
from agent.v6.agents.coder import make_coder
from agent.v6.agents.tester import make_tester
from agent.v6.orchestrator import Orchestrator


# The single source of truth for the v7 topology.
V7_EDGES: dict[str, dict[str, Optional[str]]] = {
    "architect": {"to_coder":     "coder",     "fail": None},
    "coder":     {"to_tester":    "tester",    "to_architect": "architect", "fail": None},
    "tester":    {"to_coder":     "coder",     "done":         None,        "fail": None},
}

V7_ENTRY = "architect"


def build_v7_pipeline(
    *,
    model: Model,
    cli_path: Optional[Path],
    project_dir: Path,
    make_exe: Path,
    max_hops: int = 8,
    on_event: Optional[Callable] = None,
) -> Orchestrator:
    """Build a ready-to-run v7 orchestrator with all three agents wired up.

    Every agent gets the same pi_ai `model`. To use different models per
    agent (e.g. cheaper for architect, sharper for coder), call the
    make_*-factories directly and assemble the orchestrator yourself.

    `on_event` (if provided) is called with `{"agent": str, "event": EcoAgentEvent}`
    so handlers can disambiguate events from architect/coder/tester
    without inspecting tool-name patterns.
    """
    def _make_wrapped(agent_name: str):
        if on_event is None:
            return None
        def wrapped(ev):
            on_event({"agent": agent_name, "event": ev})
        return wrapped

    configured_max_iters = int(os.getenv("AGENT_MAX_ITERATIONS", "0")) or None
    architect = make_architect(
        model=model, cli_path=cli_path, project_dir=project_dir,
        max_iters=configured_max_iters,
        on_event=_make_wrapped("architect"),
    )
    coder = make_coder(
        model=model, project_dir=project_dir, make_exe=make_exe,
        max_iters=configured_max_iters,
        on_event=_make_wrapped("coder"),
    )
    tester = make_tester(
        model=model, project_dir=project_dir,
        max_iters=configured_max_iters,
        on_event=_make_wrapped("tester"),
    )
    return Orchestrator(
        agents={"architect": architect, "coder": coder, "tester": tester},
        edges=V7_EDGES,
        entry=V7_ENTRY,
        max_hops=max_hops,
    )
