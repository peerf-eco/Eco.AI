import os
import re
import sys
import json
import uuid
import asyncio
import logging
import shutil
from pathlib import Path

# Add project root to PYTHONPATH for agent imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict, Any, AsyncGenerator, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from agent.config.loader import load_config, load_role_config
from eco_harness.roles import make_role_agent

from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)

# RAG init status

app = FastAPI(title="EcoOS Agent API")
HARNESS_CONFIG = load_config(Path(__file__).resolve().parent.parent)

_configured_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3100,http://127.0.0.1:3100",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount output files
os.makedirs("output", exist_ok=True)
app.mount("/files", StaticFiles(directory="output"), name="files")



@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "v7"}


@app.get("/config")
async def harness_config():
    return {
        "languages": ["C", "CPP", "Python", "Java"],
        "platforms": [
            {"os": "Linux", "arch": "x86_64", "label": "Linux · x86_64"},
            {"os": "Windows", "arch": "x86_64", "label": "Windows · x86_64"},
            {"os": "Linux", "arch": "arm64", "label": "Linux · arm64"},
            {"os": "macOS", "arch": "arm64", "label": "macOS · arm64"},
        ],
        "roles": {
            name: {
                "backend": spec.backend,
                "model": spec.model,
                "reasoning": spec.reasoning,
                "skill_versions": spec.skill_versions,
                "budgets": spec.budgets.model_dump(),
            }
            for name, spec in HARNESS_CONFIG.roles.items()
        },
        "languages": {
            name: {
                "prompt": spec.prompt,
                "skill_versions": spec.skill_versions,
                "eco_wizard": spec.eco_wizard,
            }
            for name, spec in HARNESS_CONFIG.languages.items()
        },
        "models": {
            name: profile.model_dump()
            for name, profile in HARNESS_CONFIG.models.items()
        },
    }


class WorkspaceConfigRequest(BaseModel):
    roles: dict[str, dict[str, Any]] = Field(default_factory=dict)
    languages: dict[str, dict[str, Any]] = Field(default_factory=dict)
    harness: dict[str, Any] = Field(default_factory=dict)


@app.put("/config/workspace")
async def update_workspace_config(request: WorkspaceConfigRequest):
    workspace_path = HARNESS_CONFIG.workspace_override
    if workspace_path is None:
        raise HTTPException(status_code=500, detail="Workspace config path is unavailable")
    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    import yaml
    workspace_path.write_text(
        yaml.safe_dump(request.model_dump(), sort_keys=False),
        encoding="utf-8",
    )
    return {"status": "ok", "path": str(workspace_path)}


@app.post("/rag/import")
async def import_rag_documents(
    files: list[UploadFile] = File(...),
    relative_paths: str = Form(""),
):
    """Accept individual files or browser directory uploads and update the shared index."""
    import tempfile
    from scripts.import_rag import import_inputs

    path_hints = json.loads(relative_paths) if relative_paths else {}
    with tempfile.TemporaryDirectory(prefix="eco-rag-upload-") as temp_dir:
        upload_root = Path(temp_dir)
        input_paths: list[Path] = []
        for index, uploaded in enumerate(files):
            name = path_hints.get(str(index)) or uploaded.filename or f"upload-{index}"
            safe_name = Path(name.replace("\\", "/"))
            if safe_name.is_absolute() or ".." in safe_name.parts:
                raise HTTPException(status_code=400, detail="Invalid upload path")
            destination = upload_root / safe_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(await uploaded.read())
            input_paths.append(destination)
        index_path = Path(os.getenv(
            "MARKETPLACE_INDEX_PATH",
            str(Path(__file__).resolve().parent.parent / "marketplace_index.sqlite"),
        ))
        try:
            stats = await asyncio.to_thread(
                import_inputs,
                input_paths,
                index_path=index_path,
                rebuild=False,
            )
        except Exception as error:
            logger.exception("RAG import failed")
            raise HTTPException(status_code=500, detail=f"RAG import failed: {error}") from error
    return {"status": "ok", "stats": stats}


