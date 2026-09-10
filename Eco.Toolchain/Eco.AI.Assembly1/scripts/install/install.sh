#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# Eco.AI Harness — native installer (Linux / macOS)
#
# One-command install, no source checkout:
#   curl -fsSL https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/install.sh | sh
# or download and run:
#   sh install.sh [--docker] [--update] [--project-dir <dir>]
#
# GitHub-only install: the manifest, wheel, binaries, and RAG index all come
# from public release assets of peerf-eco/eco-harness-releases (no auth).
#
# Native flow: uv installs Python 3.11 if missing → venv at $ECO_HARNESS/venv →
# wheel from the release manifest → native eco-cli/eco-wizard binaries for the
# target OS (no wine anywhere) → prebuilt RAG index → PATH shims → done.
# Eco platform standard paths (see env.example): ECO_HOME (default ~/ecoos) is
# the ecosystem root, ECO_TOOLCHAIN=$ECO_HOME/toolchain, and the app home
# ECO_HARNESS=$ECO_TOOLCHAIN/eco-harness. eco-cli/eco-wizard are downloaded
# ONLY when not already present (ECO_CLI / ECO_WIZARD env vars or the standard
# locations); existing installs are kept (version-checked, replacement
# recommended) and fresh downloads land in $ECO_TOOLCHAIN/<tool>, falling back
# to the app-home bin/ folder when the toolchain dirs cannot be created.
# Docker flow (--docker): writes a customer docker-compose.yml and starts it.
#
# Missing API keys NEVER block the install: a starter .env with empty values
# is seeded, and the in-app /setup wizard (or manual .env edit) completes it.
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

# Eco platform standard (ECO_* may be preset in the environment):
ECO_HOME="${ECO_HOME:-$HOME/ecoos}"                      # ecosystem root
ECO_TOOLCHAIN="${ECO_TOOLCHAIN:-$ECO_HOME/toolchain}"    # tools root
ECO_HARNESS="${ECO_HARNESS:-$ECO_TOOLCHAIN/eco-harness}" # harness app home
ECO_PROJECTS_DIR="${ECO_PROJECTS_DIR:-$ECO_HOME/workspace}"
export ECO_HOME ECO_TOOLCHAIN ECO_HARNESS ECO_PROJECTS_DIR
MANIFEST_URL="${ECO_MANIFEST_URL:-https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/manifest.json}"
IMAGE_REPO="${ECO_HARNESS_IMAGE:-ghcr.io/peerf-eco/eco.ai}"
PROJECT_DIR_ARG=""
MODE="native"
UPDATE_ONLY=""

usage() { sed -n '2,24p' "$0"; exit 0; }
while [ $# -gt 0 ]; do
  case "$1" in
    --docker) MODE="docker"; shift ;;
    --update) UPDATE_ONLY=1; shift ;;
    --project-dir) PROJECT_DIR_ARG="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "unknown flag: $1" >&2; usage ;;
  esac
done

log() { printf '\033[1;32m[eco-harness]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[eco-harness] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# Single source for the .env seed template (deduped across docker/native).
seed_env() {
  cat > "$1" <<'ENVEOF'
# Eco.AI Harness configuration. The in-app /setup wizard writes here too.
OPENAI_API_KEY=
OPENROUTER_URL=https://openrouter.ai/api/v1
LLM_MODEL=tencent/hy3
EMBEDDINGS_MODEL=qwen/qwen3-embedding-8b
ECO_API_TOKEN=
ENVEOF
  # Seeded before keys exist, but keep it restrictive anyway: the wizard and
  # /rag/token endpoints store real secrets in this file later.
  chmod 600 "$1"
}

# ── OS / arch detection ──────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
  Linux) OS_KEY="linux" ;;
  Darwin) OS_KEY="darwin" ;;
  *) die "unsupported OS: $OS (Windows users: use install.ps1 or --docker)" ;;
esac
case "$ARCH" in
  x86_64|amd64) ARCH_KEY="x86_64" ;;
  aarch64|arm64) ARCH_KEY="arm64" ;;
  *) die "unsupported architecture: $ARCH" ;;
esac
log "detected platform: $OS_KEY/$ARCH_KEY"

command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1 ||
  die "need curl or wget to download the installer assets"

fetch() { # fetch <url> <output>
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$1" -o "$2"
  else
    wget -qO "$2" "$1"
  fi
}

sha256_file() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$1" | cut -d' ' -f1; }

