# Eco.AI Assembly Meta-Harness

Eco.AI Assembly is a cross-platform ACOM component assembly harness. It owns
the EcoOS domain tools, marketplace RAG, project-generation policy, bounded
role orchestration, human plan approval, and a shared event contract. Agent
backends are replaceable: the built-in agent, Pi, Codex, and Claude Code can
be selected per role.

## Install

Two customer-grade flows, both one command, no source checkout, no wine.
The installer always downloads **native** eco-cli / eco-wizard builds for
your OS (never wine), plus the prebuilt marketplace RAG index, verified
against the release manifest's sha256 checksums. Missing API keys never
block install or launch — finish configuration in the in-app `/setup`
wizard (or later in the app-home `.env`).

### Linux

```bash
curl -fsSL https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/install.sh | sh
```

or download and inspect first: `curl -fsSLO https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/install.sh && sh install.sh`.

- Requires `curl` or `wget` (everything else — including Python 3.11 — is
  provided by `uv` automatically, per-user, no sudo).
- Shims land in `~/.local/bin/eco-harness` and `~/.local/bin/eco-harness-update`;
  if `~/.local/bin` is not on your `PATH`, add it:
  `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc` (or your shell profile).

### macOS

```bash
curl -fsSL https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/install.sh | sh
```

Same as Linux; downloaded binaries are Apple-Silicon/Intel native (arm64 /
x86_64) and the installer strips the Gatekeeper quarantine attribute
(`xattr -d com.apple.quarantine`) so first launch is not blocked. Gatekeeper
may still warn on first run of an unsigned binary — right-click → Open, or
System Settings → Privacy & Security → Allow.

### Windows

From PowerShell:

```powershell
irm https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/install.ps1 | iex
```

or from cmd.exe:

```bat
powershell -Command "irm 'https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/install.ps1' | iex"
```

or download and run: `powershell -ExecutionPolicy Bypass -File install.ps1`.
`uv` provides Python 3.11 if missing; the app installs to
`%USERPROFILE%\ecoos\toolchain\eco-harness` and `eco-harness.cmd` /
`eco-harness-update.cmd` shims are added to your **user PATH** (available in
new terminals).

### After install (all native OSes)

```bash
eco-harness                 # serve the UI + API on http://localhost:8000
eco-harness-update          # self-update (wheel + binaries + RAG index)
eco-harness doctor          # one-command health report
```

Open http://localhost:8000 — the setup wizard at `/setup` walks you through
the OpenRouter key (or **Skip — add later in `.env`**; the app runs degraded
but starts regardless).

Installed layout (Eco platform standard, see `env.example`):
`ECO_HOME` (default `~/ecoos`) is the ecosystem root, `ECO_TOOLCHAIN` =
`$ECO_HOME/toolchain`, and the app home `ECO_HARNESS` =
`$ECO_TOOLCHAIN/eco-harness`:

```text
~/ecoos/                          # ECO_HOME — Eco OS ecosystem root
├── toolchain/                    # ECO_TOOLCHAIN
│   ├── eco-cli/                  # ECO_CLI      (native eco-cli + bundle)
│   ├── eco-wizard/               # ECO_WIZARD
│   ├── eco-idl/                  # ECO_IDL      (future)
│   └── eco-harness/              # ECO_HARNESS — this app's home:
│       ├── venv/                 #   Python 3.11 venv (uv-managed)
│       ├── bin/                  #   fallback binary dir + Windows shims
│       ├── data/                 #   marketplace_index.sqlite + marketplace_cache/
│       ├── .env                  #   OPENAI_API_KEY, ECO_API_TOKEN, … (chmod 600)
│       ├── workspace.yaml        #   UI settings overrides
│       ├── output/               #   generated projects + session registry
│       └── traces/               #   per-session LLM traces
├── framework/devkit              # ECO_FRAMEWORK
├── framework/runtime             # ECO_FRAMEWORK_RT
└── workspace/                    # ECO_PROJECTS_DIR — your projects
```

eco-cli / eco-wizard are downloaded ONLY when not already present: the
installer checks `ECO_CLI` / `ECO_WIZARD` env vars and the standard locations
first, keeps user-installed copies as-is (version-checked — outdated ones get
a replacement recommendation instead of an overwrite; `PATH` finds are never
probed/executed), and installs fresh downloads into
`$ECO_TOOLCHAIN/<tool>`, falling back to the app-home `bin/` folder when
those directories cannot be created. Harness-managed copies (carrying the
`.<tool>.version` marker) are refreshed in place by `eco-harness update`.
When `ECO_CLI` or `ECO_WIZARD` is supplied in the installer environment, the
installer intentionally persists that value into the app-home `.env`; this
keeps the explicitly selected user-owned binary winning on later launches
and avoids silently switching versions.

Uninstall: remove the app home (`~/ecoos/toolchain/eco-harness`, Windows:
`%USERPROFILE%\ecoos\toolchain\eco-harness`; pre-standard installs:
`~/.eco-harness`) and the shim files / user-PATH entry. The installer-managed
tool directories are sibling paths (`$ECO_TOOLCHAIN/eco-cli` and
`$ECO_TOOLCHAIN/eco-wizard`); remove those only when they are not shared with
other Eco tools. Preserve `$ECO_HOME/framework` and `$ECO_HOME/workspace` if
other Eco components or projects use them. For a complete Eco installation
removal, delete `$ECO_HOME` only after confirming it contains no other data.

### Docker (any host with Docker)

```bash
# Linux / macOS (note `-s --` to pass flags through the pipe):
curl -fsSL https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/install.sh | sh -s -- --docker
```

```powershell
# Windows — irm | iex cannot take flags; download first, then run:
curl.exe -fsSLO https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/install.ps1
powershell -ExecutionPolicy Bypass -File install.ps1 -Docker
```

Writes the app home's `docker-compose.yml` with your absolute host paths,
pulls the prebuilt multi-arch image (linux/amd64 + linux/arm64) from
ghcr.io, starts it, then downloads the native binaries and RAG index from
the same public GitHub release (sha256-verified, exactly like the native
flow) into the mounted ecosystem root (visible to the container as `/data`;
tools use `/data/toolchain/<tool>` and the harness app home is
`/data/toolchain/eco-harness`). The in-container update uses the public
release manifest by default — no S3 or extra configuration involved.

