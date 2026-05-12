"""Tests for builder tools."""
import subprocess
from pathlib import Path
from agent.v6.tools.builder import (
    make_builder_tools, RunMakeArgs, ReportBuildPassArgs, ReportBuildFailArgs,
)


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_run_make_invokes_cmd_with_vcvarsall(monkeypatch, project_dir):
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
    assert captured["kw"]["shell"] is False
    assert captured["kw"]["timeout"] == 300
    assert captured["kw"]["env"]["MSYS_NO_PATHCONV"] == "1"


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
