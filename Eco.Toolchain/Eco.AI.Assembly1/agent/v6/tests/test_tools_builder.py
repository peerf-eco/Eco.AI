"""Tests for builder tools."""
import subprocess
from pathlib import Path
from agent.v6.tools import builder as builder_mod
from agent.v6.tools.builder import (
    make_builder_tools, RunMakeArgs, ReportBuildPassArgs, ReportBuildFailArgs,
)


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_run_make_invokes_cmd_with_vcvarsall(monkeypatch, project_dir):
    monkeypatch.setattr(builder_mod, "_IS_WINDOWS", True)
    captured = {}
    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        captured["kw"] = kw
        class R: returncode = 0; stdout = "Build succeeded"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_builder_tools(project_dir=project_dir,
                               vcvarsall=Path(r"C:/vcvarsall.bat"),
                               make_exe=Path(r"C:/make.exe"))
    r = _tool(tools, "run_make").execute(RunMakeArgs())
    assert not r.is_error
    # cmd should be a list (argv), shell=False
    assert isinstance(captured["cmd"], list)
    assert captured["cmd"][0] == "cmd.exe"
    assert captured["kw"]["shell"] is False
    assert captured["kw"]["timeout"] == 300
    assert captured["kw"]["env"]["MSYS_NO_PATHCONV"] == "1"


def test_run_make_linux_uses_make_directly(monkeypatch, project_dir):
    """On Linux: spawn make directly, no cmd.exe, no vcvarsall."""
    monkeypatch.setattr(builder_mod, "_IS_WINDOWS", False)
    captured = {}
    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        captured["kw"] = kw
        class R: returncode = 0; stdout = "ok"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_builder_tools(project_dir=project_dir,
                               vcvarsall=None,
                               make_exe=Path("make"))
    r = _tool(tools, "run_make").execute(RunMakeArgs(target="all"))
    assert not r.is_error, r.content
    assert captured["cmd"] == ["make", "all"]
    assert captured["kw"]["shell"] is False


def test_run_make_windows_requires_vcvarsall(monkeypatch, project_dir):
    """On Windows: vcvarsall=None fails cleanly without spawning anything."""
    monkeypatch.setattr(builder_mod, "_IS_WINDOWS", True)
    called = {"runs": 0}
    def fake_run(*a, **kw):
        called["runs"] += 1
        class R: returncode = 0; stdout = ""; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_builder_tools(project_dir=project_dir, vcvarsall=None, make_exe=Path("make.exe"))
    r = _tool(tools, "run_make").execute(RunMakeArgs())
    assert r.is_error
    assert "vcvarsall" in r.content.lower()
    assert called["runs"] == 0


def test_run_make_failure_returns_is_error(monkeypatch, project_dir):
    def fake_run(cmd, **kw):
        class R: returncode = 1; stdout = "error C2065:"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_builder_tools(project_dir=project_dir,
                               vcvarsall=Path(r"C:/vcvarsall.bat"),
                               make_exe=Path(r"C:/make.exe"))
    r = _tool(tools, "run_make").execute(RunMakeArgs())
    assert r.is_error
    assert "C2065" in r.content


def test_report_pass_fail_args_schemas():
    p = ReportBuildPassArgs(artifact_path="C:/Project1/out.exe")
    f = ReportBuildFailArgs(error_md="## Error\nundefined symbol")
    assert p.artifact_path.endswith(".exe")
    assert "undefined" in f.error_md


def test_run_make_rejects_injection_via_target(monkeypatch, project_dir):
    """LLM-supplied target must be regex-validated — any shell metachar rejected."""
    called = {"runs": 0}
    def fake_run(*a, **kw):
        called["runs"] += 1
        class R: returncode = 0; stdout = ""; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_builder_tools(project_dir=project_dir,
                               vcvarsall=Path(r"C:/vcvarsall.bat"),
                               make_exe=Path(r"C:/make.exe"))
    for bad in ("all & calc.exe", "all && rm -rf /", "all; whoami", "../etc/passwd"):
        r = _tool(tools, "run_make").execute(RunMakeArgs(target=bad))
        assert r.is_error, f"target {bad!r} should be rejected"
        assert "invalid make target" in r.content
    assert called["runs"] == 0, "subprocess.run must NEVER fire for rejected targets"


def test_run_make_accepts_normal_targets(monkeypatch, project_dir):
    """Normal make targets pass validation."""
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})())
    tools = make_builder_tools(project_dir=project_dir,
                               vcvarsall=Path(r"C:/vcvarsall.bat"),
                               make_exe=Path(r"C:/make.exe"))
    for good in ("all", "clean", "Eco.X.exe", "test_target", "x-y"):
        r = _tool(tools, "run_make").execute(RunMakeArgs(target=good))
        assert not r.is_error, f"target {good!r} should pass"