@app.get("/rag/export")
async def export_rag_index():
    index_path = Path(os.getenv(
        "MARKETPLACE_INDEX_PATH",
        str(Path(__file__).resolve().parent.parent / "marketplace_index.sqlite"),
    ))
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="Marketplace RAG index is unavailable")
    return FileResponse(
        index_path,
        media_type="application/vnd.sqlite3",
        filename="marketplace_index.sqlite",
    )


# ═══════════════════════════════════════════════════════════════════════════
# V7 WEBSOCKET — three-agent pipeline (architect → coder → tester) with
# backward handoff edges and HITL plan review.
#
# Flow:
#   1. User sends user_request.
#   2. Architect (planner) runs. Its handoff (to_coder.message) is surfaced
#      to the UI as plan_review_required.
#   3. User clicks Approve → coder+tester sub-orchestrator runs with the plan
#      as seed. User clicks Reject + comment → planner re-runs with user_req
#      + feedback appended. User can iterate plans as many times as needed.
#   4. If planner stops via `fail` instead of `to_coder`, pipeline ends as
#      pipeline_done(failed).
#
# Reuses the v6 client event shape: plan_review_required + plan_decision are
# exactly what the existing frontend (use-v6-socket.ts) already handles.
#
# Mapping (internal → v6 client event):
#   architect-agent active   → phase_change phase=planning node=planner
#   coder-agent active       → phase_change phase=coding   node=coder
#   tester-agent active      → phase_change phase=testing  node=tester
#   EcoAgent.TEXT_DELTA      → node_event event=text_delta
#   EcoAgent.THINKING_DELTA  → node_event event=thinking_delta
#   EcoAgent.TOOL_START/END  → node_event event=tool_call_start|end
#   EcoAgent.DONE handoff    → node_event event=text_delta (surfaces message)
#   EcoAgent.ERROR           → node_event event=error
#   planner.to_coder         → plan_review_required (HITL gate)
#   user plan_decision       → consumed, then approve/reject branch
#   orchestrator terminates  → pipeline_done status=success|failed
# ═══════════════════════════════════════════════════════════════════════════

_MERMAID_FENCE_RE = re.compile(
    r"```mermaid\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE,
)


def _last_assistant_text(history: list) -> str:
    """Extract the text content of the most recent assistant turn from a
    pi_ai history list. Used to surface what the model said in failure
    reports when it stops without a tool call — otherwise "no_tool_call"
    is opaque to the user and the developer.
    """
    for msg in reversed(history):
        # pi_ai AssistantMessage has a .content list mixing TextContent and ToolCall
        content_list = getattr(msg, "content", None)
        if content_list is None:
            continue
        text_parts: list[str] = []
        for c in content_list:
            t = getattr(c, "text", None)
            if isinstance(t, str) and t.strip():
                text_parts.append(t)
        if text_parts:
            return "\n".join(text_parts)
    return ""


