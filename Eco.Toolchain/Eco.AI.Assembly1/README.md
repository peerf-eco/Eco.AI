# Eco.AI Assembly Meta-Harness

Eco.AI Assembly is a cross-platform ACOM component assembly harness. It owns
the EcoOS domain tools, marketplace RAG, project-generation policy, bounded
role orchestration, human plan approval, and a shared event contract. Agent
backends are replaceable: the built-in agent, Pi, Codex, and Claude Code can
be selected per role.

## Quick Start

The shortest path uses the Makefile targets (`setup` → `index` →
`preflight` → `up`); the equivalent manual steps follow below.

```bash
make setup      # .venv + agent/requirements.txt + .env seeded from env.example
make index      # fetch marketplace components + build the RAG index (needs tokens in .env)
make preflight  # validate binaries, cache, index (--fix applies safe fixes)
make up         # docker compose up --build
```

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
#    (or let the preflight script seed it for you:)
#    python scripts/dev_preflight.py --fix

# 2. Edit .env with your settings. At minimum set:
#      OPENAI_API_KEY  - OpenRouter API key (used by build_marketplace_index.py embeddings)
#      ECO_API_TOKEN   - Eco marketplace token (used by fetch_marketplace.py)
#      ECO_CLI_PATH    - absolute path to the eco-cli binary (or put it in <repo>/bin/)
#      ECO_WIZARD_PATH - absolute path to the eco-wizard binary (or put it in <repo>/bin/)
#    OPENROUTER_URL defaults to https://openrouter.ai/api/v1 if unset.

# 3. Prepare executables — canonical home is <repo>/bin/ (gitignored):
mkdir -p bin
cp /path/to/eco-cli bin/
cp /path/to/eco-wizard bin/
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

### Executable Resolution

All external tool binaries (eco-cli, eco-wizard, and the optional external
sub-agents) are resolved by one shared policy —
`agent/internal/tools/binaries.py::resolve_binary`:

1. `ECO_CLI_PATH` / `ECO_WIZARD_PATH` / `ECO_<NAME>_PATH` environment variable
2. `<repo>/bin/<name>` — the canonical, gitignored home (place binaries here)
3. `/opt/<name>` — container bind-mount location (docker-compose.yml)
4. Legacy platform-suffixed siblings (`<repo>/eco-cli-linux/eco-cli`,
   `<repo>/eco-cli-windows/eco-cli.exe`) — kept for backwards compatibility
5. System `PATH`

Windows `.exe` binaries on Linux run through a wine wrapper configured via
`ECO_CLI_PREFIX` / `ECO_WIZARD_PREFIX` (e.g. `wine64`).

**When to use the env vars:** custom executable locations, forcing the Windows
binary, or pinning a specific version. For normal setups just drop the
binaries into `<repo>/bin/` or leave them in Docker mount points — no config
needed.

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

### Environment Variable Matrix

Canonical reference for every environment variable the harness reads.
`.env` is loaded via python-dotenv; shell exports win over nothing (dotenv
does not override already-set variables).

