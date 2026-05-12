"""Shared validators for V6 tools."""
from __future__ import annotations
import re
from pathlib import Path

_CID_RE     = re.compile(r"^[0-9A-F]{32}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


def is_valid_cid(cid: str) -> bool:
    return bool(_CID_RE.match(cid))


def is_valid_version(version: str) -> bool:
    return bool(_VERSION_RE.match(version))


def ensure_inside(parent: Path, child: Path) -> bool:
    """True if `child` resolves inside `parent`. Rejects `..`-escape."""
    try:
        parent_r = Path(parent).resolve(strict=False)
        child_r  = Path(child).resolve(strict=False)
        child_r.relative_to(parent_r)
        return True
    except ValueError:
        return False