# ── Existing tool detection (eco-cli / eco-wizard are never re-downloaded) ───
# A tool counts as present when its standard env var (ECO_CLI / ECO_WIZARD)
# resolves, or the standard toolchain dir ($ECO_TOOLCHAIN/<tool> — binary file
# or per-tool directory), or the app-home bin/ fallback holds the executable.
tool_present() { # tool_present <tool> <env_var> — prints path, rc 0/1
  local tool="$1" env_var="$2" candidate env_val="${!2:-}"
  if [ -n "$env_val" ] && [ -e "$env_val" ]; then
    printf '%s\n' "$env_val"; return 0
  fi
  for candidate in \
    "$ECO_TOOLCHAIN/$tool/$tool" "$ECO_TOOLCHAIN/$tool" "$ECO_HARNESS/bin/$tool"; do
    if [ -f "$candidate" ]; then printf '%s\n' "$candidate"; return 0; fi
  done
  command -v "$tool" >/dev/null 2>&1 && { command -v "$tool"; return 0; }
  return 1
}

# ── Docker mode: compose-only install ────────────────────────────────────────
if [ "$MODE" = "docker" ]; then
  command -v docker >/dev/null 2>&1 || die "docker not found — install Docker first (https://docs.docker.com/get-docker/)"
  mkdir -p "$ECO_HOME" "$ECO_TOOLCHAIN" "$ECO_HARNESS"
  PROJECT_DIR="${PROJECT_DIR_ARG:-$ECO_PROJECTS_DIR/default}"
  mkdir -p "$PROJECT_DIR"
  TMP_TAG_MANIFEST="$(mktemp)"
  IMAGE_TAG=""
  if fetch "$MANIFEST_URL" "$TMP_TAG_MANIFEST" 2>/dev/null; then
    IMAGE_TAG="$(sed -n 's/.*"tag"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$TMP_TAG_MANIFEST" | head -1 || true)"
    # Prefer the manifest's published repo over the compile-time default so
    # the installer always pulls what the release pipeline actually pushed.
    MANIFEST_REPO="$(sed -n 's/.*"repo"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$TMP_TAG_MANIFEST" | head -1 || true)"
    [ -n "$MANIFEST_REPO" ] && IMAGE_REPO="$MANIFEST_REPO"
  else
    log "WARNING: manifest unreachable at $MANIFEST_URL — falling back to $IMAGE_REPO:latest"
  fi
  rm -f "$TMP_TAG_MANIFEST"
  IMAGE_TAG="${IMAGE_TAG:-latest}"
  cat > "$ECO_HARNESS/docker-compose.yml" <<EOF
# Generated by install.sh — customer Docker install.
# Update:   docker compose -f $ECO_HARNESS/docker-compose.yml pull && docker compose -f $ECO_HARNESS/docker-compose.yml up -d
# Project:  change the ECO_PROJECT_DIR host path below to point at another folder.
services:
  eco-harness:
    image: $IMAGE_REPO:$IMAGE_TAG
    container_name: eco-harness
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      ECO_HOME: /data
      ECO_TOOLCHAIN: /data/toolchain
      ECO_HARNESS: /data/toolchain/eco-harness
      ECO_PROJECT_DIR: /project
      ECO_WORKTREE_ROOT: /data/worktrees
      GIT_CONFIG_COUNT: "1"
      GIT_CONFIG_KEY_0: safe.directory
      GIT_CONFIG_VALUE_0: /project
    env_file:
      - $ECO_HARNESS/.env
    volumes:
      - $ECO_HOME:/data
      - $ECO_TOOLCHAIN:/data/toolchain
      - $ECO_HARNESS:/data/toolchain/eco-harness
      - $PROJECT_DIR:/project
    restart: unless-stopped
EOF
  if [ ! -f "$ECO_HARNESS/.env" ]; then
    seed_env "$ECO_HARNESS/.env"
  fi
  log "pulling image $IMAGE_REPO:$IMAGE_TAG ..."
  docker compose -f "$ECO_HARNESS/docker-compose.yml" pull
  docker compose -f "$ECO_HARNESS/docker-compose.yml" up -d --wait
  # Populate the mounted /data (ECO_HOME) with the native binaries and the
  # prebuilt RAG index from the manifest — the image itself ships neither
  # (keeps the image small and lets `docker compose pull` update them).
  # eco-cli/eco-wizard already present on the host volume are kept.
  log "downloading binaries + prebuilt RAG index into $ECO_HARNESS ..."
  if ! docker compose -f "$ECO_HARNESS/docker-compose.yml" exec -T eco-harness \
      python -m eco_harness update; then
    log "WARNING: in-container download failed — run 'docker compose -f $ECO_HARNESS/docker-compose.yml exec eco-harness python -m eco_harness update' and check 'python -m eco_harness doctor'"
  fi
  log "Docker install complete."
  log "  UI + API:  http://localhost:8000  (setup wizard at /setup)"
  log "  Config:    $ECO_HARNESS/.env"
  log "  Update:    docker compose -f $ECO_HARNESS/docker-compose.yml pull && docker compose -f $ECO_HARNESS/docker-compose.yml up -d"
  exit 0
