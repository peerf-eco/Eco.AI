# Eco.AI Assembly Meta-Harness

Eco.AI Assembly is a cross-platform ACOM component assembly harness. It owns
the EcoOS domain tools, marketplace RAG, project-generation policy, bounded
role orchestration, human plan approval, and a shared event contract. Agent
backends are replaceable: the built-in agent, Pi, Codex, and Claude Code can
be selected per role.

## Quick Start

### Option 1: Docker Compose (Recommended)
```bash
# Prerequisites on the host (these run on the host, NOT inside the container):
#   - Python 3.11+
#   - Docker Engine / Docker Desktop
#   - eco-cli and eco-wizard executables (see step 3)
# Note: the frontend is built inside the container by `docker compose build`,
# so a host `npm install` is NOT required for this option.

# 1. Copy environment template
cp env.example .env

# 2. Edit .env with your settings. At minimum set:
#      OPENAI_API_KEY  - OpenRouter API key (used by build_marketplace_index.py embeddings)
#      ECO_API_TOKEN   - Eco marketplace token (used by fetch_marketplace.py)
#      ECO_CLI_PATH    - absolute path to the eco-cli binary (or put eco-cli on PATH)
#      ECO_WIZARD_PATH - absolute path to the eco-wizard binary (or put eco-wizard on PATH)
#    OPENROUTER_URL defaults to https://openrouter.ai/api/v1 if unset.

# 3. Prepare executables (on host, outside container)
#    Place executables in these directories relative to project root:
#    - ../eco-cli-linux/eco-cli            (Linux ELF, preferred)
#    - ../eco-cli-windows/eco-cli.exe      (Windows .exe, fallback via wine)
#    - ../eco-wizard-linux/eco-wizard      (Linux ELF, preferred)
#    - ../eco-wizard-windows/eco-wizard.exe (Windows .exe, fallback via wine)
#    Or skip this and set ECO_CLI_PATH / ECO_WIZARD_PATH in .env (see step 2).

# 4. Set up the host Python environment for the initialization scripts
#    build_marketplace_index.py imports agent.rag.* (sqlite-vec, tree-sitter,
#    httpx, openai, python-dotenv), so the agents' dependencies must be installed.
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r agent/requirements.txt

# 5. Export the variables the host scripts read from the shell, then run them
#    (fetch_marketplace.py reads ECO_API_TOKEN/ECO_CLI_PATH from the shell env,
#     so export them; build_marketplace_index.py loads .env itself via dotenv)
export ECO_API_TOKEN="token generated in ecoos.dev marketplace (component registry)"
export ECO_CLI_PATH="path to eco-cli on this PC"

python scripts/fetch_marketplace.py
python scripts/build_marketplace_index.py

# 6. (Optional but recommended) Preflight check validates .env, index, cache, executables
python scripts/dev_preflight.py

# 7. Start the application (builds api + frontend images, mounts the index/cache/executables)
docker compose up --build

# Access at:
# - UI: http://localhost:3100
# - API: http://localhost:8100
```

### Option 2: Local Development
```bash
# 1. Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r agent/requirements.txt

# 2. Set up Node.js frontend
cd frontend
npm install
cd ..

# 3. Configure environment
cp env.example .env
# Edit .env with your settings

# 4. Prepare executables (place in PATH or set ECO_CLI_PATH/ECO_WIZARD_PATH)

# 5. Run initialization scripts
python scripts/fetch_marketplace.py
python scripts/build_marketplace_index.py

# 6. Start services in separate terminals:
# Terminal 1: uvicorn backend.server:app --host 0.0.0.0 --port 8000
# Terminal 2: cd frontend && npm run dev
```

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

### Executable Directory Structure

The system uses a consistent directory structure for executables with Linux priority:

```
../ (relative to project root)
├── eco-cli-linux/          # Linux ELF executable (preferred)
│   └── eco-cli
├── eco-cli-windows/        # Windows .exe executable (fallback via wine)
│   └── eco-cli.exe
├── eco-wizard-linux/       # Linux ELF executable (preferred)
│   └── eco-wizard
└── eco-wizard-windows/     # Windows .exe executable (fallback via wine)
    └── eco-wizard.exe
```

**Path Resolution Priority:**
1. Environment variables (`ECO_CLI_PATH`, `ECO_WIZARD_PATH`) - **Use to override automatic detection**
2. Linux executables (preferred for Docker containers)
3. Windows executables via wine (fallback)
4. System PATH
5. Configuration files

The system automatically detects and uses the appropriate executable with
wine prefix support for Windows executables on Linux.

**When to use `ECO_CLI_PATH`/`ECO_WIZARD_PATH`:**
- To use a custom executable location not in the standard directories
- To force use of Windows executable when Linux version is available
- To specify exact path when multiple versions exist
- For development/testing with different executable versions

**When NOT needed:**
- When using standard directory structure (`../eco-cli-linux/`, etc.)
- When executables are in system PATH
- For normal Docker Compose deployment (automatic detection works)

## Setup Details

### Environment Configuration

1. **Copy environment template:**
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` file:** Set at minimum:
   - `OPENAI_API_KEY` - Your OpenRouter API key
   - `OPENROUTER_URL` - OpenRouter API URL (default: `https://openrouter.ai/api/v1`)
   - `ECO_API_TOKEN` - Eco marketplace token (for `fetch_marketplace.py`)

3. **Optional environment variables:**
   - `ECO_CLI_PATH` - Override eco-cli executable path
   - `ECO_WIZARD_PATH` - Override eco-wizard executable path
   - `ECO_WORKTREE_ROOT` - Custom worktree directory
   - `ECO_CLI_PREFIX`/`ECO_WIZARD_PREFIX` - Wine prefix for Windows executables (e.g., `wine64`)

### Initialization Scripts (Run on Host Machine)

**These scripts MUST run on the host machine BEFORE starting Docker containers:**

1. **Fetch marketplace components:**
   ```bash
   # Requires: ECO_API_TOKEN in .env
   # Downloads components to ./marketplace_cache/
   python scripts/fetch_marketplace.py
   ```

2. **Build RAG index:**
   ```bash
   # Requires: OPENAI_API_KEY in .env
   # Creates marketplace_index.sqlite from marketplace_cache/
   python scripts/build_marketplace_index.py
   ```

3. **Preflight check (optional but recommended):**
   ```bash
   # Validates setup before starting containers
   python scripts/dev_preflight.py
   ```

**Note:** These scripts interact with external APIs and download files to the host filesystem. They cannot run inside containers because:
- Need access to host filesystem for `marketplace_cache/`
- May need to download executables or large files
- Some require API tokens that shouldn't be in container images

### Executable Preparation

Place executables in these locations **relative to project root on host** depending on your OS and files locations, example:
- `../eco-cli-linux/eco-cli` - Linux ELF (preferred)
- `../eco-cli-windows/eco-cli.exe` - Windows .exe (fallback via wine)
- `../eco-wizard-linux/eco-wizard` - Linux ELF (preferred)
- `../eco-wizard-windows/eco-wizard.exe` - Windows .exe (fallback via wine)

Docker Compose will mount these directories into the container at `/opt/eco-*-linux/` and `/opt/eco-*-windows/`.

### Docker Compose Deployment

**Prerequisites (on host):**
1. `.env` file configured
2. `marketplace_index.sqlite` created (via `build_marketplace_index.py`)
3. `marketplace_cache/` directory populated (via `fetch_marketplace.py`)
4. Executables placed in `../eco-*-linux/` and `../eco-*-windows/` directories

**Start the application:**
```bash
docker compose up --build
```

**Access endpoints:**
- Web UI: http://localhost:3100
- API: http://localhost:8100
- WebSocket: ws://localhost:8100/ws/chat

