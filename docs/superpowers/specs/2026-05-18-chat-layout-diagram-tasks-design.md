# Design — Wider Chat, Zoomable Diagram, Live Task Checklist in plan.md

**Date:** 2026-05-18
**Branch:** `feat/v6-five-node-pipeline`
**Authors:** YanGaev2 + Claude
**Status:** Draft — awaiting user approval

---

## 1. Problem

Three independent UX defects in the V6 chat surface (visible in user screenshot
from `Eco.AI.Assembly1/frontend`):

1. **Chat is too narrow.** Both the message column and input dock are pinned to
   `max-w-3xl` (~768 px) in `chat-interface.tsx:177` and `:204`. On a 2K monitor
   this leaves ~70 % of horizontal real estate unused; long markdown blocks,
   Mermaid diagrams and code panels are forced into a narrow column and have to
   scroll horizontally.
2. **Architecture diagram has no enlarged view.** `MermaidDiagram` renders the
   SVG inline in the message stream at the parent's width. Users want to open
   the diagram in a larger view and zoom into details.
3. **No live progress checklist inside the plan.** The plan markdown today
   contains a `## Acceptance criteria` section but no actionable task list, and
   nothing updates as the coder agent makes progress. The user wants a GFM
   checkbox list (`- [ ]` / `- [x]`) inside the plan markdown that gets ticked
   off automatically by the coder agent as it finishes each piece of work —
   the same pattern Claude Code / Codex use for their TodoWrite tool.

The first two are purely frontend. The third spans planner prompt, coder tool,
state, WebSocket events and frontend rendering, but introduces **no new UI
components** — it reuses the existing markdown rendering pipeline via
`remark-gfm` (which already converts `- [x]` to `<input type="checkbox"
checked>` out of the box).

---

## 2. Goals & Non-Goals

### Goals

- Make the chat usable on wide displays (≥1440 px) without horizontal scroll on
  typical message content.
- Allow the user to click any rendered Mermaid diagram and view it in a larger
  panel with pan and zoom.
- Persist the approved plan as `{project_dir}/plan.md` on disk so the developer
  can open and edit it in their own editor.
- Inside that file, surface a GFM task list that the coder agent ticks off as
  it completes each task. The same updated content streams back to the chat,
  so the in-chat plan also shows the checkmarks live.

### Non-Goals

- No new "Tasks" UI sidebar / panel / widget. The task list lives **inside**
  the plan markdown only.
- No live frontend parsing or matching of phase events to task list lines.
  Frontend just renders whatever `plan_md` it currently has.
- No human-facing "click checkbox to toggle" interaction in the chat. The
  GFM-rendered checkboxes are read-only (the default for `remark-gfm`); humans
  toggle by editing the file on disk.
- No granular per-tool task updates. One tick = one logical user task completed
  by coder (typically a file written or a behavior wired up).

---

## 3. Design

### 3.1 Chat width

**Files:** `Eco.Toolchain/Eco.AI.Assembly1/frontend/components/chat/chat-interface.tsx`

Two changes in the same file:

| Where | From | To |
|-------|------|----|
| Messages container (line 177) | `mx-auto max-w-3xl px-4 py-6 space-y-5` | `mx-auto max-w-7xl px-6 lg:px-8 py-6 space-y-5` |
| Input dock (line 204) | `mx-auto max-w-3xl` | `mx-auto max-w-5xl px-6 lg:px-8` |

Rationale:

- `max-w-7xl` (~1280 px) for messages — accommodates rendered Mermaid, multi-
  column tables, and shows ~4× more code on screen than `max-w-3xl`. Still
  caps to prevent absurd line lengths on 4K+ ultrawides where 95+-char prose
  lines hurt readability.
- `max-w-5xl` (~1024 px) for input dock — the input is a single-line entry
  with a platform picker and send button. Wider than that and it looks like a
  search bar, not a chat input.
- `px-6 lg:px-8` paddings keep content off the edge on narrow viewports and
  give breathing room on large ones.

No breakpoint-specific `max-w` cascade — one good width beats three "almost
right" ones. If a user reports it's still too narrow at 4K, we revisit.

### 3.2 Zoomable Mermaid diagram