```bash
# update the image:
docker compose -f ~/ecoos/toolchain/eco-harness/docker-compose.yml pull && \
docker compose -f ~/ecoos/toolchain/eco-harness/docker-compose.yml up -d
# update the binaries + RAG index (re-runs the manifest-driven download):
docker compose -f ~/ecoos/toolchain/eco-harness/docker-compose.yml exec eco-harness python -m eco_harness update
# health:
docker compose -f ~/ecoos/toolchain/eco-harness/docker-compose.yml exec eco-harness python -m eco_harness doctor
```

### Key paths / env vars in installed mode

| What | Where |
|---|---|
| Ecosystem root (`ECO_HOME`) | `~/ecoos` (`toolchain/`, `framework/`, `workspace/`) |
| App home (`ECO_HARNESS`) | `$ECO_HOME/toolchain/eco-harness` (`venv/`, `bin/`, `data/`, `.env`, `output/`, `traces/`) |
| User project (`ECO_PROJECT_DIR`) | picked in the UI folder browser (or pre-set with `--project-dir`); defaults to `ECO_PROJECTS_DIR` (`$ECO_HOME/workspace`) when it exists |
| Binary lookup order | explicit → `ECO_CLI` / `ECO_WIZARD` env (legacy `ECO_<NAME>_PATH` still read) → `$ECO_TOOLCHAIN/<name>` → app-home `bin/` (`.exe` probed on Windows) → `PATH` |
| Prebuilt index | `$ECO_HARNESS/data/marketplace_index.sqlite` (refreshed by `eco-harness update`) |
| Config file | `$ECO_HARNESS/.env` (or `$ECO_HARNESS/workspace.yaml` for UI settings) |

For the packaging internals (wheel contents, manifest contract, hosted
artifacts, CI pipeline) and the go-live checklist (§18.9) see
`WORKING_DOCUMENTATION.md` §18.

## Quick Start (developers)

The shortest path uses the Makefile targets (`setup` → `index` →
`preflight` → `up`); the equivalent manual steps follow below.

```bash
make setup      # .venv + eco_harness/agent/requirements.txt + .env seeded from env.example
make index      # fetch marketplace components + build the RAG index (needs tokens in .env)
make preflight  # validate binaries, cache, index (--fix applies safe fixes)
make up         # docker compose up --build (dev stack, UI :3100 / API :8100)
```

> Package note: the Python packages moved under `eco_harness/` for PyPI
> (`eco_harness.agent`, `eco_harness.backend`). Repo-root `agent` / `backend`
> remain as import shims; use the `eco_harness.*` names in new code.

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
#      ECO_CLI         - absolute path to the eco-cli binary (or put it in <repo>/bin/
#                        or $ECO_TOOLCHAIN/eco-cli; legacy ECO_CLI_PATH still works)
#      ECO_WIZARD      - absolute path to the eco-wizard binary (same options;
#                        legacy ECO_WIZARD_PATH still works)
#    OPENROUTER_URL defaults to https://openrouter.ai/api/v1 if unset.

# 3. Prepare executables — canonical home is <repo>/bin/ (gitignored):
mkdir -p bin
cp /path/to/eco-cli bin/
cp /path/to/eco-wizard bin/
#    On a Windows host ALSO drop the Linux ELF builds (extensionless
#    eco-cli / eco-wizard + libaws-crt-jni.so) into bin/ — the dev container
#    consumes them through the monorepo bind-mount.
#    Or skip this and set ECO_CLI / ECO_WIZARD in .env (see step 2).

# 4. Set up the host Python environment for the initialization scripts
#    build_marketplace_index.py imports eco_harness.agent.rag.* (sqlite-vec,
#    tree-sitter, httpx, python-dotenv), so the harness deps are required.
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r eco_harness/agent/requirements.txt

# 5. Export the variables the host scripts read from the shell, then run them
#    (fetch_marketplace.py reads ECO_API_TOKEN/ECO_CLI from the shell env;
#     ECO_CLI is optional when bin/eco-cli(.exe) is in place,
#     build_marketplace_index.py loads .env itself via dotenv)
export ECO_API_TOKEN="token generated in ecoos.dev marketplace (component registry)"
# export ECO_CLI="path to eco-cli on this PC"   # only outside <repo>/bin/

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
source .venv/bin/activate  # On Windows: .venv\Scripts\activate or in GitBash use: source .venv/Scripts/activate

pip install -r eco_harness/agent/requirements.txt

# 2. Set up Node.js frontend
cd frontend
npm install
cd ..

# 3. Configure environment
cp env.example .env
# Edit .env with your settings

# 4. Prepare executables (place in PATH or set ECO_CLI/ECO_WIZARD)

# 5. Run initialization scripts
python scripts/fetch_marketplace.py
python scripts/build_marketplace_index.py

# 6. Start services in separate terminals:
# Terminal 1: uvicorn eco_harness.backend.server:app --host 127.0.0.1 --port 8000
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
`eco_harness/agent/internal/tools/binaries.py::resolve_binary`:

1. explicit argument (harness.yaml `eco_*_path` settings, tool args)
2. `ECO_CLI` / `ECO_WIZARD` env (legacy `ECO_<NAME>_PATH` spellings still honoured)
3. `$ECO_TOOLCHAIN/<name>` — the standard platform location (binary inside
   the tool directory or the file itself)
4. `<repo>/bin/<name>` — the canonical, gitignored dev home / installed-mode
   app-home `bin/` fallback (the Windows `.exe` spelling is required)
5. System `PATH` (called as-is)

No other locations are probed. The dev container reads `<repo>/bin/` (the
same canonical home) through the monorepo bind-mount at `/app`, so neither
host nor container needs env vars; use `ECO_CLI` / `ECO_WIZARD`
in `.env` only for custom locations.

Native installs never need wine: the installer downloads the target-OS build
into `$ECO_TOOLCHAIN/<name>` and falls back to the app-home `bin/` directory.
`ECO_CLI_PREFIX` / `ECO_WIZARD_PREFIX`
wine wrappers remain available only as a legacy override.