def _workspace_header(project_dir: Path, marketplace_cache_root: Path) -> str:
    """Prefix every agent seed with a workspace orientation block.

    The block tells the model three things:
      1. Where it's working — absolute paths for project_dir AND the
         read-only marketplace_cache.
      2. How to explore — grep / glob / read examples (claude-code-style
         primitives that hide the absolute-path detail under a
         basename-prefix anchoring rule).
      3. That repeating an identical tool call wastes an iteration.

    Without this, coder previously burned 30+ iterations on path-guessing
    list_dir('.') / list_dir('/') — see project_v6_path_semantics.
    """
    return (
        f"=== Workspace ===\n"
        f"You are running in two locations:\n"
        f"  project_dir (read-write, where you author code and build):\n"
        f"    {project_dir.resolve()}\n"
        f"  marketplace_cache (read-only, every published EcoOS component):\n"
        f"    {marketplace_cache_root.resolve()}\n"
        f"\n"
        f"=== How to explore ===\n"
        f"Use grep / glob / read — same primitives a human developer uses.\n"
        f"Paths can be relative; if the first segment matches one of the\n"
        f"two roots above (e.g. 'marketplace_cache/Eco.Math.C89/...'), the\n"
        f"tool anchors there. Otherwise relative paths land in project_dir.\n"
        f"\n"
        f"Find a symbol across the marketplace:\n"
        f"  grep(pattern='IEcoComponentFactory', glob='*.h',\n"
        f"       path='marketplace_cache')\n"
        f"\n"
        f"List a known directory tree:\n"
        f"  glob(pattern='**/SharedFiles/*.h',\n"
        f"       path='marketplace_cache/Eco.Math.C89')\n"
        f"\n"
        f"Open a specific file:\n"
        f"  read(path='marketplace_cache/Eco.Math.C89/SharedFiles/IEcoMathC89.h')\n"
        f"\n"
        f"Same primitives work over your own work in project_dir — e.g.\n"
        f"read(path='Eco.Math.C89/SharedFiles/IEcoMathC89.h') reads the\n"
        f"already-pulled copy (relative paths anchor at project_dir).\n"
        f"\n"
        f"Re-running the same call with identical arguments is wasted work —\n"
        f"the result is already in your tool-result history above.\n"
        f"\n"
    )


def _save_mermaid_blocks(plan_md: str, project_dir: Path) -> list[Path]:
    """Extract ```mermaid fenced blocks from the planner's handoff markdown
    and save each into project_dir/docs/architecture_NN.mmd. Returns the
    list of paths written (empty if no diagrams in the plan)."""
    blocks = [m.group(1).strip() for m in _MERMAID_FENCE_RE.finditer(plan_md)]
    if not blocks:
        return []
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, body in enumerate(blocks, start=1):
        path = docs_dir / (f"architecture.mmd" if i == 1 else f"architecture_{i}.mmd")
        try:
            path.write_text(body + "\n", encoding="utf-8")
            written.append(path)
        except OSError:
            logger.exception(f"failed to save mermaid block {i} to {path}")
    return written


# Always-required framework components (memory: Eco.System1/InterfaceBus1/
# MemoryManager1/Core1/FileSystemManagement1). Deterministic across every run,
# so we materialize them up-front instead of letting the coder hand-copy
# headers one write_file at a time (observed: 7-21 wasted LLM calls per run).
_FRAMEWORK_COMPONENTS = (
    "Eco.Core1", "Eco.InterfaceBus1", "Eco.MemoryManager1",
    "Eco.FileSystemManagement1", "Eco.System1",
)
# Subtrees the Linux Makefile actually consumes: headers + the static lib.
_FRAMEWORK_SUBDIRS = ("SharedFiles", "BuildFiles/Linux/x86_64/StaticRelease")


def _prepull_framework(project_dir: Path, cache_root: Path) -> list[str]:
    """V7_PREPULL_FRAMEWORK=1: copy the always-required framework components
    from marketplace_cache into project_dir (idempotent). marketplace_cache and
    `eco_cli pull` produce byte-identical layouts, so this is exactly what the
    architect's pull would deposit — minus the LLM round-trips. Returns the
    list of component names made present."""
    import shutil
    present: list[str] = []
    for comp in _FRAMEWORK_COMPONENTS:
        src_root = cache_root / comp
        if not src_root.is_dir():
            continue
        for sub in _FRAMEWORK_SUBDIRS:
            src = src_root / sub
            if not src.is_dir():
                continue
            dst = project_dir / comp / sub
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)
        present.append(comp)
    return present


