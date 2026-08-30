import os
import re
import sys
import json
import uuid
import asyncio
import logging
import shutil
import hashlib
import base64
import time
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

# Add the repo root (dev checkout) to PYTHONPATH for direct `python server.py`
# runs; package imports work without it under uvicorn from the repo root.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from typing import List, Dict, Any, AsyncGenerator
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from eco_harness.agent.config.loader import (
    load_config,
    load_marketplace_framework_components,
    load_role_config,
)
from eco_harness.agent.internal.tools import binaries, paths
from eco_harness.backend.session_export import (
    build_project_export,
    default_traces_root,
    iter_project_jsonl,
    render_export_text,
    safe_export_name,
)
from eco_harness.worktrees import WorktreeError, create_worktree
from eco_harness.roles import make_role_agent

from dotenv import load_dotenv


load_dotenv()
# Installed mode: also load the app-home .env ($ECO_HOME/.env). Precedence is
# .env < process env — dotenv never overrides variables that are already set.
load_dotenv(paths.eco_home() / ".env")

logger = logging.getLogger(__name__)

# RAG init status

app = FastAPI(title="EcoOS Agent API")
HARNESS_CONFIG = load_config()

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

def _output_root() -> Path:
    """Shared output-root policy (see paths.output_root)."""
    return paths.output_root()


_output_dir = _output_root()
os.makedirs(_output_dir, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(_output_dir)), name="files")


# ═══════════════════════════════════════════════════════════════════════════
# ACTIVE SESSIONS — in-memory map of thread_id -> WebSocket for sessions that
# currently have a live connection. Lets the UI stop (abort) a running or
# suspended session from the projects panel even when that session is not the
# one currently displayed in the main chat area. Populated on connect and
# cleared on disconnect / abort.
# ═══════════════════════════════════════════════════════════════════════════

ACTIVE_SESSIONS: dict[str, "WebSocket"] = {}


# ═══════════════════════════════════════════════════════════════════════════
# PROJECT & SESSION REGISTRY — persisted at <output_root>/.harness-registry.json
#
# The web UI's left panel lists whitelisted projects (folders explicitly
# registered by the user) and each project's coding sessions (one per chat
# thread). Shape:
#   {"projects":  [{id, path, name, added_at}],
#    "sessions":  [{id, thread_id, project_path, title, created_at,
#                   updated_at, status}]}
# Session ids are the first 8 chars of thread_id — matching the chat-<id8>
# output directory convention. Removing a project from the panel deletes its
# registry entry only — sessions, traces, and folders are never touched.
# ═══════════════════════════════════════════════════════════════════════════

def _context_window() -> int:
    """Configured model context window (tokens) for the session context-load
    gauge. Override with HARNESS_CONTEXT_WINDOW; the default is a safe 128k."""
    try:
        return max(1024, int(os.getenv("HARNESS_CONTEXT_WINDOW", "131072")))
    except (TypeError, ValueError):
        return 131072


def _traces_root() -> Path:
    """Shared traces-root policy (see paths.traces_root)."""
    return paths.traces_root()


def _registry_path() -> Path:
    return _output_root() / ".harness-registry.json"


def _sweep_legacy_nested_app_dirs(output_root: Path) -> list[Path]:
    """Detect leftover `--app/...` nested project dirs from pre-fix runs.

    Bug history (ses-9257ff60 → ses-6acd93e6 → ses-e9b2c2ad): the
    previous implementation of `_default_project_dir` used
    `Path("./output").resolve()`, which is CWD-relative. When the
    server was started with CWD = an old project's working dir, the
    new default project_dir became nested INSIDE the old one as
    `output/<old>/output/<old>/--app/Eco.Toolchain/...`. The eco-wizard
    then wrote the new project's files into that nested tree, and
    subsequent runs picked up the same project and saw TWO project
    trees (ses-e9b2c2ad's 22-turn coder run spent 7 turns on
    list_dir/glob trying to disambiguate `Eco.TrigTable` from
    `--app/Eco.Toolchain/.../Eco.TrigTable`).

    The fix in `_default_project_dir` and the trace-dir construction
    anchors paths to the repo root, preventing NEW nesting. This sweep
    detects EXISTING nested residue so the user (and the panel) can
    clean it up explicitly. It does NOT auto-delete; deletion happens
    only via POST /api/projects/cleanup-legacy (or the scoped
    end-of-session helper) and is subject to the 24 h plan.md guard.

    Heuristic — a candidate must show the actual nesting-bug signature,
    otherwise live projects (every chat dir legitimately contains an
    `--app/Eco.Toolchain/...` tree) would match:
      (a) its name is literally "--app", AND
      (b) its ancestor chain below `output_root` contains a directory
          named `output` — the residue of the CWD-relative
          `Path("./output").resolve()` bug — AND
      (c) it contains at least one ACOM component marker (SourceFiles/,
          MakefileExe, ...) proving a pre-fix run created a project
          here.

    Pure walker: returns the list of `Path`s that match; never follows
    symlinks and never returns anything outside `output_root`.
    """
    if not output_root or not output_root.is_dir():
        return []
    root = output_root.resolve()
    ACOM_MARKERS = (
        "SourceFiles", "SharedFiles", "HeaderFiles", "DesignFiles",
        "AssemblyFiles", "BuildFiles", "DependenciesFiles", "EcoMain.c",
        "MakefileExe", "EcoSystem1", "EcoMathC89", "EcoInterfaceBus1",
    )

    def _has_nested_output_component(p: Path) -> bool:
        # The CWD-nesting bug is the ONLY way an `output` component can
        # appear between the output root and an `--app` dir: live
        # projects look like `<output_root>/<chat-*>/--app` with no
        # `output` component below the root.
        try:
            rel = p.resolve().relative_to(root)
        except (OSError, ValueError):
            return False
        return "output" in rel.parts

    def _has_acom_marker(d: Path) -> bool:
        # Depth-bounded walk for an ACOM project marker. Capped at 6
        # levels deep and 2000 entries; exceeding the cap is NOT a
        # match (size alone proves nothing — only a marker does).
        try:
            count = 0
            for root_dir, dirs, files in d.walk(on_error=lambda e: None,
                                                follow_symlinks=False):
                depth = len(root_dir.relative_to(d).parts) if root_dir != d else 0
                if depth > 6:
                    dirs.clear()
                    continue
                for marker in ACOM_MARKERS:
                    if marker in dirs or marker in files:
                        return True
                count += len(files) + len(dirs)
                if count > 2000:
                    return False
        except OSError:
            pass
        return False

    from collections import deque
    queue = deque([(root, 0)])
    scanned = 0
    candidates: list[Path] = []
    while queue and scanned < 10_000:
        d, depth = queue.popleft()
        scanned += 1
        if depth > 5:
            continue
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for e in entries:
            # Never follow symlinks: a symlinked component could point
            # the sweep (and any later rmtree) outside the output root.
            if e.is_symlink() or not e.is_dir():
                continue
            if e.name == "--app":
                if (_has_nested_output_component(e) and _has_acom_marker(e)):
                    candidates.append(e)
            elif depth < 5:
                queue.append((e, depth + 1))
    return candidates


def _load_registry() -> dict:
    try:
        data = json.loads(_registry_path().read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("projects", [])
            data.setdefault("sessions", [])
            # Repair paths recorded with a stale output-root prefix so the panel
            # and subsequent runs point at the harness's current output root.
            # The heal-save must never discard the loaded registry: if the
            # file is read-only to us (e.g. written by a root-owned server
            # run), the in-memory heal still applies and the panel renders.
            try:
                if _heal_registry_paths(data):
                    _save_registry(data)
            except OSError:
                logger.warning(
                    "registry path heal could not be persisted (%s is not "
                    "writable); serving healed paths from memory",
                    _registry_path(),
                )
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"projects": [], "sessions": []}


def _heal_registry_paths(registry: dict) -> bool:
    """Re-anchor stored project/session paths that only differ from the current
    output root by a stale prefix (cwd drift). Returns True if anything changed.

    See ``_remap_to_output_root`` for the security reasoning: the remapped path
    always lands inside the output root."""
    changed = False
    for entry in registry.get("projects", []):
        raw = entry.get("path")
        if not raw:
            continue
        fixed = str(_remap_to_output_root(Path(raw).expanduser()))
        if fixed != str(raw):
            entry["path"] = fixed
            changed = True
    for sess in registry.get("sessions", []):
        raw = sess.get("project_path")
        if not raw:
            continue
        fixed = str(_remap_to_output_root(Path(raw).expanduser()))
        if fixed != str(raw):
            sess["project_path"] = fixed
            changed = True
    return changed


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
    """Registry entry for a whitelisted project folder.

    Naming convention (see docs/ID_NAMING.md): harness-generated dirs
    (``output/proj-<8hex>``, legacy ``output/chat-<8hex>``) get the short
    ``proj-XXXX`` base32 ref as both id and display name so the panel card
    reads like a project, not a session id. User-registered folders keep
    the SHA-1-based id and the directory basename."""
    if _is_harness_project_path(path):
        ref = _harness_project_ref(path)
        return {
            "id": ref,
            "path": str(path),
            "name": ref,
            "added_at": _now_iso(),
        }
    return {
        "id": hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12],
        "path": str(path),
        "name": path.name or str(path),
        "added_at": _now_iso(),
    }


# Harness-generated project dirs sit directly under the output root and
# carry the chat-<8hex> / proj-<8hex> naming from _default_project_dir.
_HARNESS_DIR_RE = re.compile(r"(?:chat|proj)-[0-9a-f]{8}")

# Crockford base32 alphabet (32 chars; excludes I/L/O/U so a proj- ref
# can be read aloud or typed reliably).
_HARNESS_REF_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _is_harness_project_path(path: Path) -> bool:
    """True when `path` is a harness-generated project dir directly under
    the output root (``proj-<8hex>`` or the legacy ``chat-<8hex>``)."""
    try:
        rel = path.resolve().relative_to(_output_root().resolve())
    except (OSError, ValueError, RuntimeError):
        return False
    return len(rel.parts) == 1 and bool(_HARNESS_DIR_RE.fullmatch(rel.parts[0]))


def _harness_project_ref(path: Path) -> str:
    """Stable short card ref (``proj-XXXX``, 4 base32 chars) derived from
    the SHA-1 of the path. Stable across renames of the registry entry and
    identical for the same folder, so a re-added project keeps its ref."""
    digest = hashlib.sha1(str(path).encode("utf-8")).digest()
    value = int.from_bytes(digest[:4], "big")
    suffix = "".join(
        _HARNESS_REF_ALPHABET[(value >> (5 * i)) & 0x1F] for i in range(4)
    )
    return f"proj-{suffix}"


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