**When to use the env vars:** custom executable locations or pinning a
specific version. Values must be **absolute** paths (no `~` expansion, no
repo-root anchoring) and are interpreted by the resolving process — a host
path for host runs, a container path (e.g. `/app/...`) inside the api
container. For normal setups just drop the binaries into `<repo>/bin/`
(dev), use the standard toolchain directories, or let the installer
provision them — no config is needed.

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
| `ECO_CLI` | binary resolution | `$ECO_TOOLCHAIN/eco-cli` → `<repo>/bin/eco-cli` → PATH | eco-cli binary or tool dir (legacy `ECO_CLI_PATH` still read) |
| `ECO_WIZARD` | binary resolution | `$ECO_TOOLCHAIN/eco-wizard` → `<repo>/bin/eco-wizard` → PATH | eco-wizard binary or tool dir (legacy `ECO_WIZARD_PATH` still read) |
| `ECO_IDL` | binary resolution (reserved) | `$ECO_TOOLCHAIN/eco-idl` → `<repo>/bin/eco-idl` → PATH | future eco-idl binary or tool dir (legacy `ECO_IDL_PATH` also read) |
| `ECO_CLI_PREFIX` | eco_cli tool | — | Wrapper command for Windows binaries under Linux (e.g. `wine64`) |
| `ECO_WIZARD_PREFIX` | eco_wizard tool | — | Same, for eco-wizard |
| `ECO_WIZARD_TIMEOUT_S` | eco_wizard tool | `180` | Scaffold generation timeout |
| `ECO_CLAUDE_PATH` / `ECO_CODEX_PATH` / `ECO_GROK_PATH` / `ECO_PI_PATH` | factory / ExternalCliBackend | PATH lookup | External sub-agent binaries; flags come from `config/agents/external/<name>.yaml` |
| `ECO_MAKE_EXE` | server chat handler | `make` | Path to the make binary used by builds |
| `MARKETPLACE_CACHE_ROOT` | paths.py consumers | `<repo>/marketplace_cache` → `$ECO_HOME/data/marketplace_cache` → `/app/marketplace_cache` | Pre-pulled component cache |
| `MARKETPLACE_INDEX_PATH` | paths.py consumers | `<repo>/marketplace_index.sqlite` → `$ECO_HOME/data/marketplace_index.sqlite` → `/app/marketplace_index.sqlite` | sqlite-vec RAG index |
| `ECO_FRAMEWORK` | paths/assembler, eco_cli pulls, index builder, eco-wizard | `<repo>/eco_framework` | Standard ACOM env var: root of the component development kits (`<Component>_DK_v.<ver>/<Component>/`). Used to source Eco.Core1 base headers into prompts, as `eco-cli pull -d` download target, and via `build_marketplace_index.py --source framework` |
| `HARNESS_OUTPUT_ROOT` | server | `<repo>/output` (dev) / `$ECO_HOME/output` (installed) | Where per-chat workspace dirs are created |
| `HARNESS_TRACES_DIR` | server | `<repo>/traces` (dev) / `$ECO_HOME/traces` (installed) | Per-conversation LLM trace folders |
| `HARNESS_ALLOWED_ROOTS` | server: `/api/fs/browse`, `/api/projects`, WS `project_dir` | home dir + `HARNESS_OUTPUT_ROOT` | Extra directories (os.pathsep-separated) the UI may browse, register, or target as `project_dir` |
| `HARNESS_MAX_HOPS` | orchestrator | `8` | Max handoff hops (also `harness.yaml.max_hops`) |
| `HARNESS_PLAN_HANDOFF_MAX_BYTES` | architect `to_coder` gate | `8192` (`harness.yaml.plan_handoff_max_bytes`) | Bytes-of-markdown cap on the architect's handoff to the coder. Plan validator BLOCKS the `to_coder` call when the plan exceeds this; raise for big multi-component apps, lower when targeting small-context models. |
| `AGENT_MAX_ITERATIONS` | `build_pipeline` runs only | unset | Overrides per-role `max_iters` for scripted pipeline runs; production `/ws/chat` uses `budgets.max_iters` from `config/roles.yaml` |
| `HARNESS_DYNAMIC_TAIL_ITEMS` | agent context | `5` (`harness.yaml`: 12) | Newest tool results kept verbatim in context |
| `HARNESS_RETAINED_TOOL_OUTPUTS` | agent context | `budgets.yaml.retained_tool_outputs` (5) | Wired alias controlling `max_tool_results` context retention |
| `HARNESS_SOURCE_MAX_BYTES` | context assembler | `300000` | Cap on static source material in the system prompt |
| `HARNESS_PREPULL_FRAMEWORK` | server scaffold | `1` | `0` disables copying framework components into project_dir |
| `HARNESS_TOOL_DEDUP` | read-only tool memo-dedup | on | `0` disables dedup kill-switch (consistent name across code/.env/env.example) |
| `HARNESS_WARM_SEED` | server warm-retry | `0` | `1` enables warm retry seeds |
| `HARNESS_SCAFFOLD` | server scaffold | on | `0` disables pre-seeding src/EcoMain.c + Makefile |
| `FILE_SEARCH_BACKEND` | server `/api/fs/search` | `os_walk` | File-search backend for the `@`-mention picker: `os_walk` (zero-dependency recursive walk, default) or `fff` (opt-in `fff-search` wheel; automatically falls back to `os_walk` if the wheel is absent). The query `backend` param is only a hint. |
| `ECO_WORKTREE_ROOT` / `ECO_PROJECT_DIR` | worktrees / server | repo default / unset (UI folder picker) | Isolated git-worktree root / user project dir (installed mode: user projects + worktrees live under it) |
| `ECO_HARNESS_WORKSPACE_CONFIG` | config loader | `<repo>/.eco-harness/workspace.yaml` (dev) / `$ECO_HOME/workspace.yaml` (installed) | Workspace override file |
| `ECO_ROLE_<ROLE>_BACKEND` / `_MODEL` / `_REASONING` / `_MAX_TOKENS` | config loader | `roles.yaml` | Per-role overrides (e.g. `ECO_ROLE_CODER_BACKEND=pi`) |
| `DEFAULT_LANGUAGE` | config loader | `C` | Default implementation language |

Optional external env vars consumed indirectly by eco-cli/eco-wizard:
`ECO_API_TOKEN`, `ECO_FRAMEWORK` / `ECO_FRAMEWORK_PATH` (framework DK path).

