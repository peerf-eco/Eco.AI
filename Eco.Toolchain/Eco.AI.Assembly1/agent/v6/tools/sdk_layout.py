"""SDK layout resolver — abstracts away three observed package layouts under source/.

EcoOS SDK packages on disk come in three flavours:

  versioned 2-level (the common case):
      <sdk_root>/Eco.Math.C89_DK_v.1.0.1.2/Eco.Math.C89/SharedFiles/...

  versioned 1-level (legacy / rare):
      <sdk_root>/Eco.Old_DK_v.1.0.0.0/SharedFiles/...

  flat (framework infra — Eco.MemoryManager1, etc.):
      <sdk_root>/Eco.MemoryManager1/SharedFiles/...

Tools that need to read .h files or copy the package must target the "inner
root" — the directory that DIRECTLY contains SharedFiles/. Without a single
resolver, each tool has to reimplement this branching and they drift apart.

CID-named directories like `0000000000000000000000004D656D31/` are build
artefacts (one .dll inside) and are deliberately excluded from listings — they
are never independently planned/pulled by the LLM.
"""
from __future__ import annotations
import re
from pathlib import Path

_DK_RE = re.compile(r"^(?P<base>.+)_DK_v\.(?P<ver>\d+\.\d+\.\d+\.\d+)$")
_CID_DIR_RE = re.compile(r"^[0-9A-F]{32}$")


def _has_payload(p: Path) -> bool:
    """True if `p` is a directory that looks like an EcoOS package inner root."""
    return p.is_dir() and ((p / "SharedFiles").is_dir() or (p / "BuildFiles").is_dir())


def resolve_component_root(sdk_root: Path, base_name: str,
                           version: str | None = None) -> Path | None:
    """Return the directory that directly contains SharedFiles/BuildFiles, or None.

    Search order:
      1. Versioned 2-level: `<sdk_root>/<base>_DK_v.<ver>/<base>/`
      2. Versioned 1-level: `<sdk_root>/<base>_DK_v.<ver>/` (if SharedFiles/BuildFiles is right there)
      3. Flat: `<sdk_root>/<base>/`

    If `version` is supplied, only that version is considered for (1)/(2);
    otherwise the highest-sorted version wins (lexicographic on the version string —
    sufficient for N.N.N.N format).
    """
    if not Path(sdk_root).is_dir():
        return None

    # Collect candidate versioned packages.
    candidates: list[tuple[str, Path]] = []
    for d in Path(sdk_root).iterdir():
        if not d.is_dir():
            continue
        m = _DK_RE.match(d.name)
        if not m or m.group("base") != base_name:
            continue
        if version is not None and m.group("ver") != version:
            continue
        candidates.append((m.group("ver"), d))

    for _ver, outer in sorted(candidates, key=lambda t: t[0], reverse=True):
        inner = outer / base_name
        if _has_payload(inner):
            return inner
        if _has_payload(outer):
            return outer
        # Outer exists but no recognisable payload — keep searching older versions.

    # Flat fallback.
    flat = Path(sdk_root) / base_name
    if _has_payload(flat):
        return flat

    return None


def list_component_roots(sdk_root: Path) -> list[str]:
    """Return base-names of all packages under sdk_root that look usable.

    Includes versioned packages (deduplicated by base name) AND flat framework
    packages. Excludes CID-named build-artifact directories.
    """
    if not Path(sdk_root).is_dir():
        return []
    names: set[str] = set()
    for d in Path(sdk_root).iterdir():
        if not d.is_dir():
            continue
        if _CID_DIR_RE.match(d.name):
            continue
        m = _DK_RE.match(d.name)
        if m:
            names.add(m.group("base"))
            continue
        # Flat: name without _DK_v. — but verify it actually has a payload to
        # avoid surfacing random subdirs (Lessons/, tmp/, ...).
        if _has_payload(d):
            names.add(d.name)
    return sorted(names)