**Volume Mounts in Docker Compose:**
- `./marketplace_index.sqlite:/app/marketplace_index.sqlite` - RAG index (read-write)
- `./marketplace_cache:/app/marketplace_cache` - Component cache (read-only)
- `../../../../Dist/eco-cli/eco-cli-windows/eco-cli.exe:/opt/eco-cli-windows:ro` - Windows eco-cli executable
- `../../../../Dist/eco-cli/eco-cli:/opt/eco-cli:ro` - Linux eco-cli executable (preferred)
- `../../../../Dist/eco-cli/libaws-crt-jni.so :/opt/libaws-crt-jni.so:ro` - Linux eco-cli executable (preferred)
- `../../../../Dist/eco-cli/eco-wizard-windows/eco-wizard.exe:/opt/eco-wizard-windows:ro` - Windows eco-wizard executable
- `../../../../Dist/eco-wizard/eco-wizard:/opt/eco-wizard:ro` - Linux eco-wizard executable (preferred)

**Important:** The RAG index (`marketplace_index.sqlite`) is mounted read-write because the UI can update it through import functionality. The component cache (`marketplace_cache/`) is read-only as it contains pre-downloaded components.

## Configuration

Repository configuration is under `config/`:

### Path Resolution System

The system uses intelligent path resolution with the following logic:

**For Docker containers:**
1. Checks `/opt/eco-cli-linux/eco-cli` (Linux ELF, preferred)
2. Falls back to `/opt/eco-cli-windows/eco-cli.exe` (Windows .exe via wine)
3. Same logic for eco-wizard

**For local development:**
1. Checks `ECO_CLI_PATH` environment variable (if set)
2. Checks `../eco-cli-linux/eco-cli` (relative to project)
3. Checks `../eco-cli-windows/eco-cli.exe` (relative to project)
4. Checks system PATH for `eco-cli` or `eco-cli.exe`

**Environment Variable Examples:**
```bash
# Use Linux executable (default in Docker)
export ECO_CLI_PATH=/opt/eco-cli-linux/eco-cli
export ECO_WIZARD_PATH=/opt/eco-wizard-linux/eco-wizard

# Use Windows executable via wine (fallback)
export ECO_CLI_PATH=/opt/eco-cli-windows/eco-cli.exe
export ECO_WIZARD_PATH=/opt/eco-wizard-windows/eco-wizard.exe
export ECO_CLI_PREFIX=wine64
export ECO_WIZARD_PREFIX=wine64

# Custom path (development)
export ECO_CLI_PATH=/usr/local/bin/eco-cli
export ECO_WIZARD_PATH=/home/user/tools/eco-wizard
```

**Default `.env` configuration:**
```
# Linux paths (preferred, work in Docker):
ECO_CLI_PATH=/opt/eco-cli-linux/eco-cli
ECO_WIZARD_PATH=/opt/eco-wizard-linux/eco-wizard

# Windows paths (fallback via wine, comment out unless needed):
# ECO_CLI_PATH=/opt/eco-cli-windows/eco-cli.exe
# ECO_WIZARD_PATH=/opt/eco-wizard-windows/eco-wizard.exe
# ECO_CLI_PREFIX=wine64
# ECO_WIZARD_PREFIX=wine64
```

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

Model selection (important): the working chat model is `tencent/hy3` — the older
`tencent/hy3-preview` slug was removed from OpenRouter's standard routing (it now
only exists on Tencent's own TokenHub endpoint). `OPENROUTER_PROVIDER_PIN=tencent`
is set with `allow_fallbacks=False`, so **every role's `models.yaml` profile must
resolve to a `tencent`-provider model**; pinning a non-tencent model (e.g.
`deepseek/...`) makes OpenRouter 404. Each role's `per_query_tokens` budget is sent
as `max_tokens`; a context-window-aware clamp in
`agent/pi_ai/providers/openai_completions.py` caps it to fit the model context once
the system prompt is included, preventing HTTP 400 overflow. `harness.yaml:
source_roots` / `max_source_bytes` (300000) are currently unused (see context
injection below).