| Variable | Read by | Default | Purpose |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | embedder, providers | — | OpenRouter API key (RAG embeddings + LLM calls) |
| `OPENROUTER_URL` | providers | `https://openrouter.ai/api/v1` | OpenRouter endpoint |
| `LLM_MODEL` | config loader | `tencent/hy3-preview` | Default model id (sets/overrides the `default` profile) |
| `ECO_API_TOKEN` | fetch_marketplace.py, eco-cli | — | Eco marketplace token |
| `ECO_CLI_PATH` | binary resolution | `<repo>/bin/eco-cli` → `/opt/eco-cli` → PATH | eco-cli binary location |
| `ECO_WIZARD_PATH` | binary resolution | `<repo>/bin/eco-wizard` → `/opt/eco-wizard` → PATH | eco-wizard binary location |
| `ECO_CLI_PREFIX` | eco_cli tool | — | Wrapper command for Windows binaries under Linux (e.g. `wine64`) |
| `ECO_WIZARD_PREFIX` | eco_wizard tool | — | Same, for eco-wizard |
| `ECO_WIZARD_TIMEOUT_S` | eco_wizard tool | `180` | Scaffold generation timeout |
| `ECO_CLAUDE_PATH` / `ECO_CODEX_PATH` / `ECO_GROK_PATH` / `ECO_PI_PATH` | factory / ExternalCliBackend | PATH lookup | External sub-agent binaries; flags come from `config/agents/external/<name>.yaml` |
| `ECO_MAKE_EXE` | server chat handler | `make` | Path to the make binary used by builds |
| `MARKETPLACE_CACHE_ROOT` | paths.py consumers | `<repo>/marketplace_cache` → `/app/marketplace_cache` | Pre-pulled component cache |
| `MARKETPLACE_INDEX_PATH` | paths.py consumers | `<repo>/marketplace_index.sqlite` → `/app/marketplace_index.sqlite` | sqlite-vec RAG index |
| `HARNESS_OUTPUT_ROOT` | server | `./output` | Where per-chat workspace dirs are created |
| `HARNESS_TRACES_DIR` | server | `./traces` | Per-conversation LLM trace folders |
| `HARNESS_MAX_HOPS` | orchestrator | `8` | Max handoff hops (also `harness.yaml.max_hops`) |
| `AGENT_MAX_ITERATIONS` | `build_pipeline` runs only | unset | Overrides per-role `max_iters` for scripted pipeline runs; production `/ws/chat` uses `budgets.max_iters` from `config/roles.yaml` |
| `HARNESS_DYNAMIC_TAIL_ITEMS` | agent context | `5` (`harness.yaml`: 12) | Newest tool results kept verbatim in context |
| `HARNESS_RETAINED_TOOL_OUTPUTS` | agent context | `budgets.yaml.retained_tool_outputs` (5) | Wired alias controlling `max_tool_results` context retention |
| `HARNESS_SOURCE_MAX_BYTES` | context assembler | `300000` | Cap on static source material in the system prompt |
| `HARNESS_PREPULL_FRAMEWORK` | server scaffold | `1` | `0` disables copying framework components into project_dir |
| `HARNESS_TOOL_DEDUP` | read-only tool memo-dedup | on | `0` disables dedup kill-switch (consistent name across code/.env/env.example) |
| `HARNESS_WARM_SEED` | server warm-retry | `0` | `1` enables warm retry seeds |
| `HARNESS_SCAFFOLD` | server scaffold | on | `0` disables pre-seeding src/EcoMain.c + Makefile |
| `ECO_WORKTREE_ROOT` | worktrees | repo default | Isolated git-worktree root |
| `ECO_HARNESS_WORKSPACE_CONFIG` | config loader | `.eco-harness/workspace.yaml` | Workspace override file |
| `ECO_ROLE_<ROLE>_BACKEND` / `_MODEL` / `_REASONING` / `_MAX_TOKENS` | config loader | `roles.yaml` | Per-role overrides (e.g. `ECO_ROLE_CODER_BACKEND=pi`) |
| `DEFAULT_LANGUAGE` | config loader | `C` | Default implementation language |

Optional external env vars consumed indirectly by eco-cli/eco-wizard:
`ECO_API_TOKEN`, `ECO_FRAMEWORK` / `ECO_FRAMEWORK_PATH` (framework DK path).

3. **Optional configuration notes:**
   - `MARKETPLACE_CACHE_ROOT` / `MARKETPLACE_INDEX_PATH` are normally NOT
     needed: on a host checkout the repo-root artifacts are detected
     automatically; in Docker the `/app` mounts are detected too.

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

Place the binaries in the canonical gitignored home relative to project root:

```
bin/
├── eco-cli       # Linux ELF (preferred)
└── eco-wizard    # Linux ELF (preferred)
```

Docker Compose bind-mounts the vendored ELF files directly into the
container at `/opt/eco-cli` and `/opt/eco-wizard`; both locations are found
automatically by `resolve_binary`.

### Docker Compose Deployment

**Prerequisites (on host):**
1. `.env` file configured
2. `marketplace_index.sqlite` created (via `build_marketplace_index.py`)
3. `marketplace_cache/` directory populated (via `fetch_marketplace.py`)
4. Binaries placed in `<repo>/bin/eco-cli` and `<repo>/bin/eco-wizard`
   (or available at the `/opt/...` mount points)

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
- `../../../../Dist/eco-cli/eco-cli:/opt/eco-cli:ro` - eco-cli executable
- `../../../../Dist/eco-cli/libaws-crt-jni.so:/opt/libaws-crt-jni.so:ro` - AWS CRT JNI library for eco-cli (no space before the colon)
- `../../../../Dist/eco-wizard/eco-wizard:/opt/eco-wizard:ro` - eco-wizard executable

