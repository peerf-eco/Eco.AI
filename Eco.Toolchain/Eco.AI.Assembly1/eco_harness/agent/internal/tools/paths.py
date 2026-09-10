"""Host/container/installed aware location policy for the harness.

Why this exists
---------------
The harness runs in three environments:

  - dev checkout: a normal source tree where ``config/``, ``scripts/`` and
    the repo-root artifacts (``marketplace_index.sqlite`` etc.) live
  - container: repo copied to ``/app``, artifacts bind-mounted at
    ``/app/marketplace_cache`` and ``/app/marketplace_index.sqlite``
  - installed (pip wheel): no source checkout at all — the app lives in
    the harness app home (``ECO_HARNESS``, default
    ``<ECO_HOME>/toolchain/eco-harness`` with ``ECO_HOME`` defaulting to
    ``~/ecoos``) and points at the user's project directory via
    ``ECO_PROJECT_DIR``

Older code hard-coded the container paths (``/app/...``) as defaults, which
silently broke host runs. This module is the single source of truth for
location resolution; every other module resolves paths through it.

Core anchors (Eco platform standard, see env.example "ECO PLATFORM PATHS")
----------------------------------------------------------------------------

  ``eco_os_root()``   ``ECO_HOME`` env or ``~/ecoos`` — the Eco OS ecosystem
                      root (toolchain/, framework/, workspace/).
  ``toolchain_root()``  ``ECO_TOOLCHAIN`` env or ``<ECO_HOME>/toolchain``.
  ``eco_home()``      ``ECO_HARNESS`` env or ``<toolchain>/eco-harness`` — the
                      installed app home: ``bin/`` (fallback binary dir +
                      Windows shims), ``data/`` (marketplace index + cache),
                      ``.env`` and the uv-managed venv live here. Legacy
                      ``ECO_HOME`` app homes (container ``/data``, older
                      ``~/.eco-harness`` installs) keep resolving — see the
                      docstring for the exact fallback order.
  ``projects_root()`` ``ECO_PROJECTS_DIR`` env or ``<ECO_HOME>/workspace`` —
                      where user projects live.
  ``project_dir()``   ``ECO_PROJECT_DIR`` env — the user project the UI's
                      folder picker selected. User projects, worktrees and
                      per-session ``output/`` artifacts belong under here in
                      installed mode.
  ``repo_root()``     dev checkout root; ``ECO_HOME`` in installed mode (so
                      legacy ``<repo>/<artifact>`` lookups keep working).
  ``package_root()``  the ``eco_harness`` package directory itself (wheel
                      data such as ``config/`` defaults and ``web_static/``
                      is shipped inside it).
  ``is_dev_checkout()``  True when running from a source checkout.

Artifact resolution order (``_resolve``):

  1. explicit env var (``MARKETPLACE_CACHE_ROOT`` /
     ``MARKETPLACE_INDEX_PATH`` / ``ECO_FRAMEWORK``)
  2. ``<repo_root>/<artifact>`` when it exists — dev checkout root, or the
     container ``WORKDIR=/app`` (which IS the repo root there)
  3. ``<app home>/data/<artifact>`` when it exists — the installed layout
  4. ``/app/<artifact>`` when it exists — covers mounts laid out differently
     from the image layout
  5. ``<repo_root>/<artifact>`` anyway — deterministic fallback so callers
     can produce a consistent "not found" error message pointing at the
     expected location

A one-line warning is logged (once per artifact kind per process) when the
resolved path does not exist, instead of failing silently.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# agent/internal/tools/paths.py moved to eco_harness/agent/internal/tools/:
# parents[3] = the eco_harness package dir, parents[4] = checkout root
# (= site-packages when installed from the wheel).
PACKAGE_ROOT = Path(__file__).resolve().parents[3]
_CHECKOUT_ROOT = PACKAGE_ROOT.parent
_CONTAINER_ROOT = Path("/app")

# Eco platform standard paths (Eco OS infrastructure layout):
#   <ECO_HOME>/toolchain/eco-cli     ← ECO_CLI      (Components Marketplace)
#   <ECO_HOME>/toolchain/eco-wizard  ← ECO_WIZARD   (project template generator)
#   <ECO_HOME>/toolchain/eco-idl     ← ECO_IDL      (interface generator, future)
#   <ECO_HOME>/toolchain/eco-harness ← ECO_HARNESS  (this app)
#   <ECO_HOME>/framework/devkit      ← ECO_FRAMEWORK
#   <ECO_HOME>/framework/runtime     ← ECO_FRAMEWORK_RT
#   <ECO_HOME>/workspace             ← ECO_PROJECTS_DIR
DEFAULT_ECO_OS_ROOT = "ecoos"

_warned: set[str] = set()


def _env_path(var: str) -> Path | None:
    """Read an env-var path, returning None when unset/blank."""
    value = (os.environ.get(var) or "").strip()
    if not value:
        return None
    return Path(value).expanduser()


def eco_os_root() -> Path:
    """Eco OS ecosystem root: ``ECO_HOME`` env or ``~/ecoos``.

    The standard infrastructure root holding ``toolchain/`` (all Eco tools
    plus third-party build tools), ``framework/`` (devkit + runtime) and
    ``workspace/`` (user projects). This is NOT the harness app home — see
    :func:`eco_home` for that.
    """
    value = _env_path("ECO_HOME")
    if value is not None:
        return value.resolve()
    return (Path.home() / DEFAULT_ECO_OS_ROOT).resolve()


def toolchain_root() -> Path:
    """Toolchain root: ``ECO_TOOLCHAIN`` env or ``<ECO_HOME>/toolchain``.

    Parent of the per-tool directories (``eco-cli/``, ``eco-wizard/``,
    ``eco-idl/``, ``eco-harness/``) that hold the native executables.
    """
    value = _env_path("ECO_TOOLCHAIN")
    if value is not None:
        return value.resolve()
    return eco_os_root() / "toolchain"


def tool_install_dir(name: str) -> Path:
    """Standard install dir for an Eco tool executable: ``<toolchain>/<name>``.

    ``ECO_CLI`` / ``ECO_WIZARD`` default here. The binary sits inside the dir
    (``<dir>/<name>[.exe]``) so the dir can be put on ``PATH`` wholesale, and
    zip bundles (extra .so/.md files) stay next to their executable.
    """
    return toolchain_root() / name


def tool_fallback_dir() -> Path:
    """Fallback binary dir: the app home ``bin/`` folder.

    The historical install location for native binaries (``$ECO_HOME/bin``
    before the platform standard; Windows ``.cmd`` shims still land here).
    Used when the toolchain dirs above the harness home cannot be created
    (read-only $HOME layouts, restricted containers) or by older installs.
    """
    return eco_home() / "bin"


def _looks_like_app_home(path: Path) -> bool:
    """Heuristic: does this dir look like an installed harness app home?"""
    return any(
        (path / marker).exists()
        for marker in ("venv", ".env", "bin", "data")
    )


def eco_home() -> Path:
    """Installed app home: ``ECO_HARNESS`` env or ``<toolchain>/eco-harness``.

    Holds the native-binary fallback dir (``bin/``), the prebuilt RAG data
    (``data/marketplace_index.sqlite``, ``data/marketplace_cache/``), the
    ``.env`` seeded by the setup wizard / installer, and (in the native
    install) the uv-managed venv.

    Fallback order (newest standard first, legacy kept working):

      1. ``ECO_HARNESS`` env — explicit app home (the customer image sets
         ``ECO_HARNESS=/data`` so the mount stays the app home while
         ``ECO_HOME`` means the ecosystem root).
      2. legacy ``ECO_HOME`` env when it LOOKS like an app home (contains
         ``venv``/``.env``/``bin``/``data``) — installs and containers predating
         the platform standard set ``ECO_HOME`` to the app home directly.
      3. ``<ECO_TOOLCHAIN>/eco-harness`` when it looks like an app home —
         an install under the new standard.
      4. legacy default ``~/.eco-harness`` when that exists (pre-standard
         native installs with no env vars set).
      5. fresh-install default: ``<ECO_TOOLCHAIN>/eco-harness``.
    """
    value = _env_path("ECO_HARNESS")
    if value is not None:
        return value.resolve()
    legacy = _env_path("ECO_HOME")
    if legacy is not None and _looks_like_app_home(legacy):
        return legacy.resolve()
    standard = toolchain_root() / "eco-harness"
    if _looks_like_app_home(standard):
        return standard.resolve()
    legacy_default = (Path.home() / ".eco-harness").resolve()
    if legacy_default.is_dir() and _looks_like_app_home(legacy_default):
        return legacy_default
    return standard


def projects_root() -> Path:
    """User projects root: ``ECO_PROJECTS_DIR`` env or ``<ECO_HOME>/workspace``.

    The standard parent directory for user projects (``project_alpha/``,
    ``project_beta/``, ...). Only a default — :func:`project_dir` decides the
    active project.
    """
    value = _env_path("ECO_PROJECTS_DIR")
    if value is not None:
        return value.resolve()
    return eco_os_root() / "workspace"


def project_dir() -> Path:
    """User project directory: ``ECO_PROJECT_DIR`` env.

    Set per session from the UI folder picker in installed mode. User
    projects, harness worktrees and per-session ``output/`` artifacts live
    under this directory. Defaults to the dev checkout root while running
    from a source checkout, else ``ECO_PROJECTS_DIR``/``<ECO_HOME>/workspace``
    when that exists, and the app home as the last resort.
    """
    value = _env_path("ECO_PROJECT_DIR")
    if value is not None:
        return value.resolve()
    if is_dev_checkout():
        return repo_root()
    workspace = projects_root()
    if workspace.is_dir():
        return workspace
    return eco_home()


def is_dev_checkout() -> bool:
    """True when running from a source checkout (vs. an installed wheel).

    Dev-container note: the dev compose bind-mounts the monorepo at /app and
    runs uvicorn with working_dir = /app/<...>/Eco.AI.Assembly1, so this
    package resolves from the MOUNTED checkout and _CHECKOUT_ROOT is that
    checkout root (pyproject.toml + config/ present) — NOT the image's /app.
    The detection therefore behaves identically in the dev container and on
    a host checkout."""
    return (_CHECKOUT_ROOT / "pyproject.toml").is_file() or (
        _CHECKOUT_ROOT / "config"
    ).is_dir()


def repo_root() -> Path:
    """Dev checkout root; ``ECO_HOME`` in installed mode.

    Legacy callers treat this as "the directory that holds the runtime
    artifacts" — in installed mode that is the app home.
    """
    if is_dev_checkout():
        return _CHECKOUT_ROOT
    return eco_home()


def package_root() -> Path:
    """The ``eco_harness`` package directory (wheel data lives inside it)."""
    return PACKAGE_ROOT


def config_dir(root: Path | None = None) -> Path:
    """The active ``config/`` directory.

    Dev checkout: ``<repo>/config``. Installed wheel: the copy shipped as
    package data inside ``eco_harness/config``. An explicit ``root`` always
    wins (callers that pass a project root expect ``<root>/config``).
    """
    if root is not None:
        return Path(root) / "config"
    if is_dev_checkout():
        return repo_root() / "config"
    return PACKAGE_ROOT / "config"


def output_root() -> Path:
    """Session/project output root, anchored to a stable absolute base:
    ``HARNESS_OUTPUT_ROOT`` (CWD-relative values resolve against the dev
    repo root) → ``<repo>/output`` on a dev checkout → app home ``output/``
    installed. Single source of truth for server, doctor, and tooling."""
    env_root = (os.environ.get("HARNESS_OUTPUT_ROOT") or "").strip()
    if env_root:
        base = Path(env_root).expanduser()
        if not base.is_absolute():
            base = repo_root() / base
        return base.resolve()
    if is_dev_checkout():
        return (repo_root() / "output").resolve()
    return (eco_home() / "output").resolve()


def traces_root() -> Path:
    """Per-session LLM trace root — same policy as :func:`output_root` with
    ``HARNESS_TRACES_DIR`` → ``<repo>/traces`` (dev) → app home ``traces/``
    (installed). Single source of truth for server and session export."""
    env_traces = (os.environ.get("HARNESS_TRACES_DIR") or "").strip()
    if env_traces:
        base = Path(env_traces).expanduser()
        if not base.is_absolute():
            base = repo_root() / base
        return base.resolve()
    if is_dev_checkout():
        return (repo_root() / "traces").resolve()
    return (eco_home() / "traces").resolve()


def _resolve(
    *,
    env_var: str,
    filename: str,
    exists,
    repo: Path | None = None,
    extra_candidates: tuple[Path, ...] = (),
) -> Path:
    """Shared resolution logic; see module docstring for the policy."""
    value = (os.environ.get(env_var) or "").strip()
    if value:
        return Path(value)

    root = (Path(repo) if repo is not None else repo_root()).resolve()
    candidates = [
        root / filename,
        *extra_candidates,
        eco_home() / "data" / filename,
        _CONTAINER_ROOT / filename,
    ]
    for candidate in candidates:
        if exists(candidate):
            return candidate

    if env_var not in _warned:
        _warned.add(env_var)
        logger.warning(
            "%s not found (tried %s) — tools that depend on it will report "
            "'not found'. Run `eco-harness update`, build it "
            "(scripts/build_marketplace_index.py / scripts/fetch_marketplace.py) "
            "or set %s.",
            filename,
            ", ".join(str(c) for c in candidates),
            env_var,
        )
    return candidates[0]


def marketplace_cache_root(*, repo: Path | None = None) -> Path:
    """Directory of the pre-pulled component DEVKIT snapshot.

    Env override: ``MARKETPLACE_CACHE_ROOT``.
    """
    return _resolve(
        env_var="MARKETPLACE_CACHE_ROOT",
        filename="marketplace_cache",
        exists=lambda p: p.is_dir(),
        repo=repo,
    )


def marketplace_index_path(*, repo: Path | None = None) -> Path:
    """Location of the sqlite-vec RAG index.

    Env override: ``MARKETPLACE_INDEX_PATH``.
    """
    return _resolve(
        env_var="MARKETPLACE_INDEX_PATH",
        filename="marketplace_index.sqlite",
        exists=lambda p: p.is_file(),
        repo=repo,
    )


def framework_root(*, repo: Path | None = None) -> Path:
    """Root of the ACOM components development kits (``ECO_FRAMEWORK``).

    This is the standard Eco platform environment variable: a directory
    holding one ``<Component>_DK_v.<ver>/<Component>/`` tree per development
    kit, plus the static-link libraries under each DK's ``BuildFiles/``. The
    harness reuses it (instead of inventing its own variable) for:

      - sourcing base-type headers (``Eco.Core1/SharedFiles``) into the
        static system prompt (see ``agent/context/assembler.py``)
      - populating the RAG index (``scripts/build_marketplace_index.py
        --source framework``)
      - ``eco-cli pull -d`` downloads land here automatically

    Resolution: ``ECO_FRAMEWORK`` env → ``<repo>/eco_framework`` when present →
    ``<ECO_HOME>/framework/devkit`` (platform standard) when present →
    ``<ECO_HOME>/data/eco_framework`` when present → deterministic
    ``<repo>/eco_framework`` fallback (warn once when missing).
    """
    return _resolve(
        env_var="ECO_FRAMEWORK",
        filename="eco_framework",
        exists=lambda p: p.is_dir(),
        repo=repo,
        extra_candidates=(eco_os_root() / "framework" / "devkit",),
    )


def framework_runtime_root(*, repo: Path | None = None) -> Path:
    """Root of the ACOM components runtime (``ECO_FRAMEWORK_RT``).

    Standard platform variable for the component runtime environment
    (``<ECO_HOME>/framework/runtime``). Reserved for runtime-side consumers
    (ECO_FRAMEWORK is the devkit counterpart); resolution mirrors
    :func:`framework_root` with the runtime default.
    """
    return _resolve(
        env_var="ECO_FRAMEWORK_RT",
        filename="eco_framework_runtime",
        exists=lambda p: p.is_dir(),
        repo=repo,
        extra_candidates=(eco_os_root() / "framework" / "runtime",),
    )
