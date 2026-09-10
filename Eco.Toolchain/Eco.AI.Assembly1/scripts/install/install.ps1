# ═══════════════════════════════════════════════════════════════════════════
# Eco.AI Harness — native installer (Windows PowerShell)
#
# One-command install, no source checkout:
#   irm https://github.com/peerf-eco/eco-coder-releases/releases/latest/download/install.ps1 | iex
# or download and run:
#   powershell -ExecutionPolicy Bypass -File install.ps1 [-Docker]
#
# GitHub-only install: the manifest, wheel, binaries, and RAG index all come
# from public release assets of peerf-eco/eco-coder-releases (no auth).
#
# Native flow: uv installs Python 3.11 if missing → venv at $ECO_HARNESS\venv →
# wheel from the release manifest → native eco-cli.exe / eco-wizard.exe
# (no wine anywhere) → prebuilt RAG index → user-PATH shims → done.
# Eco platform standard paths (see env.example): ECO_HOME (default
# %USERPROFILE%\ecoos) is the ecosystem root, ECO_TOOLCHAIN=$ECO_HOME\toolchain,
# the app home ECO_HARNESS=$ECO_TOOLCHAIN\eco-harness. eco-cli / eco-wizard are
# downloaded ONLY when not already present (ECO_CLI / ECO_WIZARD env vars or
# the standard locations); existing copies are kept (version-checked,
# replacement recommended) and fresh downloads land in $ECO_TOOLCHAIN\<tool>,
# falling back to the app-home bin\ folder when that cannot be created.
# Missing API keys NEVER block the install: the in-app /setup wizard or a
# manual .env edit completes configuration.
# ═══════════════════════════════════════════════════════════════════════════
[CmdletBinding()]
param(
    [switch]$Docker,
    [switch]$Update,
    [string]$ProjectDir
)

$ErrorActionPreference = "Stop"

# Single source for the .env seed template (deduped across docker/native).
$EnvSeed = @"
# Eco.AI Harness configuration. The in-app /setup wizard writes here too.
OPENAI_API_KEY=
OPENROUTER_URL=https://openrouter.ai/api/v1
LLM_MODEL=tencent/hy3
EMBEDDINGS_MODEL=qwen/qwen3-embedding-8b
ECO_API_TOKEN=
"@

function Write-EnvSeed {
    param([string]$Path)
    $EnvSeed | Set-Content -Path $Path -Encoding UTF8
    # Seeded before keys exist, but keep it restrictive anyway: the wizard
    # and /rag/token endpoints store real secrets in this file later.
    icacls $Path /inheritance:r /grant:r "$($env:USERNAME):F" | Out-Null
}

# Eco platform standard (ECO_* may be preset in the environment):
$ECO_HOME          = if ($env:ECO_HOME) { $env:ECO_HOME } else { Join-Path $env:USERPROFILE "ecoos" }
$ECO_TOOLCHAIN     = if ($env:ECO_TOOLCHAIN) { $env:ECO_TOOLCHAIN } else { Join-Path $ECO_HOME "toolchain" }
$ECO_HARNESS       = if ($env:ECO_HARNESS) { $env:ECO_HARNESS } else { Join-Path $ECO_TOOLCHAIN "eco-harness" }
$ECO_PROJECTS_DIR  = if ($env:ECO_PROJECTS_DIR) { $env:ECO_PROJECTS_DIR } else { Join-Path $ECO_HOME "workspace" }
$MANIFEST_URL      = if ($env:ECO_MANIFEST_URL) { $env:ECO_MANIFEST_URL } else { "https://github.com/peerf-eco/eco-coder-releases/releases/latest/download/manifest.json" }
$IMAGE_REPO        = if ($env:ECO_HARNESS_IMAGE) { $env:ECO_HARNESS_IMAGE } else { "ghcr.io/peerf-eco/eco.ai" }
$env:ECO_HOME = $ECO_HOME
$env:ECO_TOOLCHAIN = $ECO_TOOLCHAIN
$env:ECO_HARNESS = $ECO_HARNESS
$env:ECO_PROJECTS_DIR = $ECO_PROJECTS_DIR

