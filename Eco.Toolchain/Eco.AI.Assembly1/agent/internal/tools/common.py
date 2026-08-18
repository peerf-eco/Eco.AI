"""Shared validators for internal tools."""
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


def resolve_inside(project_dir: Path, args_path: str) -> Path:
    """Resolve `args_path` to a Path that should live inside `project_dir`.

    Acceptance rules, in order:
      1. Absolute path — returned as-is (caller's ensure_inside still validates).
      2. Path that already resolves (from CWD) into project_dir — returned
         as-is for backwards compatibility (older prompts produced strings like
         "output/v7-XXX/Eco.Math.C89" that work from the uvicorn CWD).
      3. Otherwise — anchored against project_dir. This is what current prompts
         teach: pass paths relative to project_dir (e.g. "Eco.Math.C89").
    """
    p = Path(args_path)
    if p.is_absolute():
        return p
    project_abs = project_dir.resolve(strict=False)
    cwd_candidate = (Path.cwd() / p).resolve(strict=False)
    try:
        cwd_candidate.relative_to(project_abs)
        return Path.cwd() / p
    except ValueError:
        return project_dir / p


def ensure_inside_any(roots: list[Path], child: Path) -> bool:
    """True if `child` resolves inside ANY of `roots`."""
    return any(ensure_inside(r, child) for r in roots)


def decode_text(data: bytes) -> str:
    """Decode file bytes to text lossy-but-safe for mixed encodings.

    Cache headers can be UTF-8 (sometimes with a BOM) or legacy Cyrillic
    CP1251. Strip a leading UTF-8 BOM so the model never sees a stray U+FEFF,
    then try UTF-8, CP1251 (Cyrillic Windows), and finally latin-1 — this never
    raises, so a stray non-UTF-8 byte can't break a tool call.
    """
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")

