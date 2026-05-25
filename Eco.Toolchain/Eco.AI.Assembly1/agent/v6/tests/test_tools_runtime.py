"""Tests for runtime.py — run_artifact via subprocess.run mock."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent.v6.tools.runtime import make_runtime_tools, _RunArgs


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def _mock_run(monkeypatch, *, rc=0, stdout="", stderr="", raise_exc=None):
    captured = {"calls": []}
    def fake_run(cmd, **kw):
        captured["calls"].append({"cmd": cmd, "kw": kw})
        if raise_exc is not None:
            raise raise_exc
        class R: pass
        R.returncode = rc; R.stdout = stdout; R.stderr = stderr
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    return captured


@pytest.fixture
def artifact(project_dir: Path) -> Path:
    p = project_dir / "calc.exe"
    p.write_bytes(b"\x00\x00")  # just exists
    return p


def test_run_artifact_happy_path(artifact, project_dir, monkeypatch):
    cap = _mock_run(monkeypatch, rc=0, stdout="2+2=4\n")
    tools = make_runtime_tools(project_dir=project_dir)
    r = _tool(tools, "run_artifact").execute(_RunArgs(artifact_path=str(artifact)))
    assert not r.is_error
    assert "rc: 0" in r.content
    assert "2+2=4" in r.content
    call = cap["calls"][0]
    assert call["cmd"] == [str(artifact)]
    assert call["kw"]["shell"] is False
    assert call["kw"]["timeout"] == 30


def test_run_artifact_passes_stdin(artifact, project_dir, monkeypatch):
    cap = _mock_run(monkeypatch, rc=0, stdout="echoed\n")
    tools = make_runtime_tools(project_dir=project_dir)
    _tool(tools, "run_artifact").execute(_RunArgs(artifact_path=str(artifact), stdin="hello\n"))
    assert cap["calls"][0]["kw"]["input"] == "hello\n"


def test_run_artifact_no_stdin_passes_none(artifact, project_dir, monkeypatch):
    cap = _mock_run(monkeypatch, rc=0)
    tools = make_runtime_tools(project_dir=project_dir)
    _tool(tools, "run_artifact").execute(_RunArgs(artifact_path=str(artifact)))
    assert cap["calls"][0]["kw"]["input"] is None


def test_run_artifact_reports_stderr_separately(artifact, project_dir, monkeypatch):
    _mock_run(monkeypatch, rc=1, stdout="output line\n", stderr="error line\n")
    tools = make_runtime_tools(project_dir=project_dir)
    r = _tool(tools, "run_artifact").execute(_RunArgs(artifact_path=str(artifact)))
    # rc != 0 is NOT a tool error — it's a program result. Tester decides.
    assert not r.is_error
    assert "rc: 1" in r.content
    assert "--- stdout ---" in r.content and "output line" in r.content
    assert "--- stderr ---" in r.content and "error line" in r.content


def test_run_artifact_empty_stdout_is_marked(artifact, project_dir, monkeypatch):
    _mock_run(monkeypatch, rc=0, stdout="", stderr="")
    tools = make_runtime_tools(project_dir=project_dir)
    r = _tool(tools, "run_artifact").execute(_RunArgs(artifact_path=str(artifact)))
    assert not r.is_error
    assert "(empty)" in r.content


def test_run_artifact_rejects_outside_project_dir(project_dir, tmp_path, monkeypatch):
    _mock_run(monkeypatch)
    tools = make_runtime_tools(project_dir=project_dir)
    r = _tool(tools, "run_artifact").execute(
        _RunArgs(artifact_path=str(tmp_path / "outside.exe"))
    )
    assert r.is_error
    assert "outside" in r.content


def test_run_artifact_rejects_missing_file(project_dir, monkeypatch):
    _mock_run(monkeypatch)
    tools = make_runtime_tools(project_dir=project_dir)
    r = _tool(tools, "run_artifact").execute(
        _RunArgs(artifact_path=str(project_dir / "nope.exe"))
    )
    assert r.is_error
    assert "does not exist" in r.content


def test_run_artifact_rejects_directory(project_dir, monkeypatch):
    (project_dir / "subdir").mkdir()
    _mock_run(monkeypatch)
    tools = make_runtime_tools(project_dir=project_dir)
    r = _tool(tools, "run_artifact").execute(
        _RunArgs(artifact_path=str(project_dir / "subdir"))
    )
    assert r.is_error
    assert "not a regular file" in r.content


def test_run_artifact_timeout_reports_likely_hang(artifact, project_dir, monkeypatch):
    _mock_run(monkeypatch, raise_exc=subprocess.TimeoutExpired(cmd=[str(artifact)], timeout=30))
    tools = make_runtime_tools(project_dir=project_dir)
    r = _tool(tools, "run_artifact").execute(_RunArgs(artifact_path=str(artifact)))
    assert r.is_error
    assert "hung" in r.content.lower()
    # Explicit nudge for the tester to use fail() honestly.
    assert "fail" in r.content.lower()


def test_run_artifact_permission_error(artifact, project_dir, monkeypatch):
    _mock_run(monkeypatch, raise_exc=PermissionError("not executable"))
    tools = make_runtime_tools(project_dir=project_dir)
    r = _tool(tools, "run_artifact").execute(_RunArgs(artifact_path=str(artifact)))
    assert r.is_error
    assert "not executable" in r.content.lower()


def test_run_artifact_truncates_huge_output(artifact, project_dir, monkeypatch):
    big = "x" * 100_000
    _mock_run(monkeypatch, rc=0, stdout=big)
    tools = make_runtime_tools(project_dir=project_dir)
    r = _tool(tools, "run_artifact").execute(_RunArgs(artifact_path=str(artifact)))
    assert not r.is_error
    assert "truncated" in r.content
    assert len(r.content) < len(big)


def test_factory_shape(project_dir):
    tools = make_runtime_tools(project_dir=project_dir)
    assert {t.name for t in tools} == {"run_artifact"}