**Important:** The RAG index (`marketplace_index.sqlite`) is mounted read-write because the UI can update it through import functionality. The component cache (`marketplace_cache/`) is read-only as it contains pre-downloaded components.

## Configuration

Repository configuration is under `config/`:

### Path Resolution System

One shared resolver (`agent/internal/tools/binaries.py::resolve_binary`)
handles every external binary, host and container alike:

1. Explicit config (e.g. `harness.yaml` `eco_cli_path` / `eco_wizard_path`)
2. `ECO_CLI_PATH` / `ECO_WIZARD_PATH` / `ECO_<NAME>_PATH` environment variable
3. `<repo>/bin/<name>` (canonical, gitignored)
4. `/opt/<name>` (Docker bind-mount point)
5. Legacy platform-suffixed siblings (`<repo>/eco-cli-linux/eco-cli`,
   `<repo>/eco-cli-windows/eco-cli.exe`) — backwards compatibility only
6. System `PATH`

**Environment Variable Examples:**
```bash
# Canonical home (recommended):
export ECO_CLI_PATH=$PWD/bin/eco-cli
export ECO_WIZARD_PATH=$PWD/bin/eco-wizard

# Docker mount points:
export ECO_CLI_PATH=/opt/eco-cli
export ECO_WIZARD_PATH=/opt/eco-wizard

# Windows executable via wine:
export ECO_CLI_PATH=/path/to/eco-cli.exe
export ECO_CLI_PREFIX=wine64

# Custom path (development)
export ECO_CLI_PATH=/usr/local/bin/eco-cli
export ECO_WIZARD_PATH=/home/user/tools/eco-wizard
```

