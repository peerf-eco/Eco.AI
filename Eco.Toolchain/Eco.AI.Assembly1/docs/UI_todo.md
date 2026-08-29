# UI / UX TODO — trace & project identity

The full analysis (see `reasoning chain 2.txt` and `docs/reasonning concludes.txt`)
identified a set of UI / UX problems. The minimal first cut (carried in this
repo) shipped three changes:

1. Trace folder renamed `traces/chat-<8hex>/` → `traces/ses-<8hex>/` so the
   on-disk path matches the session card id visually.
2. Session cards now show the `ses-` prefix as a small monospace chip and a
   `📂` copy-to-clipboard button on hover.
3. Hover tooltip on each session card reveals the trace dir, the last
   trace file, and the last error (if any) — driven by a new
   `GET /api/sessions/{id}/trace` endpoint.

Everything below is **out of scope** for the minimal first cut and is the
work for the rest of this quarter. Items are ordered by the user-visible
impact-to-effort ratio, ties broken by blast radius.

---

## P0 — high impact, low effort

### UI-1. Project card `proj-` prefix
Today, the project card title is the directory basename (e.g. `A`).
For a project that is a *harness-managed* dir (`output/chat-<8hex>/`)
the title shows the cryptic `chat-ea0e66f1`, indistinguishable from a
session id. Apply the recommended `proj-` prefix:

- `_project_entry(path)` returns `"id": "proj-" + base32-4` for harness-
  generated paths; keeps the SHA-1-based id for user-registered paths.
- `ProjectsPanel` shows `proj-` as a leading chip (same shape as the
  `ses-` chip on session cards) when the id has that prefix.
- Migrate the default project_dir from `output/chat-<8hex>/` to
  `output/proj-<8hex>/` (one-line change in `_default_project_dir`,
  and a sibling `chat-<8hex>` → `proj-<8hex>` migration in
  `_remap_to_output_root` so existing data keeps working).

Files: `backend/server.py:164-170, 1920, 216`; `frontend/components/chat/project-panel.tsx`.

### UI-2. "X sessions" / "X traces" badge on the project card
The project card has no count of its sessions or traces — the user has
to expand the project to see anything. Add a small monospace badge on
the card (under the path) showing `N sessions · M traces`. Compute
`M` from a new `GET /api/projects/{id}/traces` endpoint that sums the
per-session trace dir file counts; or piggyback on `GET /api/projects`
and extend the response shape with `trace_count` and `session_count`
(no extra round trip).

Files: `backend/server.py:455-482` (list_projects); `frontend/components/chat/project-panel.tsx:179-223`.

### UI-3. Project card "Open in file browser" affordance
Today the user cannot jump from the project card to the on-disk folder
without copy-pasting the path. Add a small folder icon button on the
project card (similar to the `📂` we just added on session cards) that
copies `project.path` to the clipboard. The existing `handleCopyTracePath`
helper in `chat-interface.tsx` is the template; rename to
`handleCopyProjectPath` and wire it into `ProjectCardMenu` or a new
top-right icon button.

Files: `frontend/components/chat/project-panel.tsx:289-369`; `frontend/components/chat/chat-interface.tsx`.

---

## P1 — high impact, medium effort

### UI-4. Trace Browser modal
The single biggest usability win. New component
`frontend/components/chat/trace-browser.tsx` that opens as a `<dialog>`
when the user clicks the new project-card "X traces" badge or a session
card's "open" button. Layout:

```
+-----------------------------------------------------------+
|  trace-browser  ses-1ca5b8f4                            x  |
+-----------------------------------------------------------+
|  Threads (most recent first)                                |
|  > ses-1ca5b8f4  aborted  Сделай конвертер...  1m ago     |
|      001-architect.json  ok  11k                          |
|      002-architect.json  ok  4.2k                         |
|      003-coder.json      HTTP 400  262k  <-- clickable    |
|  > ses-2855db5b  success  Собери калькулятор... 3d ago    |
|  ...                                                      |
+-----------------------------------------------------------+
|  Most recent failure:                                     |
|  [003-coder.json content — first 4KB]                    |
+-----------------------------------------------------------+
```

Each row click copies the trace file path; the "Most recent failure"
section is auto-populated by scanning for the first file with
`meta.error` non-empty. Driven entirely by the existing
`GET /api/sessions/{id}/trace` endpoint (no new backend work needed).

Files: new `frontend/components/chat/trace-browser.tsx`;
`frontend/components/chat/chat-interface.tsx` (open/close state);
`frontend/components/chat/project-panel.tsx` (button on the card).

### UI-5. Status dot precedence on the project card
Today `ProjectStatusDot` (lines 557-588) shows a single dot whose
colour is `selected > hasRunning > hasSuspended > idle`. The dot does
not distinguish "has failed sessions" from "has aborted sessions" or
"all success". Add a "most recent session status" indicator (small
text under the badge from UI-2: e.g. `last: failed (3m ago)`). Use the
existing `relativeTime()` helper; one line of text per card is enough.

