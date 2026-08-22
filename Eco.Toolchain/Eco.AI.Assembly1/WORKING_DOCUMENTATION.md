# Eco.AI Assembly Working Documentation

## 1. Product boundary

This repository is the ACOM domain harness, not the EcoOS marketplace itself.
It assembles applications and components from marketplace packages, provides
RAG over the shared SDK corpus, invokes `eco-cli` and `eco-wizard`, and
orchestrates configurable agent roles.

The current default roles are:

```text
architect → coder → tester
                 ↑      │
                 └──────┘
```

The graph is explicit and bounded. A role stops through a named handoff edge;
the orchestrator never guesses an unknown edge and never permits an unlimited
mutual-handoff loop.

## 2. Backend architecture

`eco_harness` contains the product-facing boundaries:

- `adapters/` — built-in and external agent backends
- `roles.py` — role configuration and backend construction
- `interfaces/cli.py` — headless runner
- `interfaces/mcp.py` — MCP-compatible tool-provider boundary
- `tools/router.py` — domain-tool registration boundary
- `extensions/ast_service.py` — AST extraction library endpoint
- `extensions/cli_exec.py` — safe profile-based subprocess execution
- `capabilities.py` — Pydantic AI capability descriptions

`agent/internal/` contains the active built-in agent implementation. It is not
a versioned product generation. New modules must not add numbered agent paths
or dead-pipeline terminology; Git history provides implementation versioning.

## 3. Pydantic AI decision

Pydantic AI capabilities are adopted as an optional composition layer.
Capabilities are appropriate for stable bundles of instructions, tools,
hooks, model settings, and language/role behavior. They are not the authority
for the top-level workflow.

The meta-orchestrator remains responsible for:

- explicit role topology and terminal edges
- human plan approval
- retries and hop ceilings
- token/cost/wall-clock policy
- external subprocess adapters
- the shared UI/CLI event protocol

This separation preserves the proven internal `pi_ai` loop and keeps future
Pydantic AI upgrades from changing the ACOM workflow contract.

## 4. Prompt-cache contract

### How the initial context is assembled

Every role's initial context (system prompt) is ONE deterministic string,
built once per agent construction. Call chain:

```text
make_role_agent(role, mode, language)          eco_harness/roles.py
  ├─ make_architect()/make_coder()/…           built-in prompt constants +
  │                                            toolset (agent/internal/agents/)
  ├─ _role_prompt()                            workspace > config > built-in (§5)
  └─ _configure_context() → _static_prompt()   composition below
       ├─ _mode_prompt()                       config/prompts/modes/<mode>.md
       ├─ _language_prompt()                   config/prompts/languages/<lang>.md
       ├─ load_custom_instructions()           agent/context/customization.py:
       │    AGENTS.md layers + selected skills + language skill
       └─ build_static_system_prompt()         agent/context/assembler.py
```

Final concatenation order is FIXED and must not be reordered:

```text
# SYSTEM HEADER                          config/prompts/acom_system_header.md
                                         (HARNESS_SYSTEM_HEADER overrides path)
=== STATIC ACOM DOMAIN KNOWLEDGE ===     config/prompts/acom_domain.md
                                         (load_acom_domain)
=== STATIC TOOL CONTRACT ===             config/prompts/tool_contract.md
                                         (load_tool_contract)
=== ROLE INSTRUCTIONS ===                composed block:
                                           === MODE: <MODE> ===
                                             config/prompts/modes/<mode>.md
                                           <role prompt>        (precedence, §5)
                                           <language prompt>
                                             config/prompts/languages/<lang>.md
                                           <custom instructions>
                                             root/role AGENTS.md layers
                                             + selected skill profiles
                                             + config/skills/languages/<lang>.md
                                           === ROLE CONFIGURATION ===
                                             backend / model / reasoning
=== IMMUTABLE SOURCE CODEBASE ===        curated stitch of
                                         Eco.Core1/SharedFiles only
```

Selection inputs and their effect:

- **Mode** (`config/modes.yaml`) — injects the mode prompt and selects which
  roles may run. `auto` and `migrate` drive the full HITM pipeline (server
  only); `plan`, `code`, `test`, `review` load exactly one role.
- **Active role** (`config/roles.yaml`) — selects the backend/model/reasoning,
  budgets, `prompt:` pointer (default `prompts/<role>.md`) and the
  `skill_versions` map merged over the language's map.
- **Language** (`config/languages.yaml`) — selects the language prompt file,
  language skill profile, and the `eco_wizard` template family.