def _remap_to_output_root(candidate: Path) -> Path:
    """Repair a project path recorded with a stale output-root prefix.

    The output root resolves relative to the server's CWD, which can change
    between runs (e.g. a container ``working_dir`` moved, or
    ``HARNESS_OUTPUT_ROOT`` was overridden). Projects/sessions registered under
    the old prefix (e.g. ``/app/output/chat-x``) then fall outside the allowed
    roots and every new run that selects them is rejected before it starts —
    surfacing as "project_dir is outside the allowed roots".

    Also repairs the chat- → proj- default-dir rename (UI_PRD I-13): a
    registry entry pointing at a legacy ``<root>/chat-<id8>`` dir is remapped
    to the ``<root>/proj-<id8>`` sibling whenever that sibling exists on
    disk, so sessions recorded before the rename stay attached to their
    project folder.

    We only repair the specific drift where the path is ``<X>/output/<name>`` but
    the harness now resolves its output root to a different ``<Y>/output``. This
    keeps the security boundary intact: genuinely foreign paths (e.g.
    ``/etc/secrets``) are left untouched and still rejected, while the remapped
    result always lands inside the current output root."""
    candidate = candidate.resolve()
    m = re.fullmatch(r"chat-([0-9a-f]{8})", candidate.name)
    if m:
        proj_sibling = candidate.parent / f"proj-{m.group(1)}"
        if proj_sibling.is_dir() and _is_within_allowed(proj_sibling):
            return proj_sibling
    if _is_within_allowed(candidate):
        return candidate
    if candidate.parent.name == "output":
        alt = _output_root() / candidate.name
        if _is_within_allowed(alt):
            return alt
    return candidate


@app.get("/api/fs/browse")
async def fs_browse(path: str | None = None, files: bool = False):
    """List subdirectories (and optionally files) of `path` (home when omitted)
    for the folder / file picker."""
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
        if child.name.startswith(".") or child.is_symlink():
            continue
        if child.is_dir():
            entries.append({"name": child.name, "path": str(child), "type": "dir"})
        elif files and child.is_file():
            try:
                size = child.stat().st_size
            except OSError:
                size = 0
            entries.append(
                {"name": child.name, "path": str(child), "type": "file", "size": size}
            )
    # Hide the ".." escape hatch when the parent sits outside the allowlist.
    parent = None
    if target.parent != target and _is_within_allowed(target.parent):
        parent = str(target.parent)
    return {"path": str(target), "parent": parent, "entries": entries}


@app.get("/api/fs/roots")
async def fs_roots():
    """Browsable root locations for the folder/file picker UI.

    The picker runs against the SERVER's filesystem (inside the api container
    in the dev stack), which is easy to mistake for the browser host's disks.
    Exposing the allowlist lets the UI show quick-jump chips and explain
    "outside the allowed roots" rejections concretely."""
    return {
        "home": str(Path.home().resolve()),
        "output_root": str(_output_root().resolve()),
        "roots": [str(root) for root in _allowed_roots()],
    }


# ── File search (the @-mention backend) ──────────────────────────────────────
# Two swappable backends behind a single endpoint:
#   • os_walk — zero-dependency recursive os.walk (default). Secure, adequate
#     for the active-project root (the common case).
#   • fff     — opt-in fff-search index (FILE_SEARCH_BACKEND=fff). Falls back to
#     os_walk if the wheel is missing so the service stays functional with zero
#     native deps by default.

_SEARCH_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv",
    "marketplace_cache", ".eco-attachments",
}
_SEARCH_FILE_CAP = 20_000


def _search_os_walk(q: str, root: Path, limit: int, depth: int) -> list[dict]:
    """Hand-rolled recursive search. Returns a list of
    {name, path, size, mtime}. Prunes hidden dirs, symlinks, and heavy dirs."""
    ql = q.lower()
    hits: list[dict] = []
    seen_files = 0

    def _emit(base: Path, rel_parts: tuple[str, ...]) -> None:
        nonlocal seen_files
        try:
            children = sorted(base.iterdir(), key=lambda c: c.name.lower())
        except (OSError, PermissionError):
            # A single unreadable directory must not abort the whole walk (B4):
            # skip it and let siblings continue.
            return
        for child in children:
            if seen_files >= _SEARCH_FILE_CAP:
                return
            if child.name.startswith(".") or child.name.startswith("__"):
                continue
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name in _SEARCH_SKIP_DIRS:
                    continue
                if len(rel_parts) < depth:
                    _emit(child, rel_parts + (child.name,))
                continue
            seen_files += 1
            fl = child.name.lower()
            rel = "/".join(rel_parts + (child.name,))
            if ql in fl:
                rank = 0
            elif ql in rel:
                rank = 1
            else:
                continue
            try:
                st = child.stat()
                size = st.st_size
                mtime = st.st_mtime
            except OSError:
                size = mtime = 0
            hits.append({
                "name": child.name,
                "path": str(child),
                "size": size,
                "mtime": mtime,
                "_rank": rank,
                "_rel": rel,
            })

    try:
        _emit(root, ())
    except (OSError, PermissionError):
        pass
    hits.sort(key=lambda h: (h["_rank"], h["_rel"]))
    return [
        {"name": h["name"], "path": h["path"], "size": h["size"], "mtime": h["mtime"]}
        for h in hits[:limit]
    ]


_fff_indexes: dict[Path, Any] = {}


def _search_fff(q: str, root: Path, limit: int) -> list[dict] | None:
    """Typo-tolerant / frecency-ranked search via the opt-in fff-search wheel.
    Returns None if FFF is unavailable or errors so the caller can fall back."""
    try:
        import fff  # type: ignore
    except ImportError:
        logger.warning("FILE_SEARCH_BACKEND=fff but fff-search is not installed; "
                       "falling back to os_walk")
        return None
    try:
        if root not in _fff_indexes:
            _fff_indexes[root] = fff.FFFIndex(str(root))
        index = _fff_indexes[root]
        items = index.file_search(query=q)
        out: list[dict] = []
        for item in items[:limit]:
            rel = getattr(item, "relative_path", None) or str(item)
            full = root / rel if not Path(rel).is_absolute() else Path(rel)
            try:
                st = full.stat()
                size = st.st_size
                mtime = st.st_mtime
            except OSError:
                size = mtime = 0
            out.append({
                "name": full.name,
                "path": str(full),
                "size": size,
                "mtime": mtime,
            })
        return out
    except Exception as error:  # never crash the search on a missing index
        logger.warning("fff search failed (%s); falling back to os_walk", error)
        return None


@app.get("/api/fs/search")
async def fs_search(
    q: str = "",
    root: str | None = None,
    limit: int = 50,
    depth: int = 8,
    backend: str = "os_walk",
):
    """Filename/path substring search backing the @-mention autocomplete.

    `root` defaults to the first allowed root (home); when provided it must
    resolve within the allowed roots. Returns files only:
    {root, truncated, backend, results:[{name,path,size,mtime}]}."""
    # The server owns backend selection (D1): FILE_SEARCH_BACKEND env wins, the
    # query `backend` param is only a hint. This keeps the lean-dependency
    # default in force unless an operator explicitly opts into fff.
    env_backend = (os.getenv("FILE_SEARCH_BACKEND") or "").strip().lower()
    effective = env_backend or backend or "os_walk"
    if effective not in ("os_walk", "fff"):
        effective = "os_walk"

    # Home-root walks are the heaviest path (PRD risk note): require a longer
    # query so we don't fs_walk all of $HOME on a single keystroke.
    root_explicit = bool(root)
    min_q = 2 if (not root_explicit) else 1
    if len(q) < min_q:
        return {"root": root or "", "truncated": False, "backend": effective, "results": []}
    try:
        if root_explicit:
            target = _ensure_allowed(Path(root).expanduser().resolve())
        else:
            target = _allowed_roots()[0]
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not target.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Search root is not a directory: {target}",
        )
    try:
        limit = max(1, min(int(limit), 200))
        depth = max(1, min(int(depth), 16))
    except (TypeError, ValueError):
        limit, depth = 50, 8

    results: list[dict] | None = None
    used_backend = effective
    if effective == "fff":
        results = _search_fff(q, target, limit)
        if results is None:
            used_backend = "os_walk"
    if results is None:
        results = _search_os_walk(q, target, limit, depth)
    return {
        "root": str(target),
        "truncated": len(results) >= limit,
        "backend": used_backend,
        "results": results,
    }


@app.get("/api/projects")
async def list_projects():
    """Whitelisted projects with their grouped sessions.

    ALSO returns a `legacy_nested_app_dirs` list — the detected legacy
    `--app` residue (empty when there is none). GET is report-only:
    the frontend can surface the list, and deletion happens only via
    the explicit `POST /api/projects/cleanup-legacy` endpoint.
    """
    output_root = _output_root()
    # Sweep in a worker thread: the BFS walk is disk-bound and must not
    # block the event loop while other sessions are streaming. GET is
    # report-only — deletion happens exclusively via the explicit
    # POST /api/projects/cleanup-legacy endpoint (review before delete).
    legacy_dirs = await run_in_threadpool(
        _sweep_legacy_nested_app_dirs, output_root,
    )
    if legacy_dirs:
        # Log once per request — the user can hit /api/projects/cleanup-legacy
        # to actually delete the trees. Logging the resolved paths helps the
        # user verify they are the expected ones.
        for d in legacy_dirs:
            logger.warning(
                "legacy nested --app dir detected: %s "
                "(use POST /api/projects/cleanup-legacy to remove)",
                d,
            )
    return {
        "projects": _build_project_list(),
        "legacy_nested_app_dirs": [str(d) for d in legacy_dirs],
    }


def _build_project_list() -> list[dict]:
    """Whitelisted projects with their grouped sessions.

    Only folders explicitly registered by the user (registry["projects"])
    are visible in the panel — session paths and legacy output/chat-* dirs
    are no longer materialized as projects. Sessions whose project_path
    is not whitelisted simply don't render; their records stay in the
    registry.

    Each session in the response is enriched with the trace-bookkeeping
    fields (trace_dir, trace_last_file, trace_last_error, trace_call_count)
    so the left panel can render the `ses-` chip + the hover tooltip + the
    copy-to-clipboard button WITHOUT a second round trip per session.
    Computing _session_trace_meta() is cheap (a listdir per session + at
    most one 4 KB read); for a typical project with N<=20 sessions the
    whole request is under a millisecond on warm disk.

    Response extras (UI_PRD I-8/I-10/I-13):
      • session_count / trace_count — panel badge data, no extra round trip.
      • Projects are sorted by most recent session activity (falling back
        to added_at) so the project the user touched last rises to the top.
      • Legacy harness dirs still registered under a ``chat-`` name get the
        computed ``proj-XXXX`` ref as their display name (id/path stay as
        stored so DELETE/export lookups keep working).
    """
    registry = _load_registry()
    whitelisted: dict[str, dict] = {
        entry["path"]: {**entry, "auto": False}
        for entry in registry["projects"]
    }

    grouped: dict[str, list[dict]] = {}
    for session in registry["sessions"]:
        grouped.setdefault(_session_project_path(session), []).append(session)

    result = []
    for ppath, entry in whitelisted.items():
        proj_sessions = sorted(
            grouped.get(ppath, []),
            key=lambda s: s.get("updated_at") or "",
            reverse=True,
        )
        # Enrich each session with trace meta inline. The trace-bookkeeping
        # fields are the same shape the messages endpoint already returns,
        # so the panel can render them on a GET /api/projects response too.
        enriched = [{**s, **_session_trace_meta(s)} for s in proj_sessions]
        display = {**entry}
        try:
            is_harness = _is_harness_project_path(Path(entry["path"]))
        except (OSError, RuntimeError):
            is_harness = False
        if is_harness and not str(entry.get("name", "")).startswith("proj-"):
            display["name"] = _harness_project_ref(Path(entry["path"]))
        result.append({
            **display,
            "sessions": enriched,
            "session_count": len(enriched),
            "trace_count": sum(s.get("trace_call_count") or 0 for s in enriched),
        })
    result.sort(key=_project_activity_key, reverse=True)
    return result


