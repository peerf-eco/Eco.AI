# UI PRD — Chat Harness Look & Feel and Information Flow

> Target location: `docs/UI_PRD.md` (user-requested). Write permissions during planning restrict edits to plan dirs — the implementing agent should copy this file verbatim to `docs/UI_PRD.md` as the first step.

Status: proposed · Author: planning session 2026-08-29 · Supersedes ordering in `docs/UI_todo.md` (item ids from that file are reused as `T-UI-n`).

## 1. Goals

- Make the harness UI **informative at a glance**: timestamps, token/context state, session stats — without opening extra panels.
- Remove **visual defects** that undermine trust (overlapping text, frozen counters, cramped chat pane).
- Give the user **clear action flow**: project → session → trace → export, each reachable in ≤ 2 clicks.

Non-goals: redesign of the visual theme, backend pipeline changes beyond two small read-only API additions.

## 2. Issue rating

Rated by (user impact × frequency) with ease as the tie-breaker. Effort: S = <~100 LOC / 1 component, M = 1–3 components or small backend touch, L = new endpoint + migration or new modal.

| # | Issue | Source | Impact | Effort | Phase |
|---|-------|--------|--------|--------|-------|
| I-1 | Historical session text overlaps the chat pane | user report | High (broken rendering of a core view) | S | 1 |
| I-2 | Session totals chip overlaps the progress-bar graphics | user report | High (always visible during runs) | S | 1 |
| I-3 | Historical session view has no timestamp (only "N d ago" on cards) | user report | High | S | 1 |
| I-4 | Chat pane uses ~40% of screen width (`max-w-3xl` cap) | user report | High | S | 1 |
| I-5 | Token-counter ovals frozen / missing tooltip while a phase is in progress | user report | Medium-High | S–M | 2 |
| I-6 | No context-load (%) indicator for the running session | user report | Medium-High | M | 2 |
| I-7 | Projects panel width is fixed (272px); no drag-to-resize | user report | Medium | S–M | 2 |
| I-8 | Project card lacks session/trace counts (T-UI-2) | todo file | Medium | S | 2 |
| I-9 | Session cards have no 3-dot menu; actions are inconsistent (T-UI-8) | todo file | Medium | M | 2 |
| I-10 | Projects sorted by `added_at`, not by activity (T-UI-14) | todo file | Medium | S | 2 |
| I-11 | Project card shows no "last status / last failure" signal (T-UI-5) | todo file | Medium | S | 2 |
| I-12 | Trace Browser modal missing — biggest usability win (T-UI-4) | todo file | High | M–L | 3 |
| I-13 | `proj-` prefix for harness-generated project dirs + migration (T-UI-1, T-UI-7) | todo file | Medium | M | 3 |
| I-14 | Project menu entries: Copy path / Show traces / Open last failed trace (T-UI-3, T-UI-6) | todo file | Medium | S–M | 3 |
| I-15 | Folder picker: "navigate into before select" hint + outside-roots message (T-UI-9, T-UI-20) | todo file | Low-Med | S | 3 |
| I-16 | Misc backlog: auto-dismiss notice (T-UI-11), target-triple chips (T-UI-12), open-in-file-browser (T-UI-13), auto badge (T-UI-15), per-session export (T-UI-16), stable path hashing (T-UI-17), ID_NAMING doc (T-UI-18), last-session-id chip (T-UI-19), project-id in tooltip (T-UI-10) | todo file | Low | S each | 3 / backlog |

## 3. Phase 1 — Defect fixes & quick wins (frontend-only, no API changes)