Files: `frontend/components/chat/project-panel.tsx:179-223, 557-588`.

### UI-6. 3-dot menu gains "Copy path" + "Show traces"
Today the project-card 3-dot menu has Export (JSONL / TXT) + Remove.
Add (above the existing entries):

- "Copy project path" — calls `handleCopyProjectPath` (UI-3).
- "Show trace browser" — opens the modal (UI-4) on the project.
- "Open last failed trace" — shortcut that opens the trace-browser
  modal and auto-jumps to the most recent `meta.error` row.

For sessions nested under the project, also add a session-level
"Open trace browser" entry to the (currently nonexistent) session
3-dot menu.

Files: `frontend/components/chat/project-panel.tsx:289-369` and a new
session row menu.

---

## P2 — medium impact, medium effort

### UI-7. Drop the default `chat-<8hex>` project_dir, adopt `proj-<8hex>`
- `_default_project_dir()` returns `output/proj-<8hex>`.
- `_remap_to_output_root` handles both `chat-` and `proj-` legacy
  prefixes so old data is still discoverable.
- The harness-managed project name in the panel becomes the `proj-`
  prefix + 4-char base32 suffix (so the card title is `proj-7K3F`,
  not `chat-ea0e66f1`).
- The user-registered project keeps its directory basename as the
  name (e.g. `A`) — the `proj-` prefix is only for harness-generated
  dirs.

Files: `backend/server.py:1920, 216-238, 164-170`; `frontend/components/chat/types.ts`.

### UI-8. Standardize the 3-dot menu trigger everywhere
Today the project card has a 3-dot menu (only when the card has
sessions), but session cards have no 3-dot menu at all — they have
an inline stop button. Add a 3-dot menu to each session card with
"Open trace browser", "Copy trace path", "Copy session id", and the
existing "Stop" entry. Use the same `useDismissable` + `MenuItem`
primitives as the project card. Keeps the visual language consistent
and gives room to add the "Open last failed trace" shortcut.

Files: `frontend/components/chat/project-panel.tsx:289-369, 500-538`.

### UI-9. Folder picker: "navigate INTO before select"
Today the file browser lets the user select the parent dir or the
target dir interchangeably, with no visual hint that the parent is a
common mis-click. Add a helper line in the picker: `Tip: navigate into
a project folder before selecting it — selecting a parent folder
includes all subfolders in the project list.` Plus: a "Select this
folder" CTA that is *disabled* until the path the user is hovering
is a non-empty leaf directory (currently the picker accepts any
level).

Files: `frontend/components/chat/file-browser.tsx` (or whichever
component owns the picker dialog).

### UI-10. Project card hover should also show the project id
Today the project-card hover is `name\npath` only. Add a third line
with the project id (the SHA-1 prefix for user-registered projects,
the `proj-…` base32 for harness-generated ones) so the user can copy
it from the tooltip when they need to grep a log or reference it in
a support ticket.

Files: `frontend/components/chat/project-panel.tsx:179-223`.

---

## P3 — lower priority

### UI-11. Mute the per-card transient notice when nothing changed
Today `handleCopyTracePath` shows a `panelNotice` that lingers until
the user clicks the dismiss `X`. A copy that takes 50 ms deserves a
toast that auto-dismisses after 1.5 s. The existing
`setPanelNotice` API can stay; only the timing needs to change.

Files: `frontend/components/chat/chat-interface.tsx:535-543` and
the `notice`/`onDismissNotice` panel block in `project-panel.tsx`.

### UI-12. Show the chat-frame "target triple" chips on the project card
The chat frame already accepts `target_triple: {os, arch, build_variant}`.
The project card should also remember the most recent target triple
chosen in any of its sessions, and show it as a small chip group
(like `Linux · x86_64 · Static`). Lets the user see at a glance
whether the project is being built for the right target without
opening a session.

Files: `backend/server.py:_record_session_start` (store the triple on
the session), `GET /api/projects` (compute the latest from the
sessions), `project-panel.tsx:179-223`.

### UI-13. Trace file: one-click "open in file browser" if the user has set HARNESS_ALLOWED_ROOTS
The minimal first cut copies the path to the clipboard. For a
harness running on the user's laptop (not a container), an
`window.open('file://' + path)` is the natural next step. The
security boundary is the existing `HARNESS_ALLOWED_ROOTS` allowlist
in `_ensure_allowed`. Add a backend endpoint `GET /api/fs/open?path=…`
that re-validates against the allowlist and emits a platform-specific
shell open (xdg-open on Linux, open on macOS, start on Windows).
Disabled when running in a container (env probe).

Files: new `backend/server.py` endpoint, `frontend/components/chat/project-panel.tsx` button.

### UI-14. Sort projects by activity
Today `list_projects` sorts by `added_at` (newest added first). Most
users re-open the project they touched most recently, not the one
they added most recently. Switch the sort key to
`max(session.updated_at) or added_at` so the most-recently-active
project rises to the top.

Files: `backend/server.py:481`.