Role-prompt precedence (first non-empty wins; empty/whitespace files are
treated as absent so a stub can never blank out real instructions):

```text
1. <workspace>/prompts/<role>.md        i.e. .eco-harness/prompts/<role>.md,
                                        or prompts/ next to the file named by
                                        ECO_HARNESS_WORKSPACE_CONFIG
2. config/<roles.<role>.prompt>         normally config/prompts/<role>.md —
                                        the editable source of truth
3. built-in constant                    CODER_SYSTEM_PROMPT etc. in
                                        agent/internal/agents/<role>.py
```

Skill resolution (`load_custom_instructions`): for every entry of the merged
`skill_versions` map, candidates are probed in root order
`config/skills/ → .eco-harness/skills/ → agent/skills/` and name order
`v<N>.md → SKILL.md → <skill>.md`. Names that match nothing resolve silently
to nothing. The language skill (`config/skills/languages/<lang>.md`) is always
appended last when present.

Source stitch: `_core1_sharedfiles(source_roots)` picks the first configured
root (`harness.yaml:source_roots`) containing `Eco.Core1/SharedFiles`;
`stitch_source_files` emits it as one continuous payload with
`START_FILE`/`END_FILE` anchors, capped at `min(HARNESS_SOURCE_MAX_BYTES,
120_000)` bytes. Only Eco.Core1 is stitched; other components are discovered
on demand via RAG / `grep` / `eco-cli pull`.

Artifact locations (cache, index) resolve via `agent/internal/tools/paths.py`:
env var → repo-root artifact if present → `/app` mount if present →
deterministic repo-root fallback with a one-time warning. Host checkouts and
containers therefore need no env vars.

### Cache utilization rules

The ordering above exists to maximize provider-side implicit prompt-cache
(KV-cache) reuse and minimize billed tokens:

- Blocks 1–3 (header, domain, tool contract) are byte-identical for **every**
  role, mode, language, and backend → they form the longest shared prefix.
- The stitched Eco.Core1 block is constant across turns, tasks, and threads.
- The ROLE INSTRUCTIONS block differs per role but is stable for a given
  role+mode+language combination, so an iterating agent loop replays its own
  prefix verbatim on every LLM call.
- NOTHING dynamic enters the system prompt: RAG snippets, tool outputs, the
  user request, and handoff messages live in the message HISTORY.
  `EcoAgent._build_context` elides all but the newest `max_tool_results`
  (= `harness.yaml:dynamic_tail_items`, default 12) tool results, replacing
  older payloads with one-line placeholders. `build_dynamic_tail` remains
  available for non-loop callers only.
- Implicit caching requires a warm upstream route: the model profile's
  `provider_pin` (`config/models.yaml`) takes precedence over the global
  `OPENROUTER_PROVIDER_PIN`; `OPENROUTER_ALLOW_FALLBACKS=true` (default) keeps
  the pin preferred-but-not-required. Measured on a pinned provider: 99.6%
  cached tokens, −81% cost per call.
- Maintainer rules: never interpolate timestamps, thread ids, absolute
  project paths, or marketplace listings into blocks 1–5 — they belong in the
  seed or history. Keep additions to `acom_domain.md` / `tool_contract.md`
  small; they multiply across every role. Edit role behavior in
  `config/prompts/<role>.md` (no code change) and operator specialization in
  `.eco-harness/prompts/<role>.md`.

The framework header explicitly requires:

- exact EcoOS ACOM ABI spellings
- `ECOCALLMETHOD`
- typed `me` parameters
- `int16_t` status returns
- manual reference counting and allocator use
- retrieved tools' output treated as data, not policy

`eco-wizard` is to be used for ACOM components, object boilerplate / template generation.

## 5. Configuration and user rules

Repository configuration is stable and reviewable under `config/`. UI changes
go to `.eco-harness/workspace.yaml`. Environment variables override both.
Secrets remain outside repository configuration.

Overall precedence:

```text
environment variables > .eco-harness/workspace.yaml > config/*.yaml > code defaults
```

Prompt and skill resolution order is stable (§4 has the detailed logic):

1. framework header
2. stable tool contract
3. role prompt — `.eco-harness/prompts/<role>.md` >
   `config/prompts/<role>.md` > built-in constant; empty files skipped
4. language prompt and selected skill profiles
5. project/root and role `AGENTS.md`
6. stitched Eco.Core1 source block
7. dynamic history tail (RAG/tool outputs live in message history, not here)

