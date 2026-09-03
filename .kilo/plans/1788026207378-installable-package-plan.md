# Installable Package Plan — Eco.AI Harness (Native + Docker)

Working dir: `Eco.Toolchain/Eco.AI.Assembly1`

## Goal

Two customer-grade installation flows for the ACOM meta-harness, both as close to one-command as possible:

1. **Native**: Windows / Linux / macOS — no source checkout, no manual prerequisite steps.
2. **Docker**: any host with Docker — prebuilt images, no build step.

## Decisions (confirmed with user)

| Topic | Decision |
|---|---|
| Native packaging | Bootstrap script + PyPI wheel; `uv` provides Python 3.11 automatically if missing |
| Binaries | eco-cli / eco-wizard native builds for all 3 OSes already on S3 (public HTTPS). Installer always downloads the target-OS build. **No wine.** `ECO_CLI_PATH` / `ECO_WIZARD_PATH` overrides still honored for users with existing installs |
| RAG data | Prebuilt `marketplace_index.sqlite` + `marketplace_cache` downloaded from S3 at install; local rebuild can override |
| Frontend | Next.js `output: 'export'` static bundle shipped inside the wheel, served by FastAPI on the same port. No Node.js on user machines |
| Usage model | App lives in `~/.eco-harness`; user points it at any project folder via the UI (path-resolution refactor required) |
| Onboarding | In-app setup wizard (`/setup`): paste OpenRouter key / optional Eco token, live validation, writes config. "Add later in .env" escape hatch — missing keys never block install or launch |
| Docker | Prebuilt image on ghcr.io + thin customer `docker-compose.yml`; `install.sh --docker` generates compose + runs it |
| Distribution | PyPI (wheel) + ghcr.io (image) + S3 `manifest.json` (single version source of truth for binaries, index, wheel, image) |
| Updates | Manual `eco-harness update` (native) / `docker compose pull` (docker). No auto-update |

## Target layout (native)

```
~/.eco-harness/
  bin/eco-cli  bin/eco-wizard          # per-OS native binaries from S3
  data/marketplace_index.sqlite
  data/marketplace_cache/
  .env                                  # seeded by wizard or user
  venv/                                 # uv-managed app venv
```

Shims `eco-harness`, `eco-harness-update` put on PATH (`~/.local/bin` on POSIX; user PATH on Windows).

## Task list (ordered)

### 1. Package restructure (pyproject.toml)
- Namespacing: top-level `agent` and `backend` packages are too generic for PyPI — move them under `eco_harness/` (e.g. `eco_harness.agent`, `eco_harness.backend`); keep shims/back-compat imports for the dev repo.
- Add wheel data: `config/` defaults, `env.example`, frontend static export → `eco_harness/web_static/` (built in CI, included as package data).
- Console scripts: `eco-harness` (start/serve — exists), `eco-harness update`, `eco-harness doctor`.

### 2. Path resolution refactor (`agent/internal/tools/paths.py`, `binaries.py`)
- Introduce `ECO_HOME` (default `~/.eco-harness`) for data: binaries, index, cache, `.env`.
- Introduce `ECO_PROJECT_DIR` (set per session from the UI folder picker) for user projects, worktrees, `output/`.
- `repo_root()` keeps working in dev checkouts; installed mode resolves from `ECO_HOME`.
- `binaries.py`: add `~/.eco-harness/bin/<name>` (i.e. `$ECO_HOME/bin`) to the candidate list, ahead of `/opt`.

### 3. Frontend static export
- `next.config.mjs`: `output: 'export'`.
- API base: when `NEXT_PUBLIC_API_URL` is unset, use same-origin (`window.location.origin`) in `components/chat/*` (5 files currently hardcode fallback `http://localhost:8100`).
- FastAPI (`backend/server.py`): mount `eco_harness/web_static` at `/` after all API routes; SPA-style fallback to `index.html`.

### 4. First-run setup wizard
- Backend: `GET /api/setup/status`, `POST /api/setup/config` (validate OpenRouter key with a live minimal call; write `ECO_HOME/.env`).
- Frontend: `/setup` page (works within static export — client-side route); UI shows a "finish setup" banner until configured. Skippable.
- Config precedence: `ECO_HOME/.env` < process env (existing env vars always win).

### 5. Installer scripts (`scripts/install/`)
- `install.sh` (POSIX) and `install.ps1` (Windows), hosted at a stable URL (S3/GitHub raw) for `curl | sh` / `iwr | iex`, plus downloadable file.
- Steps: detect OS/arch → install `uv` if missing (`uv python install 3.11`) → create `~/.eco-harness/venv`, `uv pip install eco-harness` → read S3 `manifest.json`, download `bin/`, index tarball (verify sha256) → seed `.env` from `env.example` → install PATH shims → print "open http://localhost:8000".
- `--docker` flag: instead of venv steps, write a customer `docker-compose.yml` (pulls `ghcr.io/.../eco-harness:<tag>`, mounts `~/.eco-harness` + chosen project dir, port 8000) and `docker compose up -d`.

### 6. Customer Docker image
- New production `Dockerfile` (single image, API + static UI): slim python:3.11, installs wheel from the built artifact, no wine, no monorepo bind-mounts. Keep the current dev compose untouched.
- Build for `linux/amd64` **and** `linux/arm64` (Apple Silicon).

### 7. Release pipeline + manifest
- `manifest.json` on S3: versions + sha256 + URLs for eco-cli/eco-wizard per OS/arch, index tarball, latest wheel, latest image tag.
- CI: build frontend export → build wheel → publish PyPI; build/push multi-arch image to ghcr.io; publish manifest.
- eco-cli/eco-wizard binary publishing stays owned by the EcoCLI pipeline; the installer only consumes the manifest.

### 8. Update + uninstall
- `eco-harness update`: read manifest → `uv pip install -U eco-harness` → refresh changed binaries/index → report.
- Docker: `docker compose pull && docker compose up -d` (documented; script flag `--update`).
- Uninstall docs: delete `~/.eco-harness` (+ PATH shims).

## Risks

- **macOS Gatekeeper / Windows SmartScreen**: downloaded native binaries will be flagged unless signed/notarized by the eco-cli build pipeline. Installer should `xattr -d com.apple.quarantine` on macOS as a stopgap; proper signing is an EcoCLI-pipeline dependency.
- **Package rename churn**: moving `agent`/`backend` under `eco_harness` touches many imports; do it with a compatibility shim and full test run (`make test`).
- **Path refactor regressions**: worktree/git logic is monorepo-coupled today; `ECO_PROJECT_DIR` split needs careful tests around `git worktree add` outside a repo checkout.
- **Index staleness**: prebuilt index drifts from the marketplace; `eco-harness update` refresh plus documented local rebuild covers it.
- **S3 manifest is a new hard dependency** for install and update; serve with immutable+versioned objects and a "latest" pointer.

## Validation

- `eco-harness doctor` (new): venv/Python version, binaries present + executable, index loads via sqlite-vec, `.env` keys (warn, not block), static UI served, project dir writable.
- Fresh-VM matrix: Windows 11 (PowerShell flow), Ubuntu 22.04+, macOS 14+ (both arches); Docker flow on all three.
- E2E per flow: open UI → complete /setup → point at a sample project → run one chat/build task → verify `output/` artifacts and worktrees land under the project dir.
- Regression: `make test` + `docker compose up` dev stack still works after restructure.

## Out of scope

- Telemetry / crash reporting; auto-update daemon; OS-native installers (MSI/pkg); licensing server; S3 bucket/URL naming (owned by infra).
