"""Tests for setup.py tools — ecoos_pull, list_dir, read_file, mark_setup_done."""
import subprocess
from pathlib import Path
import pytest
from agent.v6.tools import setup as setup_mod
from agent.v6.tools.setup import (
    make_setup_tools, EcoosPullArgs, ListDirArgs, ReadFileArgs, MarkSetupDoneArgs,
)


@pytest.fixture
def fake_cli(tmp_path: Path, monkeypatch):
    """Mock eco-cli binary path + subprocess.run; force Windows pathway."""
    monkeypatch.setattr(setup_mod, "_IS_WINDOWS", True)
    cli = tmp_path / "eco-cli.exe"
    cli.write_text("")  # only needs to exist
    captured = {"calls": []}
    def fake_run(cmd, **kw):
        captured["calls"].append({"cmd": cmd, "kw": kw})
        class R:
            returncode = 0
            stdout = "pulled OK"
            stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    return cli, captured


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_ecoos_pull_invokes_cli_with_argv_list(fake_cli, project_dir):
    cli, cap = fake_cli
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir,
                             allowed_components=[{"cid": "A"*32, "version": "1.0.1.2"}])
    r = _tool(tools, "ecoos_pull").execute(EcoosPullArgs(cid="A"*32, version="1.0.1.2"))
    assert not r.is_error
    call = cap["calls"][0]
    assert call["cmd"][0] == str(cli)
    assert "pull" in call["cmd"]
    assert call["kw"]["shell"] is False
    assert call["kw"]["timeout"] == 60


def test_ecoos_pull_rejects_invalid_cid(fake_cli, project_dir):
    cli, _ = fake_cli
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir,
                             allowed_components=[{"cid": "A"*32, "version": "1.0.1.2"}])
    r = _tool(tools, "ecoos_pull").execute(EcoosPullArgs(cid="not-hex", version="1.0.1.2"))
    assert r.is_error
    assert "invalid cid" in r.content.lower()


def test_ecoos_pull_rejects_unplanned_component(fake_cli, project_dir):
    cli, _ = fake_cli
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir,
                             allowed_components=[{"cid": "B"*32, "version": "1.0.1.2"}])
    r = _tool(tools, "ecoos_pull").execute(EcoosPullArgs(cid="A"*32, version="1.0.1.2"))
    assert r.is_error
    assert "not in plan" in r.content.lower()


def test_list_dir_inside_project_dir(project_dir, fake_cli):
    cli, _ = fake_cli
    (project_dir / "SharedFiles").mkdir()
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir, allowed_components=[])
    r = _tool(tools, "list_dir").execute(ListDirArgs(path=str(project_dir / "SharedFiles")))
    assert not r.is_error


def test_list_dir_rejects_outside(project_dir, fake_cli, tmp_path):
    cli, _ = fake_cli
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir, allowed_components=[])
    r = _tool(tools, "list_dir").execute(ListDirArgs(path=str(tmp_path / "elsewhere")))
    assert r.is_error
    assert "outside" in r.content.lower()


def test_mark_setup_done_args():
    args = MarkSetupDoneArgs(downloaded_paths=["/path/a", "/path/b"])
    assert args.downloaded_paths == ["/path/a", "/path/b"]


# ── Linux pathway — eco-cli absent, copy from sdk_root ─────────────────────

def test_ecoos_pull_linux_copies_from_sdk_root(tmp_path, project_dir, monkeypatch):
    """Linux pathway: copy the resolved inner root from sdk_root into project_dir."""
    monkeypatch.setattr(setup_mod, "_IS_WINDOWS", False)
    def fake_run(*a, **kw):
        raise AssertionError("subprocess.run must not be invoked on Linux pathway")
    monkeypatch.setattr(subprocess, "run", fake_run)

    sdk = tmp_path / "sdk"
    inner = sdk / "Eco.X_DK_v.1.0.1.2" / "Eco.X"
    (inner / "SharedFiles").mkdir(parents=True)
    (inner / "SharedFiles" / "IEcoX.h").write_text("/* x */")

    tools = make_setup_tools(
        cli_path=None,
        project_dir=project_dir,
        allowed_components=[{"cid": "A"*32, "version": "1.0.1.2", "name": "Eco.X"}],
        sdk_root=sdk,
    )
    r = next(t for t in tools if t.name == "ecoos_pull").execute(
        EcoosPullArgs(cid="A"*32, version="1.0.1.2")
    )
    assert not r.is_error, r.content
    copied = project_dir / "Eco.X" / "SharedFiles" / "IEcoX.h"
    assert copied.exists()
    assert copied.read_text() == "/* x */"


def test_ecoos_pull_linux_missing_package(tmp_path, project_dir, monkeypatch):
    """Linux pathway reports a clear error if the SDK mirror has no matching dir."""
    monkeypatch.setattr(setup_mod, "_IS_WINDOWS", False)
    sdk = tmp_path / "sdk"
    sdk.mkdir()
    tools = make_setup_tools(
        cli_path=None,
        project_dir=project_dir,
        allowed_components=[{"cid": "A"*32, "version": "1.0.1.2", "name": "Eco.X"}],
        sdk_root=sdk,
    )
    r = next(t for t in tools if t.name == "ecoos_pull").execute(
        EcoosPullArgs(cid="A"*32, version="1.0.1.2")
    )
    assert r.is_error
    assert "not found in local sdk_root" in r.content.lower()


