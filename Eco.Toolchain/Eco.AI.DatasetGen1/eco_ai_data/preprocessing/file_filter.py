from pathlib import Path
from typing import Iterable, Iterator, List


class FileFilter:
    def __init__(self, include_extensions: List[str], exclude_dirs: List[str], max_file_bytes: int) -> None:
        self.include_extensions = {e.lower() for e in include_extensions}
        self.exclude_dirs = set(exclude_dirs)
        self.max_file_bytes = max_file_bytes

    def iter_python_files(self, root: Path) -> Iterator[Path]:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if not self._is_allowed_extension(path):
                continue
            if self._is_excluded(path, root):
                continue
            if not self._is_size_ok(path):
                continue
            yield path

    def filter_paths(self, paths: Iterable[Path], root: Path) -> Iterator[Path]:
        for path in paths:
            if self._is_allowed_extension(path) and not self._is_excluded(path, root) and self._is_size_ok(path):
                yield path

    def _is_allowed_extension(self, path: Path) -> bool:
        return path.suffix.lower() in self.include_extensions

    def _is_size_ok(self, path: Path) -> bool:
        try:
            return path.stat().st_size <= self.max_file_bytes
        except OSError:
            return False

    def _is_excluded(self, path: Path, root: Path) -> bool:
        try:
            rel_parts = path.relative_to(root).parts
        except ValueError:
            rel_parts = path.parts
        for part in rel_parts:
            if part in self.exclude_dirs:
                return True
        return False