### UI-15. Inheritable "Auto" badge for harness-generated projects
When the user clicks a generated project (a `chat-…` or `proj-…` dir
that was created automatically by the WebSocket handler because the
user didn't pick one), the project card should show an "auto" chip
next to the title. Already computed in `list_projects` (`"auto": False`
is hard-coded today; the WebSocket path can set it to `True` when
`_default_project_dir` is in use). This makes the panel more honest
about which folders the user explicitly whitelisted vs which the
harness invented for them.

Files: `backend/server.py:_record_session_start` (set `auto: True`
when the project_dir is the default), `backend/server.py:481`.

### UI-16. Per-session export from the session card
Today only the **project** has a 3-dot menu with "Export sessions".
Add the same menu entry to a future session 3-dot menu (UI-8) so the
user can export a single session's transcript without leaving the
panel.

Files: `frontend/components/chat/project-panel.tsx` (new session
3-dot menu) plus a `GET /api/sessions/{id}/export?format=jsonl|txt`
endpoint that reuses `iter_project_jsonl` /
`render_export_text` from `backend/session_export.py`.

### UI-17. Stable project path display
Today the project path is the absolute resolved path. If the user
moves the folder (or the harness is restarted in a different cwd),
the card shows the new path but the SHA-1 id is unchanged — meaning
the card "moves with the folder" but loses its history. Decide:
(a) trust the absolute path, drop history when the path changes;
or (b) hash the path *before* resolving symlinks, so /home and
/home-relative links to the same folder hash to the same id.
Currently `_ensure_allowed` always calls `.resolve()` which expands
symlinks. Recommended: hash the **unresolved** user-supplied path for
the id, but keep the resolved path for the display + IO operations.

Files: `backend/server.py:164-170, 488-505`.

---

## P4 — spec-level items (read-the-whole-list before doing any)

### UI-18. Document the de-facto naming convention
The minimal first cut changed the trace-dir prefix. The follow-up
will change the project-dir prefix. Document the resulting
three-namespace convention (proj- / ses- / devkit-id) in a single
new file `docs/ID_NAMING.md`, then point the architect prompt, the
session_export README, and the project panel comment block to it.
This stops the same "what prefix means what" question coming back.

Files: new `docs/ID_NAMING.md`; references in
`config/prompts/architect.md`, `backend/session_export.py`,
`backend/server.py:_project_entry` docstring,
`frontend/components/chat/project-panel.tsx` module header.

### UI-19. Agent self-explanation: when the harness invents a session id, tell the user
The agent loop may produce a session id (e.g. `8fc99e0c`) that
collides with another session (1-in-4B, but non-zero) or that the
user simply cannot remember. Add a small "Last session id" indicator
in the main chat card (top right corner) so the user has a one-click
copy of the id for support tickets and for the architect when
debugging.

Files: `frontend/components/chat/chat-card.tsx` (or equivalent
component that hosts the streaming area).

### UI-20. Project path validation: visual feedback for the "outside allowed roots" 400
Today when the user picks a path outside `HARNESS_ALLOWED_ROOTS`
the server answers 400 with a long string. The picker dialog should
catch that 400 and show a friendlier red message inline: "This
folder is outside the harness allowed roots. Add it to
HARNESS_ALLOWED_ROOTS to enable." Reduces the "why was my click
rejected" support load.

Files: `frontend/components/chat/file-browser.tsx` (or equivalent
component) — catch the 400 and replace the message.

---

## Sequencing

- **Sprint A (this week):** UI-1, UI-2, UI-3. Pure rename + label work,
  no state machine changes, no new endpoints. Reuses the helper
  shape added in the minimal first cut.
- **Sprint B:** UI-4 (Trace Browser modal). Single new component, all
  backend already in place. Biggest user-visible win.
- **Sprint C:** UI-5, UI-6, UI-7. Project-dir prefix rename needs a
  one-off data migration (the harness moves old `chat-<id8>/` dirs
  to `proj-<id8>/` so the SHA-1 stays stable), which justifies
  shipping it on its own.
- **Sprint D:** UI-8, UI-9, UI-10. Card affordances.
- **Backlog:** UI-11 through UI-20, picked as user feedback lands.

Each item should be picked up as its own PR with:
- a short before/after screenshot (or screenshot diff) for the panel;
- the test case(s) in `backend/tests/test_session_export.py` (or a
  new `test_ux_routes.py`) that pin the new endpoint behavior;
- a one-line entry in this file's "Done" section below.

## Done (carried in the minimal first cut)

- [x] `traces/chat-<8hex>/` → `traces/ses-<8hex>/` (minimal first cut).
- [x] Session card shows `ses-` chip + hover tooltip with trace path
      + `📂` copy-to-clipboard button.
- [x] `GET /api/sessions/{id}/trace` returns per-file trace meta
      including last error.
- [x] `GET /api/sessions/{id}/messages` surfaces trace meta inline.
- [x] Legacy `traces/chat-<id>/` is still discoverable so old exports
      keep working (regression guard in `TestSessionTraceEndpoint`).