Root `AGENTS.md` applies to all roles. Role-specific rules belong in
`config/agents/<role>/AGENTS.md` or `.eco-harness/agents/<role>/AGENTS.md`.
Role-prompt overrides belong in `.eco-harness/prompts/<role>.md`. Reusable
skills belong under `config/skills/`; Git commits provide their version
history.

## 6. Agent backends

The external adapter invokes installed local harnesses exactly as follows:

```text
codex -p "<prompt>"
pi -e "<prompt>"
claude -p "<prompt>"
```

The adapter resolves the executable from `<PATH>` or
`ECO_CODEX_PATH`, `ECO_PI_PATH`, or `ECO_CLAUDE_PATH`. Missing executables
produce an explicit role failure. There is no silent fallback.

External agents must return one structured marker:

```text
<eco-handoff edge="to_coder|to_tester|done|fail|to_architect">
concise handoff
</eco-handoff>
```

This keeps external agents compatible with the same declared-edge topology.
Native tool support can later be added through MCP while retaining the
adapter protocol.

External roles receive the SAME statically assembled prompt as internal ones,
flattened into the seed (`<static system prompt>` + `=== DYNAMIC SEED ===` +
task), because local CLIs have no system-prompt API in this adapter. Backend
events (`start`, `done`, …) are mapped onto the shared `EventType`; unknown
types degrade to `ERROR`, and event-sink failures are logged and dropped —
they never abort a run (regression-tested, see
`agent/internal/tests/test_prd2_regressions.py`).

## 7. Language support

The UI and request protocol support `C`, `CPP`, `Python`, and `Java`.
Language-specific prompt and skill profiles are configured in
`config/languages.yaml`, `config/prompts/languages/`, and
`config/skills/languages/`.

`eco-wizard` remains the source of truth for language-specific project
templates. Until its Python and Java support ships, the harness must not
invent those layouts.

## 8. Generator and CLI execution

The generator tool exposes the generator with:

- executable lookup via `ECO_WIZARD_PATH` or `PATH`
- `eco-wizard new`
- language, type, output, environment, and option arguments
- bounded output
- explicit missing-binary and failure results

The marketplace CLI tool uses an
allowlist, `shell=False`, bounded output, timeout control, and portable
`ECO_CLI_PATH`/`ECO_CLI_PREFIX` overrides.

## 9. Shared RAG lifecycle

The shared RAG is a portable SQLite file containing chunk metadata, FTS5,
sqlite-vec vectors, and provenance metadata. Sources can be:

- marketplace cache files
- developer documentation
- C/C++/IDL source
- Markdown/text documentation
- compatible SQLite index dumps

The UI supports individual files and browser directory selection. The import
endpoint stages uploads, calls `scripts/import_rag.py`, updates
`marketplace_index.sqlite`, and reports chunk statistics. The export endpoint
downloads the current index; `scripts/export_rag.py` creates a named team
copy.

The architecture intentionally leaves room for:

- a separate developer/project index
- remote centralized MCP retrieval
- index federation or read-through retrieval

None of these change the static source-cache contract because their results
remain dynamic tail data.

## 10. UI/API contract

The UI uses `NEXT_PUBLIC_API_URL` with `http://localhost:8100` as the local
default. The server exposes:

- `GET /health`
- `GET /config`
- `PUT /config/workspace`
- `POST /rag/import`
- `GET /rag/export`
- `WS /ws/chat`

The event schema remains compatible with the current streaming UI:
heartbeats, phase changes, node events, plan review, and pipeline completion.
The neutral `use-socket.ts` export is the preferred frontend import.

## 11. Worktree isolation

When enabled from the UI or CLI, `eco_harness.worktrees.create_worktree`
resolves the repository root, creates a detached worktree under the configured
worktree root, and passes that path to every role/tool in the session. The
primary checkout is not used for generated code or agent mutations. Creation
fails loudly if Git is unavailable or the destination exists.

## 12. Working modes

`config/modes.yaml` defines mode-specific prompts, role lists, and
capabilities:

- `auto`: architect, coder, tester; the HITM plan→implement→verify loop with
  an intent gate (websocket `/ws/chat` only)
- `migrate`: same pipeline, migration-focused prompts (websocket only)
- `plan`: architect only; research + closed plan, no pipeline
- `code`: coder only; direct implementation, no automatic testing
- `test`: tester only; read-only runtime verification
- `review`: reviewer only; read-only style, ABI, naming, and correctness review