function Write-Log { param([string]$Message) Write-Host "[eco-harness] $Message" -ForegroundColor Green }
function Die { param([string]$Message) Write-Host "[eco-harness] ERROR: $Message" -ForegroundColor Red; exit 1 }

# Existing tool detection: eco-cli / eco-wizard are never re-downloaded over
# an install the user already has (ECO_CLI / ECO_WIZARD env vars, the standard
# toolchain dir, or the app-home bin\ fallback).
function Find-Tool {
    param([string]$Tool, [string]$EnvVar)
    $envVal = [Environment]::GetEnvironmentVariable($EnvVar)
    if ($envVal) {
        if (Test-Path -LiteralPath $envVal -PathType Leaf) { return $envVal }
        if (Test-Path -LiteralPath $envVal -PathType Container) {
            foreach ($envCandidate in @(
                (Join-Path $envVal "$Tool.exe"),
                (Join-Path $envVal $Tool)
            )) {
                if (Test-Path -LiteralPath $envCandidate -PathType Leaf) {
                    return $envCandidate
                }
            }
        }
    }
    foreach ($candidate in @(
        (Join-Path $ECO_TOOLCHAIN "$Tool\$Tool.exe"),
        (Join-Path $ECO_HARNESS "bin\$Tool.exe")
    )) {
        if (Test-Path $candidate -PathType Leaf) { return $candidate }
    }
    $onPath = Get-Command $Tool -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    return $null
}

# ── Docker mode ──────────────────────────────────────────────────────────────
if ($Docker) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Die "docker not found - install Docker Desktop first (https://docs.docker.com/get-docker/)"
    }
    New-Item -ItemType Directory -Force -Path $ECO_HOME | Out-Null
    New-Item -ItemType Directory -Force -Path $ECO_TOOLCHAIN | Out-Null
    New-Item -ItemType Directory -Force -Path $ECO_HARNESS | Out-Null
    $projectDir = if ($ProjectDir) { $ProjectDir } else { Join-Path $ECO_PROJECTS_DIR "default" }
    New-Item -ItemType Directory -Force -Path $projectDir | Out-Null

    $imageTag = "latest"
    try {
        $manifest = Invoke-RestMethod -Uri $MANIFEST_URL -TimeoutSec 30
        if ($manifest.image.tag) { $imageTag = $manifest.image.tag }
        if ($manifest.image.repo) { $script:IMAGE_REPO = $manifest.image.repo }
    } catch { Write-Log "manifest unavailable, using image tag 'latest'" }

    $envHost = ($ECO_HARNESS -replace '\\', '/')
    $homeHost = ($ECO_HOME -replace '\\', '/')
    $toolchainHost = ($ECO_TOOLCHAIN -replace '\\', '/')
    $projHost = ($projectDir -replace '\\', '/')
    @"
# Generated by install.ps1 - customer Docker install.
# Update:  docker compose -f `"$envHost/docker-compose.yml`" pull && docker compose -f `"$envHost/docker-compose.yml`" up -d
services:
  eco-harness:
    image: $IMAGE_REPO`:$imageTag
    container_name: eco-harness
    ports:
      - `"127.0.0.1:8000:8000`"
    environment:
      ECO_HOME: /data
      ECO_TOOLCHAIN: /data/toolchain
      ECO_HARNESS: /data/toolchain/eco-harness
      ECO_PROJECT_DIR: /project
      ECO_WORKTREE_ROOT: /data/worktrees
      GIT_CONFIG_COUNT: `"1`"
      GIT_CONFIG_KEY_0: safe.directory
      GIT_CONFIG_VALUE_0: /project
    env_file:
      - $envHost/.env
    volumes:
      - ${homeHost}:/data
      - ${toolchainHost}:/data/toolchain
      - ${envHost}:/data/toolchain/eco-harness
      - ${projHost}:/project
    restart: unless-stopped
