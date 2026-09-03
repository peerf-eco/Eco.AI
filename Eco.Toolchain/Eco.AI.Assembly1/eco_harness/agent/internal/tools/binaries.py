"""Single binary-resolution policy for every external tool executable.

Why this exists
---------------
Before PRD_2 Phase 2 there were four conflicting conventions:

  - ``backend/server.py::resolve_executable_path`` (env → /opt mounts →
    Windows-via-wine → PATH → harness.yaml)
  - ``agent/internal/tools/eco_cli.py::_resolve_cli_path`` (explicit arg →
    env → ``<repo>/eco-cli-{linux,windows}/`` → PATH)
  - ``agent/internal/tools/eco_wizard.py::_resolve_wizard`` (env → PATH)
  - ``eco_harness/adapters/factory.py`` (raw ``ECO_<NAME>_PATH`` env → bare name)

Each had different fallbacks, so a binary found by one consumer was invisible
to another. This module is now the single source of truth.

Resolution order
----------------

  1. ``explicit`` argument (caller-provided path, e.g. a tool arg or
     ``harness.yaml`` setting)
  2. ``ECO_<NAME>_PATH`` environment variable (the historical spellings
     ``ECO_CLI_PATH`` / ``ECO_WIZARD_PATH`` are checked for the matching
     tools; external backends use ``ECO_<BACKEND>_PATH``)
  3. ``<repo>/bin/<name>`` — the canonical, gitignored home for vendored
     binaries on a host checkout
  4. ``$ECO_HOME/bin/<name>`` (default ``~/.eco-harness/bin``) — where the
     native installer deposits the downloaded builds
  5. ``/opt/<name>`` — container bind-mount location (docker-compose.yml)
  6. platform-suffixed legacy siblings next to the repo root:
     ``<repo>/<name>-linux/<name>`` then ``<repo>/<name>-windows/<name>.exe``
     (kept for backwards compatibility with the old layout)
  7. system ``PATH`` (``<name>``, then ``<name>.exe``)

Returns ``None`` when nothing is found; callers are expected to raise or
return an actionable error message naming the tried locations.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from pathlib import Path

from eco_harness.agent.internal.tools.paths import eco_home, repo_root

logger = logging.getLogger(__name__)

# Historical env-var spellings kept working alongside the generic
# ECO_<NAME>_PATH derivation.
_KNOWN_ENV_VARS: dict[str, tuple[str, ...]] = {
    "eco-cli": ("ECO_CLI_PATH",),
    "eco-wizard": ("ECO_WIZARD_PATH",),
}


def _slug(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")


def _env_candidates(name: str) -> list[str]:
    vars_to_check = [*_KNOWN_ENV_VARS.get(name, ()), f"ECO_{_slug(name)}_PATH"]
    values: list[str] = []
    for var in vars_to_check:
        value = (os.environ.get(var) or "").strip()
        if value:
            values.append(value)
    return values


def resolve_binary(
    name: str,
    *,
    repo: Path | None = None,
    explicit: Path | str | None = None,
) -> Path | None:
    """Resolve one external executable, or ``None`` if absent everywhere."""
    root = Path(repo) if repo is not None else repo_root()

    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(Path(value) for value in _env_candidates(name))

    # Canonical gitignored home: <repo>/bin/<name>.
    candidates.append(root / "bin" / name)

    # Installed-app home: $ECO_HOME/bin/<name> (~/.eco-harness/bin) — where
    # the native installer deposits the downloaded eco-cli / eco-wizard
    # builds (named <name>.exe on Windows, matching update._refresh_binaries).
    # Checked ahead of /opt so an installed home wins over a stale container
    # mount.
    installed_suffix = ".exe" if sys.platform.startswith("win") else ""
    candidates.append(eco_home() / "bin" / f"{name}{installed_suffix}")

    # Container bind-mount locations (docker-compose.yml mounts the ELF
    # directly at /opt/<name>).
    candidates.append(Path("/opt") / name)

    # Legacy platform-suffixed siblings (old vendored layout).
    candidates.append(root / f"{name}-linux" / name)
    candidates.append(root / f"{name}-windows" / f"{name}.exe")

    for candidate in candidates:
        try:
            if candidate.is_file():
                logger.debug("resolve_binary(%s) -> %s", name, candidate)
                return candidate
        except OSError:  # pragma: no cover - defensive
            continue

    for on_path in (shutil.which(name), shutil.which(f"{name}.exe")):
        if on_path:
            logger.debug("resolve_binary(%s) -> %s (PATH)", name, on_path)
            return Path(on_path)
    return None


def describe_search_order(name: str) -> str:
    """Human-readable search order for actionable 'not found' errors."""
    return (
        f"{name} lookup order: "
        f"ECO_{_slug(name)}_PATH env → <repo>/bin/{name} → "
        f"$ECO_HOME/bin/{name} (~/.eco-harness/bin) → /opt/{name} → "
        f"<repo>/{name}-linux/{name} → <repo>/{name}-windows/{name}.exe → PATH"
    )
