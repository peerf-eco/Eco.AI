# Eco.AI Assembly Meta-Harness

Eco.AI Assembly is a cross-platform ACOM component assembly harness. It owns
the EcoOS domain tools, marketplace RAG, project-generation policy, bounded
role orchestration, human plan approval, and a shared event contract. Agent
backends are replaceable: the built-in agent, Pi, Codex, and Claude Code can
be selected per role.

## Current runtime

The production path is:

```text
Next.js UI → FastAPI /ws/chat → architect → plan approval → coder ↔ tester
                         └────── marketplace RAG, eco-cli, eco-wizard
```

The WebSocket path is `/ws/chat`. New code should use the neutral
`eco_harness` modules and the shared chat event contract.

## Requirements

- Python 3.11+
- Node.js and npm for the UI
- Docker Desktop or Docker Engine for the compose deployment
- An OpenRouter-compatible API key for the internal agent and embeddings
- `eco-cli` for marketplace discovery and component downloads
- `eco-wizard` for generated project/component structure
- Optional external sub-agents installed on `PATH`:
  - `codex -p "prompt"`
  - `pi -e "prompt"`
  - `claude -p "prompt"`

If a configured external executable is missing, the selected role fails with
an actionable error. The harness does not silently fall back to another agent.

## Local setup

```cmd
copy env.example .env
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r agent\requirements.txt
cd frontend
npm install
cd ..
```

Set `OPENAI_API_KEY`, `OPENROUTER_URL`, and the executable paths in `.env`.
Set `ECO_WORKTREE_ROOT` to override the default sibling worktree directory.
On Linux and macOS, use the equivalent virtual-environment activation command.

Prepare the marketplace corpus and index:

```cmd
python scripts\fetch_marketplace.py
python scripts\build_marketplace_index.py
```

Run the API:

```cmd
uvicorn backend.server:app --host 0.0.0.0 --port 8000
```

Run the UI in a second terminal:

```cmd
cd frontend
npm run dev
```

The compose deployment publishes the API on `http://localhost:8100` and the
UI on `http://localhost:3100`:

```cmd
docker compose up --build
```

Create `marketplace_index.sqlite` and `marketplace_cache` before starting
compose. Run the preflight check first:

```cmd
python scripts\dev_preflight.py
```

The mounts are writable because the UI can update the shared index.

## Configuration

Repository configuration is under `config/`:

| File | Purpose |
| --- | --- |
| `harness.yaml` | defaults, cache limits, hop limits, executable paths |
| `models.yaml` | named model profiles |
| `roles.yaml` | backend, model profile, reasoning, tools, budgets |
| `languages.yaml` | supported languages and language skill profiles |
| `prompts/` | stable role and framework prompt fragments |
| `skills/` | ACOM, generator, and language skills |
| `tools.yaml` | timeouts and output limits |
| `marketplace.yaml` | cache/index and framework component settings |
| `ui.yaml` | UI defaults and selector options |
| `security.yaml` | security policy defaults |

Precedence is:

```text
environment variables > .eco-harness/workspace.yaml > config/*.yaml > code defaults
```

UI role settings are stored in `.eco-harness/workspace.yaml`. Keep API keys
and secrets in `.env` or a secret manager, never in YAML.

Each role can select an internal or external backend:

```yaml
roles:
  architect:
    backend: internal
    model: reasoning_heavy
    reasoning: high
  coder:
    backend: codex
    model: coding_balanced
    reasoning: medium
  tester:
    backend: pi
    model: cheap_fast
    reasoning: low
```

Model profiles may use a named profile or a provider model ID. Per-role
budgets include token limits, iteration limits, wall-clock limits, and
optional cost ceilings.

## Language and platform selection

The UI exposes `C`, `CPP`, `Python`, and `Java` beside the platform selector.
Language prompt and skill profiles are selected from `config/languages.yaml`
and `config/skills/languages/`. Python and Java layouts are intentionally
delegated to the upcoming `eco-wizard` release rather than invented by the
model.

## RAG import and export

The Settings panel accepts individual files, browser-selected folders, source
documents, Markdown/text documentation, and compatible SQLite dumps. Imports
update `marketplace_index.sqlite` through `scripts/import_rag.py`.

The API endpoints are:

- `POST /rag/import`
- `GET /rag/export`

For CLI use:

```cmd
python scripts\import_rag.py path\to\docs path\to\dump.sqlite
python scripts\export_rag.py --index marketplace_index.sqlite --out marketplace_index.team.sqlite
```

The current design keeps one shared marketplace index for team exchange.
Separate personal/project indexes and remote MCP-backed retrieval remain
future-compatible extension points.

## Generator and marketplace rules

Generated boilerplate must be produced by the local `eco-wizard` tool. The
internal coder receives the tool but not a template-generation instruction
that bypasses it. If a component is absent locally, the architect uses
`eco-cli` to discover and pull it from the marketplace.

`backend/scaffold/` remains only as an explicit compatibility fallback. It is
not used when `eco-wizard` is available. Set `HARNESS_SCAFFOLD=1` to force the
fallback or leave the variable unset to use the automatic compatibility rule.

## Customization

Project-wide rules go in the root `AGENTS.md`. Role-specific rules can be
placed in:

```text
config/agents/<role>/AGENTS.md
.eco-harness/agents/<role>/AGENTS.md
```

Reusable skills can be placed in:

```text
config/skills/<skill>/SKILL.md
.eco-harness/skills/<skill>/SKILL.md
agent/skills/<skill>.md
```

Language skills belong in `config/skills/languages/<language>.md`. Stable
prompt changes belong in `config/prompts/`; workspace-specific instructions
belong in `.eco-harness/`.

## Working modes

The UI mode selector and CLI support:

- `create` or `/create` — create an application/component from scratch
- `migrate` or `/migrate` — analyze and migrate an existing codebase to ACOM
- `test` or `/test` — run the read-only testing agent
- `review` or `/review` — run the read-only ACOM style/correctness reviewer

Each mode selects its own system prompt and capability set from
`config/modes.yaml`.

## Worktree isolation

Enable **Worktree** beside the chat input, or pass `--worktree` to the CLI.
The harness creates a detached Git worktree outside the primary checkout and
uses it as the project root for all subsequent agent filesystem operations in
that session. It never silently modifies the primary checkout. A custom
destination can be configured through `ECO_WORKTREE_ROOT`.

```cmd
python -m eco_harness run "Migrate this project" --mode migrate --worktree
python -m eco_harness /review "Check this code" --worktree
```

## CLI and future MCP use

The headless entrypoint is:

```cmd
python -m eco_harness run "Build a calculator" --mode create --language C
python -m eco_harness serve --api
```

`eco_harness.adapters.AgentBackend`, `eco_harness.tools.ToolRouter`,
`eco_harness.interfaces.mcp`, and `eco_harness.extensions` are stable
boundaries for future CLI products, MCP servers, AST endpoints, and UI
panels. The current FastAPI server is an optional interface over those
boundaries, not the domain core.

## Validation

```cmd
python -m compileall -q agent backend eco_harness scripts
cd frontend
npm run build
```

See `WORKING_DOCUMENTATION.md` for the consolidated architectural decisions,
cache contract, migration notes, swarm extension design, and operational
troubleshooting.