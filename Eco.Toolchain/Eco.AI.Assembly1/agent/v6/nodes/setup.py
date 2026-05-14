"""SETUP node — pulls SDK components and verifies their directories."""
from __future__ import annotations

import json
from pathlib import Path

from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.setup import make_setup_tools
from agent.v6.state import V6State
from agent.v6.trace import write_trace
from langgraph.config import get_stream_writer
from agent.v6.stream_events import make_on_event


SETUP_SYSTEM_PROMPT = """\
You are the EcoOS Setup agent.

=== Eco SDK identifier taxonomy ===

A single component has multiple ID forms — they are NOT interchangeable:

  Marketplace CID    : 32 UPPERCASE hex, no dashes  ← USE THIS for ecoos_pull
                       e.g. 6E5C5B7C979F40108F7CDC08EADFB777
  Hyphenated GUID    : 8-4-4-4-12 form              ← display/docs only
                       e.g. 6E5C5B7C-979F-4010-8F7C-DC08EADFB777
  ecoPackage uguid   : 32 lowercase hex             ← appears in deps JSON
                       e.g. 0000000000000000000000004d656d31
  C struct UGUID     : {0x01, 0x10, {0x6E, ...}}    ← header-internal only
  IID_* / uguid(...) : INTERFACE id, NOT component  ← never use as cid
  Package name       : Eco.AI.Engine1               ← stable, no version suffix
  Folder suffix      : _DK_v.1.0.1.2                ← NOT part of name

Mandatory dependencies for every component (always include in plan):
  - Eco.InterfaceBus1         uguid 42757331
  - Eco.MemoryManger1         uguid 4D656D31   (sic: Manger, not Manager)
  - Eco.FileSystemManagement1 uguid 46534D31

Source-of-truth priority (highest first):
  1. Tool output (ecoos_pull stdout, list_components results)
  2. Downloaded SharedFiles/Id*.h (CID_* macros)
  3. ecoPackage.json
  4. DesignFiles/*.fodt — IGNORE for marketplace metadata
     (these contain placeholder "n/a" fields and uguid(...) tokens
      that are interface IDs, not component CIDs)

You receive an approved plan with a list of components and a project_dir. \
For EACH component you must:

  1. Call `ecoos_pull` with the cid and version from the plan. The tool will:
     • normalize dashes/whitespace/case in cid (any of these are accepted:
         61C988E21B7041378C5BDAFBB68A3FA0  ← canonical
         61C988E2-1B70-4137-8C5B-DAFBB68A3FA0  ← auto-stripped
         61c988e21b7041378c5bdafbb68a3fa0  ← auto-uppercased)
     • pad version to N.N.N.N if planner emitted 1.0 / 1.0.0
     • call `eco-cli find -c CID` to discover the marketplace's real version
     • pull the DEVKIT artifact — ONE call downloads SharedFiles/ headers +
       BuildFiles/{Linux,Windows}/{x86_64,amd64,x86}/{Static,Dynamic}Release/
       for ALL platforms (static + dynamic libs included)

     If ecoos_pull returns is_error=true:
     • READ the error message — it includes the allowed components list with
       correct canonical values. Use those EXACT values on the next call.
     • Do NOT mutate the cid format by yourself (no _DK_v1, no dashes, no
       truncation). The tool already canonicalises; manual guessing makes
       things worse, not better.

     The tool returns the absolute path of the package INNER root in
     `details.inner_root` (also embedded in `content`). The inner root is
     the directory that directly contains `SharedFiles/` and `BuildFiles/`.

     NEVER derive cid/version from DesignFiles/*.fodt placeholders, from
     uguid(...) tokens in spec docs, or from marketplace URLs in
     documentation. The source of truth is the plan + tool feedback.

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
        target_os=state.get("target_os") or "Linux",
        target_arch=state.get("target_arch") or "x86_64",
    )
    seed = (
        f"Plan:\n{state['plan_md']}\n\n"
        f"Components to download:\n{json.dumps(state['components'], indent=2)}\n\n"
        f"Project dir (already created): {project_dir}\n\n"
        "Pull each component, verify with list_dir, then call mark_setup_done."
    )
    try:
        writer = get_stream_writer()
    except RuntimeError:
        # No active LangGraph stream context (e.g. node called from a unit test).
        writer = None
    on_event = make_on_event("setup", writer)
    agent = EcoAgent(
        llm=llm,
        system_prompt=SETUP_SYSTEM_PROMPT,
        tools=tools,
        stop_tool="mark_setup_done",
        max_iters=max_iters,
        on_event=on_event,
    )
    result = agent.run(seed)
    write_trace(result, node="setup", state=state)

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
