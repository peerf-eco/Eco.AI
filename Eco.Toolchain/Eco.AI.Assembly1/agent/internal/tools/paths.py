"""Host/container aware default locations for shared marketplace artifacts.

Why this exists
---------------
The harness runs in two environments:

  - container: repo copied to ``/app``, artifacts bind-mounted at
    ``/app/marketplace_cache`` and ``/app/marketplace_index.sqlite``
  - host: a normal checkout where ``/app`` does not exist

Older code hard-coded the container paths (``/app/...``) as defaults, which
silently broke host runs: ``search_marketplace`` raised FileNotFoundError even
with the index sitting in the repo root, and the grep/glob/read whitelist
dropped ``marketplace_cache`` entirely while the workspace header still told
the model to search it.

Resolution order (both environments work without any env var):

  1. explicit env var (``MARKETPLACE_CACHE_ROOT`` / ``MARKETPLACE_INDEX_PATH``)
  2. ``<repo_root>/<artifact>`` when it exists — on host this is the checkout;
     inside the container ``WORKDIR=/app`` IS the repo root, so this matches
     the bind-mount target automatically
  3. ``/app/<artifact>`` when it exists — covers mounts laid out differently
     from the image layout
  4. ``<repo_root>/<artifact>`` anyway — deterministic fallback so callers can
     produce a consistent "not found" error message pointing at the expected
     location

A one-line warning is logged (once per artifact kind per process) when the
resolved path does not exist, instead of failing silently.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# agent/internal/tools/paths.py → agent/internal/tools → agent/internal → agent → repo
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTAINER_ROOT = Path("/app")

_warned: set[str] = set()


def repo_root() -> Path:
    """Repository root on a host checkout; ``/app`` inside the container."""
    return _REPO_ROOT


def _resolve(
    *,
    env_var: str,
    filename: str,
    exists,
    repo: Path | None = None,
) -> Path:
    """Shared resolution logic; see module docstring for the policy."""
    root = (Path(repo) if repo is not None else _REPO_ROOT).resolve()
    value = (os.environ.get(env_var) or "").strip()
    if value:
        return Path(value)

    repo_candidate = root / filename
    if exists(repo_candidate):
        return repo_candidate

    container_candidate = _CONTAINER_ROOT / filename
    if exists(container_candidate):
        return container_candidate

    if env_var not in _warned:
        _warned.add(env_var)
        logger.warning(
            "%s not found at %s — tools that depend on it will report "
            "'not found'. Build it (scripts/build_marketplace_index.py / "
            "scripts/fetch_marketplace.py) or set %s.",
            filename, repo_candidate, env_var,
        )
    return repo_candidate


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
