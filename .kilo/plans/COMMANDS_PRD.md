# COMMANDS_PRD.md — Chat Input Enhancements for the EcoOS ACOM Harness UI

> Status: Implementation-ready PRD. Scope: 4 features for the chat input dock.
> Target stack: Next.js 14 + React 18 + Tailwind (frontend), FastAPI + WebSocket (backend).

---

## 1. Confirmed design decisions (from stakeholder Q&A)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Attachment lifetime | **Session-scoped** — available to every message in the current session; **cleared on New Session**. |
| 2 | File content delivery | **Hybrid**: small text files (<40 KB) inlined into the prompt; large text files copied into `project_dir` and referenced by path (agent reads on demand); images copied into `project_dir` and referenced by path. |
| 3 | `+` file picker | **Extend the existing `FolderBrowser`** into a combined browser that lists files + dirs from the active project root with multi-select. |
| 4 | Image handling | **Copy to `project_dir/.eco-attachments` + path reference** in the prompt (no inline multimodal in v1). |

---

## 2. Current architecture (read before coding)

**Data flow (user → agent):**
1. `frontend/components/chat/chat-interface.tsx` — owns the `<textarea>`, the dock toolbar, header, and session/project state. `onSend()` (line 182) calls `sendUserRequest(input, {platform, language, mode, useWorktree, projectDir})`.
2. `frontend/components/chat/use-harness-socket.ts` (re-exported by `use-socket.ts`) — `sendUserRequest` (line 512) emits a `user_request` WS message of type `UserRequestMessage` (`types.ts:332`).
3. `backend/server.py` — `chat_endpoint` (`/ws/chat`, line 818) parses `user_request`, resolves `project_dir` (`_default_project_dir`/worktree/override, lines 1044–1094), then builds an agent **seed** string and runs the pipeline.
   - One-shot modes (test/review/code/plan): seed at `server.py:1146` → `(workspace + user_req)`.
   - AUTO pipeline: planner seed at `server.py:1203` → `workspace + user_req`; planner-retry seed at `server.py:1317`; coder seed at `server.py:1443` → `workspace + approved_plan_md + scaffold_note`.
4. The workspace header (`_workspace_header`, `server.py:643`) teaches the agent that `read`/grep/glob anchor at `project_dir` or `marketplace_cache`.

**Critical constraint (drives the hybrid design):** the agent `read` tool (`agent/internal/tools/code_search.py:368` `_read`) is sandboxed to `allowed_roots = [project_dir, marketplace_cache, …]`. A file **outside** `project_dir` cannot be read by the agent via tools. Therefore attached files must be **inlined** OR **copied into `project_dir`** to be usable. Copying into `project_dir/.eco-attachments/` makes them readable (path resolves inside `project_dir`).

**Existing helpers to reuse:**
- `backend/server.py`: `_allowed_roots()` (line 127), `_is_within_allowed()` (line 148), `_ensure_allowed()` (line 156), `_workspace_header()` (line 643).
- `frontend/components/chat/folder-browser.tsx` — directory-only modal, breadcrumb + allowed-roots filtering; base for the file picker.
- `frontend/components/chat/types.ts` — `FsListing`, `FsEntry`, `UserRequestMessage`, `ChatMessage`.

---

## 3. Shared changes: attachment model & backend delivery

### 3.1 Frontend attachment type (`frontend/components/chat/types.ts`)
Add:
```ts
export type AttachmentKind = "text" | "image";
export interface Attachment {
  id: string;                 // crypto.randomUUID()
  name: string;              // display name / file name
  path?: string;             // absolute path (mention / picker); absent for paste
  kind: AttachmentKind;
  mime?: string;
  size?: number;
  content?: string;          // pasted payload (base64 data URL for images, or text)
  previewUrl?: string;       // object URL for image thumbnail in chip
  source: "mention" | "picker" | "paste" | "drop";
}
```
Also extend `ChatMessage` (types.ts:189) with `attachments?: Attachment[]` so the user bubble can render what was sent.

### 3.2 `UserRequestMessage` (types.ts:332) — add field
```ts
attached_files?: Array<{
  name: string;
  path?: string;
  kind: AttachmentKind;
  mime?: string;
  size?: number;
  content?: string;   // for paste-only attachments (no path)
}>;
```

