"""Manifest-driven self-update for the native (wheel) install.

Reads the release manifest (a single version source of truth for binaries,
RAG index, wheel, and image tags), upgrades the eco-harness wheel in the
running venv, refreshes any changed native binaries / prebuilt index under
``ECO_HOME``, and prints a report.

Docker installs update differently (``docker compose pull``) and never call
this module.
"""
from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import urlopen

from eco_harness.agent.internal.tools.paths import eco_home

DEFAULT_MANIFEST_URL = os.getenv(
    "ECO_MANIFEST_URL",
    "https://downloads.ecoos.dev/eco-harness/manifest.json",
)

# Manifest keys become filesystem paths and install specs — constrain them to
# a safe charset so a hostile manifest can never traverse or inject options.
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass
class UpdateReport:
    wheel: str = "unchanged"
    binaries: list[str] = field(default_factory=list)
    index: str = "unchanged"
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"wheel: {self.wheel}"]
        lines += [f"binary: {b}" for b in self.binaries]
        lines.append(f"index: {self.index}")
        lines += [f"error: {e}" for e in self.errors]
        return "\n".join(lines)


def _platform_key() -> tuple[str, str]:
    system = sys.platform
    machine = platform.machine().lower()
    arch = "x86_64" if machine in ("amd64", "x86_64") else "arm64"
    if system.startswith("win"):
        return "windows", "x86_64"
    if system.startswith("darwin"):
        return "darwin", arch
    return "linux", arch


