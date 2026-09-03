"""Host/container/installed aware location policy for the harness.

Why this exists
---------------
The harness runs in three environments:

  - dev checkout: a normal source tree where ``config/``, ``scripts/`` and
    the repo-root artifacts (``marketplace_index.sqlite`` etc.) live
  - container: repo copied to ``/app``, artifacts bind-mounted at
    ``/app/marketplace_cache`` and ``/app/marketplace_index.sqlite``
  - installed (pip wheel): no source checkout at all — the app lives in
    ``ECO_HOME`` (default ``~/.eco-harness``) and points at the user's
    project directory via ``ECO_PROJECT_DIR``

Older code hard-coded the container paths (``/app/...``) as defaults, which
silently broke host runs. This module is the single source of truth for
location resolution; every other module resolves paths through it.

Core anchors
------------

  ``eco_home()``      ``ECO_HOME`` env or ``~/.eco-harness`` — the installed
                      app home: ``bin/`` (native eco-cli / eco-wizard),
                      ``data/`` (marketplace index + cache), ``.env`` and the
                      uv-managed venv live here.
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
  3. ``<ECO_HOME>/data/<artifact>`` when it exists — the installed layout
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

_warned: set[str] = set()


def eco_home() -> Path:
    """Installed app home: ``ECO_HOME`` env or ``~/.eco-harness``.

    Holds the native binaries (``bin/``), the prebuilt RAG data
    (``data/marketplace_index.sqlite``, ``data/marketplace_cache/``), the
    ``.env`` seeded by the setup wizard / installer, and (in the native
    install) the uv-managed venv.
    """
    value = (os.environ.get("ECO_HOME") or "").strip()
    if value:
        return Path(value).expanduser().resolve()
    return (Path.home() / ".eco-harness").resolve()


def project_dir() -> Path:
    """User project directory: ``ECO_PROJECT_DIR`` env.

    Set per session from the UI folder picker in installed mode. User
    projects, harness worktrees and per-session ``output/`` artifacts live
    under this directory. Defaults to the dev checkout root while running
    from a source checkout, and to ``ECO_HOME`` otherwise.
    """
    value = (os.environ.get("ECO_PROJECT_DIR") or "").strip()
    if value:
        return Path(value).expanduser().resolve()
    if is_dev_checkout():
        return repo_root()
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
    repo root) → ``<repo>/output`` on a dev checkout → ``<ECO_HOME>/output``
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
    ``HARNESS_TRACES_DIR`` → ``<repo>/traces`` (dev) → ``<ECO_HOME>/traces``
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
) -> Path:
    """Shared resolution logic; see module docstring for the policy."""
    value = (os.environ.get(env_var) or "").strip()
    if value:
        return Path(value)

    root = (Path(repo) if repo is not None else repo_root()).resolve()
    candidates = [
        root / filename,
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

    This is the standard ACOM environment variable: a directory holding one
    ``<Component>_DK_v.<ver>/<Component>/`` tree per development kit, plus the
    static-link libraries under each DK's ``BuildFiles/``. The harness reuses
    it (instead of inventing its own variable) for:

      - sourcing base-type headers (``Eco.Core1/SharedFiles``) into the
        static system prompt (see ``agent/context/assembler.py``)
      - populating the RAG index (``scripts/build_marketplace_index.py
        --source framework``)
      - ``eco-cli pull -d`` downloads land here automatically

    Resolution: ``ECO_FRAMEWORK`` env → ``<repo>/eco_framework`` when present →
    ``<ECO_HOME>/data/eco_framework`` when present → deterministic
    ``<repo>/eco_framework`` fallback (warn once when missing).
    """
    return _resolve(
        env_var="ECO_FRAMEWORK",
        filename="eco_framework",
        exists=lambda p: p.is_dir(),
        repo=repo,
    )