fi

if [ -n "$UPDATE_ONLY" ]; then
  # Legacy installs (pre platform-standard) keep working: fall back to the
  # historical ECO_HOME app home or ~/.eco-harness when the standard location
  # has no venv.
  if [ ! -x "$ECO_HARNESS/venv/bin/python" ] && [ -x "$ECO_HOME/venv/bin/python" ]; then
    log "no install at $ECO_HARNESS — updating the legacy install at $ECO_HOME"
    ECO_HARNESS="$ECO_HOME"
  fi
  if [ ! -x "$ECO_HARNESS/venv/bin/python" ] && [ -x "$HOME/.eco-harness/venv/bin/python" ]; then
    log "no install at $ECO_HARNESS — updating the legacy install at $HOME/.eco-harness"
    ECO_HARNESS="$HOME/.eco-harness"
  fi
  export ECO_HARNESS
  [ -x "$ECO_HARNESS/venv/bin/python" ] || die "no install at $ECO_HARNESS — run without --update first"
  exec "$ECO_HARNESS/venv/bin/python" -m eco_harness update
fi

# ── Native flow ──────────────────────────────────────────────────────────────
# 1. uv (provides Python 3.11 automatically)
if ! command -v uv >/dev/null 2>&1; then
  log "installing uv ..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  else
    wget -qO- https://astral.sh/uv/install.sh | sh
  fi
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
command -v uv >/dev/null 2>&1 || die "uv installation failed"

# 2. venv + wheel
if [ -d "$HOME/.eco-harness" ] && [ ! -d "$ECO_HARNESS" ]; then
  log "NOTE: a legacy install exists at $HOME/.eco-harness — this run creates a fresh"
  log "  install at $ECO_HARNESS. To update the legacy install instead:"
  log "  ECO_HARNESS=$HOME/.eco-harness sh install.sh --update   (or migrate its venv/.env/data over)"