### 3.1 I-1 · Fix text overflow in historical session view
**Root cause.** When a session is opened from the panel, `/api/sessions/{id}/messages` is converted into plain `text` blocks (`chat-interface.tsx:477-500`) rendered by `StreamMessage`'s text case (`stream-message.tsx:93-102`). That case uses `max-w-none` prose with **no horizontal containment**, so long unbroken lines (log output, long code lines, URLs) push past the bubble and the pane. In live sessions long payloads land in `tool_call` / `build_fail` blocks which already have `overflow-auto` (`stream-message.tsx:203`) — hence "only historical overlaps".
**Steps.**
1. In `stream-message.tsx` text and answer cases: wrap the prose container with `min-w-0 overflow-x-auto` and add `break-words` on the prose div; ensure `pre` inside prose gets `overflow-x-auto whitespace-pre`.
2. Add `min-w-0` to the flex column parent (`stream-message.tsx:65`) so flex children cannot force expansion.
3. Regression check: open the widest historical session available; verify no horizontal scroll on the pane itself, only inside code blocks.

### 3.2 I-2 · Move session totals out of the progress bar
**Root cause.** `phase-stepper.tsx:44-57` renders the total-token chip `absolute right-4 top-1` on the same strip as the connector ovals (which are translated `-translate-y-1/2` across `top-0`) — guaranteed collision on the right side of the bar.
**Steps.**
1. Remove the absolute chip from `PhaseStepper`.
2. Render session totals (tokens, per-phase I/O tooltip) as a compact chip group in the **header row right side** (`chat-interface.tsx:769-780`, next to the Connected pill), or — when a session is being viewed (I-3 banner) — on the viewing banner's free right side. Recommended: header chip, always in the same place.
3. Keep the `Coins` icon + `formatTokens` helper (move them out of `phase-stepper.tsx` into a shared `token-chip.tsx` or inline in the header).

### 3.3 I-3 · Timestamps on session views and cards
**Data already exists**: `SessionInfo.created_at` / `updated_at` (`types.ts:495-496`); backend sets them (`server.py:1087-1088, 1106`). No API change.
**Steps.**
1. Viewing banner (`chat-interface.tsx:834-873`): right of the task title render `· started <hh:mm dd MMM> · ended <…>` (use `updated_at` as "ended"; for `running` show "running since …"). Use a small `formatTimestamp(iso)` helper (locale `Intl.DateTimeFormat`), plus the existing `relativeTime` in a tooltip.
2. Session rows (`project-panel.tsx:544-549`): keep the compact `relativeTime` but add the absolute timestamp to the tooltip (`tipLines`) — one line each for created/updated.
3. Project card tooltip: include last-session timestamp.

### 3.4 I-4 · Widen the chat reading column
**Root cause.** `max-w-3xl` (768px) at `chat-interface.tsx:875` (messages) and `:903` (input dock).
**Steps.**
1. Introduce a single constant/`--chat-max-w` used by both places; default `max-w-4xl` on <1600px viewports and `max-w-5xl` above (pure CSS: `max-w-4xl 2xl:max-w-5xl`).
2. Optional (nice-to-have, still frontend-only): a small width toggle in the header ("Normal / Wide") persisted to localStorage, mirroring the `PANEL_OPEN_STORAGE_KEY` pattern.
3. Verify the input dock and message column stay aligned (same container class).

**Phase 1 validation**: `npm run lint`/typecheck; manual pass — open a historical session (no overflow), run a live request (totals chip in header, no overlap over stepper), resize window (column adapts), timestamps visible in banner and tooltips.

## 4. Phase 2 — Live telemetry & panel ergonomics

### 4.1 I-5 · Live token ovals on the active phase
**Root cause.** Connector ovals render only when `tokens.total > 0` (`phase-stepper.tsx:132`) and only update when a `usage` event arrives (per **completed** LLM call — `use-harness-socket.ts:289-312`). During a long call the oval is absent or stale with no affordance.
**Steps.**
1. In `Connector`, render the oval for the **active** phase even at zero tokens, in a "waiting" style (pulsing dot or `…` inside the pill) so the user sees accounting is live.
2. Always attach the `title` tooltip (currently only rendered with the oval) — including `input/output` split and "updates after each model call".
3. Add an animated `animate-pulse` class while `phase === currentPhase` to signal liveness.

