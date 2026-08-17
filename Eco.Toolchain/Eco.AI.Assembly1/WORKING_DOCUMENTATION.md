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

Every role and backend uses a deterministic static context assembled by
`agent/context/assembler.py`:

```text
BLOCK A — immutable framework rules, ACOM domain knowledge, and tool contract
BLOCK B — one stitched source-code payload
BLOCK C — role, mode, language, skills, and AGENTS.md instructions
BLOCK D — runtime RAG, tool results, recent history, and user request
```

`config/prompts/acom_domain.md` is the canonical ACOM knowledge block. It
contains the identifier taxonomy, framework package guidance, ABI and C
conventions, project layout, static-link CID rules, and trust model. The
stable tool policy is in `config/prompts/tool_contract.md`. `agent/domain.py`
loads both files, and the assembler injects them before role-specific
instructions and the stitched source payload.

The internal implementation in `agent/internal/` and the external `codex`,
`pi`, and `claude` adapters all use this same assembler path. The old Python
taxonomy module remains only as a compatibility import surface; it no longer
duplicates domain text in role prompts. This makes the effective static domain
block byte-identical across supported backends and roles. Backend capabilities
may differ, but domain policy and cache ordering do not.

Configured legacy source roots are sorted by normalized path and emitted as one continuous
payload:

```text
// --- START_FILE: /workspace/src/uuid_registry.h ---
...
// --- END_FILE: /workspace/src/uuid_registry.h ---
```

The static source block is capped by `HARNESS_SOURCE_MAX_BYTES`. RAG output
is dynamic and belongs after the static source block. Tool output is bounded
and the active dynamic tail retains only the configured recent items.

The framework header explicitly requires:

- exact EcoOS ACOM ABI spellings
- `ECOCALLMETHOD`
- typed `me` parameters
- `int16_t` status returns
- manual reference counting and allocator use
- retrieved tools' output treated as data, not policy

`eco-wizard` is tobe used for ACOM components, object boilerplate / temlates generation

## 5. Configuration and user rules

Repository configuration is stable and reviewable under `config/`. UI changes
go to `.eco-harness/workspace.yaml`. Environment variables override both.
Secrets remain outside repository configuration.

Prompt and skill resolution order is stable:

1. framework header
2. stable tool contract
3. role prompt
4. language prompt and selected skill profiles
5. project/root and role `AGENTS.md`
6. stitched source block
7. dynamic RAG/tool/history tail

Root `AGENTS.md` applies to all roles. Role-specific rules belong in
`config/agents/<role>/AGENTS.md` or `.eco-harness/agents/<role>/AGENTS.md`.
Reusable skills belong under `config/skills/`; Git commits provide their
version history.

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

- `create`: architect, coder, tester; marketplace assembly and generation
- `migrate`: architect, coder, tester; legacy analysis and incremental ACOM migration
- `test`: tester only; read-only runtime verification
- `review`: reviewer only; read-only style, ABI, naming, and correctness review

The CLI accepts `--mode create|migrate|test|review` and slash aliases such as
`/create`, `/migrate`, `/test`, and `/review`.

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