def _project_activity_key(project: dict) -> str:
    """Sort key: the project's most recent session update, falling back to
    when the project was added (UI_PRD I-10 — users re-open what they
    touched last, not what they added last)."""
    latest = max(
        (s.get("updated_at") or "" for s in project.get("sessions", [])),
        default="",
    )
    return latest or project.get("added_at") or ""


@app.post("/api/projects/cleanup-legacy")
async def cleanup_legacy_nested_app_dirs():
    """Delete the legacy `--app/...` nested project dirs that the
    startup sweep detected on the last GET /api/projects call.

    Safety: any --app tree whose plan.md — in the tree itself or any
    parent up to the output root — is newer than 24 h is PRESERVED
    (the user may be mid-session). Trees that contain only generated
    source from a completed/aborted run are removed.

    Returns the list of removed dirs and the list of preserved dirs.
    """
    removed, preserved = await run_in_threadpool(
        _cleanup_legacy_dirs, _output_root(),
    )
    return {"removed": removed, "preserved": preserved}


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


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Remove a project from the panel whitelist — a visual/UI operation only.

    Deletes the registry["projects"] entry and nothing else: sessions, traces,
    and the folder on disk are untouched (re-adding the folder via the browser
    restores it). Returns 409 when any session of this project is still
    running so the panel never hides live work."""
    registry = _load_registry()
    entry = next(
        (p for p in registry["projects"] if p.get("id") == project_id), None,
    )
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown project: {project_id}")
    for session in _sessions_for_project(registry, entry.get("path")):
        if session.get("status") == "running":
            raise HTTPException(
                status_code=409,
                detail="Project has a running session",
            )
    registry["projects"] = [
        p for p in registry["projects"] if p.get("id") != project_id
    ]
    _save_registry(registry)
    return {"status": "ok", "removed": project_id}


# ── Session inspection & control ─────────────────────────────────────────────
# The left panel lists sessions but the main chat area only ever shows the
# live connection's thread. These endpoints let the UI (1) replay a session's
# reconstructed transcript into the main view and (2) stop a running/suspended
# session so it can be removed from the panel.

def _find_session(registry: dict, session_id: str) -> dict | None:
    """Look up a session record by its 8-char short id."""
    for session in registry["sessions"]:
        if session.get("id") == session_id:
            return session
    return None


def _session_trace_dir(session: dict) -> Path:
    """Return the on-disk trace dir for a session.

    The minimal-first-cut naming: traces/ses-<8hex>/ (one folder per
    session, NOT per project). `session_id` is the 8-char prefix;
    `thread_id` is the full UUID when present (preferred for symmetry
    with the WebSocket layer).
    """
    raw = session.get("thread_id") or session.get("id") or ""
    short = raw[:8] if raw else "unknown"
    return _traces_root() / f"ses-{short}"


def _session_trace_dirs(session: dict) -> list[Path]:
    """Candidate trace dirs for a session, newest-prefix first.

    The minimal-first-cut renames the canonical path to ``traces/ses-<id>/``
    but legacy traces still live under ``traces/chat-<id>/`` from previous
    runs. The metadata helper scans both so the UI can show a useful
    summary regardless of when the session ran. Returns an ordered list
    of dirs that exist on disk (empty list if neither does).
    """
    raw = session.get("thread_id") or session.get("id") or ""
    short = raw[:8] if raw else "unknown"
    root = _traces_root()
    candidates = [root / f"ses-{short}", root / f"chat-{short}"]
    return [c for c in candidates if c.is_dir()]


def _session_trace_dir(session: dict) -> Path:
    """Canonical trace dir (the new ses- prefix). For the metadata helper
    that scans both new and legacy dirs, use ``_session_trace_dirs``."""
    raw = session.get("thread_id") or session.get("id") or ""
    short = raw[:8] if raw else "unknown"
    return _traces_root() / f"ses-{short}"


def _session_trace_meta(session: dict) -> dict:
    """Best-effort summary of the session's trace folder for the UI.

    Returns a small dict: trace_dir (str), trace_last_file (str|None),
    trace_last_error (str|None), trace_call_count (int). The frontend
    uses these to (a) render the trace path in the session-card hover
    tooltip, and (b) one-click jump to the failing trace file when
    the session ended in `failed` / `aborted`. Cheap (a single
    listdir + at most one file read for the last call's meta).

    Scans BOTH the new ses- dir and the legacy chat- dir so traces
    written before the rename are still discoverable.
    """
    dirs = _session_trace_dirs(session)
    tdir = _session_trace_dir(session)  # canonical for the UI label
    out: dict = {"trace_dir": str(tdir), "trace_last_file": None,
                 "trace_last_error": None, "trace_call_count": 0}
    files: list = []
    for d in dirs:
        try:
            files.extend(d.glob("*.json"))
        except OSError:
            continue
    files.sort()
    out["trace_call_count"] = len(files)
    if not files:
        return out
    last = files[-1]
    out["trace_last_file"] = str(last)
    # Read only the meta block of the last file — a few hundred bytes.
    try:
        with last.open("r", encoding="utf-8") as fh:
            chunk = fh.read(8192)
        # Lazy JSON parse: we just want the top-level "meta" object. Cheap
        # regex pulls the error / stop_reason out without a full parse —
        # fine for tooltips.
        import re as _re
        m_err = _re.search(r'"error"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', chunk)
        if m_err:
            out["trace_last_error"] = m_err.group(1)[:280]
    except (OSError, ValueError):
        pass
    return out


@app.get("/api/sessions/{session_id}/messages")
async def session_messages(session_id: str):
    """Reconstruct a session's conversation as a flat, renderable transcript.

    Reuses backend.session_export.session_turns: each turn becomes a user
    message (the question) followed by an assistant message (reasoning + the
    final/stop-tool answer), in the order they occurred. Sessions without
    usable traces yield an empty message list with the metadata intact so the
    UI can still show "no recorded transcript"."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
        raise HTTPException(status_code=400, detail="Invalid session id")
    registry = _load_registry()
    session = _find_session(registry, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Unknown session: {session_id}")

    from eco_harness.backend.session_export import session_turns, default_traces_root

    turns = session_turns(session, default_traces_root())
    messages: list[dict] = []
    for turn in turns:
        question = (turn.get("question") or "").strip()
        if question:
            messages.append({"role": "user", "text": question})
        reasoning = (turn.get("reasoning_chain") or "").strip()
        answer = (turn.get("final_answer") or "").strip()
        parts: list[str] = []
        if reasoning:
            parts.append(f"**Reasoning**\n\n{reasoning}")
        if answer:
            parts.append(answer)
        body = "\n\n".join(parts)
        if body:
            messages.append({"role": "assistant", "text": body})

    return {
        "session": {
            **{k: session.get(k) for k in (
                "id", "thread_id", "project_path", "title",
                "created_at", "updated_at", "status",
            )},
            # Minimal-first-cut: surface the trace dir + last file in every
            # session message response so the panel can render the trace
            # path on hover without a second round trip.
            **_session_trace_meta(session),
        },
        "messages": messages,
    }


@app.get("/api/sessions/{session_id}/trace")
async def session_trace(session_id: str):
    """Lightweight summary of the session's trace folder.

    Returns the trace dir, the per-call file list (newest last), and the
    meta block of the most recent file. Drives the "open trace folder"
    and "open last failing call" affordances in the project panel.
    """
    if not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
        raise HTTPException(status_code=400, detail="Invalid session id")
    registry = _load_registry()
    session = _find_session(registry, session_id)
    if session is None:
        raise HTTPException(
            status_code=404, detail=f"Unknown session: {session_id}",
        )
    meta = _session_trace_meta(session)
    files: list[dict] = []
    # Scan both the new ses-* dir and any legacy chat-* dir so a single
    # endpoint serves all sessions regardless of when they ran.
    for tdir in _session_trace_dirs(session):
        for path in sorted(tdir.glob("*.json")):
            info = {"path": str(path), "name": path.name, "size": 0,
                    "error": "", "label": "", "ts": ""}
            try:
                info["size"] = path.stat().st_size
            except OSError:
                pass
            try:
                with path.open("r", encoding="utf-8") as fh:
                    chunk = fh.read(4096)
                m_label = re.search(r'"label"\s*:\s*"([^"]+)"', chunk)
                m_err = re.search(r'"error"\s*:\s*"([^"]+)"', chunk)
                m_ts = re.search(r'"ts"\s*:\s*"([^"]+)"', chunk)
                if m_label:
                    info["label"] = m_label.group(1)
                if m_err:
                    info["error"] = m_err.group(1)[:280]
                if m_ts:
                    info["ts"] = m_ts.group(1)
            except (OSError, ValueError):
                pass
            files.append(info)
    return {**meta, "files": files}


@app.post("/api/sessions/{session_id}/abort")
async def abort_session(session_id: str):
    """Stop a running or suspended session.

    Marks the session finished in the registry (so it becomes removable from
    the panel) and, when the session still has a live WebSocket, closes that
    connection — which makes the handler's disconnect path record the abort
    too. Idempotent: re-aborting an already-finished session is a no-op."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
        raise HTTPException(status_code=400, detail="Invalid session id")
    registry = _load_registry()
    session = _find_session(registry, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Unknown session: {session_id}")

    thread_id = session.get("thread_id") or ""
    # Flip registry status so the panel stops treating it as live work.
    if session.get("status") == "running":
        try:
            _record_session_end(thread_id, Path(session.get("project_path") or "."), "aborted")
        except Exception:
            logger.exception("abort_session: failed to record end")

    # Signal the live connection (if any) to tear down.
    ws = ACTIVE_SESSIONS.get(thread_id)
    if ws is not None:
        try:
            await ws.close()
        except Exception:
            pass
        ACTIVE_SESSIONS.pop(thread_id, None)

    return {"status": "ok", "aborted": session_id}


# ── Session export (fine-tuning data) ────────────────────────────────────────
# Turns are rebuilt from traces/chat-<id8>/ by backend/session_export.py:
# JSONL = one training record per turn; TXT = human-readable labeled blocks.

_EXPORT_MEDIA_TYPES = {
    "jsonl": "application/x-ndjson",
    "txt": "text/plain; charset=utf-8",
}


def _export_format(format_param: str) -> str:
    fmt = (format_param or "").strip().lower()
    if fmt not in ("jsonl", "txt"):
        raise HTTPException(status_code=400, detail="format must be 'jsonl' or 'txt'")
    return fmt


_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _safe_id(value: str, fallback: str = "x") -> str:
    """Fold an externally supplied id (e.g. the ``thread_id`` query param) to
    a path-safe charset so it can never carry ``/`` or ``..`` into a filename
    or directory built from it."""
    folded = _SAFE_ID_RE.sub("-", value or "").strip("-")
    return folded or fallback


def _session_project_path(session: dict) -> str:
    """Association key: a session belongs to the project whose registry path
    matches its ``project_path``; the empty string groups orphaned sessions."""
    return session.get("project_path") or ""


def _sessions_for_project(registry: dict, project_path: str) -> list[dict]:
    """All sessions of one project, most recently updated first."""
    sessions = [
        s for s in registry["sessions"]
        if _session_project_path(s) == project_path
    ]
    return sorted(
        sessions, key=lambda s: s.get("updated_at") or "", reverse=True,
    )


def _project_sessions(registry: dict, project: dict) -> list[dict]:
    """The project's sessions, most recently updated first."""
    return _sessions_for_project(registry, project.get("path"))


def _export_streaming_response(
    project_session_pairs: list[tuple[dict, list[dict]]], fmt: str, filename: str,
):
    """Stream the export without blocking the event loop: each project's trace
    history is built in a worker thread and streamed incrementally, so memory
    stays bounded to a single project and live websockets are not frozen."""

    async def _iter():
        for index, (project, sessions) in enumerate(project_session_pairs):
            export = await run_in_threadpool(
                build_project_export, project, sessions, default_traces_root(),
            )
            if fmt == "jsonl":
                for line in iter_project_jsonl(export):
                    yield line + "\n"
            else:
                if index:
                    yield "\n"
                yield render_export_text(export)

    return StreamingResponse(
        _iter(),
        media_type=_EXPORT_MEDIA_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/projects/{project_id}/export")
async def export_project(project_id: str, format: str = "jsonl"):
    """Export one project's sessions as JSONL/TXT (question, context,
    reasoning chain, final answer per turn)."""
    fmt = _export_format(format)
    registry = _load_registry()
    project = next(
        (p for p in registry["projects"] if p.get("id") == project_id), None,
    )
    if project is None:
        raise HTTPException(status_code=404, detail=f"Unknown project: {project_id}")
    filename = (
        f"{safe_export_name(project.get('name') or 'project')}-sessions.{fmt}"
    )
    return _export_streaming_response(
        [(project, _project_sessions(registry, project))], fmt, filename,
    )


@app.get("/api/export/all")
async def export_all_projects(format: str = "jsonl"):
    """Export every whitelisted project's sessions as one combined file."""
    fmt = _export_format(format)
    registry = _load_registry()
    projects = sorted(
        registry["projects"], key=lambda p: p.get("added_at") or "", reverse=True,
    )
    pairs = [(p, _project_sessions(registry, p)) for p in projects]
    return _export_streaming_response(
        pairs, fmt, f"harness-sessions-all.{fmt}",
    )


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
        # Panel visibility is whitelist-only: a session against an
        # unregistered dir is recorded here but never auto-added to
        # registry["projects"] — the folder shows up once explicitly added.
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
    # End-of-session cleanup: residue from a pre-fix run inside THIS
    # session's own project dir is now stale (the session either
    # succeeded or was aborted; either way the work has moved on).
    # Scoped to the session's own project dir — never the output root,
    # so other (possibly still-running) sessions' trees are untouched.
    try:
        removed, _preserved = _cleanup_legacy_dirs(Path(project_dir).resolve())
        for d in removed:
            logger.info("end-of-session legacy cleanup removed: %s", d)
    except Exception:
        logger.exception("end-of-session legacy cleanup failed")


_LEGACY_PLAN_GUARD_SECONDS = 24 * 3600


def _recent_plan_md(candidate: Path, stop_root: Path) -> bool:
    """24h plan.md safety guard for legacy cleanup.

    A candidate is PRESERVED when a `plan.md` newer than the guard
    window exists in the candidate itself OR any of its parents up to
    the sweep's scan root — in the real ACOM layout plan.md lives at
    the chat-dir root (`output/chat-<id>/plan.md`), not inside `--app`,
    so checking only the candidate would never protect a live session.
    """
    stop = stop_root.resolve() if stop_root else None
    now = time.time()
    d = candidate
    while True:
        plan = d / "plan.md"
        try:
            if plan.is_file() and (now - plan.stat().st_mtime) < _LEGACY_PLAN_GUARD_SECONDS:
                return True
        except OSError:
            # TOCTOU (deleted/locked between is_file and stat):
            # treat as stale rather than crashing the caller.
            pass
        if stop is not None:
            try:
                parent = d.parent.resolve()
            except OSError:
                return False
            if parent == d or not parent.is_relative_to(stop):
                return False
            d = parent
        else:
            parent = d.parent
            if parent == d:
                return False
            d = parent


def _cleanup_legacy_dirs(scan_root: Path) -> tuple[list[str], list[str]]:
    """Single implementation of legacy `--app` residue cleanup, shared
    by POST /api/projects/cleanup-legacy and the scoped end-of-session
    helper. Sweeps `scan_root`, deletes each candidate subject to the
    24 h plan.md guard, and returns (removed, preserved) path lists so
    every call site reports identical behavior."""
    try:
        legacy_dirs = _sweep_legacy_nested_app_dirs(scan_root)
    except Exception:
        logger.exception("legacy --app sweep failed for %s", scan_root)
        return [], []
    removed: list[str] = []
    preserved: list[str] = []
    for d in legacy_dirs:
        if _recent_plan_md(d, scan_root):
            preserved.append(str(d))
            continue
        try:
            shutil.rmtree(d)
            removed.append(str(d))
        except OSError as e:
            preserved.append(f"{d} (rmtree failed: {e})")
    return removed, preserved


def cleanup_legacy_nested_app_dirs_thread_safe(scan_root: Path) -> int:
    """Callable from the server's own code paths (no FastAPI request
    context). Returns the number of trees removed. Delegates to the
    shared _cleanup_legacy_dirs implementation (same sweep, same 24 h
    plan.md guard, same error handling as the cleanup endpoint)."""
    removed, _preserved = _cleanup_legacy_dirs(scan_root)
    return len(removed)
    return removed



@app.get("/health")
async def health_check():
    return {"status": "ok", "protocol": "chat"}


@app.get("/config")
async def harness_config():
    # Serves the in-memory config. The global is swapped ONLY by
    # PUT /config/workspace (after a validated save) — never mid-request — so
    # in-flight WS pipelines cannot observe a config that changes under them.
    # Out-of-band edits to workspace.yaml show up on the next save or restart.
    return {
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
                "permissions": spec.permissions.model_dump(),
            }
            for name, spec in HARNESS_CONFIG.roles.items()
        },
        # Harness-level permission defaults. Per-role resolved policies are
        # already serialized under roles[name].permissions — not duplicated
        # here.
        "permissions": {
            "defaults": HARNESS_CONFIG.default_permissions.model_dump(),
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
        "providers": {
            name: profile.model_dump()
            for name, profile in HARNESS_CONFIG.providers.items()
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
    # User-managed model registry: named profiles merged over config/models.yaml
    # on next load (see load_config). Shape mirrors ModelProfile plus the
    # profile name as the mapping key; a None value REMOVES the profile.
    models: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
    # User-defined LLM endpoints (local inference servers, self-hosted
    # gateways). Named and referenced by ModelProfile.provider; a None value
    # REMOVES the provider.
    providers: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
    # LLM permission policy: {"defaults": {...}, "roles": {<role>: {...}}}.
    permissions: dict[str, Any] = Field(default_factory=dict)


def _validate_workspace_sections(provided: dict[str, Any]) -> None:
    """Reject settings that would break (or poison) the next config load.

    Each provided section is parsed through the same pydantic models the
    loader uses, so a bad payload is answered with a 400 at save time instead
    of a crashed harness at next restart.
    """
    from eco_harness.agent.config.loader import LanguageSpec, ModelProfile, PermissionSpec, ProviderProfile, RoleSpec
    from pydantic import ValidationError

    try:
        for role_spec in (provided.get("roles") or {}).values():
            RoleSpec(**role_spec)
        for language_spec in (provided.get("languages") or {}).values():
            LanguageSpec(**language_spec)
        for profile in (provided.get("models") or {}).values():
            if profile is not None:
                ModelProfile(**profile)
        for provider in (provided.get("providers") or {}).values():
            if provider is not None:
                ProviderProfile(**provider)
        permissions = provided.get("permissions") or {}
        defaults = permissions.get("defaults")
        if defaults is not None:
            PermissionSpec(**defaults)
        for role_delta in (permissions.get("roles") or {}).values():
            PermissionSpec(**role_delta)
    except (ValidationError, TypeError) as error:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace settings: {error}",
        ) from error


@app.put("/config/workspace")
async def update_workspace_config(request: WorkspaceConfigRequest):
    global HARNESS_CONFIG
    # Trust model: this is a LOCAL dev harness — the whole API (including the
    # chat WS, which runs agents with full tool access) is bound to
    # 127.0.0.1 without auth by design. This endpoint is the single writer of
    # workspace.yaml, validates every section against the loader's schema,
    # and merges into the existing file so sections a client does not send
    # (e.g. harness) are preserved. Exposing the port beyond localhost
    # requires a fronting proxy with auth for the ENTIRE API, not just this
    # route.
    workspace_path = HARNESS_CONFIG.workspace_override
    if workspace_path is None:
        raise HTTPException(status_code=500, detail="Workspace config path is unavailable")

    # exclude_unset: only sections present in the request body are merged.
    # An absent section keeps its existing workspace value; an explicitly
    # empty section (e.g. models: {}) clears it.
    provided = request.model_dump(exclude_unset=True)
    _validate_workspace_sections(provided)

    import yaml

    existing: dict[str, Any] = {}
    if workspace_path.exists():
        try:
            loaded = yaml.safe_load(workspace_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except yaml.YAMLError:
            logger.warning("existing workspace.yaml is unparseable; replacing provided sections")
    existing.update(provided)

    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    workspace_path.write_text(
        yaml.safe_dump(existing, sort_keys=False),
        encoding="utf-8",
    )

    # Single swap point for the global: reload OFF the event loop and only
    # publish the new config if it parses — a rejected save never leaves a
    # broken in-memory state behind.
    try:
        HARNESS_CONFIG = await asyncio.to_thread(
            load_config,
        )
    except Exception as error:
        logger.exception("workspace config reload failed after save")
        raise HTTPException(
            status_code=500,
            detail=f"Settings were written but failed to load: {error}",
        ) from error
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
        index_path = _marketplace_index_path()
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
    index_path = _marketplace_index_path()
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="Marketplace RAG index is unavailable")
    return FileResponse(
        index_path,
        media_type="application/vnd.sqlite3",
        filename="marketplace_index.sqlite",
    )


def _marketplace_index_path() -> Path:
    return paths.marketplace_index_path()


def _fetch_summary_path() -> Path:
    """marketplace_cache/_fetch_summary.json — written by
    scripts/fetch_marketplace.py on every marketplace pull."""
    return paths.marketplace_cache_root() / "_fetch_summary.json"


@app.get("/rag/status")
async def rag_status():
    """Index summary for the settings panel: size, chunk count, last import."""
    index_path = _marketplace_index_path()
    if not index_path.is_file():
        return {
            "available": False,
            "chunks": 0,
            "size_bytes": 0,
            "last_import": None,
            "last_updated": None,
        }

    size_bytes = index_path.stat().st_size

    def _read() -> dict:
        import sqlite3

        connection = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
        try:
            try:
                chunks = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            except sqlite3.Error:
                chunks = 0
            try:
                row = connection.execute(
                    "SELECT value FROM meta WHERE key = 'last_import'",
                ).fetchone()
                last_import = json.loads(row[0]) if row and row[0] else None
            except (sqlite3.Error, ValueError):
                last_import = None
        finally:
            connection.close()

        # Last full update of the marketplace data (UI: "Last updated" under
        # the Update Index button): the newer of the index file mtime (any
        # build/merge/import) and the fetch summary (last marketplace pull).
        markers = [index_path, _fetch_summary_path()]
        last_updated = max(
            (m.stat().st_mtime for m in markers if m.is_file()), default=0,
        )
        last_updated_iso = (
            datetime.fromtimestamp(last_updated, tz=timezone.utc).isoformat()
            if last_updated else None
        )
        return {
            "available": True,
            "chunks": chunks,
            "size_bytes": size_bytes,
            "last_import": last_import,
            "last_updated": last_updated_iso,
        }

    try:
        return await asyncio.to_thread(_read)
    except Exception:
        logger.exception("RAG status read failed")
        return {"available": True, "chunks": 0, "size_bytes": size_bytes, "last_import": None}


# ── Marketplace index update (Settings → RAG "Update Index") ─────────────────
# Runs the two existing maintenance scripts sequentially:
#   1. scripts/fetch_marketplace.py   — re-pulls component DEVKITs into
#      marketplace_cache/ (updating ecoPackage.json + _profiles/<name>.json)
#   2. scripts/build_marketplace_index.py — rebuilds the sqlite vector index
#      (marketplace_index.sqlite) from the refreshed cache
# Both are long-running (fetch is network-bound, build embeds ~1200 chunks),
# so the work happens in a daemon thread and the UI polls the job status.
_RAG_UPDATE_STEPS = [
    ("fetch_marketplace", "scripts/fetch_marketplace.py"),
    ("build_index", "scripts/build_marketplace_index.py"),
]
_RAG_UPDATE_LOG_LINES = 200
_RAG_UPDATE_STEP_TIMEOUT = 1800  # seconds per script before it is killed

_rag_update_lock = threading.Lock()
_rag_update_job: Dict[str, Any] = {"state": "idle"}


def _rag_update_finish(state: str, error: str | None = None) -> None:
    with _rag_update_lock:
        _rag_update_job.update({
            "state": state,
            "finished_at": _now_iso(),
            "error": error,
        })


def _rag_update_append_log(line: str) -> None:
    with _rag_update_lock:
        tail: List[str] = _rag_update_job.setdefault("log_tail", [])
        tail.append(line.rstrip())
        del tail[:-_RAG_UPDATE_LOG_LINES]


def _run_rag_update() -> None:
    repo_root = paths.repo_root()
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    index_path = _marketplace_index_path()
    try:
        for step, script in _RAG_UPDATE_STEPS:
            with _rag_update_lock:
                _rag_update_job["step"] = step
            script_path = repo_root / script
            if not script_path.is_file():
                raise RuntimeError(f"Script not found: {script}")
            # build_marketplace_index.py without flags skips when the index
            # already exists — update runs must use --merge (in-place, only
            # new/changed chunks, user imports kept) for an existing index,
            # and a plain first build when there is none.
            step_args = ["--merge"] if step == "build_index" and index_path.is_file() else []
            try:
                process = subprocess.Popen(
                    [sys.executable, str(script_path), *step_args],
                    cwd=str(repo_root),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            except OSError as error:
                raise RuntimeError(f"Failed to start {script}: {error}") from error
            try:
                assert process.stdout is not None
                for line in process.stdout:
                    _rag_update_append_log(line)
                returncode = process.wait(timeout=_RAG_UPDATE_STEP_TIMEOUT)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise RuntimeError(f"{script} timed out after {_RAG_UPDATE_STEP_TIMEOUT}s")
            if returncode != 0:
                with _rag_update_lock:
                    last_lines = _rag_update_job.get("log_tail", [])[-5:]
                raise RuntimeError(
                    f"{script} exited with code {returncode}: "
                    + " | ".join(last_lines)
                )
        _rag_update_finish("success")
    except Exception as error:
        logger.exception("RAG marketplace index update failed")
        _rag_update_finish("failed", str(error))


@app.post("/rag/update-index")
async def start_rag_update():
    """Kick off the fetch → rebuild pipeline for the marketplace RAG index."""
    with _rag_update_lock:
        if _rag_update_job.get("state") == "running":
            raise HTTPException(status_code=409, detail="Index update is already running")
        _rag_update_job.clear()
        _rag_update_job.update({
            "state": "running",
            "step": None,
            "started_at": _now_iso(),
            "finished_at": None,
            "error": None,
            "log_tail": [],
        })
    threading.Thread(target=_run_rag_update, daemon=True, name="rag-update").start()
    return {"status": "started"}


@app.get("/rag/update-index/status")
async def rag_update_status():
    """Poll the marketplace index update job (state, current step, log tail)."""
    with _rag_update_lock:
        snapshot = {**_rag_update_job, "log_tail": list(_rag_update_job.get("log_tail", []))}
    return snapshot


# ── Marketplace token (Settings → RAG) ───────────────────────────────────────
# scripts/fetch_marketplace.py reads ECO_API_TOKEN from the environment. The
# default comes from .env; these endpoints let the user set or replace it
# from the UI. The value is applied to the RUNNING process env (so the next
# update job's subprocesses inherit it) and persisted to the repo .env. It
# is never echoed back — only a masked preview is returned.

class RagTokenUpdate(BaseModel):
    token: str = ""


def _env_file_path() -> Path:
    """Dev checkout: <repo>/.env. Installed wheel: $ECO_HOME/.env."""
    if paths.is_dev_checkout():
        return paths.repo_root() / ".env"
    return paths.eco_home() / ".env"


def _mask_token(token: str) -> str | None:
    if not token:
        return None
    return f"••••{token[-4:]}" if len(token) >= 8 else "••••"


def _upsert_env_file(key: str, value: str | None) -> None:
    """Set KEY=value in the repo .env (replace or append). value=None removes
    the line. Every other line is preserved verbatim."""
    env_path = _env_file_path()
    lines: List[str] = []
    if env_path.is_file():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    prefix = f"{key}="
    lines = [line for line in lines if not line.strip().startswith(prefix)]
    if value:
        lines.append(f"{key}={value}")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    # Secrets (API keys, tokens) live in this file — keep it user-only even
    # if it was created world-readable by an older run.
    try:
        env_path.chmod(0o600)
    except OSError:
        pass


@app.get("/rag/token")
async def get_rag_token():
    """Whether a marketplace token is configured + a masked preview."""
    token = os.getenv("ECO_API_TOKEN", "")
    return {"configured": bool(token), "masked": _mask_token(token)}


@app.put("/rag/token")
async def set_rag_token(payload: RagTokenUpdate):
    """Set (or clear with an empty token) the marketplace token at runtime
    and persist it to the repo .env for future server starts."""
    token = payload.token.strip()
    if token:
        os.environ["ECO_API_TOKEN"] = token
    else:
        os.environ.pop("ECO_API_TOKEN", None)
    try:
        await asyncio.to_thread(_upsert_env_file, "ECO_API_TOKEN", token or None)
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Token applied for this session but could not be persisted "
                f"to .env: {error}"
            ),
        ) from error
    return {"configured": bool(token), "masked": _mask_token(token)}


# ── First-run setup wizard (/setup) ──────────────────────────────────────────
# The wizard is purely opt-in convenience: missing keys NEVER block install or
# app launch (the harness degrades to preflight-style warnings instead). It
# validates the OpenRouter key with a live minimal call, writes the chosen
# values into the .env the server loads (repo .env on a dev checkout,
# $ECO_HOME/.env installed), and mirrors them into the running process env.
# Precedence stays: .env < process env — existing env vars always win.

class SetupConfigRequest(BaseModel):
    openrouter_key: str = ""
    eco_token: str = ""
    llm_model: str | None = None
    embeddings_model: str | None = None


@app.get("/api/setup/status")
async def setup_status():
    """What the wizard needs, what is configured, where config is stored."""
    return {
        "configured": bool(os.getenv("OPENAI_API_KEY", "")),
        "items": {
            "openrouter_key": {
                "label": "OpenRouter API key",
                "required": True,
                "configured": bool(os.getenv("OPENAI_API_KEY", "")),
                "masked": _mask_token(os.getenv("OPENAI_API_KEY", "")),
            },
            "eco_token": {
                "label": "EcoOS marketplace token",
                "required": False,
                "configured": bool(os.getenv("ECO_API_TOKEN", "")),
                "masked": _mask_token(os.getenv("ECO_API_TOKEN", "")),
            },
            "llm_model": {
                "label": "LLM model",
                "required": False,
                "configured": bool(os.getenv("LLM_MODEL", "")),
                "masked": None,
            },
        },
        "env_file": str(_env_file_path()),
        "skippable": True,
    }


async def _validate_openrouter_key(key: str, base_url: str) -> None:
    """Live minimal OpenRouter call — rejects typos at setup time."""
    import httpx

    url = base_url.rstrip("/") + "/key"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                url, headers={"Authorization": f"Bearer {key}"},
            )
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach OpenRouter ({base_url}): {error}",
        ) from error
    if response.status_code == 401:
        raise HTTPException(
            status_code=400, detail="OpenRouter rejected this key (401).",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail=f"OpenRouter key check failed (HTTP {response.status_code}).",
        )