def _write_scaffold(project_dir: Path, cache_root: Path | None = None) -> str:
    """V7_SCAFFOLD=1: pre-seed project_dir/src with the proven entry-point
    skeleton + build template (backend/scaffold/*). When V7_PREPULL_FRAMEWORK=1
    and cache_root is given, also materialize the framework deps. Returns the
    seed note appended to the coder's context."""
    templates = Path(__file__).parent / "scaffold"
    dst = project_dir / "src"
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("EcoMain.c", "Makefile"):
        (dst / name).write_text(
            (templates / name).read_text(encoding="utf-8"), encoding="utf-8")

    # Proven win (R6): default ON. Disable with V7_PREPULL_FRAMEWORK=0.
    framework_note = ""
    if cache_root is not None and os.getenv("V7_PREPULL_FRAMEWORK", "1") != "0":
        try:
            present = _prepull_framework(project_dir, cache_root)
            if present:
                framework_note = (
                    "Framework components are ALREADY in project_dir with "
                    "headers and the Linux static lib, and the skeleton already "
                    "wires their factory symbols:\n  "
                    + ", ".join(present) + "\n"
                    "Do NOT pull, glob, list, or re-copy these — read a "
                    "framework header ONLY if you need an exact signature you "
                    "cannot infer from the skeleton. Spend your reads on the "
                    "TASK-SPECIFIC components named in the plan.\n"
                )
        except Exception:
            logger.exception("prepull_framework failed")

    return (
        "\n=== Scaffold (pre-seeded, PROVEN — adapt, don't replace) ===\n"
        "project_dir already contains src/EcoMain.c (entry-point skeleton) and\n"
        "src/Makefile (build template with the correct defines and lib ordering\n"
        "for this SDK). EcoMain(pIUnk) is the entry point — the real main() lives\n"
        "in Eco.System1 and calls it; never write your own main(). Fill the TODOs\n"
        "in src/EcoMain.c, pull only the TASK-SPECIFIC components named in the\n"
        "plan, then build with run_build(project_subdir='src'); binary is src/app.\n"
        + framework_note
        + "\n"
    )


def _project_manifest(project_dir: Path, max_entries: int = 60) -> str:
    """Short listing for warm retry seeds: pulled component dirs + own files."""
    comps: list[str] = []
    own: list[str] = []
    try:
        for p in sorted(project_dir.iterdir()):
            if p.is_dir() and p.name.startswith("Eco."):
                comps.append(f"{p.name}/  (pulled component)")
        for p in sorted(project_dir.rglob("*")):
            rel = p.relative_to(project_dir)
            if rel.parts[0].startswith("Eco."):
                continue
            if p.is_file():
                own.append(str(rel).replace("\\", "/"))
            if len(own) >= max_entries:
                own.append("...")
                break
    except OSError:
        pass
    return "\n".join(comps + own) or "(project_dir is empty)"


