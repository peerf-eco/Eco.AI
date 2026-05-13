"""SETUP node — pulls SDK components and verifies their directories."""
from __future__ import annotations

import json
from pathlib import Path

from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.setup import make_setup_tools
from agent.v6.state import V6State


SETUP_SYSTEM_PROMPT = """\
You are the EcoOS Setup agent.

You receive an approved plan with a list of components and a project_dir. \
For EACH component you must:

  1. Call `ecoos_pull` with its cid and version. The tool returns the absolute \
     path of the package INNER root inside project_dir, in `details.inner_root` \
     and embedded in `content`. The inner root is the directory that directly \
     contains `SharedFiles/` and `BuildFiles/`.

  2. Call `list_dir(<inner_root>)` to verify the package landed. You should \
     see at minimum:
       - `SharedFiles/`        (header files .h / .hpp)
       - `BuildFiles/`         (per-OS static libs)

     Then optionally `list_dir(<inner_root>/BuildFiles/<OS>/<arch>/StaticRelease/)` \
     to confirm the .lib / .a artefact is present. On Linux look under \
     `BuildFiles/Linux/x86_64/StaticRelease/`; on Windows look under \
     `BuildFiles/Windows/amd64/StaticRelease/`.

  3. When ALL components are verified, call `mark_setup_done` with a list of \
     ABSOLUTE inner-root paths (one per component). Example:
       mark_setup_done(downloaded_paths=[
         "/app/output/Calculator/Eco.Math.C89",
         "/app/output/Calculator/Eco.MemoryManager1"
       ])

If any pull or verification fails (`is_error: true`), do NOT call \
`mark_setup_done`. The agent loop will exit with max_iters and surface the \
failure to the user via the escalation panel."""


def setup_node(state: V6State, *, llm, cli_path: Path | None,
               sdk_root: Path | None = None, max_iters: int = 30) -> dict:
    """Run the setup agent.

    Args:
        state: V6 state with plan_md, components, project_dir, project_name
        llm: Language model instance
        cli_path: Path to eco-cli executable
        max_iters: Maximum agent loop iterations

    Returns:
        Delta dict with phase='coding' and downloaded_paths on success,
        or phase='failed_escalated' on error.
    """
    project_dir = Path(state["project_dir"]) if state["project_dir"] else Path("./output") / state["project_name"]
    project_dir.mkdir(parents=True, exist_ok=True)

    tools = make_setup_tools(
        cli_path=cli_path,
        project_dir=project_dir,
        allowed_components=state["components"],
        sdk_root=sdk_root,
    )
    seed = (
        f"Plan:\n{state['plan_md']}\n\n"
        f"Components to download:\n{json.dumps(state['components'], indent=2)}\n\n"
        f"Project dir (already created): {project_dir}\n\n"
        "Pull each component, verify with list_dir, then call mark_setup_done."
    )
    agent = EcoAgent(
        llm=llm,
        system_prompt=SETUP_SYSTEM_PROMPT,
        tools=tools,
        stop_tool="mark_setup_done",
        max_iters=max_iters,
    )
    result = agent.run(seed)

    if result.status == "done":
        return {
            "phase": "coding",
            "project_dir": str(project_dir),
            "downloaded_paths": result.stop_payload["downloaded_paths"],
            "setup_messages": result.history,
        }
    # max_iters or no_tool_call or error
    return {
        "phase": "failed_escalated",
        "last_failure_origin": "setup",
        "last_status": f"setup_{result.status}",
        "setup_messages": result.history,
    }