@app.post("/api/setup/config")
async def setup_config(payload: SetupConfigRequest):
    """Validate + persist wizard values. Skippable by design: an empty body
    simply reports current status."""
    updated: list[str] = []
    key = payload.openrouter_key.strip()
    if key:
        base_url = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
        await _validate_openrouter_key(key, base_url)
        os.environ["OPENAI_API_KEY"] = key
        await asyncio.to_thread(_upsert_env_file, "OPENAI_API_KEY", key)
        updated.append("OPENAI_API_KEY")
    token = payload.eco_token.strip()
    if token:
        os.environ["ECO_API_TOKEN"] = token
        await asyncio.to_thread(_upsert_env_file, "ECO_API_TOKEN", token)
        updated.append("ECO_API_TOKEN")
    if payload.llm_model and payload.llm_model.strip():
        os.environ["LLM_MODEL"] = payload.llm_model.strip()
        await asyncio.to_thread(_upsert_env_file, "LLM_MODEL", payload.llm_model.strip())
        updated.append("LLM_MODEL")
    if payload.embeddings_model and payload.embeddings_model.strip():
        os.environ["EMBEDDINGS_MODEL"] = payload.embeddings_model.strip()
        await asyncio.to_thread(
            _upsert_env_file, "EMBEDDINGS_MODEL", payload.embeddings_model.strip(),
        )
        updated.append("EMBEDDINGS_MODEL")
    return {"status": "ok", "updated": updated}


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
    from eco_harness.agent.main import get_model
    profile = config.models.get("cheap_fast")
    if profile is None:
        return None
    try:
        return get_model(profile, role=None, providers=config.providers)
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
    from eco_harness.agent.pi_ai.types import Context, UserMessage, SimpleStreamOptions
    from eco_harness.agent.pi_ai.stream import complete
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


