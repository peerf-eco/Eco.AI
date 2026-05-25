"""Tests for build.py — run_build via subprocess.run mock."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agent.v6.tools.build import make_build_tools, _BuildArgs


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
def proj_with_makefile(project_dir):
    sub = project_dir / "Eco.Calc" / "MSVC_v140"
    sub.mkdir(parents=True)
    (sub / "Makefile").write_text("all:\n\techo build\n")
    return sub


def test_run_build_invokes_make_in_subdir(proj_with_makefile, project_dir, monkeypatch):
    cap = _mock_run(monkeypatch, rc=0, stdout="cl.exe ok\n")
    make_exe = Path("/usr/bin/make")  # str(make_exe) is platform-dependent
    tools = make_build_tools(project_dir=project_dir, make_exe=make_exe)
    r = _tool(tools, "run_build").execute(_BuildArgs(project_subdir=str(proj_with_makefile)))
    assert not r.is_error
    assert "BUILD OK" in r.content
    assert "cl.exe ok" in r.content
    call = cap["calls"][0]
    assert call["cmd"] == [str(make_exe)]
    assert call["kw"]["cwd"] == str(proj_with_makefile)
    assert call["kw"]["shell"] is False


def test_run_build_passes_target(proj_with_makefile, project_dir, monkeypatch):
    cap = _mock_run(monkeypatch, rc=0, stdout="")
    tools = make_build_tools(project_dir=project_dir, make_exe=Path("make"))
    _tool(tools, "run_build").execute(
        _BuildArgs(project_subdir=str(proj_with_makefile), target="clean")
    )
    assert cap["calls"][0]["cmd"] == ["make", "clean"]


def test_run_build_rejects_outside_project_dir(project_dir, tmp_path, monkeypatch):
    _mock_run(monkeypatch)  # would assert if called
    tools = make_build_tools(project_dir=project_dir, make_exe=Path("make"))
    r = _tool(tools, "run_build").execute(_BuildArgs(project_subdir=str(tmp_path / "elsewhere")))
    assert r.is_error
    assert "outside" in r.content


def test_run_build_rejects_missing_subdir(project_dir, monkeypatch):
    _mock_run(monkeypatch)
    tools = make_build_tools(project_dir=project_dir, make_exe=Path("make"))
    r = _tool(tools, "run_build").execute(_BuildArgs(project_subdir=str(project_dir / "nope")))
    assert r.is_error
    assert "not a directory" in r.content


def test_run_build_rejects_subdir_without_makefile(project_dir, monkeypatch):
    sub = project_dir / "empty"
    sub.mkdir()
    _mock_run(monkeypatch)
    tools = make_build_tools(project_dir=project_dir, make_exe=Path("make"))
    r = _tool(tools, "run_build").execute(_BuildArgs(project_subdir=str(sub)))
    assert r.is_error
    assert "No Makefile" in r.content


def test_run_build_failure_includes_stderr(proj_with_makefile, project_dir, monkeypatch):
    _mock_run(monkeypatch, rc=2,
              stdout="compiling main.c\n",
              stderr="main.c(5): error C2065: undeclared identifier\n")
    tools = make_build_tools(project_dir=project_dir, make_exe=Path("make"))
    r = _tool(tools, "run_build").execute(_BuildArgs(project_subdir=str(proj_with_makefile)))
    assert r.is_error
    assert "BUILD FAILED" in r.content
    assert "rc=2" in r.content
    assert "error C2065" in r.content


def test_run_build_truncates_very_long_output(proj_with_makefile, project_dir, monkeypatch):
    long_log = "warning: line\n" * 2000  # ~30 KB
    _mock_run(monkeypatch, rc=0, stdout=long_log)
    tools = make_build_tools(project_dir=project_dir, make_exe=Path("make"))
    r = _tool(tools, "run_build").execute(_BuildArgs(project_subdir=str(proj_with_makefile)))
    assert not r.is_error
    assert "truncated" in r.content
    assert len(r.content) < len(long_log)


def test_run_build_timeout_is_error(proj_with_makefile, project_dir, monkeypatch):
    _mock_run(monkeypatch,
              raise_exc=subprocess.TimeoutExpired(cmd="make", timeout=300))
    tools = make_build_tools(project_dir=project_dir, make_exe=Path("make"))
    r = _tool(tools, "run_build").execute(_BuildArgs(project_subdir=str(proj_with_makefile)))
    assert r.is_error
    assert "timed out" in r.content.lower()


def test_run_build_missing_make_binary_is_error(proj_with_makefile, project_dir, monkeypatch):
    _mock_run(monkeypatch, raise_exc=FileNotFoundError("make"))
    tools = make_build_tools(project_dir=project_dir, make_exe=Path("make"))
    r = _tool(tools, "run_build").execute(_BuildArgs(project_subdir=str(proj_with_makefile)))
    assert r.is_error
    assert "not found" in r.content.lower()


def test_factory_shape(project_dir):
    tools = make_build_tools(project_dir=project_dir, make_exe=Path("make"))
    assert {t.name for t in tools} == {"run_build"}
