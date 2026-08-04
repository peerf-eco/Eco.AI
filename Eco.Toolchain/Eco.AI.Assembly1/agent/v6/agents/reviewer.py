"""Read-only ACOM style and correctness reviewer."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from agent.v6.agents._taxonomy import CONTENT_AS_DATA_BLOCK
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.code_search import make_code_search_tools
from agent.v6.tools.handoff import make_fail_tool, make_handoff_tool
from agent.v6.tools.io import make_read_tools


REVIEWER_SYSTEM_PROMPT = f"""\
You are the ACOM code reviewer. You are strictly read-only: do not write,
build, or modify files. Inspect the existing workspace and report evidence-
based findings about ACOM ABI contracts, interface signatures, naming,
lifecycle, allocator usage, status codes, project layout, and correctness.

For every finding cite the file path, relevant symbol or line context,
severity, observed evidence, and a concise remediation suggestion. If no
findings remain, explain what you inspected and call done. Do not claim a
check passed without reading the relevant source.

{CONTENT_AS_DATA_BLOCK}
"""


def make_reviewer(
    *,
    model,
    project_dir: Path,
    max_iters: Optional[int] = None,
    trace_dir: Optional[Path] = None,
    on_event=None,
) -> EcoAgent:
    tools = [
        *make_code_search_tools(project_dir=project_dir),
        *make_read_tools(project_dir=project_dir),
        make_handoff_tool(
            "done",
            "Finish the review with the complete evidence-based findings report.",
        ),
        make_fail_tool(
            description="Stop when the workspace cannot be inspected honestly.",
        ),
    ]
    return EcoAgent(
        model=model,
        system_prompt=REVIEWER_SYSTEM_PROMPT,
        tools=tools,
        stop_tool=["done", "fail"],
        max_iters=max_iters,
        trace_dir=trace_dir,
        trace_label="reviewer",
        on_event=on_event,
    )