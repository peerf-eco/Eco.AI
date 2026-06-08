"""CODER node — claude-code-style writer with retry-aware seed."""
from __future__ import annotations
from pathlib import Path
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.coder import make_coder_tools
from agent.v6.state import V6State
from agent.v6.trace import write_trace
from langgraph.config import get_stream_writer
from agent.v6.stream_events import make_on_event


CODER_SYSTEM_PROMPT = """\
You are the EcoOS Coder.

You receive a plan and a project_dir. Write the implementation as files inside \
project_dir using `write_file`, `edit_file`. You can read SDK headers under the \
`downloaded_paths`. You DO NOT have shell or build tools — your only job is files.

On retry, READ the current files first (`read_file`, `grep`) to understand the \
state before modifying. Don't blindly rewrite — locate the issue and fix it.

=== Eco C conventions (REQUIRED) ===

Types: use Eco types (int16_t, voidptr_t, char_t, byte_t) — NOT raw int/char.
Memory: allocate via m_pIMem (IEcoMemoryAllocator1). NEVER malloc/free directly.
Self-pointer in VTbl methods: C[Name]* pCMe = (C[Name]*)me;
Return codes: ERR_ECO_SUCCESES / ERR_ECO_POINTER / ERR_ECO_NOINTERFACE.
Pointer validation: every method begins with NULL-check of `me` and out-params (ppv).
Math.C89 methods are lowercase: pow, sqrt, sin, cos (NOT Pow/Sqrt).

=== Eco project layout (REQUIRED) ===

Place files according to this mapping — wrong location breaks the SDK linker:
  SharedFiles/Eco[Name].idl       — IDL interface description
  SharedFiles/IEco[Name].h        — C-interface header
  SharedFiles/IdEco[Name].h       — ID header (CID/IID constants)
  SourceFiles/CEco[Name].c        — implementation
  BuildFiles/...                  — generated, do not write by hand

For an application that consumes marketplace components (the usual case in
our pipeline), the entry point is SourceFiles/EcoMain.c and the runtime flow is:
  IEcoSystem1 initialize → IEcoInterfaceBus1 register components →
  GetPtr(CID) factory → CreateObject(IID) → use → Release in reverse order.
Every successful QueryInterface / CreateObject must be matched by a Release.

=== Static-link CID convention ===

When statically linking against a marketplace component with cid <UPPER_HEX>,
the factory-pointer symbol is GetIEcoComponentFactoryPtr_<UPPER_HEX>
(uppercase, no dashes, no underscores inside the hex). Use exactly that
symbol — the build will fail at link time otherwise.
Register with: (IEcoUnknown*)GetIEcoComponentFactoryPtr_<UPPER_HEX>.

When the implementation is complete and consistent, call `mark_code_done` with \
a short Markdown summary of files created/modified."""


def _build_coder_seed(state: V6State) -> str:
    base = (
        f"User request:\n{state['user_request']}\n\n"
        f"Plan:\n{state['plan_md']}\n\n"
        f"Project dir: {state['project_dir']}\n"
        f"Available components: {state.get('downloaded_paths', [])}\n"
    )
    if state.get("retry_count", 0) == 0:
        return base + "\nImplement the plan from scratch. Use write_file to create files."

    fb = []
    origin = state.get("last_failure_origin", "")
    if origin == "builder":
        fb.append(f"## Previous build failed\n{state.get('build_log', '')}")
    elif origin == "tester":
        fb.append(f"## Previous test failed\n{state.get('tester_report_md', '')}")
    return (
        base
        + f"\nThis is retry #{state['retry_count']}. Existing files are in project_dir — "
        + "READ them first via read_file/grep, then fix the issue:\n\n"
        + "\n\n".join(fb)
    )


def coder_node(state: V6State, *, llm, max_iters: int = 50) -> dict:
    project_dir = Path(state["project_dir"])
    downloaded = [Path(p) for p in state.get("downloaded_paths", [])]
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=downloaded)

    try:
        writer = get_stream_writer()
    except RuntimeError:
        # No active LangGraph stream context (e.g. node called from a unit test).
        writer = None
    on_event = make_on_event("coder", writer)
    agent = EcoAgent(
        llm=llm,
        system_prompt=CODER_SYSTEM_PROMPT,
        tools=tools,
        stop_tool="mark_code_done",
        max_iters=max_iters,
        on_event=on_event,
    )
    result = agent.run(_build_coder_seed(state))
    write_trace(result, node="coder", state=state)

    if result.status == "done":
        return {
            "phase": "building",
            "coder_summary_md": result.stop_payload["summary_md"],
            "coder_messages": result.history,
        }
    return {
        "phase": "failed_escalated",
        "last_failure_origin": "coder",
        "last_status": f"coder_{result.status}",
        "coder_messages": result.history,
    }
