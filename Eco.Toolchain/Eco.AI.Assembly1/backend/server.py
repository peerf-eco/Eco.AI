import os
import re
import sys
import json
import uuid
import asyncio
import logging
import shutil
import hashlib
from datetime import datetime, timezone
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
from agent.config.loader import (
    load_config,
    load_marketplace_framework_components,
    load_role_config,
)
from agent.internal.tools import binaries, paths
from eco_harness.worktrees import WorktreeError, create_worktree
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


# ═══════════════════════════════════════════════════════════════════════════
# PROJECT & SESSION REGISTRY — persisted at <output_root>/.harness-registry.json
#
# The web UI's left panel lists projects (folders registered by the user or
# seen in output/) and each project's coding sessions (one per chat thread).
# Shape:
#   {"projects":  [{id, path, name, added_at}],
#    "sessions":  [{id, thread_id, project_path, title, created_at,
#                   updated_at, status}]}
# Session ids are the first 8 chars of thread_id — matching the chat-<id8>
# output directory convention. Legacy output/chat-* dirs are seeded as idle
# sessions on read so history survives registry resets.
# ═══════════════════════════════════════════════════════════════════════════

def _output_root() -> Path:
    return Path(os.getenv("HARNESS_OUTPUT_ROOT", "./output")).resolve()


def _registry_path() -> Path:
    return _output_root() / ".harness-registry.json"


def _load_registry() -> dict:
    try:
        data = json.loads(_registry_path().read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("projects", [])
            data.setdefault("sessions", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"projects": [], "sessions": []}


def _save_registry(registry: dict) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    tmp.replace(path)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_entry(path: Path) -> dict:
    return {
        "id": hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12],
        "path": str(path),
        "name": path.name or str(path),
        "added_at": _now_iso(),
    }


class ProjectRegisterRequest(BaseModel):
    path: str


def _allowed_roots() -> list[Path]:
    """Roots the UI may browse, register, or run in: the user's home, the
    harness output root, plus any extra paths from HARNESS_ALLOWED_ROOTS
    (os.pathsep-separated). Everything else is rejected with 400 — the
    endpoints below would otherwise enumerate/create directories anywhere
    the server process can write."""
    roots: list[Path] = [Path.home().resolve(), _output_root()]
    for part in os.getenv("HARNESS_ALLOWED_ROOTS", "").split(os.pathsep):
        if not part.strip():
            continue
        try:
            roots.append(Path(part.strip()).expanduser().resolve())
        except (OSError, RuntimeError):
            continue
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _is_within_allowed(path: Path) -> bool:
    resolved = path.resolve()
    return any(
        resolved == root or root in resolved.parents
        for root in _allowed_roots()
    )


def _ensure_allowed(path: Path) -> Path:
    if not _is_within_allowed(path):
        raise HTTPException(
            status_code=400,
            detail=f"Path is outside the allowed roots (home, output root, "
                   f"HARNESS_ALLOWED_ROOTS): {path}",
        )
    return path.resolve()


@app.get("/api/fs/browse")
async def fs_browse(path: str | None = None):
    """List subdirectories of `path` (home dir when omitted) for the folder picker."""
    try:
        target = Path(path).expanduser().resolve() if path else Path.home().resolve()
    except (OSError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=f"Invalid path: {error}") from error
    _ensure_allowed(target)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {target}")
    entries: list[dict] = []
    try:
        children = sorted(target.iterdir(), key=lambda c: c.name.lower())
    except PermissionError:
        children = []
    for child in children:
        if child.is_dir() and not child.name.startswith(".") and not child.is_symlink():
            entries.append({"name": child.name, "path": str(child), "type": "dir"})
    # Hide the ".." escape hatch when the parent sits outside the allowlist.
    parent = None
    if target.parent != target and _is_within_allowed(target.parent):
        parent = str(target.parent)
    return {"path": str(target), "parent": parent, "entries": entries}