async def _chat_reply(
    user_req: str,
    model,
    attached_ctx: str | None = None,
    trace_dir: Path | None = None,
    call_no: int = 0,
) -> str:
    """One-shot direct answer for plain chat questions (no pipeline).

    When `trace_dir` is given the raw request/response pair is persisted via
    ``write_call_trace`` as a ``NNN-chat.json`` file (same convention as
    pipeline calls) so plain-chat turns show up in session exports. The file's
    ``NNN`` sequence is assigned by ``write_call_trace`` from the on-disk file
    count; ``call_no`` is recorded in the trace metadata for correlation."""
    from eco_harness.agent.pi_ai.types import Context, UserMessage, SimpleStreamOptions
    from eco_harness.agent.pi_ai.stream import complete
    from eco_harness.agent.internal.call_trace import write_call_trace
    user_msg = user_req
    if attached_ctx:
        user_msg = attached_ctx + user_msg
    ctx = Context(
        systemPrompt=_CHAT_ANSWER_SYS,
        messages=[UserMessage(content=user_msg, timestamp=0)],
    )
    msg = await complete(
        model, ctx, SimpleStreamOptions(reasoning="low", maxTokens=2000)
    )
    if trace_dir is not None:
        # write_call_trace never raises — observability must not break replies.
        write_call_trace(
            trace_dir=trace_dir,
            label="chat",
            call_no=call_no,
            iteration=0,
            model_id=getattr(model, "id", "") or "",
            request_context=ctx,
            response=msg,
            error="",
        )
    return _msg_text(msg)