@app.websocket("/ws/v7/chat")
async def v7_chat_endpoint(websocket: WebSocket):
    global HARNESS_CONFIG
    HARNESS_CONFIG = load_config(Path(__file__).resolve().parent.parent)
    await websocket.accept()

    # Lazy imports — keep startup light even if the role layer churns.
    from agent.v6.orchestrator import Orchestrator

    # V7 uses pi_ai.Model directly (no langchain). This is the path where
    # delta.reasoning is preserved end-to-end through to the UI thinking blocks.
    is_windows = sys.platform == "win32"
    cli_env_path = (
        os.getenv("ECO_CLI_PATH")
        or HARNESS_CONFIG.eco_cli_path
        or os.getenv("V6_CLI_PATH")
    )
    cli_path: Path | None = Path(cli_env_path) if cli_env_path else None
    make_env_path = (
        os.getenv("ECO_MAKE_EXE")
        or os.getenv("V6_MAKE_EXE")
        or (r"C:/Users/gaevy/gcc/bin/make.exe" if is_windows else "make")
    )
    make_exe = Path(make_env_path)

    requested_thread_id = websocket.query_params.get("thread_id")
    thread_id = requested_thread_id or str(uuid.uuid4())
    project_dir = Path(os.getenv("V7_OUTPUT_ROOT", "./output")) / f"v7-{thread_id[:8]}"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Resolved once per connection so the workspace-header block and any
    # other downstream consumer agree on which cache the agent is told
    # about. Matches the default in agent/v6/tools/code_search.py.
    marketplace_cache_root = Path(os.getenv(
        "MARKETPLACE_CACHE_ROOT", "/app/marketplace_cache"
    ))
    language = "C"

    # Per-conversation LLM trace folder. Every architect/coder/tester LLM
    # request+response is persisted here as a numbered JSON file (see
    # EcoAgent._stream_llm) — incrementally, so a trace exists after a single
    # call and even if the (now unbounded) agent loop never terminates.
    trace_dir = Path(os.getenv("V7_TRACES_DIR", "traces")) / f"v7-{thread_id[:8]}"
    trace_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"[V7 WS] connected thread_id={thread_id} "
        f"project_dir={project_dir} trace_dir={trace_dir}"
    )
    await websocket.send_json({"type": "heartbeat", "version": "v7", "thread_id": thread_id})

    # v6 client expects these agent identifiers in its `node` field — translate.
    PHASE_OF = {"architect": "planning", "coder": "coding",  "tester": "testing"}
    NODE_OF  = {"architect": "planner",  "coder": "coder",   "tester": "tester"}

    loop = asyncio.get_event_loop()

    def _make_on_event(ev_queue: asyncio.Queue, agent_name: str):
        """Build an on_event callback for a specific agent name. Called from
        the worker thread spawned by asyncio.to_thread — we marshal events
        through ev_queue to the main loop's drain task."""
        def on_event(eco_event):
            try:
                loop.call_soon_threadsafe(
                    ev_queue.put_nowait,
                    {"agent": agent_name, "event": eco_event},
                )
            except RuntimeError:
                pass  # loop closed, drop event silently
        return on_event

    async def _drain_events_until_sentinel(ev_queue: asyncio.Queue, sentinel) -> None:
        """Drain ev_queue, forwarding events to the WebSocket until sentinel arrives.

        Resets current_agent on each call so a fresh phase_change is emitted
        at the start of each agent run (planner / coder+tester are separate runs)."""
        current_agent: str | None = None
        while True:
            item = await ev_queue.get()
            if item is sentinel:
                return
            agent = item.get("agent")
            ev = item.get("event")
            if agent is None or ev is None:
                continue
            if agent != current_agent:
                current_agent = agent
                await websocket.send_json({
                    "type":  "phase_change",
                    "phase": PHASE_OF.get(agent, "planning"),
                    "node":  NODE_OF.get(agent, "planner"),
                })
            etype = ev.type.value if hasattr(ev.type, "value") else str(ev.type)
            if etype in ("text_delta", "thinking_delta",
                         "tool_call_start", "tool_call_end"):
                await websocket.send_json({
                    "type":  "node_event",
                    "node":  NODE_OF.get(agent, "planner"),
                    "event": etype,
                    "data":  ev.data or {},
                })
            elif etype == "done":
                # Stop-tool reached. Surface stop_payload.message so the user
                # sees coder/tester handoff text. Planner's handoff is handled
                # specially below via plan_review_required.
                pld = (ev.data or {}).get("payload") or {}
                stop_tool = (ev.data or {}).get("stop_tool", "")
                message = pld.get("message") or pld.get("reason") or ""
                if message and agent != "architect":
                    header = f"\n\n--- {stop_tool} ---\n" if stop_tool else "\n\n"
                    await websocket.send_json({
                        "type":  "node_event",
                        "node":  NODE_OF.get(agent, "planner"),
                        "event": "text_delta",
                        "data":  {"content": header + message},
                    })
            elif etype == "error":
                reason = (ev.data or {}).get("reason", "")
                await websocket.send_json({
                    "type":  "node_event",
                    "node":  NODE_OF.get(agent, "planner"),
                    "event": "error",
                    "data":  {"reason": reason},
                })

    async def _run_agent(agent_runner, ev_queue: asyncio.Queue, *args):
        """Run agent_runner(*args) in a worker thread and drain events
        concurrently. Returns the agent's result. Pushes a sentinel after
        the runner finishes to stop the drain task cleanly."""
        sentinel = object()

        async def run_and_signal():
            try:
                return await asyncio.to_thread(agent_runner, *args)
            finally:
                loop.call_soon_threadsafe(ev_queue.put_nowait, sentinel)

        run_task = asyncio.create_task(run_and_signal())
        drain_task = asyncio.create_task(_drain_events_until_sentinel(ev_queue, sentinel))
        result, _ = await asyncio.gather(run_task, drain_task)
        return result

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            msg_type = payload.get("type", "user_request")
            if msg_type == "abort":
                await websocket.send_json({"type": "pipeline_done", "status": "user_aborted"})
                break
            if msg_type in ("plan_decision", "escalation_decision"):
                # Stale message from a previous run with no active gate. Ignore.
                continue

            user_req = (
                payload.get("user_request")
                or payload.get("message")
                or payload.get("content")
                or ""
            )
            if not user_req:
                await websocket.send_json({"type": "error", "content": "Missing user_request"})
                continue
            language = str(payload.get("language") or HARNESS_CONFIG.default_language)
            if language not in {"C", "CPP", "Python", "Java"}:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Unsupported programming language: {language}",
                })
                continue

            # ── Phase 1: plan-review loop (planner re-runs on reject + feedback) ──
            workspace = _workspace_header(project_dir, marketplace_cache_root)
            planner_seed = workspace + user_req
            approved_plan_md: str | None = None
            terminate_chat = False

            while True:
                ev_queue: asyncio.Queue = asyncio.Queue()
                _, architect_spec, architect_profile = load_role_config(
                    "architect", HARNESS_CONFIG.root,
                )
                from agent.main import get_model as _get_model
                architect_backend = architect_spec.backend.removesuffix("_cli")
                planner = make_role_agent(
                    "architect",
                    config=HARNESS_CONFIG,
                    model=(
                        _get_model(architect_profile, role="architect")
                        if architect_backend in {"internal", "builtin", "eco"}
                        else None
                    ),
                    cli_path=cli_path,
                    project_dir=project_dir,
                    make_exe=make_exe,
                    language=language,
                    marketplace_cache_root=marketplace_cache_root,
                    trace_dir=trace_dir,
                    on_event=_make_on_event(ev_queue, "architect"),
                )
                try:
                    planner_result = await _run_agent(planner.run, ev_queue, planner_seed)
                except Exception as e:
                    logger.exception(f"[V7 WS] planner crashed thread_id={thread_id}")
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Planner crashed: {type(e).__name__}: {e}",
                    })
                    terminate_chat = True
                    break

                # Planner couldn't reach a stop-tool — surface as pipeline_done(failed).
                if planner_result.status != "done":
                    last_text = _last_assistant_text(planner_result.history)
                    text_block = (
                        f"\n\nLast assistant text (no tool call followed it):\n"
                        f"{last_text!r}"
                        if last_text else ""
                    )
                    await websocket.send_json({
                        "type": "pipeline_done",
                        "status": "failed",
                        "build_artifact": "",
                        "tester_report_md": (
                            f"Planner ended without handoff.\n"
                            f"status: {planner_result.status}\n"
                            f"error: {planner_result.error or '(none)'}"
                            f"{text_block}\n\n"
                            f"(orchestrator: agent_failed, hops=0)"
                        ),
                    })
                    terminate_chat = True
                    break

                # Planner declared an honest fail — pipeline ends here.
                if planner_result.stop_tool_name == "fail":
                    fail_reason = (planner_result.stop_payload or {}).get("reason", "") \
                                  or (planner_result.stop_payload or {}).get("message", "")
                    await websocket.send_json({
                        "type": "pipeline_done",
                        "status": "failed",
                        "build_artifact": "",
                        "tester_report_md": (
                            f"Planner declared fail.\n\n{fail_reason}\n\n"
                            f"(orchestrator: terminal, edge=fail, hops=1)"
                        ),
                    })
                    terminate_chat = True
                    break

                # Planner reached to_coder — show the plan for user review.
                plan_md = (planner_result.stop_payload or {}).get("message", "")
                await websocket.send_json({
                    "type":         "plan_review_required",
                    "plan_md":      plan_md,
                    "components":   [],
                    "project_name": "",
                })

                # Wait for the user's plan_decision (or abort).
                decision_received = False
                while not decision_received:
                    raw2 = await websocket.receive_text()
                    try:
                        p2 = json.loads(raw2)
                    except json.JSONDecodeError:
                        continue
                    p2_type = p2.get("type")
                    if p2_type == "abort":
                        await websocket.send_json({"type": "pipeline_done", "status": "user_aborted"})
                        terminate_chat = True
                        decision_received = True
                        break
                    if p2_type != "plan_decision":
                        # ignore stale events
                        continue
                    if bool(p2.get("approved")):
                        approved_plan_md = p2.get("modified_plan_md") or plan_md
                        decision_received = True
                        break
                    # Rejected — re-run planner with feedback appended.
                    reason = (p2.get("reason") or "").strip()
                    planner_seed = workspace + user_req
                    if reason:
                        planner_seed = workspace + (
                            user_req
                            + "\n\n=== Feedback on your previous plan ===\n"
                            + reason
                            + "\n\nRevise the plan addressing this feedback."
                        )
                    decision_received = True
                    # Outer while restarts planner with the new seed.

                if terminate_chat or approved_plan_md is not None:
                    break
                # else: rejected, loop continues with planner re-run

            if terminate_chat or approved_plan_md is None:
                break  # exit per-message loop

            # Persist any mermaid diagrams from the approved plan so the coder
            # (and post-mortem inspection) has them on disk under project_dir/docs/.
            try:
                saved = _save_mermaid_blocks(approved_plan_md, project_dir)
                if saved:
                    logger.info(
                        f"[V7 WS] saved {len(saved)} mermaid diagram(s) for "
                        f"thread_id={thread_id}: {[str(p) for p in saved]}"
                    )
            except Exception:
                logger.exception(f"[V7 WS] mermaid save failed thread_id={thread_id}")

            # ── Phase 2: run coder + tester sub-orchestrator with approved plan ──
            # Experiment toggles (env-gated, default off):
            #   V7_SCAFFOLD=1  — pre-seed src/EcoMain.c + src/Makefile (proven)
            #   V7_WARM_SEED=1 — re-attach workspace+plan+manifest on retry hops
            # Proven win (R2-R6): default ON. Disable with V7_SCAFFOLD=0.
            scaffold_note = ""
            wizard_configured = bool(
                HARNESS_CONFIG.eco_wizard_path
                or shutil.which("eco-wizard")
                or shutil.which("eco-wizard.exe")
            )
            fallback_scaffold_enabled = os.getenv("V7_SCAFFOLD", "0") == "1"
            if not wizard_configured and os.getenv("V7_SCAFFOLD") is None:
                fallback_scaffold_enabled = True
            if fallback_scaffold_enabled:
                try:
                    scaffold_note = _write_scaffold(project_dir, marketplace_cache_root)
                    logger.info(f"[V7 WS] scaffold pre-seeded thread_id={thread_id}")
                except Exception:
                    logger.exception(f"[V7 WS] scaffold failed thread_id={thread_id}")

            seed_builders: dict = {}
            if os.getenv("V7_WARM_SEED") == "1":
                def _coder_retry_seed(stop_message: str, _ws=workspace,
                                      _plan=approved_plan_md,
                                      _note=scaffold_note) -> str:
                    manifest = _project_manifest(project_dir)
                    return (
                        _ws
                        + "=== Approved plan (architect) ===\n" + _plan
                        + "\n\n=== Project state: files already on disk "
                          "(from your previous pass) ===\n"
                        + manifest + "\n"
                        + _note
                        + "\n=== Tester report — fix exactly this ===\n"
                        + stop_message
                    )
                seed_builders["coder"] = _coder_retry_seed

            ev_queue = asyncio.Queue()
            _, coder_spec, coder_profile = load_role_config(
                "coder", HARNESS_CONFIG.root,
            )
            _, tester_spec, tester_profile = load_role_config(
                "tester", HARNESS_CONFIG.root,
            )
            coder = make_role_agent(
                "coder",
                config=HARNESS_CONFIG,
                model=(
                    _get_model(coder_profile, role="coder")
                    if coder_spec.backend.removesuffix("_cli")
                    in {"internal", "builtin", "eco"}
                    else None
                ),
                cli_path=cli_path,
                project_dir=project_dir,
                make_exe=make_exe,
                language=language,
                marketplace_cache_root=marketplace_cache_root,
                trace_dir=trace_dir,
                on_event=_make_on_event(ev_queue, "coder"),
            )
            tester = make_role_agent(
                "tester",
                config=HARNESS_CONFIG,
                model=(
                    _get_model(tester_profile, role="tester")
                    if tester_spec.backend.removesuffix("_cli")
                    in {"internal", "builtin", "eco"}
                    else None
                ),
                cli_path=cli_path,
                project_dir=project_dir,
                make_exe=make_exe,
                language=language,
                marketplace_cache_root=marketplace_cache_root,
                trace_dir=trace_dir,
                on_event=_make_on_event(ev_queue, "tester"),
            )
            # coder.to_architect edge is terminated as None — we don't restart
            # the planner from inside the sub-orchestrator (user already approved
            # the plan; if coder thinks the plan is wrong, it should fail honestly).
            sub_orch = Orchestrator(
                agents={"coder": coder, "tester": tester},
                edges={
                    "coder":  {"to_tester": "tester", "to_architect": None, "fail": None},
                    "tester": {"to_coder":  "coder",  "done":         None, "fail": None},
                },
                entry="coder",
                max_hops=HARNESS_CONFIG.max_hops,
                seed_builders=seed_builders,
            )

            try:
                coder_seed = workspace + approved_plan_md + scaffold_note
                result = await _run_agent(sub_orch.run, ev_queue, coder_seed)
            except Exception as e:
                logger.exception(f"[V7 WS] sub_orch crashed thread_id={thread_id}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"Orchestrator error: {type(e).__name__}: {e}",
                })
                break

            success = (result.status == "terminal" and result.terminal_edge == "done")
            artifact_candidates = sorted(
                path
                for path in project_dir.rglob("*")
                if path.is_file()
                and (
                    path.name == "app"
                    or path.suffix.lower() in {".exe", ".dll", ".so", ".out"}
                )
            )
            build_artifact = (
                str(artifact_candidates[0])
                if artifact_candidates
                else ""
            )
            await websocket.send_json({
                "type":             "pipeline_done",
                "status":           "success" if success else "failed",
                "build_artifact":   build_artifact,
                "tester_report_md": result.last_message
                                    + (f"\n\n(orchestrator: {result.status}"
                                       + (f", edge={result.terminal_edge}"
                                          if result.terminal_edge else "")
                                       + f", hops={len(result.hops)})"),
            })
            break

    except WebSocketDisconnect:
        logger.info(f"[V7 WS] disconnected thread_id={thread_id}")
    except Exception:
        logger.exception(f"[V7 WS] handler crashed thread_id={thread_id}")
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
