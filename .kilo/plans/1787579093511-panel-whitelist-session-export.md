# Panel Whitelist + Session Export (fine-tuning data)

Workspace: `/home/nick/Git/Eco.AI/Eco.Toolchain/Eco.AI.Assembly1`

## Goal

Left projects panel (`frontend/components/chat/project-panel.tsx`):

1. Show only explicitly added ("whitelisted") projects; a 3-dot card menu removes a project from the panel — visual/UI only, never deletes projects, sessions, traces, or folders.
2. Export a project's sessions as JSONL or TXT with per-turn fields: `question`, `additional_context`, `reasoning_chain`, `final_answer` — for fine-tuning/training datasets.
3. Panel-header action: "Export All Projects" (JSONL/TXT combined).

## Decisions (confirmed with user)

- **Whitelist, not blacklist.** Existing `registry["projects"]` in `output/.harness-registry.json` is the whitelist. Removing = delete entry from that list; re-add = browse folder again. No schema change.
- **UI removal guard:** the card menu is disabled (grayed, explanatory tooltip) when the project is the active one (green dot) or has any session with `status == "running"`.
- **Backend removal guard:** `DELETE` returns 409 when the project has a running session.
- **Export packaging:** single file per project; JSON format = JSONL (one line per turn); plus human-readable TXT. Header menu offers Export-All in both formats.
- **Plain-chat tracing:** AUTO-mode direct answers (`_chat_reply`) also persist a trace so future exports are complete.

## Current-state facts (verified)

- Registry: `output/.harness-registry.json` `{projects:[{id,path,name,added_at}], sessions:[{id,thread_id,project_path,title,created_at,updated_at,status}]}`. Project `id` = `sha1(path)[:12]` (deterministic, `backend/server.py:115`).
- Clutter sources: `list_projects()` materializes every session path + legacy `output/chat-*` dirs as auto projects (`backend/server.py:381-436`); `_record_session_start()` auto-appends unregistered dirs (`server.py:487-488`).
- Session content lives ONLY in traces: `traces/chat-<thread_id[:8]>/NNN-<label>.json`, written by `write_call_trace` (`agent/internal/call_trace.py`): `{meta:{label,seq,model,ts,...}, request:{systemPrompt,messages[],tools[]}, response:<AssistantMessage dump>}`. Message dumps follow pi_ai shapes: user `content:str`; assistant `content:[{type:"text"|"thinking"|"toolCall",...}]` (`agent/pi_ai/types.py`).
- Every turn's seed = `workspace_header + attached_block + user_req`, so each turn's last user message embeds two stable markers: `=== Workspace ===` and `=== Attached files (user-provided session context) ===`.
- A session (= thread) may contain multiple turns; each trace file's *response* is exactly one LLM turn (no duplication across files).
- Plain-chat replies bypass tracing today (`_chat_reply`, `server.py:892-906`).
- Frontend auto-reselects a visible project when the stored `activeProjectId` disappears (`chat-interface.tsx:173-182`) — hiding/removal needs no extra handling there.
- Tests: `make test` runs pytest on `agent/internal/tests` + `compileall`. Backend has an empty `backend/tests/` package. Frontend: `npm run build` / `next lint`.

## Implementation

### 1. Backend — whitelist visibility (`backend/server.py`)

1. `list_projects()`: drop auto-materialization of session paths as projects and drop legacy `output/chat-*` seeding into the visible list. Return only `registry["projects"]`, each with grouped `sessions` (sorted by `updated_at` desc, unchanged). Sessions whose `project_path` isn't whitelisted are simply not rendered (records stay in the registry).
2. `_record_session_start()`: remove the auto-append of unregistered project dirs (lines ~487-488). Session records still upsert as today.
3. New endpoint:
   ```
   DELETE /api/projects/{project_id}
   ```
   - 404 unknown id; 409 if any session with this `project_path` has `status=="running"`; otherwise remove the entry from `registry["projects"]`, save via existing `_save_registry`, return `{status:"ok", removed:id}`. Sessions/traces untouched.
   - CORS/methods already allow DELETE.

### 2. Backend — plain-chat trace

In the AUTO-mode chat branch, wrap the `_chat_reply` exchange with `write_call_trace(trace_dir=trace_dir, label="chat", call_no=<per-connection counter>, iteration=0, model_id=gate_model.id, request_context=Context(systemPrompt=_CHAT_ANSWER_SYS, messages=[UserMessage(content=user_msg, timestamp=0)]), response=msg, error="")` (import `Context/UserMessage` already available locally there). Maintain a small per-connection `chat_call_no` counter. Failure-safe: `write_call_trace` never raises.

### 3. Backend — export module `backend/session_export.py` (new)

Pure functions, unit-testable, stdlib only:

- `session_turns(session: dict, traces_root: Path) -> list[dict]`
  - Trace folder: `traces_root / f"chat-{session['id']}"` (honors `HARNESS_TRACES_DIR` env; default `traces`). Files sorted by `meta.seq` / numeric prefix.
  - Group consecutive files into turns by their request's **last user message text** (new text ⇒ new turn).
  - Per turn:
    - `question`: user text minus leading `=== Workspace ===` section and minus the `=== Attached files … ===` block (split on the stable markers; fallbacks: no markers ⇒ whole text is question).
    - `additional_context`: attached-files block body (header line stripped), `""` if absent.
    - `reasoning_chain`: concatenation (`"\n\n"`) of all `thinking` block texts across the turn's responses in order.
    - `final_answer`: preferred = `message`/`reason`/`summary`/`report` string arg from the last stop-tool `toolCall` block (recovers handoff messages e.g. `to_coder`/`fail`); fallback = last non-empty `text` block across the turn's responses; else `""`.
  - Skip malformed files; tolerate empty/missing dir ⇒ zero turns.