# Map of (os, arch) -> the GID_IEcoSystem_<arch> macro name defined in
# marketplace_cache/Eco.Core1/SharedFiles/IEcoSystem1.h. The macro is
# selected at build time via -DECO_<OS> -DECO_<ARCH>; the seed block
# surfaces the right name so the architect never has to grep for it.
# NOTE: when the GID is not in the table we fall back to a generic
# message and ask the architect to read IEcoSystem1.h themselves.
_TARGET_GID_MACRO = {
    ("Linux",   "x86_64"):     "GID_IEcoSystem_x86_64",
    ("Linux",   "x86"):        "GID_IEcoSystem_x86_32",
    ("Linux",   "arm64"):      "GID_IEcoSystem_AARCH64",
    ("Linux",   "arm64-v8a"):  "GID_IEcoSystem_AARCH64",
    ("Linux",   "rv64gcv"):    "GID_IEcoSystem_RV64",
    ("Linux",   "rv32"):       "GID_IEcoSystem_RV32",
    ("Linux",   "mips64"):     "GID_IEcoSystem_MIPS64",
    ("Linux",   "mips"):       "GID_IEcoSystem_MIPS",
    ("Windows", "x86_64"):     "GID_IEcoSystem_x86_64",
    ("Windows", "x86"):        "GID_IEcoSystem_x86_32",
    ("Windows", "arm64"):      "GID_IEcoSystem_AARCH64",
    ("Mac",     "x86_64"):     "GID_IEcoSystem_x86_64",
    ("Mac",     "arm64"):      "GID_IEcoSystem_AARCH64",
    ("iOS",     "arm64"):      "GID_IEcoSystem_AARCH64",
    ("iOS",     "x86_64"):     "GID_IEcoSystem_x86_64",
    ("Android", "arm64-v8a"):  "GID_IEcoSystem_AARCH64",
    ("Android", "x86_64"):     "GID_IEcoSystem_x86_64",
    ("Android", "x86"):        "GID_IEcoSystem_x86_32",
    ("Android", "armeabi-v7a"): "GID_IEcoSystem_ARM",
    ("Android", "mips64"):     "GID_IEcoSystem_MIPS64",
    ("Android", "mips"):       "GID_IEcoSystem_MIPS",
    ("EcoOS",   "x86_64"):     "GID_IEcoSystem_x86_64",
}


# Map of (os, arch) -> the GID suffix embedded in the Eco.System1
# unikernel `.a` filename. The on-disk file is
# `lib000000000000000000000000<HEX8>.a` and the GID suffix is NOT
# always `53595333` ("SYS3") — the legacy Android mips / armeabi
# targets ship the older SYS1 (`…53595331.a`) and SYS2
# (`…53595332.a`) variants. Getting this wrong produces a non-
# existent path in the architect's plan and a link error in the
# coder. Discovered by enumerating
# `marketplace_cache/Eco.System1/BuildFiles/*/*/<variant>/`.
_SYSTEM1_GID = {
    # SYS3 (main modern unikernel — used by every x86_64, arm64,
    # rv64gcv, iOS, Mac, Linux, and the new Android arm64-v8a / x86_64).
    ("Linux",   "x86_64"):     "53595333",
    ("Linux",   "arm64-v8a"):  "53595333",
    ("Linux",   "rv64gcv"):    "53595333",
    ("Windows", "x86_64"):     "53595333",
    ("Mac",     "x86_64"):     "53595333",
    ("Mac",     "arm64"):      "53595333",
    ("iOS",     "arm64"):      "53595333",
    ("iOS",     "x86_64"):     "53595333",
    ("Android", "arm64-v8a"):  "53595333",
    ("Android", "x86_64"):     "53595333",
    # SYS2 (Android armeabi-v7a / x86 / mips64).
    ("Android", "armeabi-v7a"): "53595332",
    ("Android", "x86"):        "53595332",
    ("Android", "mips64"):     "53595332",
    # SYS1 (legacy Android mips / armeabi).
    ("Android", "mips"):       "53595331",
    ("Android", "armeabi"):    "53595331",
}


def _resolve_target_triple(payload: dict) -> dict:
    """Pull and normalise the user-selected target triple from a request.

    The chat frame is expected to send `target_triple: {os, arch,
    build_variant}` (see `config/UI` schema in the frontend). For backward
    compat, accept the legacy `target` shorthand. Default to Linux
    x86_64 StaticRelease when the UI has not sent a value yet — the
    architect's plan validator will still flag a missing target-triple
    block if the seed is empty.
    """
    tt = payload.get("target_triple")
    if not isinstance(tt, dict):
        legacy = payload.get("target")
        tt = legacy if isinstance(legacy, dict) else {}
    os_name = (tt.get("os") or "Linux").strip() or "Linux"
    arch = (tt.get("arch") or "x86_64").strip() or "x86_64"
    variant = (tt.get("build_variant") or tt.get("variant") or "StaticRelease").strip() or "StaticRelease"
    if variant not in ("StaticRelease", "DynamicRelease"):
        variant = "StaticRelease"
    return {"os": os_name, "arch": arch, "build_variant": variant}


def _target_triple_block(target: dict) -> str:
    """Seed block: user-selected target triple (OS / arch / build_variant)."""
    os_name = target.get("os", "Linux")
    arch = target.get("arch", "x86_64")
    variant = target.get("build_variant", "StaticRelease")
    gid_macro = _TARGET_GID_MACRO.get((os_name, arch))
    gid_note = (
        f"  GID_IEcoSystem macro for this triple: `{gid_macro}` "
        f"(selected at Eco.Core1 build time via -DECO_{os_name.upper()} -DECO_{arch.upper().replace('-V8A','_V8A')})\n"
        if gid_macro else
        f"  WARNING: no known GID_IEcoSystem_<arch> macro for {os_name}/{arch} — "
        "the plan_validator will BLOCK the handoff. Ask the user to pick a "
        "supported target triple from the chat frame.\n"
    )
    return (
        f"=== Target triple (user-selected in the chat frame) ===\n"
        f"  OS            : {os_name}\n"
        f"  arch          : {arch}\n"
        f"  build_variant : {variant}\n"
        f"{gid_note}"
        f"\n"
    )


def _pre_resolved_identifiers_block(
    target: dict,
    marketplace_cache_root: Path,
) -> str:
    """Seed block: identifiers the architect would otherwise have to grep for.

    These are facts the harness knows deterministically (from the marketplace
    cache layout, the Eco.Core1 GID table, the Eco.System1 unikernel
    convention). The architect and coder must use them verbatim — do not
    re-derive. Without this block, the prior Celsius->Fahrenheit session
    (`chat-1ca5b8f4`) spent two tool calls and 1 691 reasoning tokens
    re-discovering the same facts.
    """
    os_name = target["os"]
    arch = target["arch"]
    variant = target["build_variant"]
    # The folder name for arm64 on Linux uses the Android-style "arm64-v8a"
    # suffix; on Mac/iOS it's "arm64". Map the arch value to the on-disk
    # directory name the marketplace ships.
    build_dir_arch = {
        "x86_64": "x86_64",
        "x86": "x86",
        "arm64": "arm64",
        "arm64-v8a": "arm64-v8a",
        "rv64gcv": "rv64gcv",
        "mips64": "mips64",
        "mips": "mips",
    }.get(arch, arch)

    cache = marketplace_cache_root.resolve()
    # Pick the right GID for the target triple. The GID is embedded in
    # the `.a` filename and is NOT always `53595333` ("SYS3") — see
    # `_SYSTEM1_GID` for the per-(os,arch) mapping. When the target is
    # not in the table (rare; e.g. a future platform), we list the
    # directory for the architect and tell them to pick the only `.a`.
    system1_gid = _SYSTEM1_GID.get((os_name, arch))
    if system1_gid is not None:
        system1_lib = (
            f"{cache}/Eco.System1/BuildFiles/{os_name}/{build_dir_arch}/{variant}/"
            f"lib000000000000000000000000{system1_gid}.a"
        )
        system1_lib_note = ""
    else:
        system1_lib = (
            f"{cache}/Eco.System1/BuildFiles/{os_name}/{build_dir_arch}/{variant}/"
            "lib<UNKNOWN_GID>.a"
        )
        system1_lib_note = (
            "\n  NOTE: the (os, arch)=(" + os_name + ", " + arch + ") triple is not in\n"
            "  the per-target `_SYSTEM1_GID` table — the path above uses\n"
            "  `lib<UNKNOWN_GID>.a` as a placeholder. The architect MUST\n"
            "  list_dir this directory, read the only `.a` filename, and\n"
            "  paste the GID suffix into the plan before calling to_coder.\n"
        )
    core1_shared = f"{cache}/Eco.Core1/SharedFiles"
    # Default to the well-known x86_64 line; for other arches the
    # architect must read the matching line (the C skill tells them to).
    gid_macro = _TARGET_GID_MACRO.get((os_name, arch), "GID_IEcoSystem_x86_64")
    gid_bytes_default = (
        "{ 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, "
        "0x00, 0x00, 0x00, 0x00, 0x86, 0x64, 0x03, 0x00} }"  # x86_64
    )

    return (
        "=== Pre-resolved identifiers (USE VERBATIM — do not re-derive) ===\n"
        "Eco.System1 unikernel library (NOT an ACOM component — no CID, no\n"
        "factory symbol, never registered on the bus; just linked). It is a\n"
        "unikernel that ships a minimal ACOM microkernel with the Interface Bus\n"
        "built-in as its main, passive code path; the bus itself has no CID\n"
        "either (passive infrastructure, no compute process), so neither it nor\n"
        "the unikernel self-registers. The application code (EcoMain glue)\n"
        "RegisterComponents the actually-running ACOM components on top of it.\n"
        "  static library to LINK (not pull, not register) :\n"
        "    " + system1_lib + "\n" + system1_lib_note +
        "  Optional runtime services (queried via the bus with the IIDs\n"
        "  from the System1 SharedFiles headers — never via a CID):\n"
        "    IID_IEcoSystemInformation1 = {0x01, 0x10, {0x00, 0x00, 0x00,\n"
        "      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,\n"
        "      0x00, 0x01, 0xFF}}\n"
        "    IID_IEcoCommandArguments1 = {0x01, 0x10, {0x00, 0x00, 0x00,\n"
        "      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,\n"
        "      0x00, 0x01, 0x10}}\n"
        "\n"
        "Eco.Core1 (the mandatory base devkit, NOT a pullable component —\n"
        "its files are in the eco_framework tree and the coder includes\n"
        "from them; its `uguid` in the profile is 000000000000000000000000000000AA):\n"
        "  SharedFiles dir : " + core1_shared + "\n"
        "  IEcoSystem1     : declared there; use the macro `GID_IEcoSystem` in "
        "EcoMain.c (it expands to the arch-specific GID at compile time).\n"
        "  GID for the target triple : `" + gid_macro + "`\n"
        "  Default UGUID bytes for x86_64 (other arches — read the matching line "
        "in " + core1_shared + "/IEcoSystem1.h and quote the line number in the plan):\n"
        "    " + gid_bytes_default + "\n"
        "\n"
    )


