"""Tests for setup.py tools — ecoos_pull, list_dir, read_file, mark_setup_done."""
import subprocess
from pathlib import Path
import pytest
from agent.v6.tools.setup import (
    make_setup_tools, EcoosPullArgs, ListDirArgs, ReadFileArgs, MarkSetupDoneArgs,
)


@pytest.fixture
def fake_cli(tmp_path: Path, monkeypatch):
    """Mock eco-cli binary path + subprocess.run."""
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