@app.get("/api/projects")
async def list_projects():
    """Projects with their sessions; auto-seeds legacy output/chat-* runs."""
    registry = _load_registry()
    projects: dict[str, dict] = {
        entry["path"]: {**entry, "auto": False}
        for entry in registry["projects"]
    }
    sessions: dict[str, dict] = {}
    for session in registry["sessions"]:
        sessions[session["id"]] = session

    # Seed legacy/default chat-* dirs that have no session record yet.
    known_dirs: set[str] = set()
    for session in registry["sessions"]:
        p = session.get("project_path")
        if p:
            known_dirs.add(p)
    for d in sorted(_output_root().glob("chat-*")):
        if not d.is_dir():
            continue
        project_path = str(d)
        short_id = d.name.replace("chat-", "", 1)
        if short_id in sessions or project_path in known_dirs:
            continue
        sessions[short_id] = {
            "id": short_id,
            "thread_id": short_id,
            "project_path": project_path,
            "title": "(previous run)",
            "created_at": datetime.fromtimestamp(d.stat().st_ctime, timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(d.stat().st_mtime, timezone.utc).isoformat(),
            "status": "idle",
        }
        known_dirs.add(project_path)

    # Every distinct session project becomes a visible project entry.
    for session in sessions.values():
        ppath = session.get("project_path")
        if ppath and ppath not in projects:
            projects[ppath] = {**_project_entry(Path(ppath)), "auto": True}

    grouped: dict[str, list[dict]] = {}
    for session in sessions.values():
        grouped.setdefault(session.get("project_path") or "", []).append(session)

    result = []
    for ppath, entry in projects.items():
        proj_sessions = sorted(
            grouped.get(ppath, []),
            key=lambda s: s.get("updated_at") or "",
            reverse=True,
        )
        result.append({**entry, "sessions": proj_sessions})
    result.sort(key=lambda p: (p.get("added_at") or ""), reverse=True)
    return {"projects": result}


@app.post("/api/projects")
async def register_project(request: ProjectRegisterRequest):
    """Validate and register a folder chosen in the UI's folder browser."""
    raw = (request.path or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Path is required")
    try:
        resolved = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError) as error:
        raise HTTPException(status_code=400, detail=f"Invalid path: {error}") from error
    _ensure_allowed(resolved)
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {resolved}")
    registry = _load_registry()
    for entry in registry["projects"]:
        if entry["path"] == str(resolved):
            return {**entry, "auto": False}
    entry = _project_entry(resolved)
    registry["projects"].append(entry)
    _save_registry(registry)
    return {**entry, "auto": False}


def _record_session_start(thread_id: str, project_dir: Path, title: str) -> None:
    """Upsert a session record when a user_request starts processing."""
    try:
        registry = _load_registry()
        short_id = thread_id[:8]
        project_path = str(project_dir.resolve())
        now = _now_iso()
        for session in registry["sessions"]:
            if session["id"] == short_id:
                session["updated_at"] = now
                session["status"] = "running"
                session["project_path"] = project_path
                if title and (not session.get("title") or session["title"] == "(previous run)"):
                    session["title"] = title.strip()[:60]
                break
        else:
            registry["sessions"].append({
                "id": short_id,
                "thread_id": thread_id,
                "project_path": project_path,
                "title": title.strip()[:60],
                "created_at": now,
                "updated_at": now,
                "status": "running",
            })
        if not any(p["path"] == project_path for p in registry["projects"]):
            registry["projects"].append(_project_entry(project_dir.resolve()))
        _save_registry(registry)
    except Exception:
        logger.exception("session start recording failed")


def _record_session_end(thread_id: str, project_dir: Path, status: str) -> None:
    try:
        registry = _load_registry()
        short_id = thread_id[:8]
        for session in registry["sessions"]:
            if session["id"] == short_id:
                session["status"] = status
                session["updated_at"] = _now_iso()
                session["project_path"] = str(project_dir.resolve())
                break
        _save_registry(registry)
    except Exception:
        logger.exception("session end recording failed")



@app.get("/health")
async def health_check():
    return {"status": "ok", "protocol": "chat"}


@app.get("/config")
async def harness_config():
    return {
        "languages": ["C", "CPP", "Python", "Java"],
        "platforms": [
            {"os": "Linux", "arch": "x86_64", "label": "Linux · x86_64"},
            {"os": "Windows", "arch": "x86_64", "label": "Windows · x86_64"},
            {"os": "Linux", "arch": "arm64", "label": "Linux · arm64"},
            {"os": "macOS", "arch": "arm64", "label": "macOS · arm64"},
            {"os": "macOS", "arch": "x86_64", "label": "macOS · x86_64"},
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
        "modes": {
            name: {
                "roles": spec.roles,
                "capabilities": spec.capabilities,
            }
            for name, spec in HARNESS_CONFIG.modes.items()
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
# CHAT WEBSOCKET — three-agent pipeline (architect → coder → tester) with
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
# Reuses the existing client event shape: plan_review_required + plan_decision
# are handled by the frontend streaming hook.
#
# Mapping (internal → client event):
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


def _build_chat_model(config) -> Any:
    """Cheap model used for the AUTO-mode intent gate and direct chat answers.

    Returns None when no cheap profile is configured, so callers can skip the
    gate and always run the pipeline.
    """
    from agent.main import get_model
    profile = config.models.get("cheap_fast")
    if profile is None:
        return None
    try:
        return get_model(profile, role=None)
    except Exception:
        logger.exception("chat model init failed")
        return None


def _msg_text(msg) -> str:
    """Concatenate the text blocks of a pi_ai AssistantMessage."""
    return "".join(
        getattr(c, "text", "") or ""
        for c in (getattr(msg, "content", None) or [])
        if getattr(c, "type", None) == "text"
    )


_CHAT_GATE_SYS = (
    "You route messages for an AI coding harness. Reply with exactly one "
    "word — CODE or CHAT.\n"
    "CODE = the user wants code produced, built, fixed, refactored, or "
    "migrated (build, implement, create, write, add, fix, refactor, "
    "migrate a program, component, or feature).\n"
    "CHAT = a question, explanation, comparison, status check, or "
    "conversation that needs no code written or built."
)

_CHAT_ANSWER_SYS = (
    "You are a senior EcoOS ACOM systems assistant. Answer the user's "
    "question clearly and concisely. When the topic is code, explain using "
    "ACOM / C (C89) conventions. Do not write or build code unless the user "
    "explicitly asks you to."
)


async def _classify_intent(user_req: str, model) -> bool:
    """Return True when the message is a concrete coding task (run pipeline).

    "minimal" reasoning disables thinking so the model returns a clean one-word
    answer. We fail SAFE toward running the pipeline: only an explicit CHAT (and
    no CODE) is treated as a question; ambiguity / empty / error → CODE.
    """
    from agent.pi_ai.types import Context, UserMessage, SimpleStreamOptions
    from agent.pi_ai.stream import complete
    ctx = Context(
        systemPrompt=_CHAT_GATE_SYS,
        messages=[UserMessage(content=user_req, timestamp=0)],
    )
    try:
        msg = await complete(
            model, ctx, SimpleStreamOptions(reasoning="minimal", maxTokens=16)
        )
        text = _msg_text(msg).upper()
        # CHAT present without CODE → plain question. Otherwise (CODE, both, or
        # neither) → treat as a task so we never silently drop a request.
        return not ("CHAT" in text and "CODE" not in text)
    except Exception:
        logger.exception("intent classification failed")
        return True  # on doubt, run the pipeline rather than mis-answer


async def _chat_reply(user_req: str, model) -> str:
    """One-shot direct answer for plain chat questions (no pipeline)."""
    from agent.pi_ai.types import Context, UserMessage, SimpleStreamOptions
    from agent.pi_ai.stream import complete
    ctx = Context(
        systemPrompt=_CHAT_ANSWER_SYS,
        messages=[UserMessage(content=user_req, timestamp=0)],
    )
    msg = await complete(
        model, ctx, SimpleStreamOptions(reasoning="low", maxTokens=2000)
    )
    return _msg_text(msg)


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
    list_dir('.') / list_dir('/') — see project path semantics.
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
# Wired in PRD_2 Phase 2: config/marketplace.yaml → framework_components is
# the source of truth; the hard-coded tuple is only a fallback.
_FRAMEWORK_SUBDIRS = ("SharedFiles", "BuildFiles/Linux/x86_64/StaticRelease")


def _framework_components() -> tuple[str, ...]:
    return load_marketplace_framework_components(
        Path(__file__).resolve().parent.parent,
    )


def _prepull_framework(project_dir: Path, cache_root: Path) -> list[str]:
    """HARNESS_PREPULL_FRAMEWORK=1: copy the always-required framework components
    from marketplace_cache into project_dir (idempotent). marketplace_cache and
    `eco_cli pull` produce byte-identical layouts, so this is exactly what the
    architect's pull would deposit — minus the LLM round-trips. Returns the
    list of component names made present."""
    import shutil
    present: list[str] = []
    for comp in _framework_components():
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
    """HARNESS_SCAFFOLD=1: pre-seed project_dir/src with the proven entry-point
    skeleton + build template (backend/scaffold/*). When HARNESS_PREPULL_FRAMEWORK=1
    and cache_root is given, also materialize the framework deps. Returns the
    seed note appended to the coder's context."""
    templates = Path(__file__).parent / "scaffold"
    dst = project_dir / "src"
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("EcoMain.c", "Makefile"):
        (dst / name).write_text(
            (templates / name).read_text(encoding="utf-8"), encoding="utf-8")

    # Default ON. Disable with HARNESS_PREPULL_FRAMEWORK=0.
    framework_note = ""
    if cache_root is not None and os.getenv("HARNESS_PREPULL_FRAMEWORK", "1") != "0":
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


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    global HARNESS_CONFIG
    HARNESS_CONFIG = load_config(Path(__file__).resolve().parent.parent)
    await websocket.accept()

    # Lazy imports — keep startup light even if the role layer churns.
    from agent.internal.orchestrator import Orchestrator

    # The harness uses pi_ai.Model directly (no langchain). This is the path where
    # delta.reasoning is preserved end-to-end through to the UI thinking blocks.

    # Binary resolution now goes through the single shared policy
    # (agent/internal/tools/binaries.py): explicit config → ECO_*_PATH env →
    # <repo>/bin/<name> → /opt mount → legacy platform-suffixed siblings →
    # PATH. The harness.yaml eco_*_path settings ride in as the explicit
    # candidate.
    def resolve_executable_path(config_attr: str, default_name: str):
        """Resolve an external tool binary via binaries.resolve_binary."""
        configured = getattr(HARNESS_CONFIG, config_attr, None)
        resolved = binaries.resolve_binary(default_name, explicit=configured)
        if resolved is None:
            logger.warning(
                "Executable %s not found. %s",
                default_name,
                binaries.describe_search_order(default_name),
            )
            return None
        logger.info("Using executable: %s", resolved)
        return resolved

    # Resolve eco-cli path
    cli_path = resolve_executable_path("eco_cli_path", "eco-cli")

    # Resolve eco-wizard path
    wizard_path = resolve_executable_path("eco_wizard_path", "eco-wizard")
    
    # Set environment variables for tool resolution
    if cli_path:
        os.environ["ECO_CLI_PATH"] = str(cli_path)
        # Set wine prefix for Windows executables
        if cli_path.suffix == ".exe":
            os.environ["ECO_CLI_PREFIX"] = "wine64"
    
    if wizard_path:
        os.environ["ECO_WIZARD_PATH"] = str(wizard_path)
        # Set wine prefix for Windows executables
        if wizard_path.suffix == ".exe":
            os.environ["ECO_WIZARD_PREFIX"] = "wine64"
    
    make_env_path = os.getenv("ECO_MAKE_EXE") or "make"
    make_exe = Path(make_env_path)

    requested_thread_id = websocket.query_params.get("thread_id")
    thread_id = requested_thread_id or str(uuid.uuid4())

    def _default_project_dir() -> Path:
        return Path(os.getenv("HARNESS_OUTPUT_ROOT", "./output")) / f"chat-{thread_id[:8]}"

    project_dir = _default_project_dir()
    project_dir.mkdir(parents=True, exist_ok=True)

    # Resolved once per connection so the workspace-header block and any
    # other downstream consumer agree on which cache the agent is told
    # about. Same resolution as the code-search whitelist (env override →
    # repo-root cache → /app mount), so host runs advertise a real path.
    marketplace_cache_root = paths.marketplace_cache_root()
    language = "C"
    use_worktree = False
    worktree_path: Path | None = None

    # Per-conversation LLM trace folder. Every architect/coder/tester LLM
    # request+response is persisted here as a numbered JSON file (see
    # EcoAgent._stream_llm) — incrementally, so a trace exists after a single
    # call and even if the (now unbounded) agent loop never terminates.
    trace_dir = Path(os.getenv("HARNESS_TRACES_DIR", "traces")) / f"chat-{thread_id[:8]}"
    trace_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"[CHAT WS] connected thread_id={thread_id} "
        f"project_dir={project_dir} trace_dir={trace_dir}"
    )
    await websocket.send_json({"type": "heartbeat", "protocol": "chat", "thread_id": thread_id})

    # Session bookkeeping for the UI project panel: flip the registry status
    # when this connection's run reaches any terminal state.
    session_open = False

    def finish_session(status: str) -> None:
        nonlocal session_open
        if not session_open:
            return
        session_open = False
        _record_session_end(thread_id, project_dir, status)

    # Preserve stable node identifiers expected by the client.
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
                # Node completion card on handoff — a scannable per-node
                # success marker that also closes the streaming burst in the UI.
                if agent != "architect":
                    await websocket.send_json({
                        "type": "node_done",
                        "node": NODE_OF.get(agent, "planner"),
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
                finish_session("aborted")
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

            # Per-message project override: the UI sends the folder selected
            # in the left projects panel. Without it we fall back to (and
            # reset to) the default per-thread chat-<id8> directory, so a
            # worktree-free follow-up never writes into a previous custom
            # project by accident.
            requested_project = str(payload.get("project_dir") or "").strip()
            if requested_project:
                candidate = Path(requested_project).expanduser().resolve()
                if not _is_within_allowed(candidate):
                    await websocket.send_json({
                        "type": "error",
                        "content": (
                            f"project_dir is outside the allowed roots (home, "
                            f"output root, HARNESS_ALLOWED_ROOTS): {candidate}"
                        ),
                    })
                    continue
                try:
                    candidate.mkdir(parents=True, exist_ok=True)
                except OSError as error:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Cannot use project_dir {candidate}: {error}",
                    })
                    continue
                project_dir = candidate
            else:
                project_dir = _default_project_dir()
                project_dir.mkdir(parents=True, exist_ok=True)

            language = str(payload.get("language") or HARNESS_CONFIG.default_language)
            mode = str(payload.get("mode") or "auto").lower()
            if mode not in HARNESS_CONFIG.modes:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Unsupported working mode: {mode}",
                })
                continue
            if payload.get("use_worktree") and not use_worktree:
                try:
                    worktree = create_worktree(
                        HARNESS_CONFIG.root,
                        thread_id,
                        name=payload.get("worktree_name"),
                        root=HARNESS_CONFIG.worktree_root,
                    )
                except WorktreeError as error:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Unable to create isolated worktree: {error}",
                    })
                    continue
                worktree_path = worktree.path
                use_worktree = True
                project_dir = worktree_path
                project_dir.mkdir(parents=True, exist_ok=True)
                await websocket.send_json({
                    "type": "worktree_created",
                    "path": str(worktree_path),
                    "name": worktree.name,
                })
            if language not in {"C", "CPP", "Python", "Java"}:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Unsupported programming language: {language}",
                })
                continue

            # All validation passed — this request becomes a visible session
            # in the UI's project panel (title from the first message only).
            _record_session_start(thread_id, project_dir, user_req)
            session_open = True

            # ── One-shot modes: no automatic pipeline (test / review / code / plan) ──
            if mode in {"test", "review", "code", "plan"}:
                one_shot_role = {
                    "test": "tester",
                    "review": "reviewer",
                    "code": "coder",
                    "plan": "architect",
                }[mode]
                _, role_spec, role_profile = load_role_config(
                    one_shot_role, HARNESS_CONFIG.root,
                )
                from agent.main import get_model as _get_model
                role_backend = role_spec.backend.removesuffix("_cli")
                one_shot = make_role_agent(
                    one_shot_role,
                    config=HARNESS_CONFIG,
                    model=(
                        _get_model(role_profile, role=one_shot_role)
                        if role_backend in {"internal", "builtin", "eco"}
                        else None
                    ),
                    cli_path=cli_path,
                    project_dir=project_dir,
                    make_exe=make_exe,
                    language=language,
                    marketplace_cache_root=marketplace_cache_root,
                    mode=mode,
                    trace_dir=trace_dir,
                )
                ev_queue = asyncio.Queue()
                try:
                    result = await _run_agent(
                        one_shot.run,
                        ev_queue,
                        _workspace_header(project_dir, marketplace_cache_root) + user_req,
                    )
                except Exception as error:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"{mode.title()} agent crashed: {error}",
                    })
                    break
                report = (
                    (result.stop_payload or {}).get("message")
                    or _last_assistant_text(result.history)
                    or result.error
                    or ""
                )
                # A role may answer as plain text (no stop-tool call), e.g. the
                # architect presenting a plan in PLAN mode. Treat a non-empty
                # answer as success regardless of whether a stop tool fired.
                status_ok = result.status in ("done", "no_tool_call") and bool(report.strip())
                finish_session("success" if status_ok else "failed")
                await websocket.send_json({
                    "type": "pipeline_done",
                    "status": "success" if status_ok else "failed",
                    "build_artifact": "",
                    "tester_report_md": report,
                    "mode": mode,
                    "worktree": str(worktree_path) if worktree_path else None,
                })
                continue

            # AUTO mode: a short intent gate keeps plain chat questions out of
            # the build loop. migrate is always a task, so it skips the gate.
            if mode == "auto":
                gate_model = _build_chat_model(HARNESS_CONFIG)
                if gate_model is not None and not await _classify_intent(user_req, gate_model):
                    try:
                        answer = await _chat_reply(user_req, gate_model)
                    except Exception as error:
                        answer = f"(chat reply failed: {error})"
                    await websocket.send_json({
                        "type":  "node_event",
                        "node":  "planner",
                        "event": "text_delta",
                        "data":  {"content": answer},
                    })
                    finish_session("success")
                    await websocket.send_json({
                        "type":             "pipeline_done",
                        "status":           "success",
                        "build_artifact":   "",
                        "tester_report_md": "",
                        "mode":             mode,
                        "worktree":         str(worktree_path) if worktree_path else None,
                    })
                    continue

            # ── AUTO/MIGRATE: full plan→implement→verify pipeline ──
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
                    mode=mode,
                    trace_dir=trace_dir,
                    on_event=_make_on_event(ev_queue, "architect"),
                )
                try:
                    planner_result = await _run_agent(planner.run, ev_queue, planner_seed)
                except Exception as e:
                    logger.exception(f"[CHAT WS] planner crashed thread_id={thread_id}")
                    finish_session("failed")
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
                    finish_session("failed")
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
                    finish_session("failed")
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
                        finish_session("aborted")
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
                        f"[CHAT WS] saved {len(saved)} mermaid diagram(s) for "
                        f"thread_id={thread_id}: {[str(p) for p in saved]}"
                    )
            except Exception:
                logger.exception(f"[CHAT WS] mermaid save failed thread_id={thread_id}")

            # ── Phase 2: run coder + tester sub-orchestrator with approved plan ──
            # Experiment toggles (env-gated, default off):
            #   HARNESS_SCAFFOLD=1  — pre-seed src/EcoMain.c + src/Makefile
            #   HARNESS_WARM_SEED=1 — re-attach workspace+plan+manifest on retry hops
            scaffold_note = ""
            wizard_configured = bool(
                HARNESS_CONFIG.eco_wizard_path
                or shutil.which("eco-wizard")
                or shutil.which("eco-wizard.exe")
            )
            fallback_scaffold_enabled = os.getenv("HARNESS_SCAFFOLD", "0") == "1"
            if not wizard_configured and os.getenv("HARNESS_SCAFFOLD") is None:
                fallback_scaffold_enabled = True
            if fallback_scaffold_enabled:
                try:
                    scaffold_note = _write_scaffold(project_dir, marketplace_cache_root)
                    logger.info(f"[CHAT WS] scaffold pre-seeded thread_id={thread_id}")
                except Exception:
                    logger.exception(f"[CHAT WS] scaffold failed thread_id={thread_id}")

            seed_builders: dict = {}
            if os.getenv("HARNESS_WARM_SEED") == "1":
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
                mode=mode,
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
                mode=mode,
                trace_dir=trace_dir,
                on_event=_make_on_event(ev_queue, "tester"),
            )
            # Shared post-approval topology (agent/internal/entry.py):
            # coder.to_architect is terminated — we don't restart the planner
            # from inside the sub-orchestrator (user already approved the plan;
            # if coder thinks the plan is wrong, it should fail honestly).
            from agent.internal.entry import EXECUTION_EDGES, EXECUTION_ENTRY

            sub_orch = Orchestrator(
                agents={"coder": coder, "tester": tester},
                edges=EXECUTION_EDGES,
                entry=EXECUTION_ENTRY,
                max_hops=HARNESS_CONFIG.max_hops,
                seed_builders=seed_builders,
            )

            try:
                coder_seed = workspace + approved_plan_md + scaffold_note
                result = await _run_agent(sub_orch.run, ev_queue, coder_seed)
            except Exception as e:
                logger.exception(f"[CHAT WS] sub_orch crashed thread_id={thread_id}")
                finish_session("failed")
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

            # ── Structured failure cards, derived from the hop trace ─────────
            # The sub-orchestrator runs synchronously in one worker thread, so
            # per-hop outcomes can't stream live; we replay result.hops here.
            # tester --to_coder--> *  ⇒ test_fail (each backward hop = 1 retry)
            # coder honest-fail/crash ⇒ build_fail
            # Emitted only when the run ultimately FAILED: on a recovered
            # retry the red "failed" card would contradict the green
            # pipeline_done right after it — the retry itself is already
            # visible via tool cards / thinking blocks.
            test_retries = 0
            if not success:
                for hop in result.hops:
                    if hop.agent == "tester" and hop.edge == "to_coder":
                        test_retries += 1
                        await websocket.send_json({
                            "type":        "test_fail",
                            "reason_md":   hop.message or "(tester gave no reason)",
                            "retry_count": test_retries,
                        })
                    elif hop.agent == "coder" and (hop.edge == "fail" or hop.edge is None):
                        await websocket.send_json({
                            "type":        "build_fail",
                            "error_md":    hop.message or result.error or "(coder failed without a message)",
                            "retry_count": 0,
                        })

            # Status is recorded only after the escalation gate resolves so
            # an abort here lands as "aborted", not "failed".
            if success:
                finish_session("success")
                await websocket.send_json({
                    "type":             "pipeline_done",
                    "status":           "success",
                    "build_artifact":   build_artifact,
                    "tester_report_md": result.last_message
                                        + f"\n\n(orchestrator: {result.status}, hops={len(result.hops)})",
                })
                break

            # Failure → escalate to the user. The escalation card is a real
            # gate: wait for the Continue/Abort decision before the terminal
            # pipeline_done, otherwise the UI would re-enter a phantom
            # processing state when the user clicks a button nobody answers.
            last_coder_msg = next(
                (h.message for h in reversed(result.hops) if h.agent == "coder"), "",
            )
            last_tester_msg = next(
                (h.message for h in reversed(result.hops) if h.agent == "tester"), "",
            )
            if result.status == "loop_exceeded":
                reason_code = f"{result.last_agent}_retry_limit"
            elif result.status == "agent_failed":
                # matches the frontend REASON_LABEL keys, e.g. coder_max_iters
                failing_status = next(
                    (h.agent_status for h in reversed(result.hops) if h.agent == result.last_agent),
                    "error",
                )
                reason_code = f"{result.last_agent}_{failing_status}"
            elif result.status == "unknown_edge":
                reason_code = f"{result.last_agent}_error"
            else:
                reason_code = f"{result.last_agent}_fail"
            await websocket.send_json({
                "type":             "escalation_required",
                "reason":           reason_code,
                "failure_origin":   NODE_OF.get(result.last_agent, result.last_agent),
                "retry_count":      test_retries,
                "max_retries":      HARNESS_CONFIG.max_hops,
                "build_log":        last_coder_msg[-4000:],
                "tester_report_md": last_tester_msg[-8000:],
                "plan_md":          approved_plan_md or "",
                "coder_summary_md": last_coder_msg[-4000:],
            })

            escalation_aborted = False
            try:
                while True:
                    raw3 = await websocket.receive_text()
                    try:
                        p3 = json.loads(raw3)
                    except json.JSONDecodeError:
                        continue
                    p3_type = p3.get("type")
                    if p3_type == "abort":
                        escalation_aborted = True
                        break
                    if p3_type == "escalation_decision":
                        escalation_aborted = not bool(p3.get("continue"))
                        break
                    # stale plan_decision / anything else — ignore
            except WebSocketDisconnect:
                raise
            if escalation_aborted:
                finish_session("aborted")
                await websocket.send_json({"type": "pipeline_done", "status": "user_aborted"})
            else:
                # Continue keeps the session open for a follow-up request;
                # this run itself stays failed — the user drives what's next.
                finish_session("failed")
                await websocket.send_json({
                    "type":             "pipeline_done",
                    "status":           "failed",
                    "build_artifact":   build_artifact,
                    "tester_report_md": result.last_message,
                })
            break

    except WebSocketDisconnect:
        finish_session("aborted")
        logger.info(f"[CHAT WS] disconnected thread_id={thread_id}")
    except Exception:
        finish_session("failed")
        logger.exception(f"[CHAT WS] handler crashed thread_id={thread_id}")
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