"@ | Set-Content -Path (Join-Path $ECO_HARNESS "docker-compose.yml") -Encoding UTF8

    $envFile = Join-Path $ECO_HARNESS ".env"
    if (-not (Test-Path $envFile)) {
        Write-EnvSeed $envFile
    }

    Write-Log "pulling image $IMAGE_REPO`:$imageTag ..."
    $composeFile = Join-Path $ECO_HARNESS "docker-compose.yml"
    docker compose -f $composeFile pull
    docker compose -f $composeFile up -d --wait
    # Populate the mounted /data (ECO_HOME) with the native binaries and
    # the prebuilt RAG index from the manifest - the image itself ships
    # neither. Binaries already present on the host volume are kept.
    Write-Log "downloading binaries + prebuilt RAG index into $ECO_HARNESS ..."
    docker compose -f $composeFile exec -T eco-harness python -m eco_harness update
    if ($LASTEXITCODE -ne 0) {
        Write-Log "WARNING: in-container download failed - run 'docker compose -f $composeFile exec eco-harness python -m eco_harness update' and check 'python -m eco_harness doctor'"
    }
    Write-Log "Docker install complete. Open http://localhost:8000 (setup wizard at /setup)"
    exit 0
}

if ($Update) {
    # Legacy installs (pre platform-standard) keep working: fall back to the
    # historical %USERPROFILE%\.eco-harness app home when the standard
    # location has no venv.
    $legacyHomes = @(
        $ECO_HOME,
        (Join-Path $env:USERPROFILE ".eco-harness")
    )
    if (-not (Test-Path (Join-Path $ECO_HARNESS "venv\Scripts\python.exe"))) {
        foreach ($legacyHome in $legacyHomes) {
            $legacyPython = Join-Path $legacyHome "venv\Scripts\python.exe"
            if (Test-Path $legacyPython) {
                Write-Log "no install at $ECO_HARNESS - updating the legacy install at $legacyHome"
                $ECO_HARNESS = $legacyHome
                break
            }
        }
    }
    $env:ECO_HARNESS = $ECO_HARNESS
    $python = Join-Path $ECO_HARNESS "venv\Scripts\python.exe"
    if (-not (Test-Path $python)) { Die "no install at $ECO_HARNESS - run without -Update first" }
    & $python -m eco_harness update @args
    exit $LASTEXITCODE
}

# ── Native flow ──────────────────────────────────────────────────────────────
# 1. uv (provides Python 3.11 automatically)
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Log "installing uv ..."
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Die "uv installation failed" }

# 2. venv + wheel
Write-Log "creating app venv at $ECO_HARNESS\venv (Python 3.11 if missing) ..."
uv python install 3.11 2>$null | Out-Null
uv venv --python 3.11 (Join-Path $ECO_HARNESS "venv")

$wheelSpec = "eco-harness"
try {
    $manifest = Invoke-RestMethod -Uri $MANIFEST_URL -TimeoutSec 30
    if ($manifest.wheel.url) { $wheelSpec = $manifest.wheel.url }
} catch { Write-Log "manifest unavailable - installing eco-harness from PyPI" }
Write-Log "installing eco-harness wheel ..."
uv pip install --python (Join-Path $ECO_HARNESS "venv\Scripts\python.exe") $wheelSpec

# 3. native binaries + prebuilt index from the manifest.
# eco-cli / eco-wizard are downloaded ONLY when not already present on this
# machine (ECO_CLI / ECO_WIZARD env vars or the standard locations).
# User-installed copies are referenced as-is - the updater version-checks
# them and reports a replacement recommendation instead of overwriting;
# harness-managed copies (with the .<tool>.version marker) are refreshed in
# place by updates. Fresh downloads land in
# $ECO_TOOLCHAIN\<tool>, falling back to the app-home bin\ folder.
Write-Log "checking existing eco-cli / eco-wizard installs ..."
foreach ($tool in @(@("eco-cli", "ECO_CLI"), @("eco-wizard", "ECO_WIZARD"))) {
    $found = Find-Tool -Tool $tool[0] -EnvVar $tool[1]
    if ($found) {
        Write-Log "  $($tool[0]): found at $found - no re-download (harness-managed copies are refreshed by updates)"
    } else {
        Write-Log "  $($tool[0]): not found - will be installed into $ECO_TOOLCHAIN\$($tool[0])"
    }
}
Write-Log "downloading native binaries + prebuilt RAG index ..."
& (Join-Path $ECO_HARNESS "venv\Scripts\python.exe") -c "from eco_harness import update; import sys; r = update.run_update('$MANIFEST_URL'); print(r.summary()); sys.exit(1 if r.errors else 0)"
if ($LASTEXITCODE -ne 0) { Write-Log "WARNING: some binaries/index downloads failed - 'eco-harness doctor' shows details" }

