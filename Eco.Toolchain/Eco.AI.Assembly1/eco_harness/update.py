"""Manifest-driven self-update for the native (wheel) install.

Reads the release manifest (a single version source of truth for binaries,
RAG index, wheel, and image tags), upgrades the eco-harness wheel in the
running venv, refreshes any changed native binaries / prebuilt index under
the harness app home, and prints a report.

Binary install policy (Eco platform standard):

  - eco-cli / eco-wizard already present on the machine are NEVER
    re-downloaded over, with one exception: a copy in a managed location
    (the standard toolchain dir or the app-home ``bin/`` fallback) that
    carries the harness-written ``.<name>.version`` marker is the harness's
    own prior download and is refreshed in place when the manifest moves
    forward (that IS ``eco-harness update``).
  - every other find — ``ECO_CLI`` / ``ECO_WIZARD`` env vars, custom
    locations, ``PATH`` — is user-owned: kept to avoid version conflicts,
    reported, and recommended for replacement when its version does not
    match the manifest. Only env-var-provided binaries are probed with
    ``--version`` (explicit user opt-in); ``PATH`` and unmarked
    standard-location finds are never executed during detection.
  - fresh downloads land in the standard toolchain dir
    (``$ECO_TOOLCHAIN/eco-cli`` etc.). When those (higher-level) directories
    cannot be created, the historical app-home ``bin/`` folder is used as a
    fallback.

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
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.request import urlopen

from dotenv import load_dotenv

from eco_harness.agent.internal.tools import paths
from eco_harness.agent.internal.tools.binaries import resolve_binary_with_source

DEFAULT_MANIFEST_URL = os.getenv(
    "ECO_MANIFEST_URL",
    "https://github.com/peerf-eco/eco-harness-releases/releases/latest/download/manifest.json",
)

# Manifest keys become filesystem paths and install specs — constrain them to
# a safe charset so a hostile manifest can never traverse or inject options.
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# `eco-cli --version`-style output: first dotted number (optionally v-prefixed).
_VERSION_RE = re.compile(r"[vV]?(\d+(?:\.\d+)+)")


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


def _normalized_version(value: str | None) -> str | None:
    if not value:
        return None
    match = _VERSION_RE.search(value)
    return match.group(1) if match else None


def _marker_version(target_dir: Path, name: str) -> str | None:
    marker = target_dir / f".{name}.version"
    if not marker.is_file():
        return None
    return marker.read_text(encoding="utf-8").strip() or None


def _detect_existing_version(binary: Path) -> str | None:
    """Best-effort version of a user-configured binary (no marker): run
    ``--version`` once and parse the first dotted number.

    Only ever called for ``ECO_CLI`` / ``ECO_WIZARD`` env-var finds — an
    explicit user opt-in. PATH or unmarked filesystem finds are NEVER
    executed during detection (a shadowed PATH binary must not run merely
    because an update was requested).
    """
    try:
        proc = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    return _normalized_version(output)


def _prepare_target_dir(name: str, preferred: Path | None = None) -> Path:
    """Directory the tool's binaries are downloaded into.

    Order: the existing managed location (when the tool was already found in
    the standard toolchain dir or the legacy app-home ``bin/`` folder, so a
    refresh stays in place), then the standard toolchain dir, then the
    app-home ``bin/`` fallback — used when the toolchain (or its parents)
    cannot be created (read-only $HOME, restricted layouts).
    """
    attempts = []
    if preferred is not None:
        attempts.append(preferred)
    attempts.append(paths.tool_install_dir(name))
    attempts.append(paths.tool_fallback_dir())
    problems: list[str] = []
    for candidate in attempts:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if preferred is None and candidate != attempts[0]:
                print(
                    f"[update] WARNING: cannot create {attempts[0]} — "
                    f"falling back to {candidate}"
                )
            return candidate
        except OSError as error:
            problems.append(f"{candidate}: {error}")
    raise OSError("no writable binary install dir: " + "; ".join(problems))


def _refresh_binaries(manifest: dict, report: UpdateReport) -> None:
    system, arch = _platform_key()
    for name, platforms in (manifest.get("binaries") or {}).items():
        entry = (platforms.get(system) or {}).get(arch)
        if not entry:
            continue
        if not _SAFE_NAME_RE.fullmatch(name):
            report.errors.append(f"{name}: unsafe manifest key, skipped")
            continue
        try:
            manifest_version = entry.get("version")
            standard_dir = paths.tool_install_dir(name)
            legacy_dir = paths.tool_fallback_dir()

            # ── Existing install? Only managed copies are ever refreshed. ──
            # resolve_binary_with_source covers ECO_CLI/ECO_WIZARD env vars,
            # the standard toolchain location, the legacy app-home bin/
            # folder and PATH — and tells us which one matched.
            preferred_dir: Path | None = None
            found = resolve_binary_with_source(name)
            if found is not None:
                existing, source = found
                if existing.parent.resolve() == standard_dir.resolve():
                    managed_dir: Path | None = existing.parent
                elif existing.parent.resolve() == legacy_dir.resolve():
                    managed_dir = existing.parent  # managed legacy bin/ copy
                else:
                    managed_dir = None

                if managed_dir is not None:
                    marker = _marker_version(managed_dir, name)
                    if marker is None:
                        # Present in a managed location but never installed
                        # by the harness → user-owned: keep + recommend.
                        report.binaries.append(
                            f"{name} found at {existing} (no version marker) "
                            f"— kept to avoid version conflicts; manifest "
                            f"ships {manifest_version or 'unknown'} — "
                            f"recommend replacing it or delete it to let "
                            f"eco-harness manage it"
                        )
                        continue
                    if manifest_version and marker == manifest_version:
                        continue  # managed copy already at manifest version
                    preferred_dir = managed_dir  # stale marker → refresh here
                else:
                    # User-owned install (env var, custom location, PATH) —
                    # keep it, avoid version conflicts, recommend replacing
                    # when it does not match the manifest. Only env-var
                    # finds are probed with --version (explicit user
                    # opt-in); PATH finds are never executed.
                    found_version = (
                        _detect_existing_version(existing)
                        if source == "env"
                        else None
                    )
                    if manifest_version and (
                        _normalized_version(found_version) == _normalized_version(manifest_version)
                    ):
                        report.binaries.append(
                            f"{name} {manifest_version} already installed at "
                            f"{existing} — kept"
                        )
                    else:
                        note = "" if found_version else (
                            " (not probed)" if source == "path" else ""
                        )
                        report.binaries.append(
                            f"{name} found at {existing}{note} "
                            f"(version {found_version or 'unknown'}) — kept to "
                            f"avoid version conflicts; manifest ships "
                            f"{manifest_version or 'unknown'} — recommend "
                            f"replacing it (update the binary or unset the "
                            f"env var) to get the bundled build"
                        )
                    continue

            bin_dir = _prepare_target_dir(name, preferred_dir)

            zip_url = entry.get("zip_url")
            zip_sha = entry.get("zip_sha256")
            if zip_url and zip_sha:
                # Download the full zip and extract all files flat into bin_dir.
                # This handles eco-cli's bundle: eco-cli + libaws-crt-jni.so + SKILL.md
                with tempfile.TemporaryDirectory(prefix=f"eco-{name}-") as tmp:
                    zip_path = Path(tmp) / f"{name}.zip"
                    _download(zip_url, zip_path)
                    if _sha256(zip_path) != zip_sha:
                        raise RuntimeError("zip sha256 mismatch after download")
                    with zipfile.ZipFile(zip_path, "r") as zf:
                        for member in zf.namelist():
                            # Flat extraction into bin_dir — skip any directory entries
                            # and validate names before writing.
                            if member.endswith("/"):
                                continue
                            member_name = Path(member).name
                            if not _SAFE_NAME_RE.fullmatch(member_name):
                                raise RuntimeError(f"unsafe zip member name: {member_name}")
                            dest = bin_dir / member_name
                            if not dest.resolve().is_relative_to(bin_dir.resolve()):
                                raise RuntimeError(f"zip member escapes bin_dir: {member_name}")
                            dest.write_bytes(zf.read(member))
                            if system != "windows" and not member_name.endswith(
                                (".so", ".dylib", ".md", ".txt")
                            ):
                                dest.chmod(0o755)
                            if system == "darwin" and dest.stat().st_mode & 0o111:
                                subprocess.run(
                                    ["xattr", "-d", "com.apple.quarantine", str(dest)],
                                    check=False, capture_output=True,
                                )
            else:
                # Fallback: manifest has no zip — download primary executable only.
                suffix = ".exe" if system == "windows" else ""
                target = bin_dir / f"{name}{suffix}"
                if not target.resolve().is_relative_to(bin_dir.resolve()):
                    raise RuntimeError("resolved target escapes the binary install dir")
                if target.is_file() and _sha256(target) == entry.get("sha256"):
                    continue
                _download(entry["url"], target)
                if _sha256(target) != entry.get("sha256"):
                    raise RuntimeError("sha256 mismatch after download")
                if suffix != ".exe":
                    target.chmod(0o755)
                    if system == "darwin":
                        subprocess.run(
                            ["xattr", "-d", "com.apple.quarantine", str(target)],
                            check=False, capture_output=True,
                        )

            if manifest_version:
                (bin_dir / f".{name}.version").write_text(
                    manifest_version, encoding="utf-8"
                )
            report.binaries.append(f"{name} {manifest_version or '?'} → {bin_dir}")
        except Exception as error:  # noqa: BLE001
            report.errors.append(f"{name}: {error}")


def _safe_extractall_zip(archive: zipfile.ZipFile, destination: Path) -> None:
    """Extract a zip rejecting absolute paths and ``..`` components."""
    dest_root = destination.resolve()
    for member in archive.namelist():
        target = (dest_root / member).resolve()
        if member.startswith(("/", "\\")) or ".." in Path(member).parts:
            raise RuntimeError(f"unsafe zip member: {member}")
        if not (target == dest_root or dest_root in target.parents):
            raise RuntimeError(f"zip member escapes destination: {member}")
    archive.extractall(path=destination)


def _refresh_index(manifest: dict, report: UpdateReport) -> None:
    index = manifest.get("index")
    if not index:
        return
    data_dir = paths.eco_home() / "data"
    marker = data_dir / ".index_sha256"
    if (
        marker.is_file()
        and marker.read_text(encoding="utf-8").strip() == index.get("sha256")
    ):
        return
    with tempfile.TemporaryDirectory(prefix="eco-harness-index-") as tmp:
        archive_path = Path(tmp) / "index.zip"
        try:
            _download(index["url"], archive_path)
            if _sha256(archive_path) != index.get("sha256"):
                raise RuntimeError("sha256 mismatch after download")
            data_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path, "r") as archive:
                _safe_extractall_zip(archive, data_dir)
            marker.write_text(index["sha256"], encoding="utf-8")
            report.index = f"updated ({index['sha256'][:12]})"
        except Exception as error:  # noqa: BLE001
            report.errors.append(f"index: {error}")


def run_update(manifest_url: str | None = None) -> UpdateReport:
    report = UpdateReport()
    # The installers persist user-selected ECO_CLI/ECO_WIZARD paths in the
    # app-home .env. Load them before binary discovery so rerunning an
    # installer cannot download a duplicate bundled tool.
    load_dotenv(paths.eco_home() / ".env")
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
