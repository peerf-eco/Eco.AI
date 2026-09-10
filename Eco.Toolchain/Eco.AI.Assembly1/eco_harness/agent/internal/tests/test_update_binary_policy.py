"""update.py binary-install policy tests (Eco platform standard paths).

Locks in the installer contract:

  - eco-cli / eco-wizard are downloaded ONLY when absent everywhere
    (ECO_CLI / ECO_WIZARD env vars, standard paths, bin/, PATH are checked
    first);
  - user-owned installs (env var, custom location, PATH, or an unmarked
    copy in a managed location) are KEPT — never overwritten; only
    env-var-provided binaries are probed with --version, PATH finds are
    never executed;
  - harness-managed copies (toolchain dir / app-home bin/ WITH the
    .<name>.version marker) refresh in place; matching marker → no-op,
    stale marker → refreshed;
  - fresh downloads land in $ECO_TOOLCHAIN/<tool>, falling back to the
    app-home bin/ folder when the toolchain dirs cannot be created.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from eco_harness import update


@pytest.fixture()
def isolated(monkeypatch, tmp_path: Path) -> Path:
    """Deterministic platform roots.

    ECO_HOME (ecosystem root) sits at <tmp>/ecoos; the harness app home
    (ECO_HARNESS) is deliberately OUTSIDE it — the real-world fallback case
    where ~/ecoos/toolchain cannot be created but the app home can.
    """
    eco_root = tmp_path / "ecoos"
    for var in (
        "ECO_TOOLCHAIN", "ECO_CLI", "ECO_WIZARD",
        "ECO_CLI_PATH", "ECO_WIZARD_PATH",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ECO_HOME", str(eco_root))
    monkeypatch.setenv("ECO_HARNESS", str(tmp_path / "harness-home"))
    return eco_root


FAKE_BYTES = b"#!/bin/sh\nfake\n"


def _entry(version: str = "v2.0.0", sha256: str = "0" * 64) -> dict:
    return {
        "url": "https://example.test/eco-cli",
        "sha256": sha256,
        "version": version,
    }


def _manifest(version: str = "v2.0.0", sha256: str = "0" * 64) -> dict:
    return {"binaries": {"eco-cli": {"linux": {"x86_64": _entry(version, sha256)}}}}


def _fake_download(monkeypatch) -> str:
    """Replace _download with a stub dropping a deterministic fake executable;
    returns the REAL sha256 of that payload so the download-verification and
    no-op checks behave like production."""
    import hashlib

    def fake_download(url: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(FAKE_BYTES)

    monkeypatch.setattr(update, "_download", fake_download)
    return hashlib.sha256(FAKE_BYTES).hexdigest()


def test_downloads_into_standard_toolchain_dir(isolated: Path, monkeypatch):
    """Missing tool → downloaded into $ECO_TOOLCHAIN/eco-cli with a marker."""
    monkeypatch.setattr(update, "resolve_binary_with_source", lambda name, **kw: None)
    sha = _fake_download(monkeypatch)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(sha256=sha), report)
    tool_dir = isolated / "toolchain" / "eco-cli"
    assert not report.errors
    assert (tool_dir / "eco-cli").is_file()
    assert (tool_dir / ".eco-cli.version").read_text(encoding="utf-8") == "v2.0.0"
    assert any("toolchain" in line for line in report.binaries)


def test_falls_back_to_app_home_bin_when_toolchain_unwritable(
    isolated: Path, monkeypatch, tmp_path: Path
):
    """Uncreatable toolchain dir (path occupied by a file) → app-home bin/."""
    isolated.mkdir(parents=True)
    (isolated / "toolchain").write_text("occupies the toolchain path")
    monkeypatch.setattr(update, "resolve_binary_with_source", lambda name, **kw: None)
    sha = _fake_download(monkeypatch)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(sha256=sha), report)
    fallback = tmp_path / "harness-home" / "bin"
    assert not report.errors
    assert (fallback / "eco-cli").is_file()
    assert (fallback / ".eco-cli.version").read_text(encoding="utf-8") == "v2.0.0"


def test_user_managed_binary_is_kept_with_replacement_hint(
    isolated: Path, monkeypatch, tmp_path: Path
):
    """ECO_CLI pointing at an older user install → kept, never overwritten."""
    user_binary = tmp_path / "user-tools" / "eco-cli"
    user_binary.parent.mkdir(parents=True)
    user_binary.write_text("#!/bin/sh\nfake\n")
    monkeypatch.setenv("ECO_CLI", str(user_binary))
    monkeypatch.setattr(
        update,
        "resolve_binary_with_source",
        lambda name, **kw: (user_binary, "env"),
    )
    monkeypatch.setattr(
        update.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(
            [], 0, stdout="eco-cli version 1.0.0", stderr=""
        ),
    )
    sha = _fake_download(monkeypatch)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(version="v2.0.0", sha256=sha), report)
    assert not report.errors
    assert not (isolated / "toolchain" / "eco-cli").exists()
    assert "kept" in report.binaries[0]
    assert "recommend replacing" in report.binaries[0]


def test_user_managed_binary_matching_version_reported_kept(
    isolated: Path, monkeypatch, tmp_path: Path
):
    """Same version as the manifest → plain 'kept' note, no recommendation."""
    user_binary = tmp_path / "user-tools" / "eco-cli"
    user_binary.parent.mkdir(parents=True)
    user_binary.write_text("#!/bin/sh\nfake\n")
    monkeypatch.setenv("ECO_CLI", str(user_binary))
    monkeypatch.setattr(
        update,
        "resolve_binary_with_source",
        lambda name, **kw: (user_binary, "env"),
    )
    monkeypatch.setattr(
        update.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(
            [], 0, stdout="eco-cli 2.0.0", stderr=""
        ),
    )
    sha = _fake_download(monkeypatch)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(version="v2.0.0", sha256=sha), report)
    assert not report.errors
    assert "already installed" in report.binaries[0]
    assert "recommend" not in report.binaries[0]


def test_legacy_bin_copy_refreshes_in_place(
    isolated: Path, monkeypatch, tmp_path: Path
):
    """A stale managed copy in the app-home bin/ folder is refreshed there
    (the bin/ folder stays a supported install location)."""
    legacy_dir = tmp_path / "harness-home" / "bin"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "eco-cli").write_text("#!/bin/sh\nold\n")
    (legacy_dir / ".eco-cli.version").write_text("v1.0.0", encoding="utf-8")
    monkeypatch.setattr(
        update,
        "resolve_binary_with_source",
        lambda name, **kw: (legacy_dir / "eco-cli", "bin"),
    )
    sha = _fake_download(monkeypatch)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(version="v2.0.0", sha256=sha), report)
    assert not report.errors
    # Refreshed in place — NOT reinstalled into the toolchain dir.
    assert (legacy_dir / "eco-cli").read_bytes().startswith(b"#!/bin/sh\nfake")
    assert (legacy_dir / ".eco-cli.version").read_text() == "v2.0.0"
    assert not (isolated / "toolchain" / "eco-cli").exists()


def test_managed_toolchain_copy_up_to_date_skips_download(
    isolated: Path, monkeypatch
):
    """Marker matches the manifest → no download at all."""
    tool_dir = isolated / "toolchain" / "eco-cli"
    tool_dir.mkdir(parents=True)
    (tool_dir / "eco-cli").write_text("#!/bin/sh\nv2\n")
    (tool_dir / ".eco-cli.version").write_text("v2.0.0", encoding="utf-8")
    monkeypatch.setattr(
        update,
        "resolve_binary_with_source",
        lambda name, **kw: (tool_dir / "eco-cli", "toolchain"),
    )

    def fail_download(url: str, destination: Path) -> None:
        raise AssertionError("download must be skipped when up to date")

    monkeypatch.setattr(update, "_download", fail_download)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(version="v2.0.0"), report)
    assert not report.errors
    assert report.binaries == []


def test_unmarked_toolchain_copy_is_user_owned_and_kept(
    isolated: Path, monkeypatch
):
    """A binary parked in the standard toolchain dir WITHOUT the harness
    version marker is user-owned: kept + replacement recommendation, never
    overwritten."""
    tool_dir = isolated / "toolchain" / "eco-cli"
    tool_dir.mkdir(parents=True)
    (tool_dir / "eco-cli").write_text("#!/bin/sh\nuser-build\n")
    monkeypatch.setattr(
        update,
        "resolve_binary_with_source",
        lambda name, **kw: (tool_dir / "eco-cli", "toolchain"),
    )
    sha = _fake_download(monkeypatch)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(version="v2.0.0", sha256=sha), report)
    assert not report.errors
    assert (tool_dir / "eco-cli").read_bytes() == b"#!/bin/sh\nuser-build\n"
    assert "kept" in report.binaries[0]
    assert "no version marker" in report.binaries[0]
    assert "recommend" in report.binaries[0]


def test_stale_marker_toolchain_copy_refreshes_in_place(
    isolated: Path, monkeypatch
):
    """Managed copy (harness marker) with an older version → refreshed in
    place by `eco-harness update` — that is the update command's purpose."""
    tool_dir = isolated / "toolchain" / "eco-cli"
    tool_dir.mkdir(parents=True)
    (tool_dir / "eco-cli").write_text("#!/bin/sh\nold-managed\n")
    (tool_dir / ".eco-cli.version").write_text("v1.0.0", encoding="utf-8")
    monkeypatch.setattr(
        update,
        "resolve_binary_with_source",
        lambda name, **kw: (tool_dir / "eco-cli", "toolchain"),
    )
    sha = _fake_download(monkeypatch)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(version="v2.0.0", sha256=sha), report)
    assert not report.errors
    assert (tool_dir / "eco-cli").read_bytes().startswith(b"#!/bin/sh\nfake")
    assert (tool_dir / ".eco-cli.version").read_text(encoding="utf-8") == "v2.0.0"


