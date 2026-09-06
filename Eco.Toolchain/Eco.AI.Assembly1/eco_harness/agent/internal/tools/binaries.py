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
     binaries on a host checkout (on Windows the ``.exe`` spelling is probed
     first, then the extensionless name). In installed mode ``repo_root()``
     IS ``$ECO_HOME``, so the native installer's ``$ECO_HOME/bin`` builds
     resolve through this same candidate
  4. system ``PATH`` (``<name>``, then ``<name>.exe``)

Deprecated locations — ``$ECO_HOME/bin`` as a standalone candidate, the
``/opt`` container bind-mounts, and the platform-suffixed sibling dirs —
are intentionally NOT probed. Call them via the env vars instead: the
compose ``/opt`` mounts are consumed through ``ECO_CLI_PATH`` /
``ECO_WIZARD_PATH`` (see ``env.example``).

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

from eco_harness.agent.internal.tools.paths import repo_root

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

    # Canonical gitignored home: <repo>/bin/<name>. In installed mode
    # repo_root() IS $ECO_HOME, so the builds the native installer deposits
    # in $ECO_HOME/bin/ resolve through the same candidate. Both platform
    # flavors may sit side by side (e.g. the Windows .exe for host runs and
    # the Linux ELF that the dev container consumes via its monorepo mount),
    # so Windows probes the .exe spelling FIRST: an extensionless file there
    # is usually the container's ELF, not a host-executable binary.
    if sys.platform.startswith("win"):
        candidates.append(root / "bin" / f"{name}.exe")
    candidates.append(root / "bin" / name)

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
        f"ECO_{_slug(name)}_PATH env (ECO_CLI_PATH / ECO_WIZARD_PATH) → "
        f"<repo>/bin/{name} (.exe first on Windows) → PATH"
    )