3. **Optional configuration notes:**
   - `MARKETPLACE_CACHE_ROOT` / `MARKETPLACE_INDEX_PATH` are normally NOT
     needed: on a host checkout the repo-root artifacts are detected
     automatically; in Docker the `/app` mounts are detected too; native
     installs find them under `$ECO_HOME/data/` (seeded by the installer).

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
├── eco-cli(.exe)          # host-OS build for host-run scripts/agents
├── eco-wizard(.exe)         (eco-cli.exe / aws-crt-jni.dll on Windows)
├── eco-cli                # Linux ELF — used inside the dev container
├── eco-wizard             # (same files serve both on Linux/macOS hosts)
└── libaws-crt-jni.so      # Linux sidecar JNI lib, next to the ELF binaries
```

Both platform flavors may sit side by side: Windows host runs resolve
`eco-cli.exe` first, the dev container resolves the extensionless Linux ELF
through the monorepo bind-mount at `/app` (`<repo>/bin/` is visible
in-container at `/app/Eco.Toolchain/Eco.AI.Assembly1/bin/`) — so both host
and container resolve without any env vars and without dedicated mounts.
JNI sidecar libraries must sit NEXT TO their executables.

### Docker Compose Deployment

**Prerequisites (on host):**
1. `.env` file configured
2. `marketplace_index.sqlite` created (via `build_marketplace_index.py`)
3. `marketplace_cache/` directory populated (via `fetch_marketplace.py`)
4. Binaries placed in `<repo>/bin/` (host build `eco-cli(.exe)` /
   `eco-wizard(.exe)` plus the Linux ELFs for the container; the container
   reads them through the monorepo bind-mount — no env vars, no dedicated
   mounts)

**Start the application:**
```bash
docker compose up --build
```

**Access endpoints:**
- Web UI: http://localhost:3100
- API: http://localhost:8100
- WebSocket: ws://localhost:8100/ws/chat

**Volume Mounts in Docker Compose:**
- `../..:/app:rw` - the **entire monorepo** (the dir owning `.git`) as one
  unit, so the harness's git operations (`git worktree add`, etc.) resolve.
  Mount the repo root, not `.git` alone. `working_dir` points at the nested
  project, so the code is still reached correctly. Relative to this compose
  file, so it works on any machine with the same checkout layout.
- `${ECO_WORKTREE_HOST_DIR:-../../../Eco.AI.worktrees}:/repo-worktrees:rw` -
  host worktree root; paired with `ECO_WORKTREE_ROOT=/repo-worktrees` so
  created worktrees persist on disk. Default lands next to the monorepo root,
  same as harness host runs; override per machine via `.env`. Note: host
  `git worktree list` shows these entries as *prunable* (container-side paths
  are recorded) — see the Worktree-mode setup note below.
- `marketplace_index.sqlite` (read-write) plus read-only `marketplace_cache`,
  `eco_framework`, and `config` overlays are mounted at their nested paths on
  top of the monorepo mount (`config/:ro` keeps agent write tools away from
  prompts/permission baselines; the UI settings pane writes
  `.eco-harness/workspace.yaml`, which stays writable).
- eco-cli / eco-wizard (and their JNI sidecar libraries) have **no dedicated
  mounts**: they are consumed from `<repo>/bin/` — the canonical gitignored
  home — through the monorepo mount above
- `api.environment` also sets `GIT_CONFIG_*=safe.directory=/app` so
  root-in-container can operate on the host-owned repo (alternatively run as
  your host uid — see the commented `user:` line in the compose).

**Important:** The RAG index (`marketplace_index.sqlite`) is mounted read-write because the UI can update it through import functionality. The component cache (`marketplace_cache/`) is read-only as it contains pre-downloaded components.

## Configuration

Repository configuration is under `config/`:

### Path Resolution System

One shared resolver (`eco_harness/agent/internal/tools/binaries.py::resolve_binary`)
handles every external binary, host and container alike:

1. Explicit config (e.g. `harness.yaml` `eco_cli_path` / `eco_wizard_path`)
2. `ECO_CLI` / `ECO_WIZARD` env (legacy `ECO_<NAME>_PATH` spellings still read)
3. `$ECO_TOOLCHAIN/<name>` (standard platform location, e.g.
   `~/ecoos/toolchain/eco-cli` — binary inside the dir or the file itself)
4. `<repo>/bin/<name>` (canonical, gitignored dev home / installed-mode
   app-home `bin/` fallback; `.exe` on Windows)
5. System `PATH`

**Environment Variable Examples:**
```bash
# Canonical home (recommended):
export ECO_CLI=$PWD/bin/eco-cli
export ECO_WIZARD=$PWD/bin/eco-wizard

# Docker: no env vars needed — the container reads <repo>/bin/ (Linux ELF
# builds) through the monorepo bind-mount (see docker-compose.yml).

# Windows executable via wine:
export ECO_CLI=/path/to/eco-cli.exe
export ECO_CLI_PREFIX=wine64

# Custom path (development)
export ECO_CLI=/usr/local/bin/eco-cli
export ECO_WIZARD=/home/user/tools/eco-wizard
```

**Default `.env` configuration:**
```
# Host and container: leave unset when the binaries are in <repo>/bin/ or on
# PATH (the container reads <repo>/bin/ through the monorepo mount).
# Override only for custom locations:
# ECO_CLI=/usr/local/bin/eco-cli
# ECO_WIZARD=/home/user/tools/eco-wizard
```

| File | Purpose |
| --- | --- |
| `harness.yaml` | defaults, cache limits, hop limits, executable paths |
| `models.yaml` | named model profiles |
| `roles.yaml` | backend, model profile, reasoning, tools, budgets, per-role permission baseline |
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
per model, with this precedence (workspace profiles merge over
`config/models.yaml` per key; a workspace `models: {name: null}` entry removes a
profile):

```text
model profile's provider_pin (workspace models > config/models.yaml)  >  OPENROUTER_PROVIDER_PIN (.env)
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
`eco_harness/agent/pi_ai/providers/openai_completions.py` caps it to fit the model context once
the system prompt is included, preventing HTTP 400 overflow. `harness.yaml:
source_roots` / `max_source_bytes` (300000) now drive the curated `Eco.Core1`
stitch (see context injection below).

Live vs baked config: the **entire monorepo** is bind-mounted into the api
container (see `docker-compose.yml`), so edits to `./eco_harness`,
`./config`, and `./scripts` apply on uvicorn reload / next request (dev
compose). `working_dir` targets the nested project dir.

Precedence is:

```text
environment variables > .eco-harness/workspace.yaml > config/*.yaml > code defaults
```