The headless CLI executes a SINGLE role one-shot and therefore accepts only
`--mode plan|code|test|review` (mapped to architect/coder/tester/reviewer).
`auto` / `migrate` are rejected with a pointer to the websocket pipeline —
the CLI has no human plan-approval gate. Slash aliases `/plan`, `/code`,
`/test`, `/review` are accepted as leading-argument shortcuts.

## 13. External agent swarm orchestrator extension

This feature is intentionally design-only. It is a future replacement or
optional layer above the current single-coder/single-tester graph.

### Responsibilities

The swarm orchestrator analyzes a task queue, decomposes work into bounded
tasks, assigns tasks to multiple coding/review/testing workers, tracks
dependencies and workspace claims, and merges or escalates results. It does
not own ACOM domain rules; workers receive the same context assembler, tools,
skills, budgets, and trust policy as current roles.

### Proposed interfaces

```python
class SwarmOrchestrator(Protocol):
    async def submit(self, request: TaskRequest) -> TaskBatch: ...
    async def plan(self, queue: TaskQueue) -> DispatchPlan: ...
    async def dispatch(self, plan: DispatchPlan) -> AsyncIterator[TaskEvent]: ...
    async def reconcile(self, results: list[TaskResult]) -> SwarmReport: ...
    async def cancel(self, batch_id: str) -> None: ...
```

Core records should include:

- `TaskRequest`: user request, mode, repository/worktree, acceptance criteria
- `TaskSpec`: task ID, role, inputs, dependencies, file/resource claims, budget
- `DispatchPlan`: parallel waves, worker/backend assignment, merge policy
- `TaskResult`: status, changed paths, commits/artifacts, evidence, usage
- `TaskEvent`: queued, started, tool output, blocked, completed, failed
- `SwarmReport`: accepted changes, conflicts, failed tasks, remaining queue

### Dispatch logic

1. Normalize the user request into independent and dependent tasks.
2. Use a DAG rather than unconstrained peer-to-peer handoffs.
3. Assign workers by capability, language, model/backend, budget, and file claims.
4. Run non-conflicting tasks in parallel isolated worktrees.
5. Require every coding task to produce a patch/commit and evidence.
6. Run targeted test/review tasks after each coding wave.
7. Detect file overlap, conflicting contracts, budget exhaustion, and failed evidence.
8. Requeue only bounded, diagnosable failures; escalate ambiguous conflicts to HITL.
9. Reconcile accepted commits through a merge queue or integration worktree.
10. Emit the same event schema consumed by the CLI and UI.

### Safety and quality gates

- no shared mutable worktree between concurrent workers
- per-task and aggregate budgets
- explicit tool allowlists by worker role
- reviewer/tester evidence required before merge
- deterministic conflict ownership and retry limits
- secrets and external command policy inherited from the main harness

The first implementation should be an adapter behind the existing
`AgentBackend`/event interfaces. The current graph remains the default until
swarm scheduling is validated against deterministic integration tests.

## 14. Deployment

Before compose:

1. create `.env`
2. ensure `marketplace_cache` is a directory
3. ensure `marketplace_index.sqlite` is a regular file
4. ensure `eco-cli` and `eco-wizard` are available or configured
5. build/install the frontend dependencies

Run `python scripts/dev_preflight.py` before `docker compose up`; it fails
early when Docker would otherwise create an empty directory at the SQLite
file mount.

The API mount is writable because UI RAG import updates the shared SQLite
index. Production deployments should use an index-update job or a controlled
volume policy rather than exposing arbitrary write access.

## 15. Security and trust

- CORS defaults to local UI origins and is configurable with `CORS_ORIGINS`.
- Secrets are environment/secret-store data only.
- CLI subprocesses use argument arrays, `shell=False`, allowlists, timeouts,
  and bounded output.
- Project filesystem tools enforce project-root containment.
- Tester has no write/build tools.
- Retrieved documents, marketplace descriptions, source files, runtime output,
  and build logs are untrusted data.
- WebSocket authentication remains an optional deployment extension and
  should be enabled for non-localhost exposure.

## 16. Deprecated material

Old chat and verification documents are historical references, not production
instructions. The active decisions are consolidated here.
`agent/skills/c.md` is a reference corpus for a future `component_author`
role, not a live default skill.

Do not use old version-specific prompts, dead LangGraph instructions, or the
old Chroma path when changing the production harness.

## 17. Validation checklist

```cmd
python -m compileall -q agent backend eco_harness scripts
cd frontend
npm run build
```

For a deployment smoke test:

```cmd
curl http://localhost:8100/health
curl http://localhost:8100/config
docker compose config
```