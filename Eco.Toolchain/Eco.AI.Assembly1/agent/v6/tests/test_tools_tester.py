import json
import subprocess
from pathlib import Path
from agent.v6.tools.tester import (
    make_tester_tools, RunArtifactArgs, ReportTestPassArgs, ReportTestFailArgs,
)


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_run_artifact_captures_output(monkeypatch, project_dir):
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    def fake_run(cmd, **kw):
        class R: returncode = 0; stdout = "Result: 5\n"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_tester_tools(build_artifact=artifact)
    r = _tool(tools, "run_artifact").execute(RunArtifactArgs(timeout_s=5))
    assert not r.is_error
    payload = json.loads(r.content)
    assert payload["exit_code"] == 0
    assert "Result: 5" in payload["stdout"]
    assert payload["timed_out"] is False


def test_run_artifact_timeout(monkeypatch, project_dir):
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    def fake_run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kw.get("timeout"))
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_tester_tools(build_artifact=artifact)
    r = _tool(tools, "run_artifact").execute(RunArtifactArgs(timeout_s=2))
    assert not r.is_error  # timeout is a tested outcome, not a tool error
    payload = json.loads(r.content)
    assert payload["timed_out"] is True


def test_no_read_file_tool(project_dir):
    """Tester MUST NOT have read_file (anchoring-bias structural mitigation)."""
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    tools = make_tester_tools(build_artifact=artifact)
    assert all(t.name != "read_file" for t in tools)
    assert all(t.name != "list_dir" for t in tools)
    assert all(t.name != "glob"      for t in tools)
    assert all(t.name != "grep"      for t in tools)


def test_report_pass_fail_schemas():
    p = ReportTestPassArgs(reason_md="output matches acceptance")
    f = ReportTestFailArgs(reason_md="stdout was empty")
    assert "acceptance" in p.reason_md
    assert "empty" in f.reason_md
