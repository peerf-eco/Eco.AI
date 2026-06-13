"""Architect agent — research, design, materialize, hand off to coder."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from agent.v6.agents._taxonomy import (
    CONTENT_AS_DATA_BLOCK,
    ECO_FRAMEWORK_PACKAGES_BLOCK,
    ECO_TAXONOMY_BLOCK,
)
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.handoff import make_handoff_tool, make_fail_tool
from agent.v6.tools.io import make_read_tools
from agent.v6.tools.code_search import make_code_search_tools
from agent.v6.tools.eco_cli import make_eco_cli_tool
from agent.v6.tools.profile_cache import make_read_component_profile_tool
from agent.v6.tools.rag import make_search_marketplace_tool


ARCHITECT_SYSTEM_PROMPT = """\
You are a senior systems architect specializing in component-based software
on the EcoOS ACOM platform. You work in C (C89), with COM-style components —
interfaces, factories, vtables, QueryInterface / AddRef / Release — and
cross-platform, statically-linked builds (gcc, MSVC) for Linux, Windows,
macOS and mobile targets.

Your job: turn a user's request into a build plan for the coder — which
existing EcoOS components to use, what glue code or new components must be
written, and how it builds for the target platform.

A read-only marketplace_cache/ holds the full source of every published
EcoOS component. Your tools beyond reading files:
  search_marketplace — semantic search over components
  read_component_profile — a component's cid / version / fileId
  eco_cli(['pull', ...]) — fetch a chosen component into project_dir
  to_coder(message) — hand off the finished plan

Build toward a closed plan:
  - restate the request as the capabilities the program needs;
  - for each capability, find the component that provides it and read its
    contract, or mark it as code/component to be written;
  - resolve every dependency the chosen components introduce — including the
    entry point and what must be linked for the target platform;
  - the plan is closed when nothing is left to look up.

Hand off with to_coder: chosen components (name, cid, contract), code or
components to write, entry point and build setup, and acceptance criteria.
Everything you want to say goes INSIDE the to_coder message argument.

""" + ECO_TAXONOMY_BLOCK + "\n" + ECO_FRAMEWORK_PACKAGES_BLOCK + "\n" + CONTENT_AS_DATA_BLOCK

# Identical repeated read-only calls are answered from a memo with a one-line
# pointer (see EcoAgent.dedup_tools). eco_cli is excluded — pull mutates
# project_dir. Kill-switch: V7_TOOL_DEDUP=0.
_ARCHITECT_DEDUP_TOOLS = {
    "read", "glob", "grep", "read_file", "list_dir",
    "search_marketplace", "read_component_profile",
}


def make_architect(
    *,
    model,
    cli_path: Optional[Path],
    project_dir: Path,
    max_iters: Optional[int] = None,
    trace_dir: Optional[Path] = None,
    on_event=None,
) -> EcoAgent:
    """Build the architect EcoAgent with its read-side + pull + handoff tools.

    Note the absence of `make_write_tools` — the architect plans and pulls,
    it does not author code. Capability gating: no write_file ↔ cannot
    accidentally pre-write source the coder is supposed to write.
    """
    tools = [
        # Primary exploration trio (claude-code-style) — grep / glob / read
        # over project_dir + marketplace_cache. The architect's main way to
        # discover components, find symbols, read headers.
        *make_code_search_tools(project_dir=project_dir),
        # Domain helpers — kept for semantic discovery and CID lookup.
        make_search_marketplace_tool(),
        make_read_component_profile_tool(),
        # CLI passthrough — primarily for pull (fetch DEVKIT into project_dir).
        make_eco_cli_tool(cli_path=cli_path, project_dir=project_dir),
        # Legacy sandboxed file ops over project_dir only — kept so existing
        # parts of the prompt that reference read_file/list_dir still work.
        *make_read_tools(project_dir=project_dir),
        make_handoff_tool(
            "to_coder",
            "Hand off control to the coder agent. After this call you are done; "
            "the coder takes over with your message as its starting context.",
        ),
        make_fail_tool(),
    ]
    return EcoAgent(
        model=model,
        system_prompt=ARCHITECT_SYSTEM_PROMPT,
        tools=tools,
        stop_tool=["to_coder", "fail"],
        max_iters=max_iters,
        dedup_tools=(_ARCHITECT_DEDUP_TOOLS
                     if os.getenv("V7_TOOL_DEDUP", "1") == "1" else None),
        trace_dir=trace_dir,
        trace_label="architect",
        on_event=on_event,
    )