# 4. seed .env
$envFile = Join-Path $ECO_HARNESS ".env"
if (-not (Test-Path $envFile)) {
    Write-EnvSeed $envFile
    Write-Log "seeded $envFile (empty keys are fine - finish via /setup)"
}
# Reference user-provided tool locations in .env so the server process uses
# the same binaries the installer found (avoids version conflicts).
foreach ($envVar in @("ECO_CLI", "ECO_WIZARD")) {
    $envVal = [Environment]::GetEnvironmentVariable($envVar)
    if (-not $envVal) { continue }
    $content = Get-Content $envFile -Raw
    if ($content -match "(?m)^$envVar=") {
        $content = $content -replace "(?m)^$envVar=.*", "$envVar=$envVal"
        Set-Content -Path $envFile -Value $content -Encoding UTF8
    } else {
        Add-Content -Path $envFile -Value "$envVar=$envVal" -Encoding UTF8
    }
}
if ($ProjectDir) {
    # Native mode: pre-select the project directory (the UI folder picker can
    # always change it later). ECO_PROJECT_DIR wins over the defaults in
    # paths.project_dir().
    $content = Get-Content $envFile -Raw
    if ($content -match "(?m)^ECO_PROJECT_DIR=") {
        $content = $content -replace "(?m)^ECO_PROJECT_DIR=.*", "ECO_PROJECT_DIR=$ProjectDir"
        Set-Content -Path $envFile -Value $content -Encoding UTF8
    } else {
        Add-Content -Path $envFile -Value "ECO_PROJECT_DIR=$ProjectDir" -Encoding UTF8
    }
    Write-Log "project dir: $ProjectDir"
}

# 5. user-PATH shims (Windows has no ~/.local/bin convention)
$shimDir = Join-Path $ECO_HARNESS "bin"
New-Item -ItemType Directory -Force -Path $shimDir | Out-Null
$pythonExe = Join-Path $ECO_HARNESS "venv\Scripts\python.exe"
$cmdEcoHome = $ECO_HOME -replace '%', '%%'
$cmdEcoToolchain = $ECO_TOOLCHAIN -replace '%', '%%'
$cmdEcoHarness = $ECO_HARNESS -replace '%', '%%'
$cmdEcoProjectsDir = $ECO_PROJECTS_DIR -replace '%', '%%'
@"
@echo off
set "ECO_HOME=$cmdEcoHome"
set "ECO_TOOLCHAIN=$cmdEcoToolchain"
set "ECO_HARNESS=$cmdEcoHarness"
set "ECO_PROJECTS_DIR=$cmdEcoProjectsDir"
`"$pythonExe`" -m eco_harness serve %*
"@ | Set-Content -Path (Join-Path $shimDir "eco-harness.cmd") -Encoding ASCII

@"
@echo off
set "ECO_HOME=$cmdEcoHome"
set "ECO_TOOLCHAIN=$cmdEcoToolchain"
set "ECO_HARNESS=$cmdEcoHarness"
set "ECO_PROJECTS_DIR=$cmdEcoProjectsDir"
`"$pythonExe`" -m eco_harness update %*
"@ | Set-Content -Path (Join-Path $shimDir "eco-harness-update.cmd") -Encoding ASCII

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ";") -notcontains $shimDir) {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$shimDir", "User")
    Write-Log "added $shimDir to your user PATH (new terminals only)"
}

Write-Log "install complete."
Write-Log "  start:   eco-harness   (or $pythonExe -m eco_harness serve)"
Write-Log "  open:    http://localhost:8000  (setup wizard at /setup - keys optional)"
Write-Log "  update:  eco-harness-update   |   uninstall: delete $ECO_HARNESS and the user-PATH entry"