**Files:**
- `Eco.Toolchain/Eco.AI.Assembly1/frontend/components/chat/mermaid-diagram.tsx` (modify)
- `Eco.Toolchain/Eco.AI.Assembly1/frontend/components/chat/diagram-modal.tsx` (new)
- `Eco.Toolchain/Eco.AI.Assembly1/frontend/package.json` (add dep)

#### Inline view (unchanged behavior, with affordance)

Wrap the existing rendered SVG container in a `<button>` element. On hover
show a small "Click to expand" hint and an expand icon (lucide `Maximize2`)
overlayed in the top-right corner. Click opens the modal.

```tsx
<button
  type="button"
  onClick={() => setOpen(true)}
  className="group relative my-3 w-full overflow-x-auto rounded-md border border-slate-700/40 bg-slate-950/40 p-3 hover:border-slate-600 transition-colors"
>
  <div dangerouslySetInnerHTML={{ __html: svg }} />
  <span className="absolute right-2 top-2 opacity-0 group-hover:opacity-70 transition-opacity">
    <Maximize2 size={14} />
  </span>
</button>
```

Accessibility: button gets `aria-label="Open diagram in larger view"`.

#### Modal

New `<DiagramModal svg={string} onClose={...} />` component:

- Fullscreen overlay (`fixed inset-0 z-50 bg-black/80 backdrop-blur-sm`).
- Inner panel ~90 vw × 90 vh, glass-strong style consistent with settings
  sidebar.
- SVG rendered inside `react-zoom-pan-pinch`'s `TransformWrapper` →
  `TransformComponent`. Defaults: `initialScale=1`, `minScale=0.5`,
  `maxScale=8`, `wheel.step=0.1`.
- Top-right corner: `Reset zoom` button, `Close` (X) button.
- Closes on: X button, backdrop click, `Escape` key.

#### Dependency

Add `react-zoom-pan-pinch` (~5 KB gzipped, MIT, actively maintained, 1.5k
GitHub stars). Alternative would be hand-rolling `transform: scale/translate`
on pointer events — rejected because pinch-zoom on trackpads is fiddly and
the library handles touch/wheel/keyboard uniformly.

No PNG export in v1. The SVG itself is high-fidelity (vector) so the modal
satisfies the user's "I want to look at it bigger" need. PNG export can be
added later via `<canvas>` + `toBlob` if requested.

### 3.3 Live task checklist in `plan.md`

This is the biggest change. Three coordinated pieces: planner emits tasks,
coder ticks them, frontend re-renders.

#### 3.3.1 Planner: emit `## Задачи` section

**File:** `agent/v6/nodes/planner.py`

Extend `PLANNER_SYSTEM_PROMPT` so the plan MUST include a new section after
`## Acceptance criteria`:

```markdown
## Задачи

Concrete coding tasks for the coder agent. Each task gets a stable HTML
comment marker so the coder can flip its checkbox later.

- [ ] <!-- task-1 --> Implement CLI parser for `pow <base> <exp>` / `sqrt <x>` modes
- [ ] <!-- task-2 --> Load IEcoMathC89 via component factory
- [ ] <!-- task-3 --> Call `pVTbl1->pow(...)` / `pVTbl1->sqrt(...)`
- [ ] <!-- task-4 --> Format output with `%.6f` and handle negative-sqrt → `nan`
- [ ] <!-- task-5 --> Write Makefile that links Eco.Math.C89 statically
```

Rules added to the prompt:
- Tasks are **coding deliverables** the coder will produce — files written,
  functions implemented, behaviors wired. NOT setup/build/test phases (those
  are tracked elsewhere).
- Each task line must be `- [ ] <!-- task-N --> <description>` with N starting
  at 1 and incrementing. The HTML comment marker is the stable ID coder uses
  to tick the box.
- Typically 3-8 tasks. Don't over-decompose — one task ≈ one logical chunk
  of work, not one line of code.

#### 3.3.2 Persist `plan.md` to disk on approval

**Files:**
- `agent/v6/nodes/plan_gate.py` (extend — currently a pure `interrupt()`
  wrapper)
- `agent/v6/state.py` (already has `project_dir` and `project_name`)

After the user approves (or modifies + approves) the plan, `plan_gate`
currently returns `{"phase": "setup"}` (optionally with `plan_md`). Extend
it to also:

1. Compute `project_dir` (resolve to `./output/<project_name>` if not
   provided, matching what `setup_node:107` does today).
2. Create the directory.
3. Write the final `plan_md` (post-modification) to `{project_dir}/plan.md`.
4. Include `project_dir` in the returned delta so downstream nodes see it.

`setup_node` keeps its current `project_dir.mkdir(parents=True,
exist_ok=True)` line as a defensive no-op (idempotent), but the creation
authority moves to `plan_gate`. The setup node continues to download
packages as today; the only visible change is that the directory + plan.md
exist one node earlier in the pipeline.

#### 3.3.3 Coder: `mark_task_done` tool

**File:** `agent/v6/tools/coder.py`

Add a new tool:

```python
class MarkTaskDoneArgs(BaseModel):
    task_id: str = Field(..., description="Task marker, e.g. 'task-1' or 'task-3'")

def _mark_task_done(a: MarkTaskDoneArgs, plan_md_path: Path, on_update: Callable[[str], None]) -> ToolResult:
    if not plan_md_path.exists():
        return ToolResult(content=f"plan.md not found at {plan_md_path}", is_error=True)
    text = plan_md_path.read_text(encoding="utf-8")
    needle_unchecked = f"- [ ] <!-- {a.task_id} -->"
    needle_checked   = f"- [x] <!-- {a.task_id} -->"
    if needle_unchecked not in text:
        if needle_checked in text:
            return ToolResult(content=f"{a.task_id} already marked done — no-op", is_error=False)
        return ToolResult(content=f"task marker '{a.task_id}' not found in plan.md", is_error=True)
    new_text = text.replace(needle_unchecked, needle_checked, 1)
    plan_md_path.write_text(new_text, encoding="utf-8")
    on_update(new_text)  # ← streams plan_md_update event to frontend
    return ToolResult(content=f"marked {a.task_id} done", details={"task_id": a.task_id})
```

`make_coder_tools(...)` gains two new parameters: `plan_md_path: Path` and
`on_plan_md_update: Callable[[str], None]`. The latter is wired in
`agent/v6/nodes/coder.py` to call `writer({"type": "plan_md_update",
"plan_md": new_text})` so the LangGraph stream surfaces it through
`/ws/v6/chat`.

The CODER_SYSTEM_PROMPT gets a new section instructing the agent:

> When you complete each task listed in `## Задачи` of plan.md (located at
> `{plan_md_path}`), call `mark_task_done(task_id="task-N")` with the
> matching marker. Tick a task immediately after the work is verifiably done
> (file written, function wired, etc.) — don't wait until the end.

#### 3.3.4 WebSocket event + frontend rendering

**Files:**
- `backend/server.py` — add `plan_md_update` to event types it forwards.
- `frontend/components/chat/types.ts` — add `PlanMdUpdateEvent` to
  `ServerEvent` union and handle it.
- `frontend/components/chat/use-v6-socket.ts` — on `plan_md_update`, walk the
  message list and replace the `planMd` field of the most recent
  `plan_review` block.
- `frontend/components/chat/enhanced-markdown.tsx` — no change needed;
  `remark-gfm` already renders `- [x]` as a checked checkbox. Add minimal CSS
  so the rendered `<input type="checkbox">` doesn't look like a default
  browser control (style it as a small filled square with the existing
  emerald accent for `:checked`).

Event shape:

```ts
interface PlanMdUpdateEvent extends ServerEventBase {
  type: "plan_md_update";
  plan_md: string;
}
```

Frontend handler:

```ts
case "plan_md_update": {
  setMessages((prev) => updateBlock(
    prev,
    (b) => b.type === "plan_review",
    (b) => b.type === "plan_review" ? { ...b, planMd: ev.plan_md } : b,
  ));
  return;
}
```

Note: `updateBlock` already exists in `use-v6-socket.ts:60`. It updates ALL
matching blocks — fine, because in a normal session there's exactly one
`plan_review` block.

---

## 4. Data Flow