**Default `.env` configuration:**
```
# Leave unset when the binaries are in <repo>/bin/ or at the /opt mounts.
# Override only for custom locations:
# ECO_CLI_PATH=/usr/local/bin/eco-cli
# ECO_WIZARD_PATH=/home/user/tools/eco-wizard
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
only exists on Tencent's own TokenHub endpoint). The provider **pin** is resolved
per model, with this precedence:

```text
model profile's provider_pin (config/models.yaml)  >  OPENROUTER_PROVIDER_PIN (.env)
```

So each role's model carries its own `provider_pin` (see `config/models.yaml`,
e.g. `reasoning_heavy.provider_pin: tencent`), keeping the pin matched to that
model's provider and avoiding mismatched-pin 404s when different roles use
different models. A profile that omits `provider_pin` (the `default` profile)
falls back to the global `OPENROUTER_PROVIDER_PIN` env — that is the
`LLM_MODEL` + `OPENROUTER_PROVIDER_PIN` "default combination" for roles with no
specific model set. `allow_fallbacks` defaults to **True**, so a
missing/unavailable pinned endpoint routes to the other providers that also
serve the model (Tencent Cloud, DeepInfra, NovitaAI, …) instead of failing with
HTTP 404 "No endpoints found". Set `OPENROUTER_ALLOW_FALLBACKS=false` only if you
want strict single-provider pinning (availability traded for cache warmth).
**Every model's pin must resolve to a real OpenRouter provider for that model** —
pinning a model no provider serves (e.g. `deepseek/...` under a `tencent` pin)
makes OpenRouter 404. Each role's `per_query_tokens` budget is sent
as `max_tokens`; a context-window-aware clamp in
`agent/pi_ai/providers/openai_completions.py` caps it to fit the model context once
the system prompt is included, preventing HTTP 400 overflow. `harness.yaml:
source_roots` / `max_source_bytes` (300000) now drive the curated `Eco.Core1`
stitch (see context injection below).

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

### marketplace_cache layout

`marketplace_cache/` (mounted read-only into the container at
`/app/marketplace_cache`) has two distinct parts the agents use differently:

- `<Component>/SharedFiles/*.h` — the **interface/source headers** (e.g.
  `Eco.Core1/SharedFiles/IEcoSystem1.h`). This is the readable corpus explored
  with `grep` / `glob` / `read`. Headers are UTF-8 (sometimes with a BOM) and
  may contain Cyrillic comments; the `read`/`read_file` tools decode them
  lossy-but-safe.
- `_profiles/<Name>.json` — one **metadata profile per component** (30 in the
  current snapshot), written by `scripts/fetch_marketplace.py`. Each holds the
  raw `find -n` profile: CID, available versions, DEVKIT file manifest, and
  dependencies. It answers "given this component name, what do I `pull`?" and
  is consumed by the `read_component_profile` tool. It is **excluded from the
  RAG index** (the directory begins with `_`), so `search_marketplace` never
  embeds it.

The buildable implementation (`.c` / `.lib` / `.so`) is **not** in the cache —
it is fetched on demand via `eco-cli pull` into `project_dir`.

## Customization

Project-wide rules go in the root `AGENTS.md`. Role-specific rules can be
placed in:

```text
config/agents/<role>/AGENTS.md
.eco-harness/agents/<role>/AGENTS.md
```

Reusable skills can be placed in:

```text
config/skills/<skill>/v<N>.md   or SKILL.md
.eco-harness/skills/<skill>/SKILL.md
```

The legacy `agent/skills/` root was retired in PRD_2 Phase 2
(`agent/skills/c.md` → `config/skills/component_author/v1.md`).

  Language skills belong in `config/skills/languages/<language>.md`. Stable
  prompt changes belong in `config/prompts/`; workspace-specific instructions
  belong in `.eco-harness/`.

## Initial context injection

Every role's initial context (system prompt) is assembled once per agent
construction by `agent/context/assembler.py::build_static_system_prompt`
(driven by `eco_harness/roles.py`) from multiple sources, in a fixed order:

```text
# SYSTEM HEADER                          config/prompts/acom_system_header.md
=== STATIC ACOM DOMAIN KNOWLEDGE ===     config/prompts/acom_domain.md
=== STATIC TOOL CONTRACT ===             config/prompts/tool_contract.md
=== ROLE INSTRUCTIONS ===                composed from your selections:
                                           === MODE ===      prompts/modes/<mode>.md
                                           <role prompt>     precedence chain below
                                           <language prompt> prompts/languages/<lang>.md
                                           AGENTS.md layers + selected skills
                                           ROLE CONFIGURATION (backend/model/reasoning)
=== IMMUTABLE SOURCE CODEBASE ===        curated Eco.Core1/SharedFiles stitch
```

**How your selections drive it**

- **Mode** (`config/modes.yaml`): `auto`/`migrate` inject the pipeline-mode
  prompt and engage the full architect→approval→coder↔tester loop; `plan`,
  `code`, `test`, `review` inject their one-shot prompt and load exactly one
  role.
- **Active role** (`config/roles.yaml`): picks backend, model profile,
  reasoning level, budgets, and which skill profiles are injected.
- **Language** (`config/languages.yaml`): picks `prompts/languages/<lang>.md`,
  the language skill (`config/skills/languages/<lang>.md`), and the eco-wizard
  template family.

**Role-prompt precedence** (first non-empty wins):

```text
1. .eco-harness/prompts/<role>.md     workspace override, no repo changes needed
2. config/prompts/<role>.md           editable source of truth for each role
3. built-in constant                  fallback in agent/internal/agents/<role>.py
```

Empty or placeholder files are skipped, so they can never blank out real
instructions.

**Cache/token efficiency**: blocks 1–3 are byte-identical for every role,
mode, language, and backend; the Eco.Core1 stitch (~120 KB cap) is constant
across turns and tasks; only the ROLE INSTRUCTIONS block varies per selection
and stays stable while an agent iterates. This ordering maximizes provider
KV-cache reuse (measured: 99.6% cached tokens, −81% cost per call on a pinned
provider via `provider_pin`). Nothing dynamic — RAG results, tool outputs,
user requests — enters the system prompt; those live in message history where
all but the newest 12 tool results are elided automatically.

See `WORKING_DOCUMENTATION.md` §4 for the full developer-level contract
(skill resolution rules, artifact path resolution, maintainer rules).

Supporting changes that keep the architect fast and on-policy:

- **C language skill** (`config/skills/languages/C.md`) injects the full ACOM/C89/MISRA
  contract (EcoOS types, `IEcoMemoryAllocator1`-only allocation, UGUID byte format,
  mandatory Dev-Kit boundary, minimum stack, file/function-header discipline) into
  every C agent, so those conventions are no longer rediscovered from headers.
- **`read_component_profile` Contract Card** — returns the CID, IIDs, the
  `GetIEcoComponentFactoryPtr_<CID>` factory symbol, vtable method names, and the
  `SharedFiles/` layout in one structured call, avoiding large raw header reads.
- **`eco_cli`** now auto-resolves the binary via the shared resolver
  (`ECO_*_PATH` → `<repo>/bin/` → `/opt/` mount → legacy siblings → `PATH`) and,
  when none is found, returns an actionable error noting the read-only
  `marketplace_cache` already holds the needed headers.

## Working modes

The UI mode selector and CLI (defined in `config/modes.yaml`) choose which
role(s) run and whether the automatic plan→implement→verify pipeline is engaged:

- `auto` (default) — the deterministic loop: **architect plans → human plan
  approval (HITM) → coder ↔ tester build & runtime-test**. A lightweight intent
  gate classifies each message first: plain questions are answered directly
  (no pipeline), while a concrete coding task triggers the loop.
- `plan` — architect only: research + PRD / closed plan. **No pipeline and no
  coder hand-off** — the plan is surfaced as the final answer so you can approve
  it later in `auto` / `code`.
- `code` — coder only: direct implementation. **No architect pass and no
  automatic test pipeline**; you drive each phase manually from the mode menu.
- `migrate` — the same `auto` pipeline, but with a migration-focused system
  prompt: analyze the existing codebase, divide it into reusable modules, map
  each to ACOM component contracts, then incrementally refactor.
- `test` — read-only testing agent.
- `review` — read-only ACOM style/correctness reviewer.

In `auto` / `migrate` the architect emits `plan_review_required` and the server
waits for your `plan_decision` before the coder runs (`backend/server.py`).
`plan` / `code` / `test` / `review` load exactly one role with its profile and
never auto-trigger the cross-role pipeline, so you can switch roles freely from
the mode menu. Each mode selects its own system prompt and capability set from
`config/modes.yaml`.

## Worktree isolation

Enable **Worktree** beside the chat input, or pass `--worktree` to the CLI.
The harness creates a detached Git worktree outside the primary checkout and
uses it as the project root for all subsequent agent filesystem operations in
that session. It never silently modifies the primary checkout. A custom
destination can be configured through `ECO_WORKTREE_ROOT`.

```cmd
python -m eco_harness run "Review this component" --mode review --worktree
python -m eco_harness /plan "Design a checksum component" --worktree
```

The CLI runs a single role one-shot (`plan|code|test|review`); the full
`auto`/`migrate` pipeline needs the human plan-approval gate and lives in the
UI / websocket API.

## Workspace and per-agent limits

### How the working folder is chosen

The harness has **no UI "open folder" picker** — the workspace
(`project_dir`) is derived automatically per chat session:

- **Default:** `HARNESS_OUTPUT_ROOT` (default `./output`) + `chat-<thread8>`,
  i.e. `./output/chat-<thread8>`. In the container this is `/app/output/...`
  (the `./output` volume mount). A fresh sub-directory is created for each
  WebSocket session/thread, so concurrent chats never share a tree.
- **Worktree (isolated):** enable **Worktree** in the UI (or `--worktree` on
  the CLI). The harness then creates a detached Git worktree outside the
  primary checkout — under `ECO_WORKTREE_ROOT` — and uses that as
  `project_dir`. It never modifies the primary checkout.

All file tools are **sandboxed to `project_dir`** for writes: the coder's
`write_file` / `build` / `runtime` can only touch `project_dir`, while
`read` / `glob` / `grep` / `read_file` / `list_dir` may also read the
read-only `marketplace_cache`. UI role/model/language selections are persisted
in `.eco-harness/workspace.yaml`.

### Per-agent space limits (budgets)

Each role's limits come from `config/roles.yaml` →
`roles.<role>.budgets` and are applied identically to every sub-agent
(architect, coder, tester, reviewer):

| Budget | Effect |
| --- | --- |
| `per_query_tokens` | Sent as the model `max_tokens`; a context-window-aware clamp in `agent/pi_ai/providers/openai_completions.py` caps it so the system prompt fits (prevents HTTP 400). |
| `per_query_usd` / `per_day_usd` | Cost ceilings for a single query / per day. |
| `max_iters` | Hard cap on the agent's tool-call loop iterations. |
| `max_wall_s` | Wall-clock timeout for the agent. |

Global guards: `HARNESS_MAX_HOPS` (default `8`) bounds orchestrator
handoffs. `AGENT_MAX_ITERATIONS` (env) applies only to scripted
`build_pipeline` runs (`agent/internal/entry.py`); the production
`/ws/chat` pipeline uses each role's `budgets.max_iters` from
`config/roles.yaml`. File-tool results are also
size-capped (`read` 32 KB default / 200 KB max, `read_file` 256 KB, `grep` 100
matches, `glob` 500 entries) so a single call can't blow the context budget.

## CLI and future MCP use

The headless entrypoint is:

```cmd
python -m eco_harness run "Design a calculator component" --mode plan --language C
python -m eco_harness run "Implement the approved plan" --mode code --language C
python -m eco_harness serve --api
```

One-shot modes only (`plan|code|test|review`); use the UI / websocket for the
full `auto` pipeline with plan approval.

`eco_harness.adapters.AgentBackend`, `eco_harness.tools.ToolRouter`,
`eco_harness.interfaces.mcp`, and `eco_harness.extensions` are stable
boundaries for future CLI products, MCP servers, AST endpoints, and UI
panels. The current FastAPI server is an optional interface over those
boundaries, not the domain core.

## Troubleshooting

### Common Issues

1. **"eco-cli not found" error:**
   - Place the binary at `<repo>/bin/eco-cli` (canonical home)
   - Check Docker volume mounts in `docker-compose.yml` (`/opt/eco-cli`)
   - Verify `ECO_CLI_PATH` in `.env` if using a custom location
   - Run `python scripts/dev_preflight.py --fix` for the full lookup order

2. **GPG signature errors during Docker build:**
   - Update Dockerfile base image
   - Clear Docker build cache: `docker builder prune -a`
   - Rebuild: `docker compose build --no-cache`

3. **RAG index not found:**
   - Run `python scripts/build_marketplace_index.py` on host
   - Ensure `marketplace_index.sqlite` exists in project root
     (host and container runs auto-detect it there; set
     `MARKETPLACE_INDEX_PATH` only for custom locations)
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

## Testing

The regression suite lives in `agent/internal/tests/` and runs against the
venv created during setup (`make setup` or `python -m venv .venv` +
`pip install -r agent/requirements.txt`, which includes `pytest` via
`pytest-asyncio`). Always run it through the venv so the pinned
`pytest-asyncio` / `tree-sitter` versions match what CI expects:

```bash
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
python -m pytest agent/internal/tests -v
# Or without activating:
.venv/bin/python -m pytest agent/internal/tests
```

What the suite covers:

- **Core engine** — orchestrator edge routing, hop ceilings, seed builders,
  handoff tool contract, EcoAgent loop, file/build/runtime tools, RAG tool
  (offline, mocked embedder/store).
- **PRD_2 Phase 0 regressions** (`test_prd2_regressions.py`) — external
  bridge event marshalling (no `ModuleNotFoundError` on pi/claude/codex/grok
  backends), role-prompt precedence (workspace > config > built-in, empty
  files skipped, full STEP workflow present in the runtime prompt), and
  host-mode artifact path resolution (env → repo root → `/app` → fallback).
- **PRD_2 Phase 2 regressions** (`test_prd2_phase2.py`) — shared
  `resolve_binary` order, phantom skill-key removal, dead-YAML wiring
  (framework components, retained tool outputs, external flags),
  external-role prompt parity, and pipeline-topology constants.

Live-LLM tests are marked `@pytest.mark.live` and skipped unless you pass
`--live`. The baseline gate used before every commit is:

```bash
python -m pytest agent/internal/tests
python -m compileall -q agent backend eco_harness scripts
# equivalent one-liner:
make test
```

## Validation

```bash
source .venv/bin/activate
python -m pytest agent/internal/tests
python -m compileall -q agent backend eco_harness scripts
cd frontend
npm run build
```

See `WORKING_DOCUMENTATION.md` for the consolidated architectural decisions,
cache contract, migration notes, swarm extension design, and operational
troubleshooting.