### 4.2 I-6 · Context-load % indicator
**Design decision (recommended default).** Context usage ≈ `usage.input + usage.cache_read + usage.cache_write` (prompt side) against a context-window size configured backend-side; expose the limit via the `usage` event. Percentage shown inside the existing total chip (`"4.5k · 12%"`) and color-shifted (green → amber ≥70% → red ≥90%).
**Steps.**
1. Backend (`server.py:2505-2513` usage relay): include `context_window` (from model config/env, e.g. `HARNESS_CONTEXT_WINDOW`, default 128k) and a computed `context_used` in the relayed usage payload.
2. Frontend: extend `UsageEvent.usage` (`types.ts:400-411`); track the latest per-call `context_used` in `use-harness-socket.ts` (per-call value, **not** a sum — it replaces, not accumulates).
3. Render % inside the header totals chip from I-2; tooltip explains the estimate. If `context_window` is missing (older backend), hide the % gracefully.
4. Test pin: extend the usage-relay test in `backend/tests/` to assert the new fields.

### 4.3 I-7 · Resizable Projects panel
**Steps.**
1. Replace the hard-coded `animate={{ width: 272 }}` (`project-panel.tsx:115-120`) with a state-driven width (default 272, min 220, max 480), animated only on collapse/expand.
2. Add a 6px drag handle on the panel's right border (`cursor-col-resize`). `onDrag` updates width; persist to `localStorage` (`eco_harness.panel_width`), restore on mount like `PANEL_OPEN_STORAGE_KEY`.
3. Collapse behavior unchanged (icon rail at 60px).
4. Session rows and card content already truncate (`truncate` classes) — verify at min and max widths.

### 4.4 I-8 · Session/trace counts badge on project card (T-UI-2)
1. Backend: extend `list_projects` response (`server.py:455-482`) with `session_count` and `trace_count` (sum of trace-dir file counts per session) — no new endpoint.
2. Frontend (`project-panel.tsx:213-228`): monospace badge under the path: `N sessions · M traces`; `M` doubles as the future Trace Browser entry point (Phase 3).

### 4.5 I-9 · Session-row 3-dot menu (T-UI-8)
1. Reuse the existing `useDismissable` + `MenuItem` primitives (`project-panel.tsx:274-473`).
2. Add a hover-revealed `MoreVertical` trigger to `SessionRow` (`project-panel.tsx:497-581`) with entries: Open trace browser (no-op until Phase 3), Copy trace path, Copy session id (`ses-<id8>`), Stop (when running). Move the inline stop button into the menu for consistency.
3. Wire handlers through existing props (`onCopyTracePath`, `onStopSession`); add `onCopySessionId`.

### 4.6 I-10 · Sort projects by activity (T-UI-14)
One-line change in `server.py:481`: sort key `max(session.updated_at) or added_at` descending. Add/adjust a test.

### 4.7 I-11 · "Last status" text on project card (T-UI-5)
Under the counts badge, render `last: <status> (<relativeTime>)` from the project's most recent session (`relativeTime()` already exists, `project-panel.tsx:637-648`). Extend `ProjectStatusDot` tooltip to mention failed sessions explicitly.

**Phase 2 validation**: `backend/tests/` for the `list_projects`/usage changes; manual — drag panel to min/max and reload (width persists), watch ovals pulse and update per call, % appears and matches tooltip math.

## 5. Phase 3 — Trace Browser & naming/flow features