```
planner_node
   └─ emits plan_md with ## Задачи + [ ] <!-- task-N --> markers
      └─ V6State.plan_md updated
         └─ phase_change → awaiting_approval
            └─ frontend renders plan_review block (existing path)
plan_gate (interrupt + resume)
   └─ user approves (possibly with modifications)
      └─ create project_dir
      └─ write {project_dir}/plan.md
         └─ phase_change → setup
setup_node
   └─ pulls components (unchanged)
coder_node
   └─ make_coder_tools(plan_md_path={project_dir}/plan.md,
                       on_plan_md_update=writer-callback)
   └─ agent loop:
        - writes main.c, Makefile, etc. via write_file / edit_file
        - calls mark_task_done("task-1") when CLI parser ready
           ├─ flips [ ] → [x] in plan.md
           └─ emits plan_md_update event → ws → frontend updates plan_review block
        - calls mark_task_done("task-2") when factory wired
        - ...
        - mark_code_done(summary_md=...) when finished
builder/tester_node
   └─ unchanged
```

---

## 5. Error & Edge Cases

- **`mark_task_done` with unknown task_id** — tool returns `is_error=True`
  with the message "task marker not found"; coder retries with correct ID.
- **`mark_task_done` for already-completed task** — tool returns success with
  "already marked done — no-op"; idempotent.
- **User edits plan.md while coder is running** — last-write-wins. If user
  unchecks a box and coder then re-ticks it on next call, the file will
  reflect coder's view. We accept this; the file is primarily for human
  reading, not for human-as-controller. Document this in the user-visible
  prompt that introduces plan.md.
- **plan.md doesn't exist** (e.g., approval flow bug) — tool errors clearly;
  doesn't crash coder.
- **Plan modification on approval** — if the user edits the plan markdown in
  the approval UI, that's what gets written to plan.md. Coder works against
  the modified plan. Existing flow already passes `modified_plan_md` through
  `sendPlanDecision`; we just need to ensure `plan_gate` uses that as the
  source for the disk write.
- **Mermaid diagram with parse error** — modal not openable; the existing
  inline error display is sufficient.
- **Modal with very large SVG** — `react-zoom-pan-pinch` handles via
  scrollable transform container; no special handling needed.
- **Browser without `randomUUID`** — already covered by `newId()` fallback in
  `use-v6-socket.ts:17`.

---

## 6. Testing

### Frontend

- Visual regression: open chat at 1280, 1440, 1920, 2560 px viewport widths
  and confirm message column scales to ~1280, input dock to ~1024, and
  Mermaid diagrams expand without overflow.
- Manual: click diagram → modal opens; wheel zoom in/out; drag pan; Esc
  closes; backdrop click closes.
- Manual: send a planning request; after approval, watch checkboxes flip
  green as coder progresses. Refresh the page mid-run — last-known plan
  state should persist from the next `plan_md_update` event (existing thread
  resume covers this).

### Backend

- Unit test for `_mark_task_done`:
  - happy path: marker found, file rewritten, callback called with new text
  - idempotent path: already checked, returns ok
  - error path: unknown marker, returns error
  - error path: plan.md missing, returns error
- Unit test for plan_gate disk persistence:
  - approved plan writes `{project_dir}/plan.md` with exact content
  - modified plan writes the modified content, not the original

### Integration

- Run the existing end-to-end test (calculator example) and verify:
  - plan.md is created under `output/<project>/`
  - File contains `## Задачи` with checkboxes
  - By end of coder phase, all (or most) task checkboxes are ticked
  - Same content is visible in the chat via the in-place `plan_review`
    block update

---

## 7. Out of Scope (future work)

- PNG export from diagram modal.
- Per-tool granular progress (e.g., "wrote main.c" sub-task under "Implement
  CLI parser").
- Auto-collapse of completed task sections.
- Frontend reading plan.md directly from disk for offline browsing.
- Tester emitting `plan_md_update` to tick acceptance-criteria-style tasks
  (current scope: only coder owns ticking).
- Cross-session task list history view (the file on disk already serves
  this — `git diff plan.md`).

---

## 8. Open Questions

None remaining — user has clarified:
- Chat: "сделай правильным" → `max-w-7xl` (decided in design phase).
- Diagram: PNG vs expandable SVG → expandable SVG with zoom/pan (decided).
- Tasks: source / who-ticks / format → planner emits, coder ticks via
  dedicated tool, GFM checkboxes inside `plan.md` (decided).
