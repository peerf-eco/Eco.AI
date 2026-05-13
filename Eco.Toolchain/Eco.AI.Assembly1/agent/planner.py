"""V5 Planner node — search-only ReAct, single handoff via assign()."""

import logging
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
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
    def assign(plan_md: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        """HANDOFF: user approved the plan. Pass the FULL approved PRD as Markdown."""
        from langchain_core.messages import ToolMessage
        return Command(
            graph=Command.PARENT,
            update={
                "plan_md": plan_md,
                "phase": "coding",
                "planner_messages": [ToolMessage("Plan approved. Handing off to coder.", tool_call_id=tool_call_id)],
            }
        )

    return [list_all_components, rag_query, read_component, assign]


PLANNER_SYSTEM_PROMPT = """\
You are the EcoOS Planner. Your job is to talk with the user, explore the local
EcoOS SDK via RAG, and converge on a thorough Product Requirements Document
(PRD) describing what the Coder will build next.

## Your tools
- list_all_components()  — see the full local SDK catalog.
- rag_query(query)       — semantic search over headers + docs.
- read_component(name)   — read full IEco/IdEco headers for a known component.
- assign(plan_md)        — HANDOFF: ONLY call when the user has explicitly
                            approved the plan. Pass the full PRD in Markdown.

You DO NOT download anything, you DO NOT write files. That's the Coder's job
in the next phase.

## Conversation style

- Reply in the user's language.
- Iterate: ask clarifying questions, show partial drafts, refine.
- DO NOT paste raw tool output (header dumps, component lists) into your replies.
  Use the tools to learn, then summarise findings in your own words.
- Show the FULL PRD draft in Markdown before asking for approval. Each iteration
  show the COMPLETE updated PRD, not just the diff — so the user always sees
  what they're approving.
- Only call `assign(plan_md)` after the user explicitly approves
  (e.g. "yes, build it", "ok start", "approved", "да делай", "погнали").

## PRD format — REQUIRED sections

Use EXACTLY these `##` headings. Every section must be filled with concrete
content; placeholders like "TBD" are not acceptable.

```
## Project: <ProjectName>

<two-to-four-sentence description: what the app does, who's the user,
why it's worth building.>

## Architecture

<one-paragraph high-level description of how components fit together —
which component does what role, how data flows.>

## Components

For each component the Coder must touch, list:

- **<Name>** — source: <sdk|marketplace|develop> — <one-sentence reason>
  - usage: <what interfaces / methods this app actually calls, and why
            they fit the requirement>

For "develop" components, ALSO add:
  - spec: <interface methods, dependencies, expected behavior>

## File structure

List the files the Coder will create. Concrete relative paths. Example:
- `EcoMain.c` — entry point, registers components, runs the REPL loop
- `tests/calc_tests.c` — test cases (if applicable)

## CLI / API design

Describe the user-facing interface concretely:
- What the user types / arguments / flags
- Example session: 3-5 input/output pairs

For a service: REST endpoints / IPC contracts.

## Build target

- Platform: <Windows|Linux|both>
- Output: <executable name(s) per platform>
- Entry point: <main function or equivalent>

## Test plan

3-7 concrete tests the Executor will run. Each test states:
- Input
- Expected output / behavior

## Acceptance criteria

User-facing yes/no checks confirming "done":
- <criterion>
- ...

## Risks & open questions

Non-obvious unknowns or decisions deferred to implementation time.
```

## Quality bar

A finalised PRD should be **2-4 screens long**. If your draft fits in half a
screen, it's not detailed enough — expand Architecture, File structure, and
CLI/API design until they're concrete and unambiguous. Coder will not come
back asking questions; everything must be answered up-front.
"""


def create_planner_node(llm):
    """Return a node function for the Planner phase."""
    from langgraph.prebuilt import create_react_agent

    tools = build_planner_tools(llm)
    react = create_react_agent(llm, tools=tools, prompt=PLANNER_SYSTEM_PROMPT)

    def planner_node(state):
        result = react.invoke({"messages": state["planner_messages"]})
        new_msgs = result["messages"][len(state["planner_messages"]):]
        return {"planner_messages": new_msgs}

    return planner_node