UI role settings are stored in `.eco-harness/workspace.yaml` (written by the
Settings panel via `PUT /config/workspace`; sections a client does not send —
e.g. `harness` — are preserved). Keep API keys and secrets in `.env` or a
secret manager, never in YAML.

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

## Settings panel

The gear icon opens the settings sidebar with five tabs. Everything it saves
lands in `.eco-harness/workspace.yaml` (the workspace override layer) and is
picked up by new sessions — running pipelines keep the config they started
with. One **Save settings** button persists all tabs; **Discard** reloads the
server state.

### Roles — per-role backend, model, reasoning

Each role (architect, coder, tester, reviewer) is a card with three selects:

- **backend** — `internal` or an external CLI (`pi`, `codex`, `claude`, `grok`)
- **model** — any profile from the model registry, or **Custom…** for an
  ad-hoc `provider/model-id` string (no registry entry needed)
- **reasoning** — `minimal` … `xhigh` (overrides the profile default)

### Models — the model registry

Lists every configured model profile with provider/reasoning/PIN badges and
which roles use it. From here you can add, edit, or remove profiles:

- **Add model** takes a profile name, the model ID (`provider/model-id`), a
  provider, the default reasoning level, an optional OpenRouter **provider
  PIN** (a routing hint — which upstream provider serves the model, e.g.
  `tencent`; *not* a secret), and optional `max_tokens` / `temperature`.
- Profiles still owned by `config/models.yaml` can be edited (the edit is
  persisted as a workspace override) or deleted (persisted as a removal
  marker). A profile referenced by a role cannot be deleted.
- The `default` profile always exists — deleting it resets it to the
  `LLM_MODEL` env value.

### Access — LLM permissions

Permissions are bound to **roles**, not models: models are interchangeable
capability providers, roles are the harness's trust boundary. There are two
layers, resolved per role (later wins, key-by-key):

```text
code defaults < workspace defaults < repo roles.yaml per-role baseline < workspace per-role override
```

- **Harness defaults** — seven tool groups plus a command allowlist applied
  to every role:

  | Group | Gates |
  | --- | --- |
  | File read | `grep` `glob` `read` `read_file` `list_dir` `read_component_profile` |
  | File write | `write_file` |
  | Build | `run_build` (make) |
  | Run binaries | `run_artifact` |
  | RAG search | `search_marketplace` |
  | Skills | `read_skill` |
  | Network | `eco_cli` `eco_wizard` |

  The **command allowlist** narrows execution tokens: make targets (or
  `make` for a default build), artifact basenames for `run_artifact`, and
  eco-cli subcommands. `*` (default) allows everything; an **empty list
  denies all** gated commands.

- **Per-role overrides** — a matrix of the same groups per role. Toggle a
  cell to deviate from the defaults; a `reset` link clears a role's
  deviations. Handoff/stop tools (`to_*`, `fail`) are pipeline plumbing and
  are never gated.

Enforcement is real: denied tools are removed from the role's toolset before
the system prompt is built (the model never sees them), and gated execution
tools are wrapped with the allowlist check (`eco_harness/permissions.py`).
It is a policy layer on top of the tools' own sandboxes (project_dir
containment, eco-cli subcommand whitelist), not a replacement for them —
and it applies to **internal** backends only: external CLI backends
(pi/codex/claude/grok, marked `ext` in the matrix) run in their own process
with their own tool policy.

### RAG — index import, export, status

