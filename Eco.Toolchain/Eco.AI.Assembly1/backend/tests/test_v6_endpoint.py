"""Integration tests for /ws/v6/chat WebSocket endpoint.

These tests use FastAPI's TestClient (synchronous WebSocket client) plus a
ScriptedChatModel + monkeypatched subprocess to drive the V6 graph end-to-end
through the WS endpoint. No network, no real LLM, no real build.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent.v6.tests.conftest import ScriptedChatModel, ai_tool

_CID = "A" * 32


def _drain_until(ws, predicate, *, limit: int = 50) -> list[dict]:
    """Read WS messages until predicate(msg) is true. Returns accumulated list."""
    seen: list[dict] = []
    for _ in range(limit):
        msg = ws.receive_json()
        seen.append(msg)
        if predicate(msg):
            return seen
    raise AssertionError(f"predicate never matched after {limit} msgs; got: {seen}")


@pytest.fixture
def v6_env(monkeypatch, tmp_path):
    """Wire up env vars + sdk_root structure for V6 endpoint."""
    sdk = tmp_path / "sdk"
    pkg = sdk / "Eco.X_DK_v.1.0.1.2" / "SharedFiles"
    pkg.mkdir(parents=True)
    (pkg / "IEcoX.h").write_text("/*x*/")

    proj = tmp_path / "proj"
    proj.mkdir()

    monkeypatch.setenv("V6_SDK_ROOT", str(sdk))
    monkeypatch.setenv("V6_CLI_PATH", str(tmp_path / "eco-cli.exe"))
    monkeypatch.setenv("V6_VCVARSALL", str(tmp_path / "vcvarsall.bat"))
    monkeypatch.setenv("V6_MAKE_EXE", str(tmp_path / "make.exe"))

    return {"sdk": sdk, "project_dir": proj}


@pytest.fixture
def mock_subprocess(monkeypatch, v6_env):
    """All subprocess.run calls succeed. Tester needs the artifact to exist."""
    artifact = v6_env["project_dir"] / "app.exe"
    artifact.write_text("")
    def fake_run(cmd, **kw):
        class R: returncode = 0; stdout = "ok"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    return artifact


def _happy_path_script(artifact: Path):
    return [
        ai_tool("submit_plan", {
            "project_name": "App",
            "plan_md": "# Plan\n## Acceptance criteria\n- runs",
            "components": [{"cid": _CID, "version": "1.0.1.2", "name": "Eco.X", "reason": "x"}],
            "acceptance_criteria": ["runs"],
        }, "p1"),
        ai_tool("ecoos_pull", {"cid": _CID, "version": "1.0.1.2"}, "s1"),
        ai_tool("mark_setup_done", {"downloaded_paths": []}, "s2"),
        ai_tool("write_file", {"path": "EcoMain.c", "content": "int main(){return 0;}"}, "c1"),
        ai_tool("mark_code_done", {"summary_md": "wrote main"}, "c2"),
        ai_tool("run_make", {}, "b1"),
        ai_tool("report_build_pass", {"artifact_path": str(artifact)}, "b2"),
        ai_tool("run_artifact", {"timeout_s": 5}, "t1"),
        ai_tool("report_test_pass", {"reason_md": "ok"}, "t2"),
    ]


def test_v6_happy_path_end_to_end(monkeypatch, v6_env, mock_subprocess):
    """User → plan_review → approve → setup → coder → builder → tester → success."""
    artifact = mock_subprocess
    script = _happy_path_script(artifact)

    monkeypatch.setattr("agent.main.get_llm", lambda: ScriptedChatModel(script=script))

    from backend.server import app
    with TestClient(app).websocket_connect("/ws/v6/chat") as ws:
        hb = ws.receive_json()
        assert hb["type"] == "heartbeat" and hb["version"] == "v6"

        ws.send_text(json.dumps({
            "type": "user_request",
            "user_request": "build x",
            "project_dir": str(v6_env["project_dir"]),
        }))

        # Expect at least one phase_change and a plan_review_required
        msgs = _drain_until(ws, lambda m: m.get("type") == "plan_review_required")
        types = [m["type"] for m in msgs]
        assert "phase_change" in types
        review = msgs[-1]
        assert "Acceptance" in review["plan_md"]
        assert len(review["components"]) == 1

        # Approve
        ws.send_text(json.dumps({"type": "plan_decision", "approved": True}))

        final = _drain_until(ws, lambda m: m.get("type") == "pipeline_done")[-1]
        assert final["status"] == "success"
        assert final["build_artifact"] == str(artifact)


def test_v6_user_rejects_plan(monkeypatch, v6_env, mock_subprocess):
    """User rejects plan → pipeline_done with user_aborted."""
    artifact = mock_subprocess
    script = [_happy_path_script(artifact)[0]]  # planner only

    monkeypatch.setattr("agent.main.get_llm", lambda: ScriptedChatModel(script=script))

    from backend.server import app
    with TestClient(app).websocket_connect("/ws/v6/chat") as ws:
        ws.receive_json()  # heartbeat
        ws.send_text(json.dumps({
            "type": "user_request",
            "user_request": "build x",
            "project_dir": str(v6_env["project_dir"]),
        }))
        _drain_until(ws, lambda m: m.get("type") == "plan_review_required")

        ws.send_text(json.dumps({"type": "plan_decision", "approved": False, "reason": "no"}))
        final = _drain_until(ws, lambda m: m.get("type") == "pipeline_done")[-1]
        assert final["status"] == "user_aborted"


def test_v6_invalid_json_does_not_crash(monkeypatch, v6_env):
    """Garbage payload → error event, connection survives."""
    monkeypatch.setattr("agent.main.get_llm", lambda: ScriptedChatModel(script=[]))

    from backend.server import app
    with TestClient(app).websocket_connect("/ws/v6/chat") as ws:
        ws.receive_json()  # heartbeat
        ws.send_text("not-json{{")
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "Invalid JSON" in err["content"]


def test_v6_planner_no_tool_call_emits_escalation_required(monkeypatch, v6_env):
    """Planner LLM emits a bare text reply (no tool_calls).

    EcoAgent's run() returns status=no_tool_call → planner_node sets
      phase="failed_escalated"
      last_failure_origin="planner"
      last_status="planner_no_tool_call"
    Graph routes to escalate_node, which surfaces the reason in the
    interrupt payload. Backend WS forwards it as `escalation_required`.
    """
    from agent.v6.tests.conftest import ScriptedChatModel, ai_text

    # Single bare-text reply — no tool_calls → status=no_tool_call.
    script = [ai_text("I have no idea what to plan, sorry.")]
    monkeypatch.setattr("agent.main.get_llm", lambda: ScriptedChatModel(script=script))

    from backend.server import app
    with TestClient(app).websocket_connect("/ws/v6/chat") as ws:
        hb = ws.receive_json()
        assert hb["type"] == "heartbeat"

        ws.send_text(json.dumps({
            "type": "user_request",
            "user_request": "build something",
            "project_dir": str(v6_env["project_dir"]),
        }))

        final = _drain_until(ws, lambda m: m.get("type") == "escalation_required", limit=100)[-1]
        assert final["reason"] == "planner_no_tool_call"
        assert final["failure_origin"] == "planner"
        # Defensive: retry_count must be 0 — planner failed on FIRST attempt,
        # not after exhausting a retry ceiling.
        assert final["retry_count"] == 0
