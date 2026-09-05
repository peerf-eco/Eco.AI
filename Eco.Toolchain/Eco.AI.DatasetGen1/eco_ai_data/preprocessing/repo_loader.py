import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse


_GITHUB_TREE_RE = re.compile(
    r"^https?://github\.com/(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/tree/(?P<branch>[^/]+)(?P<subpath>/.*)?$",
    re.IGNORECASE,
)


@dataclass
class RepoSource:
    repo_id: str
    root_path: Path
    temp_dir: Optional[Path] = None

    def cleanup(self) -> None:
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class RepoLoader:
    def load(self, repo_path_or_url: str) -> RepoSource:
        if self._is_url(repo_path_or_url):
            return self._clone_remote(repo_path_or_url)
        root = Path(repo_path_or_url).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Repository path does not exist: {root}")
        return RepoSource(repo_id=root.name, root_path=root)

    def _is_url(self, value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https", "git", "ssh"} and bool(parsed.netloc)

    def _parse_github_tree_url(self, url: str) -> Optional[Tuple[str, str, Optional[str]]]:
        m = _GITHUB_TREE_RE.match(url.strip().rstrip("/"))
        if not m:
            return None
        org = m.group("org")
        repo = m.group("repo")
        branch = m.group("branch")
        subpath = (m.group("subpath") or "").lstrip("/") or None
        clone_url = f"https://github.com/{org}/{repo}.git"
        return clone_url, branch, subpath

    def _clone_remote(self, url: str) -> RepoSource:
        temp_root = Path(tempfile.mkdtemp(prefix="eco_ai_data_"))
        target = temp_root / "repo"
        clone_url = url
        branch: Optional[str] = None
        subpath: Optional[str] = None

        parsed_tree = self._parse_github_tree_url(url)
        if parsed_tree:
            clone_url, branch, subpath = parsed_tree

        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([clone_url, str(target)])

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            shutil.rmtree(temp_root, ignore_errors=True)
            raise RuntimeError(f"Failed to clone repository: {proc.stderr.strip()}")

        root = target
        if subpath:
            root = target / subpath
            if not root.exists() or not root.is_dir():
                shutil.rmtree(temp_root, ignore_errors=True)
                raise FileNotFoundError(f"Subpath not found in cloned repository: {subpath}")

        repo_id = root.name or target.name
        return RepoSource(repo_id=repo_id, root_path=root, temp_dir=temp_root)
