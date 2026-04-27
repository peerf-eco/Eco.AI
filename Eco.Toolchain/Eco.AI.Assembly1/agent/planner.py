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
        # Two valid layouts (mirrors list_all_components in tools.py):
        # 1) Eco.<Name>_DK_v.<version>/  (most components)
        # 2) Eco.<Name>/                 (plain dir, e.g. Eco.MemoryManager1)
        dk_versioned = sorted(Path(SOURCE_DIR).glob(f"{name}_DK_v.*"), reverse=True)
        if dk_versioned:
            dk = dk_versioned[0]  # latest by lexical version sort
        else:
            plain = Path(SOURCE_DIR) / name
            if plain.is_dir():
                dk = plain
            else:
                return f"ERROR: Component '{name}' not found in local SDK."
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


PLANNER_SYSTEM_PROMPT = """\
You are the EcoOS Planner. Your job is to talk with the user, search the local
EcoOS SDK via RAG, and converge on a Product Requirements Document (PRD)
describing what to build.

You have these tools:
- list_all_components()  — see the full local SDK catalog.
- rag_query(query)       — semantic search over headers + docs.
- read_component(name)   — read full IEco/IdEco headers for a known component.
- assign(plan_md)        — HANDOFF: ONLY call when the user has explicitly approved
                            the plan. Pass the full PRD in Markdown.

You DO NOT download anything, you DO NOT write files. That's the Coder's job
in the next phase.

PRD format (use exactly these headers when calling assign):

## Project: <ProjectName>

<one-paragraph description>

## Components

- **<name>** — source: sdk — <reason>
- **<name>** — source: marketplace — <reason>
- **<name>** — source: develop — <reason>
  - spec: <interface methods, dependencies>

## Build target

- Platform: <Windows|Linux>
- Output: <executable name>

## Acceptance criteria

- <criterion>

While planning, respond conversationally. Show drafts. Ask for feedback. Only
call `assign` when the user explicitly approves (e.g. "yes, build it",
"ok start", "approved"). Always reply in the user's language.
"""


def create_planner_node(llm):
    """Return a node function for the Planner phase."""
    from langgraph.prebuilt import create_react_agent
    from langchain_core.runnables import Runnable

    # create_react_agent requires the model to be a Runnable.
    # Wrap plain objects (e.g. test stubs) so the pipeline can be assembled.
    if not isinstance(llm, Runnable):
        class _RunnableAdapter(Runnable):
            def bind_tools(self, tools, **kw):
                return self
            def invoke(self, input, config=None, **kw):
                return llm.invoke(input, **kw)
        model = _RunnableAdapter()
    else:
        model = llm

    tools = build_planner_tools(llm)
    react = create_react_agent(model, tools=tools, prompt=PLANNER_SYSTEM_PROMPT)

    def planner_node(state):
        result = react.invoke({"messages": state["planner_messages"]})
        new_msgs = result["messages"][len(state["planner_messages"]):]
        return {"planner_messages": new_msgs}

    return planner_node