def fetch_manifest(url: str | None = None) -> dict:
    target = (url or DEFAULT_MANIFEST_URL).strip()
    with urlopen(target, timeout=30) as response:  # noqa: S310 - fixed https base
        import json

        return json.loads(response.read().decode("utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with urlopen(url, timeout=600) as response, tmp_path.open("wb") as fh:  # noqa: S310
            shutil.copyfileobj(response, fh)
        tmp_path.replace(destination)
    finally:
        tmp_path.unlink(missing_ok=True)


def _refresh_binaries(manifest: dict, report: UpdateReport) -> None:
    system, arch = _platform_key()
    bin_dir = eco_home() / "bin"
    for name, platforms in (manifest.get("binaries") or {}).items():
        entry = (platforms.get(system) or {}).get(arch)
        if not entry:
            continue
        # Manifest keys become file paths — never let a hostile manifest
        # traverse out of bin_dir (absolute paths, "..", separators).
        if not _SAFE_NAME_RE.fullmatch(name):
            report.errors.append(f"{name}: unsafe manifest key, skipped")
            continue
        suffix = ".exe" if system == "windows" else ""
        target = bin_dir / f"{name}{suffix}"
        try:
            if not target.resolve().is_relative_to(bin_dir.resolve()):
                raise RuntimeError("resolved target escapes ECO_HOME/bin")
            if target.is_file() and _sha256(target) == entry.get("sha256"):
                continue
            _download(entry["url"], target)
            if _sha256(target) != entry.get("sha256"):
                raise RuntimeError("sha256 mismatch after download")
            if suffix != ".exe":
                target.chmod(0o755)
                if system == "darwin":
                    # Gatekeeper stopgap: strip the quarantine attribute the
                    # browser adds to downloaded files. Proper signing is the
                    # EcoCLI pipeline's job.
                    subprocess.run(
                        ["xattr", "-d", "com.apple.quarantine", str(target)],
                        check=False, capture_output=True,
                    )
            report.binaries.append(f"{name} → {target}")
        except Exception as error:  # noqa: BLE001 - report, keep going
            report.errors.append(f"{name}: {error}")


def _safe_extractall(archive: tarfile.TarFile, destination: Path) -> None:
    """Extract a tarball rejecting absolute paths, ``..`` components, and
    links pointing outside ``destination`` — on every 3.11.x.

    ``TarFile.extractall(filter="data")`` (PEP 706) would do this too, but
    the keyword only exists from 3.11.4, so we validate members explicitly
    instead of depending on the patch release.
    """
    dest_root = destination.resolve()
    for member in archive.getmembers():
        target = (dest_root / member.name).resolve()
        if member.name.startswith(("/", "\\")) or ".." in Path(member.name).parts:
            raise RuntimeError(f"unsafe tar member: {member.name}")
        if not (
            target == dest_root or dest_root in target.parents
        ):
            raise RuntimeError(f"tar member escapes destination: {member.name}")
        if member.issym() or member.islnk():
            raise RuntimeError(f"link members not supported: {member.name}")
    archive.extractall(path=destination, members=archive.getmembers())


def _refresh_index(manifest: dict, report: UpdateReport) -> None:
    index = manifest.get("index")
    if not index:
        return
    data_dir = eco_home() / "data"
    marker = data_dir / ".index_sha256"
    if (
        marker.is_file()
        and marker.read_text(encoding="utf-8").strip() == index.get("sha256")
    ):
        return
    with tempfile.TemporaryDirectory(prefix="eco-harness-index-") as tmp:
        tarball = Path(tmp) / "index.tar.gz"
        try:
            _download(index["url"], tarball)
            if _sha256(tarball) != index.get("sha256"):
                raise RuntimeError("sha256 mismatch after download")
            data_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(tarball, "r:gz") as archive:
                # Member validation happens in _safe_extractall (works on
                # every 3.11.x); the sha256 check alone only proves the
                # tarball matches the manifest, it is not a trust statement
                # about the archive contents.
                _safe_extractall(archive, data_dir)
            marker.write_text(index["sha256"], encoding="utf-8")
            report.index = f"updated ({index['sha256'][:12]})"
        except Exception as error:  # noqa: BLE001
            report.errors.append(f"index: {error}")


def run_update(manifest_url: str | None = None) -> UpdateReport:
    report = UpdateReport()
    try:
        manifest = fetch_manifest(manifest_url)
    except Exception as error:  # noqa: BLE001
        report.errors.append(f"manifest: {error}")
        return report

    wheel = manifest.get("wheel") or {}
    installed_version = _installed_version()
    manifest_version = wheel.get("version")
    if manifest_version and manifest_version != installed_version:
        if _pip_upgrade(manifest, report):
            report.wheel = f"{installed_version} → {manifest_version} (restart to apply)"
        else:
            report.errors.append("wheel upgrade failed — see output above")
    _refresh_binaries(manifest, report)
    _refresh_index(manifest, report)
    return report


def _installed_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("eco-harness")
    except Exception:  # noqa: BLE001
        return None


def _pip_upgrade(manifest: dict, report: UpdateReport) -> bool:
    """Upgrade the wheel via uv (the native install is uv-managed; uv venvs
    have no pip), falling back to pip — trying each until one succeeds.

    The wheel is downloaded and sha256-verified against the manifest BEFORE
    installation: unlike binaries/index verification, this artifact executes
    code, so an unverified URL install is never acceptable.
    """
    wheel = manifest.get("wheel") or {}
    url = wheel.get("url")
    expected_sha = wheel.get("sha256")
    if url and expected_sha:
        verified = Path(tempfile.gettempdir()) / (
            f"eco-harness-{wheel.get('version', 'update')}.whl"
        )
        try:
            _download(url, verified)
            if _sha256(verified) != expected_sha:
                raise RuntimeError("sha256 mismatch after download")
        except Exception as error:  # noqa: BLE001
            report.errors.append(f"wheel download: {error}")
            return False
        spec = str(verified)
    else:
        # No verifiable artifact in the manifest — fall back to the PyPI
        # name (PyPI enforces its own upload integrity).
        spec = "eco-harness"

    commands = [
        ["uv", "pip", "install", "--python", sys.executable, "--upgrade"],
        [sys.executable, "-m", "pip", "install", "--upgrade"],
    ]
    for cmd in commands:
        if shutil.which(cmd[0]) is None and cmd[0] != sys.executable:
            continue
        result = subprocess.run([*cmd, spec], check=False)
        if result.returncode == 0:
            return True
    return False