def _workspace_header(
    project_dir: Path,
    marketplace_cache_root: Path,
    target: dict | None = None,
) -> str:
    """Prefix every agent seed with a workspace orientation block.

    The block tells the model four things:
      1. Where it's working — absolute paths for project_dir AND the
         read-only marketplace_cache.
      2. How to explore — grep / glob / read examples (claude-code-style
         primitives that hide the absolute-path detail under a
         basename-prefix anchoring rule).
      3. That repeating an identical tool call wastes an iteration.
      4. The user-selected target triple (OS / arch / build_variant) and
         the pre-resolved identifiers (Eco.System1 library path, GID
         macro, Eco.Core1 base dir) the architect would otherwise have
         to re-derive.

    Without (1)-(3), coder previously burned 30+ iterations on
    path-guessing list_dir('.') / list_dir('/') — see project path
    semantics. Without (4), the prior Celsius→Fahrenheit session
    (`chat-1ca5b8f4`) spent 2 tool calls and 1 691 reasoning tokens on
    exactly that re-derivation.
    """
    target = target or {"os": "Linux", "arch": "x86_64", "build_variant": "StaticRelease"}
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
        + _target_triple_block(target)
        + _pre_resolved_identifiers_block(target, marketplace_cache_root)
    )


# ── Attachment delivery (session-scoped user context) ────────────────────────
# Small text files are inlined into the prompt; large text files and images are
# copied into project_dir/.eco-attachments and referenced by path so the agent
# can read them on demand. See COMMANDS_PRD.md §3.5.

ATTACH_INLINE_LIMIT = 40_000         # per-file inline cap (bytes)
ATTACH_TOTAL_INLINE_LIMIT = 200_000  # session-wide inline cap (bytes)
ATTACH_MAX_CONTENT = 25_000_000       # hard cap on pasted disk content (B6)


def _safe_attach_name(name: str) -> str:
    """Strip directory components / make a filename safe for att_dir writes."""
    clean = Path(name).name.strip() or "attachment"
    return clean


def _same_file(a: Path, b: Path) -> bool:
    """True when two paths point at byte-identical files (size + mtime)."""
    try:
        sa, sb = a.stat(), b.stat()
    except OSError:
        return False
    return sa.st_size == sb.st_size and sa.st_mtime == sb.st_mtime