fi
log "creating app venv at $ECO_HARNESS/venv (Python 3.11 if missing) ..."
uv python install 3.11 >/dev/null 2>&1 || true
uv venv --python 3.11 "$ECO_HARNESS/venv"
WHEEL_SPEC="eco-harness"
TMP_MANIFEST="$(mktemp)"
if fetch "$MANIFEST_URL" "$TMP_MANIFEST" 2>/dev/null; then
  WHEEL_URL="$(sed -n 's/.*"url"[[:space:]]*:[[:space:]]*"\([^"]*\.whl\)".*/\1/p' "$TMP_MANIFEST" | head -1)"
  [ -n "$WHEEL_URL" ] && WHEEL_SPEC="$WHEEL_URL"
fi
rm -f "$TMP_MANIFEST"
log "installing eco-harness wheel ($WHEEL_SPEC) ..."
uv pip install --python "$ECO_HARNESS/venv/bin/python" "$WHEEL_SPEC"

# 3. native binaries + prebuilt index from the manifest.
# eco-cli / eco-wizard are downloaded ONLY when not already present on this
# machine: ECO_CLI / ECO_WIZARD env vars and the standard locations
# ($ECO_TOOLCHAIN/<tool>, app-home bin/) are checked first. Copies installed
# by the user are referenced as-is (version-checked by the updater — outdated
# ones are reported with a replacement recommendation instead of overwritten);
# harness-managed copies (with the .<tool>.version marker) are refreshed in
# place by 'eco-harness update' when the manifest moves forward.
# Fresh downloads land in $ECO_TOOLCHAIN/<tool>, with the app-home bin/
# folder as fallback when the toolchain dirs cannot be created.
log "checking existing eco-cli / eco-wizard installs ..."
for pair in "eco-cli:ECO_CLI" "eco-wizard:ECO_WIZARD"; do
  tool="${pair%%:*}"; env_var="${pair##*:}"
  if found="$(tool_present "$tool" "$env_var")"; then
    log "  $tool: found at $found — no re-download (harness-managed copies are refreshed by updates)"
  else
    log "  $tool: not found — will be installed into $ECO_TOOLCHAIN/$tool"
  fi
done
log "downloading native binaries + prebuilt RAG index ..."
"$ECO_HARNESS/venv/bin/python" - "$MANIFEST_URL" <<'PYEOF'
import sys
from eco_harness import update

manifest_url = sys.argv[1]
report = update.run_update(manifest_url)
print(report.summary())
if report.errors:
    raise SystemExit(1)
PYEOF

# 4. seed .env (missing keys never block — /setup or manual edit completes it)
if [ ! -f "$ECO_HARNESS/.env" ]; then
  seed_env "$ECO_HARNESS/.env"
  log "seeded $ECO_HARNESS/.env (empty keys are fine — finish via /setup)"
fi
# Reference user-provided tool locations in .env so the server process uses
# the same binaries the installer found (avoids version conflicts).
for env_var in ECO_CLI ECO_WIZARD; do
  env_val="${!env_var:-}"
  [ -n "$env_val" ] || continue
  if grep -q "^${env_var}=" "$ECO_HARNESS/.env" 2>/dev/null; then
    sed -i.bak "s|^${env_var}=.*|${env_var}=${env_val}|" "$ECO_HARNESS/.env" && rm -f "$ECO_HARNESS/.env.bak"
  else
    printf '%s=%s\n' "$env_var" "$env_val" >> "$ECO_HARNESS/.env"
  fi
done
if [ -n "$PROJECT_DIR_ARG" ]; then
  # Native mode: pre-select the project directory (the UI folder picker can
  # always change it later). ECO_PROJECT_DIR wins over the defaults in
  # paths.project_dir().
  if grep -q "^ECO_PROJECT_DIR=" "$ECO_HARNESS/.env" 2>/dev/null; then
    sed -i.bak "s|^ECO_PROJECT_DIR=.*|ECO_PROJECT_DIR=$PROJECT_DIR_ARG|" "$ECO_HARNESS/.env" && rm -f "$ECO_HARNESS/.env.bak"
  else
    printf '\nECO_PROJECT_DIR=%s\n' "$PROJECT_DIR_ARG" >> "$ECO_HARNESS/.env"
  fi
  log "project dir: $PROJECT_DIR_ARG"
fi

# 5. PATH shims
SHIM_DIR="$HOME/.local/bin"
mkdir -p "$SHIM_DIR"
shell_quote() { printf '%q' "$1"; }
ECO_HOME_Q=$(shell_quote "$ECO_HOME")
ECO_TOOLCHAIN_Q=$(shell_quote "$ECO_TOOLCHAIN")
ECO_HARNESS_Q=$(shell_quote "$ECO_HARNESS")
ECO_PROJECTS_DIR_Q=$(shell_quote "$ECO_PROJECTS_DIR")
cat > "$SHIM_DIR/eco-harness" <<EOF
#!/bin/sh
export ECO_HOME=$ECO_HOME_Q
export ECO_TOOLCHAIN=$ECO_TOOLCHAIN_Q
export ECO_HARNESS=$ECO_HARNESS_Q
export ECO_PROJECTS_DIR=$ECO_PROJECTS_DIR_Q
exec "$ECO_HARNESS/venv/bin/python" -m eco_harness serve "\$@"
EOF
cat > "$SHIM_DIR/eco-harness-update" <<EOF
#!/bin/sh
export ECO_HOME=$ECO_HOME_Q
export ECO_TOOLCHAIN=$ECO_TOOLCHAIN_Q
export ECO_HARNESS=$ECO_HARNESS_Q
export ECO_PROJECTS_DIR=$ECO_PROJECTS_DIR_Q
exec "$ECO_HARNESS/venv/bin/python" -m eco_harness update "\$@"
EOF
chmod +x "$SHIM_DIR/eco-harness" "$SHIM_DIR/eco-harness-update"
case ":$PATH:" in
  *":$SHIM_DIR:"*) ;;
  *)
    log "NOTE: $SHIM_DIR is not on your PATH. Add it:"
    log "  echo 'export PATH=\"$SHIM_DIR:\$PATH\"' >> ~/.bashrc  (or your shell profile)"
    ;;
esac

log "install complete."
log "  start:   eco-harness   (or $ECO_HARNESS/venv/bin/python -m eco_harness serve)"
log "  open:    http://localhost:8000  (setup wizard at /setup — keys optional)"
log "  update:  eco-harness-update   |   uninstall: delete $ECO_HARNESS and the shims in $SHIM_DIR"