Shows live index stats (chunks, size, last import), imports files/folders,
and **exports** `marketplace_index.sqlite` for backup or another workspace.
See [RAG import and export](#rag-import-and-export) for formats and endpoints.

## Language and platform selection

The UI exposes `C`, `CPP`, `Python`, and `Java` beside the platform selector.
Language prompt and skill profiles are selected from `config/languages.yaml`
and `config/skills/languages/`. Python and Java layouts are intentionally
delegated to the upcoming `eco-wizard` release rather than invented by the
model.

## RAG import and export

The Settings panel (RAG tab) shows live index stats — chunk count, size, and
the last import summary — and accepts individual files, browser-selected
folders, source documents, Markdown/text documentation, and compatible SQLite
dumps. Imports update `marketplace_index.sqlite` through
`scripts/import_rag.py`; **Export** downloads the current index (a valid
SQLite file that can be re-imported as a dump or dropped into another
workspace as-is).

The API endpoints are:

- `GET /rag/status` — chunk count, size, last-import summary
- `POST /rag/import`
- `GET /rag/export`

For CLI use:

```cmd
python scripts/build_marketplace_index.py --rebuild
# Index straight from the ACOM development-kit tree ($ECO_FRAMEWORK) instead
# of a prior fetch into marketplace_cache/:
python scripts/build_marketplace_index.py --rebuild --source framework
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

`eco_harness/backend/scaffold/` (shipped as wheel data) remains only as an
explicit compatibility fallback. It is
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

The harness has a two-layer customization model: git-tracked repo defaults
under `config/` and an operator-owned workspace layer under `.eco-harness/`
(no repo changes needed, survives pulls). Everything is resolved at agent
construction; lower layers win only when the workspace layer is absent or
empty.

### Role prompts: `config/prompts/` vs `.eco-harness/prompts/`

Resolution (first non-empty wins):

```text
1. .eco-harness/prompts/<role>.md    workspace override — replaces entirely
2. config/prompts/<role>.md          editable source of truth
3. built-in constant                 fallback in eco_harness/agent/internal/agents/<role>.py
```

Create `.eco-harness/prompts/coder.md` and the coder runs with YOUR text
instead of the repo prompt. An empty or whitespace-only file is treated as
absent, so a stub can never blank out real instructions.

### Skills: same name overrides, new names must be declared

Skill bodies are searched with the **workspace first** (`.eco-harness/skills/`
→ `config/skills/`), name order `v<N>.md → SKILL.md → <skill>.md`:

- **Same name** → your workspace body replaces the repo skill
  (`.eco-harness/skills/acom_framework/v1.md` wins over
  `config/skills/acom_framework/v1.md`).
- **Different name** → it becomes available as an additional skill, but it
  does NOT self-activate. A skill only loads when listed in the merged
  `skill_versions` map (`roles.yaml` / `languages.yaml`, overridable per
  workspace).

To activate skills for a role, override its map in
`.eco-harness/workspace.yaml`:

```yaml
roles:
  coder:
    skill_versions:            # NOTE: wholesale replacement of the repo map
      acom_framework: "1"      # keep — body from .eco-harness/skills/ if present
      eco_wizard: "1"          # keep
      team_style: "1"          # add — .eco-harness/skills/team_style/v1.md
```

Only `budgets` blocks merge key-by-key; every other role/language key
(including `skill_versions`) replaces the repo value wholesale when set in
the workspace file.

### On-demand skills (Anthropic-style)

Large or rarely-needed skills can be made dynamic instead of always baked
into the system prompt. Create a `SKILL.md` with YAML frontmatter:

```markdown
---
name: my_skill
description: One line saying WHEN the agent should fetch this skill.
---
(free-form markdown body)
```

Behavior once referenced from `skill_versions`:

- The prompt receives only the one-line description in an
  `=== ON-DEMAND SKILLS ===` manifest (plus the source path).
- Internal agents fetch the full body on demand via the auto-wired
  `read_skill` tool; external CLI agents read the listed path themselves.
- A plain `v<N>.md` file (or frontmatter-less `SKILL.md`) keeps the classic
  always-injected behavior — both forms coexist.

First live example: `config/skills/component_author/SKILL.md` (~60 KB of ACOM
C templates) — the coder sees only its description until hand-authoring
component code without eco-wizard makes fetching worthwhile.

### Rules files

Project-wide rules go in the root `AGENTS.md`; all layers found are
concatenated (repo root first):

```text
config/agents/<role>/AGENTS.md
.eco-harness/agents/<role>/AGENTS.md
```

### Domain vs language rules split

`config/prompts/acom_domain.md` holds language-agnostic ACOM knowledge
(identifier taxonomy, framework stack, dev-kit boundary, EcoMain flow, trust
model) and is shared by every role and language. All language-specific coding
conventions live once in `config/skills/languages/<lang>.md`. When adding
rules, put them in exactly one place — the two cross-reference each other
instead of duplicating.

The legacy `agent/skills/` root was retired in PRD_2 Phase 2
(`agent/skills/c.md` → `config/skills/component_author/`; the file later
became the on-demand `SKILL.md`). The root-level `agent`/`backend`
directories are now back-compat import shims — real code lives under
`eco_harness/`.

  Language skills belong in `config/skills/languages/<language>.md`. Stable
  prompt changes belong in `config/prompts/`; workspace-specific instructions
  belong in `.eco-harness/`.

## Initial context injection

Every role's initial context (system prompt) is assembled once per agent
construction by `eco_harness/agent/context/assembler.py::build_static_system_prompt`
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
3. built-in constant                  fallback in eco_harness/agent/internal/agents/<role>.py
```

Empty or placeholder files are skipped, so they can never blank out real
instructions.

**Cache/token efficiency**: blocks 1–3 are byte-identical for every role,
mode, language, and backend; the Eco.Core1 stitch is C-only (`.h` headers,
`.hpp` wrappers excluded — ~29% smaller) and constant across turns and tasks;
only the ROLE INSTRUCTIONS block varies per selection
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
  (`ECO_*_PATH` → `<repo>/bin/` → `PATH`) and,
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
waits for your `plan_decision` before the coder runs (`eco_harness/backend/server.py`).
`plan` / `code` / `test` / `review` load exactly one role with its profile and
never auto-trigger the cross-role pipeline, so you can switch roles freely from
the mode menu. Each mode selects its own system prompt and capability set from
`config/modes.yaml`.

## Attaching files & @-mention

The chat input supports **session-scoped file attachments** so the agent can
read your files directly. Attachments ride on **every** message in the current
session (until you start a New Session) — they are not cleared after a single
send, so the planner *and* the coder both see them.

- **@-mention a file** — type `@` anywhere in the message to open a file
  autocomplete. It searches from the active project root (or your home when no
  project is selected) and inserts a `@relative/path` token. The file is added
  to the attachment list and the agent reads it by its real path.
- **`+` button** — opens a file picker rooted at the active project. Select one
  or many files across folders (selections accumulate as you navigate); they are
  attached by absolute path.
- **Paste / drag-and-drop** — paste or drop images and text. Pasted content is
  attached inline (images ≤ 5 MB; larger files should use the `+` picker).
- **Chips** — attached files appear as removable chips above the input. Remove
  any one with its `×`, or clear everything with **New Session** (which keeps
  your platform / language / mode / worktree / project settings).

> **How delivery works:** small text files are inlined into the prompt; large
> text files and images are copied into `project_dir/.eco-attachments/` and
> referenced by path so the agent can `read()` them on demand; files already
> inside the project are referenced by their real relative path (no copy).
> The total attachment payload per message is capped at ~12 MB to protect the
> WebSocket connection.

## Worktree isolation

Enable **Worktree** beside the chat input, or pass `--worktree` to the CLI.
The harness creates a detached Git worktree outside the primary checkout and
uses it as the project root for all subsequent agent filesystem operations in
that session. It never silently modifies the primary checkout. A custom
destination can be configured through `ECO_WORKTREE_ROOT`.

When no explicit name is given, the worktree directory is auto-named
`<repo>-<session8>-<commit7>` (e.g. `Eco.AI.Assembly1-3f2b8c1a-d41cd09`) —
unique per session and directly findable via `git worktree list` or a
directory search. The name and full path appear on a reference strip below
the progress bar as soon as the worktree is created and stay visible until
you press New session.

> **Container setup (Worktree mode):** the `api` container runs as **root**
> while the repo is owned by your host user, so Worktree mode needs two things
> in `docker-compose.yml` (all paths below are compose-relative, so the file
> stays portable across machines):
>
> 1. Mount the **whole git repo root** (the directory that *contains* `.git`),
>    not `.git` alone, as one volume — `../..:/app:rw`. A lone `.git` mount
>    has no working tree beside it, so `git worktree add` fails. The nested
>    project code is reached via `working_dir`.
> 2. Bypass git's ownership check by setting in `api.environment`:
>    `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=safe.directory`,
>    `GIT_CONFIG_VALUE_0=/app` (scope it to the mounted repo path; `*` would
>    disable the check for every path git touches). Alternatively run the
>    container as your host uid — set `UID`/`GID` in `.env` and uncomment the
>    `user:` line in the compose (note: wine re-inits its root-baked prefix on
>    first use; `chown -R` any dirs a root-run container created first).
>    Worktrees land under `/repo-worktrees`, backed by a host bind whose
>    location is chosen per machine via `.env`: `ECO_WORKTREE_HOST_DIR=/abs/path`
>    (default: `<monorepo>.worktrees` sibling of the repo root).
>    **Pre-create that directory as your own user before the first
>    `docker compose up`** (`mkdir -p ...`) — Docker silently auto-creates
>    missing bind sources as root:root, and a typo'd path materializes an
>    unintended root-owned dir with no error.
>
> **Host visibility caveat:** worktree metadata inside `.git/worktrees/`
> records the *container* path (`/repo-worktrees/<name>`). On the host,
> `git worktree list` shows those entries as **prunable** ("gitdir file points
> to non-existent location") and host-side git operations against them fail.
> The files themselves persist on disk at `ECO_WORKTREE_HOST_DIR`. Do NOT run
> `git worktree prune` on the host — and know that automatic `git gc` prunes
> missing-worktree entries older than `gc.worktreePruneExpire`
> (default: 3.months.ago) too, silently orphaning container-created worktrees.
> If you want host gc to keep them, set `git config gc.worktreePruneExpire
> never`. For fully valid host-side entries, mount the host dir at an
> identical absolute path inside the container and point the api service's
> `ECO_WORKTREE_ROOT` env at that same path — override it via `.env` with
> `ECO_WORKTREE_CONTAINER_ROOT=/that/same/path` (compose interpolates it;
> editing `.env` is enough, no compose edit needed).

> **Monorepo scoping:** `eco_harness.worktrees.create_worktree` always
> resolves the **git toplevel** (the monorepo root that owns `.git`) — never
> the nested project folder. The worktree is therefore a *full checkout of the
> monorepo* and the session `project_dir` points at the worktree root, so the
> agent operates at **monorepo scope**, not the nested-project scope. If you
> need the agent confined to the nested project, scope `project_dir` to the
> nested sub-path inside the worktree (a harness enhancement); the worktree
> itself is always repo-wide.

```cmd
python -m eco_harness run "Review this component" --mode review --worktree
python -m eco_harness /plan "Design a checksum component" --worktree
```

The CLI runs a single role one-shot (`plan|code|test|review`); the full
`auto`/`migrate` pipeline needs the human plan-approval gate and lives in the
UI / websocket API.

## Workspace and per-agent limits

### How the working folder is chosen

The workspace (`project_dir`) is chosen per chat session:

- **Explicit project:** register a folder through the UI (project panel /
  folder browser). In installed mode this sets `ECO_PROJECT_DIR` (pre-seed
  it at install time with `--project-dir`); the user's project — including
  worktrees — lives under it.
- **Default (no project registered):** `_output_root()` —
  `HARNESS_OUTPUT_ROOT` (default `<repo>/output` on a dev checkout,
  `$ECO_HOME/output` installed) + `proj-<thread8>`. A fresh sub-directory
  is created for each WebSocket session/thread, so concurrent chats never
  share a tree.
- **Worktree (isolated):** enable **Worktree** in the UI (or `--worktree` on
  the CLI). The harness then creates a detached Git worktree outside the
  primary checkout — under `ECO_WORKTREE_ROOT` — and uses that as
  `project_dir`. It never modifies the primary checkout.

All file tools are **sandboxed to `project_dir`** for writes: the coder's
`write_file` / `build` / `runtime` can only touch `project_dir`, while
`read` / `glob` / `grep` / `read_file` / `list_dir` may also read the
read-only `marketplace_cache`. UI role/model/language selections and the
permission policy are persisted in `.eco-harness/workspace.yaml` (see
[Settings panel](#settings-panel)).

### Per-agent space limits (budgets)

Each role's limits come from `config/roles.yaml` →
`roles.<role>.budgets` and are applied identically to every sub-agent
(architect, coder, tester, reviewer):

| Budget | Effect |
| --- | --- |
| `per_query_tokens` | Sent as the model `max_tokens`; a context-window-aware clamp in `eco_harness/agent/pi_ai/providers/openai_completions.py` caps it so the system prompt fits (prevents HTTP 400). |
| `per_query_usd` / `per_day_usd` | Cost ceilings for a single query / per day. |
| `max_iters` | Hard cap on the agent's tool-call loop iterations. |
| `max_wall_s` | Wall-clock timeout for the agent. |

Global guards: `HARNESS_MAX_HOPS` (default `8`) bounds orchestrator
handoffs. `AGENT_MAX_ITERATIONS` (env) applies only to scripted
`build_pipeline` runs (`eco_harness/agent/internal/entry.py`); the production
`/ws/chat` pipeline uses each role's `budgets.max_iters` from
`config/roles.yaml`. File-tool results are also
size-capped (`read` 32 KB default / 200 KB max, `read_file` 256 KB, `grep` 100
matches, `glob` 500 entries) so a single call can't blow the context budget.

## CLI and future MCP use

The headless entrypoint is:

```cmd
python -m eco_harness run "Design a calculator component" --mode plan --language C
python -m eco_harness run "Implement the approved plan" --mode code --language C
python -m eco_harness serve            # UI + API on http://localhost:8000
```

One-shot modes only (`plan|code|test|review`); use the UI / websocket for the
full `auto` pipeline with plan approval.

`eco_harness.adapters.AgentBackend`, `eco_harness.tools.ToolRouter`,
`eco_harness.interfaces.mcp`, and `eco_harness.extensions` are stable
boundaries for future CLI products, MCP servers, AST endpoints, and UI
panels. The current FastAPI server is an optional interface over those
boundaries, not the domain core.

## Release

## Release

The release workflow (`.github/workflows/release.yml`) publishes the
multi-arch container image to ghcr.io, and on `v*` tag pushes uploads ALL
consumer assets (manifest + installers + wheel + per-platform binary zips +
RAG index) to the public releases repo
[`peerf-eco/eco-harness-releases`](https://github.com/peerf-eco/eco-harness-releases)
— the only install channel. The install one-liners in `## Install` fetch
everything from that repo's `releases/latest/download/` URLs; no S3 or other
hosting is involved in installs. The prebuilt RAG bundle — **both**
`marketplace_index.sqlite` and `marketplace_cache/` inside one zip; the
installer never regenerates them locally — lives in a private S3 bucket
served publicly via CloudFront. The build job downloads it with plain curl
from the `RAG_INDEX_URL` repo variable, so CI carries no AWS credentials at
all. Refresh the bundle from a machine with marketplace/embedding access:

```bash
python scripts/publish_rag.py    # fetch marketplace → build index → zip (index + cache) → upload
```

Credentials and upload target come from `.env` (`AWS_ACCESS_KEY_ID` /
`AWS_SECRET_ACCESS_KEY` / `AWS_REGION`, `RAG_S3_BUCKET`, `RAG_S3_KEY` — see
env.example).

### Artifact layout

All build artifacts are staged under a `tag/` directory before upload:

```text
release-staging/
└── tag/
    ├── dist/                  # Python wheel (eco_harness-<ver>-py3-none-any.whl)
    ├── install/               # install.sh + install.ps1
    ├── binaries/
    │   ├── eco-cli/
    │   │   ├── linux/amd64/   # extracted binary + original .zip
    │   │   ├── linux/arm64/
    │   │   ├── darwin/amd64/
    │   │   ├── darwin/arm64/
    │   │   └── windows/amd64/
    │   └── eco-wizard/        # same layout
    └── index/
        └── marketplace_index.zip
```

Binaries are fetched from the source repos' public release-asset URLs:

```
https://github.com/{owner}/{repo}/releases/download/<tag>/<asset>.zip
```

For example:

```
https://github.com/peerf-eco/eco-cli-releases/releases/download/<tag>/eco-cli-linux-amd64.zip
https://github.com/peerf-eco/eco-wizard/releases/download/<tag>/eco-wizard-windows-amd64.zip
```

Version resolution order: `workflow_dispatch` input → `ECO_CLI_VERSION` /
`ECO_WIZARD_VERSION` repo variable → latest release tag from the source repo.

### Trigger paths

| Trigger | `publish-image` | `publish-manifest` | Image tag |
|---|---|---|---|
| `git push origin v<x.y.z>` (tag on main) | yes | yes — public release | `<x.y.z>` + `latest` |
| `push` to a branch (e.g. `main`) | — | — | — (no run; see note) |
| `workflow_dispatch` `dry_run=true` (default) | no — build only | no — build only | — |
| `workflow_dispatch` `dry_run=false` | yes | no — build only | `dev-<sha>` |

Branch pushes deliberately trigger nothing (fail fast): a tagless build's
GHA artifacts are run-scoped and would never be reused by a later tag run,
so every tagless build is throwaway work. Use `workflow_dispatch` to verify
a build.

### Automatic release (recommended)

The canonical path — creates a versioned image and a sha256-checksummed
manifest, published to `eco-harness-releases`:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub sees `refs/tags/v0.1.0`, the workflow validates the tag is on `main`,
builds the wheel, fetches binaries from the source repos' release-asset URLs,
downloads the RAG bundle from the public distribution URL (`RAG_INDEX_URL`),
then publishes the image as
`ghcr.io/<org>/Eco.AI:0.1.0` and `latest` and uploads every consumer asset
(manifest + installers + wheel + zips + index) to the `v0.1.0` release of
`eco-harness-releases`. From that moment `releases/latest/download/...` serves
the new version to all users.

### Manual trigger (workflow_dispatch)

Open **Actions → release → Run workflow** in the GitHub UI.

- `dry_run=true` (default) — runs the `build` job only. Builds the wheel,
  fetches binaries, downloads the RAG index, and uploads the GHA artifact
  `release-assets` for inspection. Nothing is published. Use this to verify
  the build before cutting a real release.
- `dry_run=false` — additionally pushes the image tagged `dev-<sha>`
  (not a semver tag) to ghcr for testing the image build without cutting a
  release. No public release or manifest update happens outside `v*` tags.
- `eco_cli_version` / `eco_wizard_version` — optional version pins
  (e.g. `v2.1.0`). Leave blank to use the `ECO_CLI_VERSION` repo variable
  or the latest release from the source repo.

Equivalent CLI invocation:

```bash
# dry run (build only, default):
gh workflow run release.yml

# build + dev-<sha> image, no public release (releases require a v* tag):
gh workflow run release.yml -f dry_run=false

# same, pinning the bundled eco-cli version:
gh workflow run release.yml -f dry_run=false -f eco_cli_version=v2.1.0

# a real release (publishes to eco-harness-releases):
git tag v0.1.1 && git push origin v0.1.1
```

### Pinning binary versions

```bash
# Pin permanently (all future releases use this version until changed):
gh variable set ECO_CLI_VERSION --body "v2.1.0"
gh variable set ECO_WIZARD_VERSION --body "v1.0.0"

# One-off override without changing the repo variable:
gh workflow run release.yml -f dry_run=false -f eco_cli_version=v2.1.0

# Always latest (default when variable is unset):
gh variable delete ECO_CLI_VERSION
```

## Troubleshooting

### Common Issues

1. **"eco-cli not found" error:**
   - Place the binary at `<repo>/bin/eco-cli` (canonical home; `eco-cli.exe`
     on Windows)
   - In Docker, verify the Linux ELF builds sit in `<repo>/bin/` (reached
     via the monorepo bind-mount); `ECO_CLI` / `ECO_WIZARD` are
     only for custom locations
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
- Test eco-cli in container: `docker compose exec api bin/eco-cli --version`
- Verify volume mounts: `docker compose exec api ls -la bin/`

## Testing

The regression suite lives in `eco_harness/agent/internal/tests/` and
`eco_harness/backend/tests/` and runs against the venv created during
setup (`make setup` or `python -m venv .venv` +
`pip install -r eco_harness/agent/requirements.txt`, which includes
`pytest` via `pytest-asyncio`). Always run it through the venv so the pinned
`pytest-asyncio` / `tree-sitter` versions match what CI expects:

```bash
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
python -m pytest eco_harness/agent/internal/tests eco_harness/backend/tests -v
# Or without activating:
.venv/bin/python -m pytest eco_harness/agent/internal/tests eco_harness/backend/tests
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
python -m pytest eco_harness/agent/internal/tests eco_harness/backend/tests
python -m compileall -q eco_harness scripts agent backend
# equivalent one-liner:
make test
```

## Validation

```bash
source .venv/bin/activate
python -m pytest eco_harness/agent/internal/tests eco_harness/backend/tests
python -m compileall -q eco_harness scripts agent backend
cd frontend
npm run build
```

See `WORKING_DOCUMENTATION.md` for the consolidated architectural decisions,
cache contract, migration notes, swarm extension design, and operational
troubleshooting.