Live vs baked config: `./agent`, `./backend`, and `./config` are bind-mounted into
the api container, so edits apply on reload / next request. `eco_harness/` is still
`COPY`'d into the image, so edits there require `docker compose build api`.

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
python scripts/import_rag.py path/to/docs path/to/dump.sqlite
python scripts/export_rag.py --index marketplace_index.sqlite --out marketplace_index.team.sqlite
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

## Initial context injection

Every role's system prompt is assembled by
`agent/context/assembler.py::build_static_system_prompt` in this order:

```text
system header              (config/prompts/acom_system_header.md)
+ STATIC ACOM DOMAIN KNOWLEDGE   (load_acom_domain)
+ STATIC TOOL CONTRACT           (load_tool_contract)
+ ROLE INSTRUCTIONS              (role/mode prompt + language/custom)
+ IMMUTABLE SOURCE CODEBASE      (was the stitched marketplace cache)
```

The `IMMUTABLE SOURCE CODEBASE` block historically contained the **entire stitched
marketplace cache** (~80k tokens of component headers taken from
`harness.yaml: source_roots`), injected into every role prompt. That both blew the
context window (HTTP 400) and was redundant: components are discovered on demand via
the sqlite-vec RAG index (`marketplace_index.sqlite`) and the `search_marketplace` /
`eco-cli` tools. The static stitch is therefore **disabled** — `stitch_source_files`
is commented out in `build_static_system_prompt`, so the block is empty. A curated,
shorter context (rules / `AGENT.md`) will replace it later. The `source_roots` and
`max_source_bytes` settings in `harness.yaml` are currently unused.

## Working modes

The UI mode selector and CLI support (defined in `config/modes.yaml`):
`create`, `migrate`, `test`, `review`. There is **no standalone `plan` mode** —
planning is the first phase of the `create` pipeline, not a separate mode.

- `create` — architect plans → **human plan approval** → coder ↔ tester build &
  runtime-test. Even in `create` mode a human must approve the plan: the architect
  emits `plan_review_required` and the server waits for the user's `plan_decision`
  before the coder runs (`backend/server.py`).
- `migrate` — analyze and migrate an existing codebase to ACOM.
- `test` — read-only testing agent.
- `review` — read-only ACOM style/correctness reviewer.

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

## Troubleshooting

### Common Issues

1. **"eco-cli not found" error:**
   - Ensure executables are in `../eco-cli-linux/` or `../eco-cli-windows/`
   - Check Docker volume mounts in `docker-compose.yml`
   - Verify `ECO_CLI_PATH` in `.env` if using custom location

2. **GPG signature errors during Docker build:**
   - Update Dockerfile base image
   - Clear Docker build cache: `docker builder prune -a`
   - Rebuild: `docker compose build --no-cache`

3. **RAG index not found:**
   - Run `python scripts/build_marketplace_index.py` on host
   - Ensure `marketplace_index.sqlite` exists in project root
   - Check file permissions

4. **Marketplace components missing:**
   - Run `python scripts/fetch_marketplace.py` on host
   - Verify `ECO_API_TOKEN` in `.env`
   - Check network connectivity

5. **Windows executables not working in Linux container:**
   - Ensure `wine64` is installed in Docker image
   - Set `ECO_CLI_PREFIX=wine64` in `.env` for Windows executables
   - Consider using Linux executables instead

### Debugging

- Check container logs: `docker compose logs api`
- Enter container shell: `docker compose exec api bash`
- Test eco-cli in container: `docker compose exec api eco-cli --version`
- Verify volume mounts: `docker compose exec api ls -la /opt/`

## Validation

```bash
python -m compileall -q agent backend eco_harness scripts
cd frontend
npm run build
```

See `WORKING_DOCUMENTATION.md` for the consolidated architectural decisions,
cache contract, migration notes, swarm extension design, and operational
troubleshooting.