- `build_project_export(project, sessions, traces_root) -> dict`:
  `{project:{id,name,path}, exported_at, sessions:[{…SessionInfo, source:"traces"|"metadata_only", turns:[…]}]}` — `metadata_only` when no usable traces (legacy/direct-chat-before-this-feature).
- `iter_project_jsonl(export) -> Iterator[str]`: one JSON object per **turn** per line (`json.dumps(..., ensure_ascii=False)`): `{project_id, project_name, session_id, thread_id, session_title, session_status, created_at, updated_at, turn_index, question, additional_context, reasoning_chain, final_answer}`. Metadata-only sessions emit a single line with empty turn fields (nothing silently dropped).
- `render_export_text(export) -> str`: sections per session/turn:
  `===== SESSION <id> [<status>] =====`, `Title: …`, then per turn labeled blocks `QUESTION:` / `ADDITIONAL CONTEXT:` / `MODEL REASONING CHAIN:` / `FINAL ANSWER:`, `=====` separators between sessions.

### 4. Backend — export endpoints (`backend/server.py`)

```
GET /api/projects/{project_id}/export?format=jsonl|txt   # 404 unknown id
GET /api/export/all?format=jsonl|txt                      # all whitelisted projects
```
- Resolve `traces_root = Path(os.getenv("HARNESS_TRACES_DIR", "traces"))`.
- Stream via `StreamingResponse` with `media_type` `application/x-ndjson` / `text/plain; charset=utf-8` and `Content-Disposition: attachment; filename="<safe-name>-sessions.jsonl|.txt"` (sanitize project name; all-projects file: `harness-sessions-all.*`). Filenames ASCII-safe; non-ASCII chars folded out.

### 5. Frontend — panel UI (`frontend/components/chat/project-panel.tsx`)

- New props: `onRemoveProject(project)`, `onExportProject(project, format: "jsonl"|"txt")`, `onExportAll(format)`, `exportBusy: boolean`.
- Card layout restructure: outer `<div className="relative">`; existing card becomes the main `<button>` (flex-1); add a small `MoreVertical` (lucide) icon button pinned top-right (visible on hover / always when menu open), keeping the status dot.
- `ProjectCardMenu` component (pattern copied from `dropdown.tsx`: outside-mousedown + Escape close, `glass-strong` dark popover, `z-50`, opens downward-left):
  - Items: `Export sessions · JSONL`, `Export sessions · TXT`, divider, red-tinted `Remove from panel` (with title "Projects can be re-added anytime; nothing is deleted").
  - Trigger disabled (opacity-40, `cursor-not-allowed`, tooltip "Cannot remove the active project or one with running sessions") when `project.id === activeProjectId || project.sessions.some(s => s.status === "running")`.
- Header: second icon button (`FolderDown`) opening `PanelMenu` with `Export all projects · JSONL` / `· TXT` (disabled while `exportBusy`).

### 6. Frontend — wiring (`frontend/components/chat/chat-interface.tsx`)

- `handleRemoveProject`: `fetch(DELETE /api/projects/{id})`; on 409/other non-ok set a transient `panelNotice` string (rendered by the panel under the header, dismissible); always `refreshProjects()` afterwards. Auto-reselect of another visible project happens via existing effect.
- `downloadExport(url, fallbackName)` helper: `fetch` → `res.blob()` → parse filename from `Content-Disposition` → temp `<a download>` click → revoke. Errors surface through `panelNotice`.
- Pass the three handlers + `exportBusy` into `<ProjectsPanel>`.

## Files touched

- `backend/server.py` (whitelist filtering, DELETE endpoint, chat trace, export endpoints)
- `backend/session_export.py` (new)
- `backend/tests/test_session_export.py` (new; turn splitting, marker stripping, stop-tool answer extraction, metadata-only fallback, JSONL shape; FastAPI TestClient for DELETE guards incl. 409-running and export happy path using `tmp_path` registries/traces via env monkeypatch)
- `frontend/components/chat/project-panel.tsx` (menu UI, disabled logic, header export menu)
- `frontend/components/chat/chat-interface.tsx` (handlers, blob download, notice state)
- `Makefile`: extend `test` target with `.venv/bin/python -m pytest backend/tests`

## Edge cases

- Removed-then-rerun: sending a message against a non-whitelisted dir records a session but shows nothing in panel (accepted; normal flow selects a project first).
- Legacy `(previous run)` sessions without traces ⇒ metadata-only export lines.
- Empty project (no sessions) ⇒ valid header-only TXT / empty JSONL download.
- Active project removed via API while selected ⇒ frontend auto-reselect effect already covers it.
- Registry concurrency: reuse existing tmp-file+replace save pattern.

## Validation

1. `.venv/bin/python -m pytest backend/tests agent/internal/tests` and `make test` green.
2. `.venv/bin/python -m compileall -q agent backend eco_harness scripts`.
3. Frontend: `cd frontend && npm run build` (typecheck) and `npm run lint`.
4. Manual smoke: run stack (`make up` or dev servers), register 2+ projects, send a message each; verify: remove non-active project disappears and survives reload; removing active/running project is blocked (gray menu + 409); export JSONL/TXT per project and export-all contain correct four-field turns (check against `traces/chat-<id8>/` content); plain-chat Q/A now appears in a new trace file and exports.
