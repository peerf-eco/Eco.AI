from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeInfo:
    path: Path
    name: str
    commit: str


class WorktreeError(RuntimeError):
    pass


def _run_git(repo_root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout).strip()
        raise WorktreeError(f"git {' '.join(args)} failed: {detail}")
    return process.stdout.strip()


def create_worktree(
    repo_root: Path,
    session_id: str,
    *,
    name: str | None = None,
    root: Path | None = None,
) -> WorktreeInfo:
    repo_root = Path(_run_git(repo_root.resolve(), "rev-parse", "--show-toplevel")).resolve()
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", name or session_id).strip("-")
    safe_name = safe_name[:64] or session_id[:12]
    worktree_root = (root or repo_root.parent / f"{repo_root.name}.worktrees").resolve()
    path = worktree_root / safe_name
    if path.exists():
        raise WorktreeError(f"worktree destination already exists: {path}")
    worktree_root.mkdir(parents=True, exist_ok=True)
    commit = _run_git(repo_root, "rev-parse", "HEAD")
    _run_git(repo_root, "worktree", "add", "--detach", str(path), commit)
    return WorktreeInfo(path=path, name=safe_name, commit=commit)