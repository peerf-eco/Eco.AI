"""V5 Planner node — search-only ReAct, single handoff via assign()."""

import logging
from pathlib import Path

from langchain_core.tools import tool
from langgraph.types import Command

from .tools import list_all_components, rag_query, SOURCE_DIR

logger = logging.getLogger(__name__)


def build_planner_tools(llm):
    """Return list of tools for the Planner node. `llm` is unused for now (kept for symmetry)."""

    @tool
    def read_component(name: str) -> str:
        """Read interface (IEco*.h) and ID (IdEco*.h) headers for a known SDK component.

        Args:
            name: Component name like 'Eco.Math.C89'.
        """
        matches = list(Path(SOURCE_DIR).glob(f"{name}_DK_v.*"))
        if not matches:
            return f"ERROR: Component '{name}' not found in local SDK."
        dk = matches[0]
        shared = dk / "SharedFiles"
        if not shared.exists():
            return f"ERROR: SharedFiles missing for '{name}'."
        out = []
        for header in sorted(shared.glob("IEco*.h")) + sorted(shared.glob("IdEco*.h")):
            try:
                content = header.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                content = f"<read error: {e}>"
            out.append(f"// === {header.name} ===\n{content}")
        if not out:
            return f"ERROR: No headers in SharedFiles for '{name}'."
        return "\n\n".join(out)

    @tool
    def assign(plan_md: str) -> Command:
        """HANDOFF: user approved the plan. Pass the FULL approved PRD as Markdown."""
        return Command(update={"plan_md": plan_md, "phase": "coding"})

    return [list_all_components, rag_query, read_component, assign]