### 3.3 `use-harness-socket.ts` — extend `sendUserRequest`
- Add `attachedFiles?: Attachment[]` to the options object (lines 512–523).
- In the emitted payload, add `attached_files: attachedFiles?.map(a => ({ name, path, kind, mime, size, content })) ?? []`.

### 3.4 `chat-interface.tsx` — new state & wiring
- Add `const [attachments, setAttachments] = useState<Attachment[]>([])` and a `addAttachment(a)` helper that dedupes by `path` (or `name+size` for paste) and appends.
- `onSend()` (line 182) passes `attachedFiles: attachments` to `sendUserRequest`.
- Render attachment **chips** in a row directly above the `<textarea>` (inside the dock `div` at line 388) with a remove (×) control that updates `setAttachments`.
- `UserBubble` (line 511) **must** render the message's attachments as chips (text = filename, image = thumbnail) so the user sees what was sent. To enable this, `use-harness-socket.ts` (line 526) must store `attachments` on the emitted user `ChatMessage` (`{ id, role:"user", text, blocks:[], attachments }`), and `sendUserRequest` must pass the `attachments` array through to that object.
- **Budget hint (UX):** compute the sum of attachment sizes; when it exceeds ~150 KB show a small amber note near the chips ("Large context — big files will be referenced, not inlined"). This pre-warns about token cost without blocking the send.
- Dedupe rule in `addAttachment`: drop if an existing item has the same `path` (mention/picker) or same `name+size` (paste/drop).

### 3.5 Backend: `_build_attached_block` (`backend/server.py`)
Add a helper (near `_workspace_header`, ~line 689):
```python
ATTACH_INLINE_LIMIT = 40_000        # per-file inline cap (bytes)
ATTACH_TOTAL_INLINE_LIMIT = 200_000 # session-wide inline cap
ATTACH_MAX_CONTENT = 25_000_000     # hard cap on pasted disk content (server-side)

def _build_attached_block(attached, project_dir: Path) -> str:
    """attached: list[dict] from UserRequestMessage.attached_files.
    Returns a prompt block string (possibly empty). Writes/copies files into
    project_dir/.eco-attachments so the agent can read them via tools."""
```

> **Basename-collision handling (added):** `_safe_attach_name` strips directory
> components, so two attachments that share a basename (e.g. a `@`-mention
> `src/a.txt` and a pasted `a.txt`) would otherwise clobber the same
> `.eco-attachments/a.txt`. The helper therefore de-duplicates written names
> (`a.txt` → `a-2.txt`, `a-3.txt`, …) and references each file by its unique
> name, so every prompt line points at the correct content.
>
> **Disk-write cap (added):** the inline caps gate only *inlining*; path-only
> items write client `content` of any size. A server-side `ATTACH_MAX_CONTENT`
> (~25 MB) hard-limits what is written to disk — pasted content or files larger
> than this are skipped with a warning. (The 5 MB client cap is a UX guard and
> is bypassable, hence the server cap.)
**Security (mandatory):** For every item carrying a `path`, the backend MUST call `_ensure_allowed(Path(path).expanduser().resolve())` (server.py:156) before reading/copying. If the path is outside the allowed roots (home / output root / `HARNESS_ALLOWED_ROOTS`), **skip that item** and record a warning — never read arbitrary server files in response to a client-supplied path. Pasted `content` is client-provided bytes and is safe to write (it is not read from disk).

