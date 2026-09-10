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
  2. platform env vars — the standard spellings ``ECO_CLI`` / ``ECO_WIZARD``
     (and reserved ``ECO_IDL``)
     (the pre-standard ``ECO_CLI_PATH`` / ``ECO_WIZARD_PATH`` and the generic
     ``ECO_<NAME>_PATH`` are still read so old setups keep working; external
     backends use ``ECO_<BACKEND>_PATH``). A value may point at the binary
     file itself OR at the tool's directory (``<dir>/eco-cli`` /
     ``<dir>/eco-cli.exe`` are probed inside)
  3. standard toolchain location ``$ECO_TOOLCHAIN/eco-cli`` (i.e.
     ``$ECO_HOME/toolchain/eco-cli``, defaults ``~/ecoos/toolchain/...``) —
     the per-tool dir the platform standard reserves for the executable;
     probed as dir (binary inside) or file
  4. ``<app home>/bin/<name>`` — the preserved legacy binary folder (old
     installs, restricted layouts, Windows ``.cmd`` shims; in installed mode
     ``repo_root()`` IS the app home, so ``<repo>/bin/<name>`` below resolves
     this same dir). On Windows the ``.exe`` spelling is probed first
  5. ``<repo>/bin/<name>`` — the canonical, gitignored home for vendored
     binaries on a dev checkout
  6. system ``PATH`` (``<name>``, then ``<name>.exe``)

Deprecated locations — the ``/opt`` container bind-mounts and the
platform-suffixed sibling dirs — are intentionally NOT probed. Call them via
the env vars instead: the compose ``/opt`` mounts are consumed through
``ECO_CLI`` / ``ECO_WIZARD`` (see ``env.example``).

Returns ``None`` when nothing is found; callers are expected to raise or
return an actionable error message naming the tried locations.
:func:`resolve_binary_with_source` additionally reports which step matched —
used by the updater to tell user-configured binaries (``env``/``explicit``,
trusted enough for a ``--version`` probe) apart from mere filesystem finds
(toolchain/``bin``/``path``, never executed for probing).
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from pathlib import Path

from eco_harness.agent.internal.tools.paths import (
    repo_root,
    tool_install_dir,
)

logger = logging.getLogger(__name__)

# Standard env-var spellings (Eco platform standard) kept working alongside
# the legacy ``_PATH`` variants and the generic ECO_<NAME>_PATH derivation.
_KNOWN_ENV_VARS: dict[str, tuple[str, ...]] = {
    "eco-cli": ("ECO_CLI", "ECO_CLI_PATH"),
    "eco-wizard": ("ECO_WIZARD", "ECO_WIZARD_PATH"),
    # Reserved by the Eco platform for the future interface generator.
    "eco-idl": ("ECO_IDL", "ECO_IDL_PATH"),
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


def _exe_names(name: str) -> tuple[str, ...]:
    """Spellings of the executable inside a directory (Windows .exe first)."""
    if sys.platform.startswith("win"):
        return (f"{name}.exe", name)
    return (name, f"{name}.exe")


def _expand_candidate(path: Path, name: str) -> list[Path]:
    """A candidate may be the binary itself or a directory holding it.

    Directory values (the standard ``$ECO_TOOLCHAIN/eco-cli`` layout, or an
    env var pointing at a tool folder) are probed for ``<name>`` /
    ``<name>.exe`` inside; a plain file value is used as-is.
    """
    return [path, *(path / exe for exe in _exe_names(name))]


def resolve_binary_with_source(
    name: str,
    *,
    repo: Path | None = None,
    explicit: Path | str | None = None,
) -> tuple[Path, str] | None:
    """Resolve one external executable and report WHERE it came from.

    Returns ``(path, source)`` or ``None`` when absent everywhere. Source is
    one of:

      - ``"explicit"``  caller-provided path
      - ``"env"``       ``ECO_CLI`` / ``ECO_WIZARD`` (or legacy ``_PATH``)
      - ``"toolchain"`` the standard ``$ECO_TOOLCHAIN/<name>`` location
      - ``"bin"``       ``<repo>/bin/<name>`` (dev checkout home; IS the
                        app-home ``bin/`` fallback in installed mode)
      - ``path``        bare system ``PATH`` hit

    Callers that must distinguish "the user pointed at this" (env/explicit —
    trusted enough to probe) from "found somewhere" (toolchain/bin/PATH —
    never executed for probing) rely on the source.
    """
    root = Path(repo) if repo is not None else repo_root()

    specs: list[tuple[Path, str]] = []
    if explicit:
        specs.extend((p, "explicit") for p in _expand_candidate(Path(explicit), name))
    for value in _env_candidates(name):
        specs.extend((p, "env") for p in _expand_candidate(Path(value), name))

    # Standard platform location: $ECO_TOOLCHAIN/<name> (e.g.
    # ~/ecoos/toolchain/eco-cli) — per-tool dir with the binary inside.
    specs.extend((p, "toolchain") for p in _expand_candidate(tool_install_dir(name), name))

    # Preserved fallback folder: <app home>/bin/<name> (legacy installs and
    # restricted layouts). In installed mode repo_root() IS the app home, so
    # this is the same candidate as <repo>/bin/<name> below; on a dev
    # checkout <repo>/bin is the canonical gitignored vendored-binary home.
    # Both platform flavors may sit side by side (e.g. the Windows .exe for
    # host runs and the Linux ELF that the dev container consumes via its
    # monorepo mount), so Windows probes the .exe spelling FIRST: an
    # extensionless file there is usually the container's ELF, not a
    # host-executable binary.
    if sys.platform.startswith("win"):
        specs.append((root / "bin" / f"{name}.exe", "bin"))
    specs.append((root / "bin" / name, "bin"))

    for candidate, source in specs:
        try:
            if (
                sys.platform.startswith("win")
                and source in {"toolchain", "bin", "path"}
                and candidate.suffix.lower() != ".exe"
            ):
                continue
            if candidate.is_file():
                logger.debug("resolve_binary(%s) -> %s (%s)", name, candidate, source)
                return candidate, source
        except OSError:  # pragma: no cover - defensive
            continue

    for on_path in (shutil.which(name), shutil.which(f"{name}.exe")):
        if on_path:
            if sys.platform.startswith("win") and Path(on_path).suffix.lower() != ".exe":
                continue
            logger.debug("resolve_binary(%s) -> %s (PATH)", name, on_path)
            return Path(on_path), "path"
    return None


def resolve_binary(
    name: str,
    *,
    repo: Path | None = None,
    explicit: Path | str | None = None,
) -> Path | None:
    """Resolve one external executable, or ``None`` if absent everywhere."""
    found = resolve_binary_with_source(name, repo=repo, explicit=explicit)
    return found[0] if found is not None else None


def describe_search_order(name: str) -> str:
    """Human-readable search order for actionable 'not found' errors."""
    known = _KNOWN_ENV_VARS.get(name)
    env_hint = (
        " / ".join(known) if known else f"ECO_{_slug(name)}_PATH"
    )
    return (
        f"{name} lookup order: "
        f"{env_hint} env → "
        f"$ECO_TOOLCHAIN/{name} → "
        f"<repo>/bin/{name} (.exe first on Windows) → PATH"
    )
