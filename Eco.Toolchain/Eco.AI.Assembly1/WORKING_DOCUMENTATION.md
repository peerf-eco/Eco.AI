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
- `capabilities.py` — Pydantic AI v2 capability descriptions

The existing `agent/v6` directory is a historical package name for the
working internal agent implementation. New modules must not add new versioned
paths or dead-pipeline terminology. Compatibility names may remain until a
separate filesystem rename is safe.

## 3. Pydantic AI v2 decision

Pydantic AI v2 capabilities are adopted as an optional composition layer.
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

Every internal role uses a deterministic static context assembled by
`agent/context/assembler.py`:

```text
BLOCK A — immutable framework rules and stable tool contract
BLOCK B — one stitched source-code payload
BLOCK C — runtime RAG and tool results
BLOCK D — recent history and current user request
```

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
- retrieved source/tool output treated as data, not policy
- `eco-wizard` for generated boilerplate

## 5. Configuration and user rules

Repository configuration is stable and reviewable under `config/`. UI changes
go to `.eco-harness/workspace.yaml`. Environment variables override both.
Secrets remain outside repository configuration.

Prompt and skill resolution order is stable:

1. framework header
2. stable tool contract
3. role prompt
4. language prompt and selected skill versions
5. project/root and role `AGENTS.md`
6. stitched source block
7. dynamic RAG/tool/history tail

Root `AGENTS.md` applies to all roles. Role-specific rules belong in
`config/agents/<role>/AGENTS.md` or `.eco-harness/agents/<role>/AGENTS.md`.
Versioned reusable skills belong under `config/skills/`.

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
Language-specific prompt and skill versions are configured in
`config/languages.yaml`, `config/prompts/languages/`, and
`config/skills/languages/`.

`eco-wizard` remains the source of truth for language-specific project
templates. Until its Python and Java support ships, the harness must not
invent those layouts.

## 8. Generator and CLI execution

`agent/v6/tools/eco_wizard.py` exposes the generator with:

- executable lookup via `ECO_WIZARD_PATH` or `PATH`
- `eco-wizard new`
- language, type, output, environment, and option arguments
- bounded output
- explicit missing-binary and failure results

`agent/v6/tools/eco_cli.py` remains the marketplace bridge. It uses an
allowlist, `shell=False`, bounded output, timeout control, and portable
`ECO_CLI_PATH`/`ECO_CLI_PREFIX` overrides. Legacy `V6_*` names remain only as
compatibility fallbacks.

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
default and `NEXT_PUBLIC_PIPELINE_VERSION=v7`. The server exposes:

- `GET /health`
- `GET /config`
- `PUT /config/workspace`
- `POST /rag/import`
- `GET /rag/export`
- `WS /ws/v7/chat`

The event schema remains compatible with the current streaming UI:
heartbeats, phase changes, node events, plan review, and pipeline completion.
The neutral `use-socket.ts` export is the preferred frontend import; the old
hook filename remains a compatibility shim.

## 11. Deployment

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

## 12. Security and trust

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

## 13. Deprecated material

The old V3/V4/V5 chat and verification documents are historical references,
not production instructions. The active decisions are consolidated here.
`agent/skills/c.md` is a reference corpus for a future `component_author`
role, not a live default skill.

Do not use old version-specific prompts, dead LangGraph instructions, or the
old Chroma path when changing the production harness.

## 14. Validation checklist

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