Behavior:
1. If `not attached`: return `""`.
2. Create `att_dir = project_dir / ".eco-attachments"`; `att_dir.mkdir(parents=True, exist_ok=True)`.
3. For each item compute how it reaches the agent, preferring the **most token-efficient** option that still guarantees availability:
   - **File already inside `project_dir`** (resolved `path` is equal to or under `project_dir`): **reference by its real relative path only** — do NOT inline and do NOT copy. The agent's `read` tool anchors relative paths at `project_dir` (code_search.py:452), so `read(path='<relpath>')` works directly. Most token-optimal.
   - **text + `content` provided (paste):** decode (base64 for images / text) → write `att_dir/name`; reference `read(path='.eco-attachments/<name>')`. If it is small text (`len ≤ ATTACH_INLINE_LIMIT`), inline it instead of referencing (guarantees availability without a tool call).
   - **text + `path` outside `project_dir`:** read bytes (after the security check). If `len ≤ ATTACH_INLINE_LIMIT` → inline; else copy to `att_dir/name` and reference the copy.
   - **image (paste `content` or outside `path`):** decode/write or copy into `att_dir/name`; reference `.eco-attachments/<name>` as a visual reference (no inline in v1 — decision #4).
   - Track `inline_budget` against `ATTACH_TOTAL_INLINE_LIMIT`; once exceeded, force path-only (reference) for the remaining items even if small.
4. Build block:
   ```
   === Attached files (user-provided session context) ===
   The user explicitly attached these files. They are available to you:
   - <name> [text, N bytes] — inline:
     <content or first 4KB + "…(truncated, read full via read(path='.eco-attachments/<name>'))">
   - <name> [text, N bytes] — path-only: read(path='<relpath or .eco-attachments/<name>')
   - <name> [image] — visual reference at .eco-attachments/<name>
   ```

### 3.6 Inject block into every seed (server.py)
In `chat_endpoint`, after `project_dir` is finalized (post worktree, ~line 1094) and before mode dispatch, compute:
```python
attached_block = _build_attached_block(payload.get("attached_files"), project_dir)
```
Then prepend `attached_block` to:
- **AUTO chat-reply branch** (`server.py:1184` — the intent gate classified the message as plain CHAT): `_chat_reply` is called with just `user_req`; prepend `attached_block` to that input so attached context is not silently dropped on questions.
- one-shot seed (`server.py:1146`): `workspace + attached_block + user_req`
- AUTO initial (`server.py:1203`): `workspace + attached_block + user_req`
- planner-retry (`server.py:1317`): `workspace + attached_block + user_req + feedback`
- coder seed (`server.py:1443`): `workspace + attached_block + approved_plan_md + scaffold_note`

> Attachments are session-scoped: the frontend sends `attached_files` on **every** `user_request`, so each run rebuilds the block. This keeps planner + coder seeds both aware of the context.

---

## 4. Feature 1 — `@` file-mention autocomplete

### 4.1 Backend file search — `GET /api/fs/search` (`backend/server.py`)

**Search backend abstraction (recommended).** Implement a small `FileSearchBackend` protocol so the engine is swappable without rewriting the endpoint. Two implementations:
- **`os_walk` (DEFAULT)** — hand-rolled recursive `os.walk` (§4.1a). Zero dependencies, secure, adequate for the active-project root (the common case).
- **`fff` (OPT-IN)** — [FFF `fff-search`](https://pypi.org/project/fff-search/) (MIT, PyO3/Maturin `abi3` wheel, Python ≥3.10) for keystroke-reactive, typo-tolerant, frecency-ranked search (§4.1b). Enabled via env `FILE_SEARCH_BACKEND=fff`; requires `fff-search` added to deps/lock.

Signature (engine-agnostic):
```
GET /api/fs/search?q=<fragment>&root=<optional>&limit=50&depth=8&backend=os_walk|fff
```
- `root` defaults to first allowed root (`_allowed_roots()[0]`, i.e. home); if provided, `_ensure_allowed(Path(root))`.
- Return **files only**, each `{name, path, size, mtime}`, plus `{root, truncated, backend}`.
- Security: every returned `path` must resolve within allowed roots (enforced by both backends).

#### 4.1a `os_walk` backend (default)
- `os.walk` with **pruning**: hidden dirs (`name.startswith(".")`), symlinks, and heavy dirs (`node_modules`, `.git`, `__pycache__`, `.venv`, `marketplace_cache`). Enforce `depth` and a hard cap on visited files.
- Match (case-insensitive): rank 0 = substring of **basename**; rank 1 = substring of **relative path**.
- Sort by rank, then path; truncate to `limit`.
- Require `len(q) >= 1` (UI may require ≥2 to avoid full scans of large roots).

#### 4.1b `fff` backend (opt-in)
- On first use (or lazily at startup) build `fff.FFFIndex(path)` **per allowed root**; cache in a module-level `dict[root] -> FFFIndex`. Rely on FFF's background watcher thread to keep each index live (no per-query disk walk).
  - Guard: `try: import fff` — if the wheel is missing, **fall back to `os_walk`** and log a warning (keeps the service functional with zero native deps by default).
- `results = index.file_search(query=q)` → map `FileItem.relative_path`/`score` to the response shape; filter to the requested `root` (and allowed roots) before returning.
- Use FFF's native scoring (typo-resistant + frecency) directly; no need to re-rank.

#### 4.1c Analysis — `os_walk` vs FFF (for the `@`-mention UI)
| Dimension | `os_walk` (baseline) | FFF (`fff-search`) |
|---|---|---|
| Dependencies | none (stdlib) | native Rust `abi3` wheel (MIT; prebuilt, no Rust toolchain at install) |
| Speed / keystroke reactivity | fresh `os.walk` per query; fine for focused project dir, **slow on large roots** (e.g. home fallback) | persistent in-memory index + watcher → ms-level re-eval on every keystroke |
| Ranking | exact substring, basename>path | fuzzy, **typo-resistant**, **frecency**-ranked |
| Fit with this codebase | matches the project's deliberate "lean pure-Python" stance (Dockerfile has no Rust toolchain; ChromaDB/LangChain were retired to stay minimal) | introduces a native module into the server process (supply-chain trust, ABI/glibc coupling to the `python:3.11-slim-bookworm` image) |
| Operational cost | none | add `fff-search` to `requirements` + regenerate `requirements.lock`; manage per-root index lifecycle |
| Over-engineering risk | meets the spec (filename/path substring, live updates) | frecency/typo are nice-to-have, not required by the spec |

**Recommendation:** ship `os_walk` as the default (zero-risk, satisfies the requirement), expose FFF behind the `FileSearchBackend` seam as an opt-in performance upgrade for large roots / better UX. This keeps the default deployment lean while allowing FFF with a one-line config + dependency add.

### 4.2 Frontend: mention state machine (`chat-interface.tsx`)
Add state:
```ts
const [mention, setMention] = useState<{
  active: boolean; query: string; start: number; index: number;
} | null>(null);
const [mentionHits, setMentionHits] = useState<FsEntry[]>([]);
```
**Trigger detection** (in the textarea `onChange` handler, ~line 394): after `setInput`, scan backwards from the caret for the last `@` that is at string start or preceded by whitespace AND has no whitespace between it and the caret. If found:
- `mention = {active:true, query: text.slice(atPos+1, caret), start: atPos, index:0}`.
- Else `mention = null`.

**Fetch** (debounced ~150 ms when `mention.active && mention.query`):
```ts
fetch(`${API_URL}/api/fs/search?q=${enc(mention.query)}&root=${enc(activeProject?.path ?? "")}`)
```
Store into `mentionHits`. Reset `index` to 0 on new results.

**Keyboard handling** — extend the textarea `onKeyDown` (line 395): if `mention?.active`:
- `ArrowDown`/`ArrowUp`: `preventDefault()`, move `mention.index` (wrap within `mentionHits.length`).
- `Enter` **or** `Tab`: `preventDefault()`, call `selectMention(mentionHits[mention.index])`.
- `Escape`: `preventDefault()`, `setMention(null)`.

**`selectMention(hit)`**:
- Replace `input` substring `[mention.start .. caret]` with `@<relativePath> ` where `relativePath` is `hit.path` relative to the active project root (fallback absolute). 
- `addAttachment({id, name: hit.name, path: hit.path, kind: guessKind(hit.name), source:"mention"})`.
- `setMention(null)`, keep focus in textarea, place caret after the inserted token.

**Popover UI**: a small absolutely-positioned panel anchored **above** the textarea (inside the dock `div`), listing `mentionHits` with name + relative path + size, highlighting `mention.index`. Clicking a row calls `selectMention`. Show "No matches" when empty. Close on blur/outside-click/Escape. Reuse `cn`, `lucide` icons (`File`, `Folder`) and the existing `glass-strong` styling.

**Focus retention (important):** attach `onMouseDown={(e) => e.preventDefault()}` to each suggestion row (and the popover) so clicking a suggestion does **not** blur the textarea — otherwise the `blur` handler would close the popup before `click`/`selectMention` fires. Keyboard selection (Enter/Tab) is unaffected.

Implement as a small inline component `MentionPopover` in `chat-interface.tsx` (or a new `file-mention.tsx`) — keep it within the chat module.

---

## 5. Feature 2 — `+` button → FileBrowser (extend `FolderBrowser`)

### 5.1 Backend: extend `GET /api/fs/browse` (`server.py:166`)
Add query param `files: bool = False`. When `True`, include file entries in `entries` (currently dirs only). Update `FsEntry` (`types.ts:396`) to:
```ts
export interface FsEntry {
  name: string; path: string;
  type: "dir" | "file";
  size?: number;
}
```
Apply the same hidden/symlink filters; for files skip hidden names too. Directory entries keep `type:"dir"`.

### 5.2 Frontend: extend `FolderBrowser` in place
Rather than a second component, add optional props to the existing `frontend/components/chat/folder-browser.tsx` (it already has the breadcrumb + allowed-roots + loading/error UI we want to reuse). New props:
```ts
interface FolderBrowserProps {
  onClose: () => void;
  onAdded?: (project: {path:string;name:string;id:string}) => void; // existing dir mode
  mode?: "dir" | "file";            // default "dir" (preserves current behavior)
  allowMultiple?: boolean;         // default false
  onFilesSelected?: (files: {path:string;name:string;size:number}[]) => void;
}
```
Changes inside:
- `fetchListing` (line 37) appends `&files=1` when `mode === "file"` (consumes the extended `GET /api/fs/browse`).
- Directory rows: navigate (drill in) as today — in file mode a click (or double-click) on a directory still navigates so the user can traverse folders.
- File rows (mode `"file"`): render from `entry.type === "file"` entries; clicking toggles membership in a `selected: Set<string>` and shows a check/checkbox; disabled when `!allowMultiple` and another is selected (or simply ignore multi when `allowMultiple` is false).
- Footer button label/action adapts: dir mode → existing `selectFolder()` (calls `onAdded`); file mode → "Add N files" → calls `onFilesSelected([...selected])`.
- Reuses breadcrumb, allowed-roots filtering, error/loading states unchanged.

### 5.3 Wire the `+` button
- In `chat-interface.tsx`, add a `+` icon button in the dock toolbar row (line 404), left side (before `PlatformSelector`), disabled while `isProcessing`.
- On click, open `FolderBrowser` (the extended component) in `mode="file" allowMultiple onFilesSelected={(files)=>{ files.forEach(f => addAttachment({id, name:f.name, path:f.path, kind:guessKind(f.name), size:f.size, source:"picker"})); setBrowserOpen(false); }}`.
- `guessKind(name)`: image extension (`png|jpg|jpeg|gif|webp|bmp|svg`) → `"image"`, else `"text"`.
- Root the browser at `activeProject?.path` (falls back to home via backend default).

---

## 6. Feature 3 — paste & drop text + images

### 6.1 Paste handler (textarea, `chat-interface.tsx`)
Add `onPaste` to the `<textarea>`:
```ts
const onPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
  const items = Array.from(e.clipboardData.items);
  let handled = false;
  for (const it of items) {
    if (it.kind === "file" && it.type.startsWith("image/")) {
      handled = true;
      const file = it.getAsFile();
      if (file) addPastedFile(file, "image");
    } else if (it.kind === "file" && it.type.startsWith("text/")) {
      handled = true;
      const file = it.getAsFile();
      if (file) addPastedFile(file, "text");
    }
  }
  // plain text paste: let default insertion happen (do not preventDefault)
  if (handled) e.preventDefault();
};
```
`addPastedFile(file, kind)`:
- Generate `id = crypto.randomUUID()`, `name = file.name || (kind==="image"?`pasted-${Date.now()}.png`:`pasted-${Date.now()}.txt`)`.
- Read via `FileReader`:
  - image → `readAsDataURL` → store `content` (data URL) + create `previewUrl = URL.createObjectURL(file)` for the chip thumbnail; warn/reject if `file.size > 5 MB`.
  - text → `readAsText` → store `content` (raw text, truncated preview only in chip).
- `addAttachment({id, name, kind, mime:file.type, size:file.size, content, previewUrl, source:"paste"})`.

### 6.2 Drag & drop (optional but recommended)
Add `onDrop`/`onDragOver` on the dock container (line 388) mirroring `addPastedFile` over `e.dataTransfer.files`. `preventDefault` on `dragover`.

### 6.3 Backend handling of pasted `content`
Already covered by §3.5: pasted `content` (text or base64 image) is written into `project_dir/.eco-attachments/<name>` and referenced. Text content is inlined when small.

---

## 7. Feature 4 — "New Session" button

### 7.1 Behavior
Add a clearly labeled **"New Session"** button in the header (near `Settings`, ~line 323). It performs:
1. If `isProcessing`: disable the button (consistent with other controls) — do **not** silently abort. (Alternatively call `sendAbort()` then reset; choose disable for safety.)
2. Call existing `clearMessages()` (`use-harness-socket.ts:584`) — this resets `messages`, `currentPhase`, `completedPhases`, `worktree`, removes `thread_id` from sessionStorage, and **rolls a fresh thread** by reconnecting the WS.
3. **Additionally** `setAttachments([])` — attachments are session-scoped and cleared on New Session (decision #1).
4. **Do NOT reset** `platform` / `language` / `mode` / `useWorktree` (inherited from currently shown session) nor `AgentSettings` (persisted via localStorage + `PUT /config/workspace`). **Do NOT reset** `activeProject` selection.

> The existing `RotateCcw` icon (line 313, titled "New session") is redundant/ambiguous. Replace it with the explicit labeled "New Session" button (keep `clearMessages` as the underlying action). If no current session exists (no messages/thread yet), New Session simply guarantees a fresh thread with the inherited (default) settings.

### 7.2 Inheritance semantics
"Currently shown session" = the in-memory UI settings at click time (they already persist across `clearMessages`). "Default settings" = the component's initial state values when nothing has been changed. Because settings already persist in `localStorage`/component state, inheritance is automatic; no extra storage is required. Document this in code comments.

---

## 8. Validation plan

- **Unit/integration (backend):** hit `/api/fs/search?q=main` returns files within the active project, excludes `.git`/`node_modules`, respects `limit`. `/api/fs/browse?files=1` returns mixed `type`.
- **Attachment delivery:** send a `user_request` with `attached_files` containing (a) a small text file → assert its content appears inlined in the planner/coder seed logs (`traces/` or server log); (b) a large text file → assert a copy exists at `project_dir/.eco-attachments/` and the prompt contains the path reference, not full content; (c) an image → assert copy at `.eco-attachments/` and path note.
- **Frontend:** type `@` → popover opens; type `foo` → results filter; ArrowDown/Up + Enter inserts `@relativePath` and adds a chip; `+` opens FileBrowser in file mode, multi-select adds chips; paste an image → chip with thumbnail; paste text → inserted normally + (if file) chip; "New Session" clears messages + chips but keeps platform/language/mode and active project.
- **Manual E2E:** attach a source file via `@`, ask the agent to explain it; confirm the agent references/reads the file correctly (no "outside project_dir" error).

---

## 9. Risks & open questions

- **Search cost:** recursively walking `home` is expensive. Mitigate via `depth`/`limit` caps, skipping heavy dirs, and requiring `q` length ≥ 2 before querying. If the active project is unset, default root to home but keep caps tight.
- **Context bloat:** inlining is capped (40 KB/file, 200 KB total) with automatic fallback to path-only; the agent is told to `read()` large files on demand.
- **WS payload size:** pasted images are base64 inside the JSON WS message — cap at 5 MB and warn; large images should be added via the `+` picker (path-only) instead.
- **Multimodal:** v1 references image paths only (decision #4). If a future model wrapper supports vision, upgrade `_build_attached_block` to emit image content blocks — out of scope here.
- **Hidden/symlink safety:** search & browse both prune hidden dirs and symlinks, consistent with existing `fs_browse`.

## 10. Out of scope (future)

- Semantic RAG indexing of attachments.
- In-UI viewing/editing of attached file contents.
- Per-file token budgeting / automatic summarization of attached files.
- Cross-session attachment persistence.