### 5.1 I-12 · Trace Browser modal (T-UI-4) — biggest single win
1. New `frontend/components/chat/trace-browser.tsx`: `<dialog>`-based modal, opened from the project-card "M traces" badge (I-8) and the session menus (I-9). Data source: existing `GET /api/sessions/{id}/trace` — **no backend work**.
2. Layout per the spec in `docs/UI_todo.md` §UI-4: threads most-recent-first, per-file rows with status/size, row-click copies the file path, "Most recent failure" section auto-populated from the first file with non-empty `meta.error`.
3. State (open/close, target session) owned by `chat-interface.tsx`; entry buttons on `project-panel.tsx`.
4. "Open last failed trace" shortcut opens the modal pre-scrolled to the failure section (serves T-UI-6's third entry).

### 5.2 I-13 · `proj-` prefix for harness-generated project dirs (T-UI-1 + T-UI-7)
1. `_project_entry` (`server.py:164-170`): harness-generated paths get `"proj-" + base32-4` display id; user-registered keep basename/SHA-1 behavior.
2. `_default_project_dir` → `output/proj-<8hex>`; `_remap_to_output_root` migrates/accepts both legacy `chat-<8hex>` and new `proj-<8hex>` so existing data stays discoverable (`server.py:1920, 216-238`).
3. `ProjectsPanel` renders the `proj-` chip exactly like the session `ses-` chip (`project-panel.tsx:541-543` is the template).
4. Data migration is a one-off directory rename performed lazily by `_remap_to_output_root` — write a test pinning old-dir discoverability (mirror of the `TestSessionTraceEndpoint` regression guard).
5. Document the proj- / ses- / devkit-id convention in `docs/ID_NAMING.md` (T-UI-18) and link from `_project_entry` docstring + panel module header.

### 5.3 I-14 · Project-card menu entries (T-UI-3 + T-UI-6)
Generalize `handleCopyTracePath` into a clipboard helper in `chat-interface.tsx:519-539`; add "Copy project path", "Show trace browser", "Open last failed trace" above the existing Export entries in `ProjectCardMenu` (`project-panel.tsx:296-376`).

### 5.4 I-15 · Folder-picker guidance (T-UI-9 + T-UI-20)
In `folder-browser.tsx`: add the helper tip line ("navigate into a project folder before selecting"), a "Select this folder" CTA gated per the spec, and a friendly inline red message when the backend answers 400 "outside allowed roots" (replace raw `detail`).

### 5.5 I-16 · Backlog (pick as feedback lands)
T-UI-10 (project id in tooltip), T-UI-11 (auto-dismiss notice, 1.5 s), T-UI-12 (target-triple chips; needs `_record_session_start` + `list_projects` additions), T-UI-13 (`GET /api/fs/open` behind `HARNESS_ALLOWED_ROOTS`, disabled in containers), T-UI-15 (auto badge), T-UI-16 (per-session export endpoint), T-UI-17 (hash unresolved path), T-UI-19 (last-session-id chip in chat card).

## 6. Risks & notes

- **I-6 context %** is an *estimate* (prompt-side tokens vs configured window); label it as such in the tooltip to avoid "why 101%" tickets. Cache reads/writes must be included or the number will undercount badly.
- **I-13 migration** touches on-disk layout — ship alone in its own PR with the discoverability regression test, exactly as `docs/UI_todo.md` §Sequencing recommends.
- **I-1** must be verified against a real offending historical session before and after; keep a saved trace as a fixture if possible.
- Backend changes in this PRD are deliberately limited to: usage-event enrichment (I-6), `list_projects` shape/sort (I-8, I-10), `proj-` prefix/migration (I-13), and optional `/api/fs/open` (I-16). Everything else is frontend-only.

## 7. Delivery

Each numbered item ships as its own PR with: before/after screenshot for panel/bar changes, a test pinning any endpoint change (`backend/tests/test_ux_routes.py` or existing files), and a one-line "Done" entry appended to `docs/UI_todo.md`. Suggested order within a phase = document order above.

## 8. Implementation checklist

- [ ] Copy this plan to `docs/UI_PRD.md` (planning sandbox blocked writes there).
- [ ] Phase 1: I-1 → I-2 → I-3 → I-4 (independent, one PR each).
- [ ] Phase 2: I-5, I-7 frontend-first; I-6, I-8, I-10 backend touches; I-9, I-11 frontend.
- [ ] Phase 3: I-12 modal; I-13 migration solo; I-14, I-15, I-16 backlog.