def test_env_pointing_at_managed_toolchain_copy_refreshes_in_place(
    isolated: Path, monkeypatch
):
    """The standard ECO_CLI env value must not hide a managed marker copy."""
    tool_dir = isolated / "toolchain" / "eco-cli"
    tool_dir.mkdir(parents=True)
    (tool_dir / "eco-cli").write_text("#!/bin/sh\nold-managed\n")
    (tool_dir / ".eco-cli.version").write_text("v1.0.0", encoding="utf-8")
    monkeypatch.setenv("ECO_CLI", str(tool_dir))
    monkeypatch.setattr(
        update,
        "resolve_binary_with_source",
        lambda name, **kw: (tool_dir / "eco-cli", "env"),
    )
    sha = _fake_download(monkeypatch)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(version="v2.0.0", sha256=sha), report)
    assert not report.errors
    assert (tool_dir / "eco-cli").read_bytes().startswith(b"#!/bin/sh\nfake")
    assert (tool_dir / ".eco-cli.version").read_text(encoding="utf-8") == "v2.0.0"


def test_path_binary_is_kept_without_execution(isolated: Path, monkeypatch):
    """A PATH-discovered binary is kept WITHOUT running it — a shadowed or
    hostile PATH entry must not execute merely because an update was run."""
    path_binary = isolated / "opt" / "bin" / "eco-cli"
    path_binary.parent.mkdir(parents=True)
    path_binary.write_text("#!/bin/sh\nhostile\n")
    monkeypatch.setattr(
        update,
        "resolve_binary_with_source",
        lambda name, **kw: (path_binary, "path"),
    )

    def fail_run(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("PATH binaries must not be executed during update")

    monkeypatch.setattr(update.subprocess, "run", fail_run)
    sha = _fake_download(monkeypatch)
    report = update.UpdateReport()
    update._refresh_binaries(_manifest(version="v2.0.0", sha256=sha), report)
    assert not report.errors
    assert not (isolated / "toolchain" / "eco-cli").exists()
    assert "kept" in report.binaries[0]
    assert "not probed" in report.binaries[0]