def test_ecoos_pull_linux_needs_sdk_root(project_dir, monkeypatch):
    """Without sdk_root configured, Linux pathway must fail cleanly."""
    monkeypatch.setattr(setup_mod, "_IS_WINDOWS", False)
    tools = make_setup_tools(
        cli_path=None,
        project_dir=project_dir,
        allowed_components=[{"cid": "A"*32, "version": "1.0.1.2", "name": "Eco.X"}],
        sdk_root=None,
    )
    r = next(t for t in tools if t.name == "ecoos_pull").execute(
        EcoosPullArgs(cid="A"*32, version="1.0.1.2")
    )
    assert r.is_error
    assert "neither eco-cli nor sdk_root" in r.content.lower()


def test_ecoos_pull_linux_copies_inner_root_versioned_2level(tmp_path, project_dir, monkeypatch):
    """On Linux for a versioned-2-level package, copy the INNER root (the dir
    that directly contains SharedFiles/), not the outer _DK_v. directory.
    Otherwise downloaded_paths would point one level too high."""
    monkeypatch.setattr(setup_mod, "_IS_WINDOWS", False)

    sdk = tmp_path / "sdk"
    inner = sdk / "Eco.X_DK_v.1.0.1.2" / "Eco.X"
    (inner / "SharedFiles").mkdir(parents=True)
    (inner / "SharedFiles" / "IEcoX.h").write_text("/* x */")
    (inner / "BuildFiles" / "Linux" / "x86_64" / "StaticRelease").mkdir(parents=True)

    tools = make_setup_tools(
        cli_path=None,
        project_dir=project_dir,
        allowed_components=[{"cid": "A"*32, "version": "1.0.1.2", "name": "Eco.X"}],
        sdk_root=sdk,
    )
    r = next(t for t in tools if t.name == "ecoos_pull").execute(
        EcoosPullArgs(cid="A"*32, version="1.0.1.2")
    )
    assert not r.is_error, r.content
    # Inner root lands at <project_dir>/Eco.X/, with SharedFiles directly inside.
    copied = project_dir / "Eco.X" / "SharedFiles" / "IEcoX.h"
    assert copied.exists(), list(project_dir.rglob("*"))
    # Tool details expose the inner root for downstream nodes (coder/builder).
    assert r.details is not None
    assert r.details["inner_root"].endswith("Eco.X")


def test_ecoos_pull_linux_copies_flat_framework(tmp_path, project_dir, monkeypatch):
    """Flat framework packages (Eco.MemoryManager1) must also be copyable."""
    monkeypatch.setattr(setup_mod, "_IS_WINDOWS", False)

    sdk = tmp_path / "sdk"
    flat = sdk / "Eco.MemoryManager1"
    (flat / "SharedFiles").mkdir(parents=True)
    (flat / "SharedFiles" / "IEcoMem.h").write_text("/* mem */")

    tools = make_setup_tools(
        cli_path=None,
        project_dir=project_dir,
        allowed_components=[{"cid": "A"*32, "version": "1.0.1.2", "name": "Eco.MemoryManager1"}],
        sdk_root=sdk,
    )
    r = next(t for t in tools if t.name == "ecoos_pull").execute(
        EcoosPullArgs(cid="A"*32, version="1.0.1.2")
    )
    assert not r.is_error, r.content
    copied = project_dir / "Eco.MemoryManager1" / "SharedFiles" / "IEcoMem.h"
    assert copied.exists()
    assert r.details["inner_root"].endswith("Eco.MemoryManager1")


def test_ecoos_pull_linux_does_not_silently_substitute_wrong_version(tmp_path, project_dir, monkeypatch):
    """If planner asks for v2.0.0.0 but only v1.0.1.2 exists, the tool MUST
    return an error — not silently copy v1 and report success for v2."""
    monkeypatch.setattr(setup_mod, "_IS_WINDOWS", False)

    sdk = tmp_path / "sdk"
    # Only v1.0.1.2 is on disk.
    inner = sdk / "Eco.X_DK_v.1.0.1.2" / "Eco.X"
    (inner / "SharedFiles").mkdir(parents=True)
    (inner / "SharedFiles" / "IEcoX.h").write_text("/* v1 */")

    tools = make_setup_tools(
        cli_path=None,
        project_dir=project_dir,
        # Plan demands v2.0.0.0.
        allowed_components=[{"cid": "A"*32, "version": "2.0.0.0", "name": "Eco.X"}],
        sdk_root=sdk,
    )
    r = next(t for t in tools if t.name == "ecoos_pull").execute(
        EcoosPullArgs(cid="A"*32, version="2.0.0.0")
    )
    assert r.is_error, f"expected error for wrong-version, got success: {r.content}"
    assert "not found" in r.content.lower()