def _build_attached_block(attached, project_dir: Path) -> str:
    """Build a prompt block describing the user's attached files.

    `attached` is the list carried on UserRequestMessage.attached_files. Files
    already inside project_dir are referenced by their real relative path (no
    copy). Pasted content / outside-path files are either inlined (small text)
    or copied into project_dir/.eco-attachments and referenced by path.

    SECURITY: every item carrying a `path` is validated against the allowed
    roots via _ensure_allowed before any read/copy; invalid items are skipped,
    never errored (so one bad path can't sink the whole request). Pasted
    `content` is client-provided bytes and is written without a disk read.
    """
    if not attached:
        return ""
    try:
        project_dir = Path(project_dir).resolve(strict=False)
    except (OSError, RuntimeError):
        return ""
    att_dir = project_dir / ".eco-attachments"
    try:
        att_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        att_dir = None

    lines: list[str] = [
        "=== Attached files (user-provided session context) ===",
        "The user explicitly attached these files. They are available to you:",
    ]
    inline_budget = 0
    written_names: set[str] = set()

    def _dedupe(base: str) -> str:
        # Unique name inside att_dir so two attachments sharing a basename
        # (e.g. a mention `src/a.txt` and a pasted `a.txt`) never clobber
        # each other (B3).
        candidate = base
        stem = Path(base).stem
        suffix = Path(base).suffix
        n = 2
        while candidate in written_names:
            candidate = f"{stem}-{n}{suffix}"
            n += 1
        written_names.add(candidate)
        return candidate

    for item in attached:
        if not isinstance(item, dict):
            continue
        name = _safe_attach_name(str(item.get("name") or "attachment"))
        kind = item.get("kind")
        path = item.get("path")
        content = item.get("content")

        resolved: Path | None = None
        if path:
            try:
                resolved = _ensure_allowed(Path(path).expanduser().resolve())
            except Exception:
                logger.warning("attachment skipped (outside allowed roots): %s", path)
                continue

        # Case 1 — already inside project_dir: reference the real relative path.
        if resolved is not None and (
            resolved == project_dir or project_dir in resolved.parents
        ):
            rel = resolved.relative_to(project_dir)
            try:
                size = resolved.stat().st_size
            except OSError:
                size = 0
            tag = "image" if kind == "image" else "text"
            lines.append(
                f"- {name} [{tag}, {size} bytes] — path-only: "
                f"read(path='{rel}')"
            )
            continue

        # Resolve bytes / text from paste content or an outside-path file.
        # For outside files we decide inline-vs-copy by stat() size and only
        # read_bytes() when we actually inline — avoids a double read for the
        # (common) copy path (optimization 2).
        raw_bytes: bytes | None = None
        text_content: str | None = None
        file_size: int | None = None

        if content is not None:
            if kind == "image":
                try:
                    b64 = content.split(",", 1)[1] if content.startswith("data:") else content
                    raw_bytes = base64.b64decode(b64)
                except Exception:
                    raw_bytes = None
            else:
                text_content = content
                raw_bytes = content.encode("utf-8", errors="replace")
            if raw_bytes is None:
                continue
            # Server-side cap on pasted content written to disk (B6). The
            # frontend 5 MB client cap is bypassable, so guard here too.
            if len(raw_bytes) > ATTACH_MAX_CONTENT:
                logger.warning(
                    "attachment skipped (pasted content %d bytes > %d cap): %s",
                    len(raw_bytes), ATTACH_MAX_CONTENT, name,
                )
                continue
        elif resolved is not None:
            try:
                file_size = resolved.stat().st_size
            except OSError as error:
                logger.warning("attachment stat failed: %s", error)
                continue
            if file_size > ATTACH_MAX_CONTENT:
                logger.warning(
                    "attachment skipped (file %d bytes > %d cap): %s",
                    file_size, ATTACH_MAX_CONTENT, name,
                )
                continue
            if (
                kind != "image"
                and file_size <= ATTACH_INLINE_LIMIT
                and inline_budget + file_size <= ATTACH_TOTAL_INLINE_LIMIT
            ):
                try:
                    raw_bytes = resolved.read_bytes()
                    text_content = raw_bytes.decode("utf-8", errors="replace")
                except OSError as error:
                    logger.warning("attachment read failed: %s", error)
                    continue
            # else: copy-only — defer the read to shutil.copy2 below.
        else:
            continue

        # Inline only when we actually have the decoded text and it fits the
        # caps. Large pasted text falls through to the path-only branch.
        is_text = (
            kind != "image"
            and text_content is not None
            and raw_bytes is not None
            and len(raw_bytes) <= ATTACH_INLINE_LIMIT
            and inline_budget + len(raw_bytes) <= ATTACH_TOTAL_INLINE_LIMIT
        )
        if is_text:
            inline_budget += len(raw_bytes)
            # Dedupe FIRST: the truncation hint below must name the file that
            # is actually written (a collision renames it to e.g. a-2.txt).
            dest = _dedupe(name)
            snippet = (
                text_content[:4096]
                + f"\n…(truncated, read full via read(path='.eco-attachments/{dest}'))"
                if len(raw_bytes) > 4096
                else text_content
            )
            lines.append(f"- {dest} [text, {len(raw_bytes)} bytes] — inline:\n{snippet}")
            if att_dir is not None:
                try:
                    (att_dir / dest).write_bytes(raw_bytes)
                except OSError:
                    pass
            continue

        # Path-only: write (paste) or copy (outside file) into att_dir.
        if att_dir is None:
            logger.warning("attachment dropped (cannot create .eco-attachments): %s", name)
            continue
        dest = _dedupe(name)
        if resolved is not None:
            # Optimization 1: skip the copy when an identical file already sits
            # in att_dir (session-scoped re-sends hit this every request).
            dest_path = att_dir / dest
            if not (dest_path.exists() and _same_file(dest_path, resolved)):
                try:
                    shutil.copy2(resolved, dest_path)
                except OSError as error:
                    logger.warning("attachment copy failed: %s", error)
                    continue
        else:
            if raw_bytes is None:
                continue
            # Pasted content: always write. A size-only skip would silently
            # keep stale bytes when a re-send carries different content of
            # the same length, and the content is already in memory anyway.
            dest_path = att_dir / dest
            try:
                dest_path.write_bytes(raw_bytes)
            except OSError as error:
                logger.warning("attachment write failed: %s", error)
                continue
        disp_size = file_size if file_size is not None else (len(raw_bytes) if raw_bytes is not None else 0)
        if kind == "image":
            lines.append(
                f"- {dest} [image] — visual reference at .eco-attachments/{dest}"
            )
        else:
            lines.append(
                f"- {dest} [text, {disp_size} bytes] — path-only: "
                f"read(path='.eco-attachments/{dest}')"
            )

    if len(lines) <= 2:
        return ""
    return "\n".join(lines) + "\n\n"


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
    return load_marketplace_framework_components()


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
    # Per-connection config snapshot: reloaded fresh at connect so new
    # sessions pick up settings saves, but bound to a LOCAL name — the global
    # is only swapped by PUT /config/workspace, never mid-run, so a concurrent
    # session's pipeline can never observe its config changing underneath it.
    # A malformed workspace.yaml falls back to the last known good config.
    try:
        connection_config = await asyncio.to_thread(
            load_config,
        )
    except Exception:
        logger.exception("config reload at WS connect failed; using last known good")
        connection_config = HARNESS_CONFIG
    await websocket.accept()

    # Lazy imports — keep startup light even if the role layer churns.
    from eco_harness.agent.internal.orchestrator import Orchestrator

    # The harness uses pi_ai.Model directly (no langchain). This is the path where
    # delta.reasoning is preserved end-to-end through to the UI thinking blocks.

    # Binary resolution now goes through the single shared policy
    # (agent/internal/tools/binaries.py): explicit config → ECO_*_PATH env →
    # <repo>/bin/<name> → /opt mount → legacy platform-suffixed siblings →
    # PATH. The harness.yaml eco_*_path settings ride in as the explicit
    # candidate.
    def resolve_executable_path(config_attr: str, default_name: str):
        """Resolve an external tool binary via binaries.resolve_binary."""
        configured = getattr(connection_config, config_attr, None)
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

    # A caller-supplied thread_id becomes the session id and the proj-<id>
    # project folder; sanitize it so it can never carry "/" or ".." into a
    # filesystem path. Reconnects send the same raw value and get the same id.
    requested_thread_id = websocket.query_params.get("thread_id")
    thread_id = _safe_id(requested_thread_id) if requested_thread_id else str(uuid.uuid4())

    def _default_project_dir() -> Path:
        # Resolve to an ABSOLUTE path under a stable output root so the stored
        # project_path does not depend on the server's current working
        # directory.
        #
        # Bug history (chat-ea0e66f1 follow-up, ses-9257ff60): the previous
        # implementation used `Path(os.getenv("HARNESS_OUTPUT_ROOT",
        # "./output")).resolve()`. `resolve()` is CWD-relative, so when the
        # server was started with CWD = an old project's working dir
        # (e.g. the user kept the previous project selected in the panel),
        # the new default project_dir became nested INSIDE the old one:
        # `<old project>/output/chat-<id8>/`. eco-wizard then created
        # `Eco.X/Eco.X/AssemblyFiles/...` under that nested path, the coder's
        # relative `read`/`glob` calls saw an inconsistent tree, and the run
        # failed without writing any source file.
        #
        # Fix: anchor the default to the shared _output_root() policy —
        # HARNESS_OUTPUT_ROOT (CWD-relative values resolve against the dev
        # repo root), <repo>/output on a dev checkout, <ECO_HOME>/output in
        # installed mode. Always absolute, never CWD-dependent.
        return _output_root() / f"proj-{thread_id[:8]}"

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

    # Per-SESSION LLM trace folder. Every architect/coder/tester LLM
    # request+response is persisted here as a numbered JSON file (see
    # EcoAgent._stream_llm) — incrementally, so a trace exists after a single
    # call and even if the (now unbounded) agent loop never terminates.
    #
    # Minimal-first-cut naming (full split in a follow-up): the trace folder
    # uses the `ses-` prefix so the on-disk path and the project-panel
    # session-card id are visually identical. The project folder uses the
    # `proj-<8hex>` default (renamed from the legacy `chat-<8hex>` —
    # _remap_to_output_root heals old registry entries to the proj- sibling
    # when it exists; see docs/ID_NAMING.md).
    #
    # Like _default_project_dir above, the trace dir is anchored to the
    # repository root so the path is independent of the server's CWD — the
    # same bug that nested output/chat-* under output/chat-*/* would also
    # have nested traces/ under traces/chat-9257ff60/--app/.../traces/chat-*.
    traces_base = _traces_root()
    trace_dir = traces_base / f"ses-{thread_id[:8]}"
    trace_dir.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"[CHAT WS] connected thread_id={thread_id} "
        f"project_dir={project_dir} trace_dir={trace_dir}"
    )
    # Register so the UI can stop this session from the panel.
    ACTIVE_SESSIONS[thread_id] = websocket
    await websocket.send_json({"type": "heartbeat", "protocol": "chat", "thread_id": thread_id})

    # Session bookkeeping for the UI project panel: flip the registry status
    # when this connection's run reaches any terminal state.
    session_open = False

    # Per-connection counter passed to write_call_trace as metadata; the
    # NNN-chat.json file sequence itself is assigned by write_call_trace from
    # the on-disk file count, so chat replies interleave correctly with the
    # pipeline's own trace writes to the same trace_dir.
    chat_call_no = 0

    def finish_session(status: str) -> None:
        nonlocal session_open
        if not session_open:
            return
        session_open = False
        _record_session_end(thread_id, project_dir, status)

    # Preserve stable node identifiers expected by the client.
    PHASE_OF = {
        "architect": "planning", "coder": "coding",
        "tester": "testing",     "reviewer": "review",
    }
    NODE_OF  = {
        "architect": "planner",  "coder": "coder",
        "tester": "tester",      "reviewer": "reviewer",
    }

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
            elif etype == "usage":
                # Per-LLM-call token accounting for the phase stepper counters.
                usage = dict((ev.data or {}).get("usage") or {})
                if usage:
                    # Context-load gauge (UI_PRD I-6): the prompt side of THIS
                    # call against the configured window. Sent per call (the
                    # frontend replaces, not accumulates) so the gauge tracks
                    # the live context size as the session grows.
                    usage.setdefault("context_window", _context_window())
                    usage.setdefault("context_used", sum(
                        usage.get(k) or 0
                        for k in ("input", "cache_read", "cache_write")
                    ))
                    await websocket.send_json({
                        "type":  "usage",
                        "node":  NODE_OF.get(agent, "planner"),
                        "phase": PHASE_OF.get(agent, "planning"),
                        "usage": usage,
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

            # Per-message target triple (user-selected in the chat frame).
            # Resolved once here so the seed block is the same for the
            # architect, the warm-retry coder, and every hop in between.
            target_triple = _resolve_target_triple(payload)

            # Per-message project override: the UI sends the folder selected
            # in the left projects panel. Without it we fall back to (and
            # reset to) the default per-thread chat-<id8> directory, so a
            # worktree-free follow-up never writes into a previous custom
            # project by accident.
            requested_project = str(payload.get("project_dir") or "").strip()
            if requested_project:
                # Tolerate a stale output-root prefix (cwd drift) — re-anchor to
                # the current output root instead of rejecting the run before it
                # even starts. Security boundary is preserved: the remapped path
                # always stays inside the output root.
                candidate = _remap_to_output_root(Path(requested_project).expanduser())
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

            language = str(payload.get("language") or connection_config.default_language)
            mode = str(payload.get("mode") or "auto").lower()
            if mode not in connection_config.modes:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Unsupported working mode: {mode}",
                })
                continue
            if payload.get("use_worktree") and not use_worktree:
                try:
                    worktree = create_worktree(
                        # Worktrees branch the USER's project, not the harness
                        # install: in installed mode config.root is ECO_HOME
                        # (not a git repo), so anchor on ECO_PROJECT_DIR — the
                        # folder the UI picker registered for this session.
                        paths.project_dir(),
                        thread_id,
                        name=payload.get("worktree_name"),
                        root=connection_config.worktree_root,
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

            # Attachments are session-scoped: the client sends attached_files on
            # every user_request. Build the prompt block once project_dir is
            # finalized (post worktree) so both planner + coder seeds see it.
            attached_block = _build_attached_block(
                payload.get("attached_files"), project_dir
            )

            # ── One-shot modes: no automatic pipeline (test / review / code / plan) ──
            if mode in {"test", "review", "code", "plan"}:
                one_shot_role = {
                    "test": "tester",
                    "review": "reviewer",
                    "code": "coder",
                    "plan": "architect",
                }[mode]
                _, role_spec, role_profile = load_role_config(
                    one_shot_role, connection_config.root,
                )
                from eco_harness.agent.main import get_model as _get_model
                role_backend = role_spec.backend.removesuffix("_cli")
                one_shot = make_role_agent(
                    one_shot_role,
                    config=connection_config,
                    model=(
                        _get_model(role_profile, role=one_shot_role, providers=connection_config.providers)
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
                    on_event=_make_on_event(ev_queue, one_shot_role),
                )
                ev_queue = asyncio.Queue()
                try:
                    result = await _run_agent(
                        one_shot.run,
                        ev_queue,
                        _workspace_header(project_dir, marketplace_cache_root, target_triple)
                        + attached_block + user_req,
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
                gate_model = _build_chat_model(connection_config)
                if gate_model is not None and not await _classify_intent(user_req, gate_model):
                    chat_call_no += 1  # per-connection plain-chat trace counter
                    try:
                        answer = await _chat_reply(
                            user_req,
                            gate_model,
                            attached_ctx=attached_block,
                            trace_dir=trace_dir,
                            call_no=chat_call_no,
                        )
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
            workspace = _workspace_header(project_dir, marketplace_cache_root, target_triple)
            planner_seed = workspace + attached_block + user_req
            approved_plan_md: str | None = None
            terminate_chat = False

            while True:
                ev_queue: asyncio.Queue = asyncio.Queue()
                _, architect_spec, architect_profile = load_role_config(
                    "architect", connection_config.root,
                )
                from eco_harness.agent.main import get_model as _get_model
                architect_backend = architect_spec.backend.removesuffix("_cli")
                planner = make_role_agent(
                    "architect",
                    config=connection_config,
                    model=(
                        _get_model(architect_profile, role="architect", providers=connection_config.providers)
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
                    planner_seed = workspace + attached_block + user_req
                    if reason:
                        planner_seed = workspace + attached_block + (
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
                connection_config.eco_wizard_path
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
                "coder", connection_config.root,
            )
            _, tester_spec, tester_profile = load_role_config(
                "tester", connection_config.root,
            )
            coder = make_role_agent(
                "coder",
                config=connection_config,
                model=(
                        _get_model(coder_profile, role="coder", providers=connection_config.providers)
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
                config=connection_config,
                model=(
                        _get_model(tester_profile, role="tester", providers=connection_config.providers)
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
            from eco_harness.agent.internal.entry import (
                EXECUTION_EDGES,
                EXECUTION_ENTRY,
                MIGRATE_EDGES,
            )

            if mode == "migrate":
                # Migrate inserts a read-only ACOM reviewer between the coder
                # and the tester. The coder's `to_tester` handoff card is the
                # reviewer's compact seed — it carries the artifact path, the
                # acceptance criteria, and the list of source files written, so
                # the reviewer inspects only what was produced (no tree-wide
                # bloat). The reviewer forwards to the tester (or back to the
                # coder on critical findings) via its own handoff tools.
                _, reviewer_spec, reviewer_profile = load_role_config(
                    "reviewer", connection_config.root,
                )
                reviewer = make_role_agent(
                    "reviewer",
                    config=connection_config,
                    model=(
                        _get_model(reviewer_profile, role="reviewer", providers=connection_config.providers)
                        if reviewer_spec.backend.removesuffix("_cli")
                        in {"internal", "builtin", "eco"}
                        else None
                    ),
                    cli_path=cli_path,
                    project_dir=project_dir,
                    make_exe=make_exe,
                    language=language,
                    marketplace_cache_root=marketplace_cache_root,
                    mode=mode,
                    pipeline=True,
                    trace_dir=trace_dir,
                    on_event=_make_on_event(ev_queue, "reviewer"),
                )
                sub_agents = {
                    "coder": coder,
                    "reviewer": reviewer,
                    "tester": tester,
                }
                sub_edges = MIGRATE_EDGES
            else:
                sub_agents = {"coder": coder, "tester": tester}
                sub_edges = EXECUTION_EDGES

            sub_orch = Orchestrator(
                agents=sub_agents,
                edges=sub_edges,
                entry=EXECUTION_ENTRY,
                max_hops=connection_config.max_hops,
                seed_builders=seed_builders,
            )

            try:
                coder_seed = workspace + attached_block + approved_plan_md + scaffold_note
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
                "max_retries":      connection_config.max_hops,
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
    finally:
        # Drop the live-connection registration so a later abort cannot try to
        # close an already-dead socket.
        if ACTIVE_SESSIONS.get(thread_id) is websocket:
            ACTIVE_SESSIONS.pop(thread_id, None)


# ═══════════════════════════════════════════════════════════════════════════
# STATIC UI — the Next.js static export shipped inside the wheel
# (eco_harness/web_static, built in CI). Mounted LAST so every API / WS route
# above keeps priority; unknown paths fall back to index.html (SPA-style
# client-side routing), except API-shaped paths which stay 404.
#
# In the dev stack the UI runs via `next dev` on its own port and this mount
# is skipped (no built out/ present) — nothing changes for developers.
# ═══════════════════════════════════════════════════════════════════════════

_API_PREFIXES = ("/api/", "/rag", "/ws/", "/files/", "/config", "/health")


class _SPAFallbackStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 404 and not scope.get(
            "path", ""
        ).startswith(_API_PREFIXES):
            # Next.js static export emits flat `<route>.html` files, so
            # /setup must resolve to setup.html before the index fallback.
            html_response = await super().get_response(f"{path}.html", scope)
            if html_response.status_code != 404:
                return html_response
            return await super().get_response("index.html", scope)
        return response


def _web_static_dir() -> Path | None:
    """First existing static-UI build: wheel package data → dev export out/."""
    candidates = [
        paths.package_root() / "web_static",
        paths.repo_root() / "frontend" / "out",
    ]
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


_web_static = _web_static_dir()
if _web_static is not None:
    app.mount(
        "/",
        _SPAFallbackStaticFiles(directory=str(_web_static), html=True),
        name="ui",
    )
    logger.info("serving static UI from %s", _web_static)
else:
    logger.info("no static UI build found — API-only mode")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
