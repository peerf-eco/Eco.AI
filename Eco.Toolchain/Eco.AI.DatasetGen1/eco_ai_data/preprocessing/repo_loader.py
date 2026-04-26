import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


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

    def _clone_remote(self, url: str) -> RepoSource:
        temp_root = Path(tempfile.mkdtemp(prefix="eco_ai_data_"))
        target = temp_root / "repo"
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            shutil.rmtree(temp_root, ignore_errors=True)
            raise RuntimeError(f"Failed to clone repository: {proc.stderr.strip()}")
        return RepoSource(repo_id=target.name, root_path=target, temp_dir=temp_root)
