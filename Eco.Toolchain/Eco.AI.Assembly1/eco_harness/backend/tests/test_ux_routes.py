"""Tests for the UI/UX route and naming changes (docs/UI_PRD.md phase 2–3).

Covers: the proj- project ref naming (_project_entry / display-name heal),
chat- → proj- path remap, per-project session/trace counts, the
activity-based project sort order behind GET /api/projects, and the
Settings → RAG "Update Index from marketplace" job endpoints.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.server import (
    _context_window,
    _harness_project_ref,
    _is_harness_project_path,
    _project_entry,
    _remap_to_output_root,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Server app pointed at a throwaway output root."""
    monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
    monkeypatch.setenv("HARNESS_TRACES_DIR", str(tmp_path / "traces"))
    from backend import server
    with TestClient(server.app) as test_client:
        yield test_client


def _write_registry(output_root: Path, projects: list[dict], sessions: list[dict]):
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / ".harness-registry.json").write_text(
        json.dumps({"projects": projects, "sessions": sessions}),
        encoding="utf-8",
    )


def _harness_dir(tmp_path: Path, name: str) -> Path:
    d = tmp_path / "output" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


SESSION = {
    "id": "abc12345",
    "thread_id": "abc12345-rest",
    "project_path": "/tmp/proj",
    "title": "Build a calculator",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:10:00+00:00",
    "status": "success",
}


# ── proj- naming (I-13) ──────────────────────────────────────────────────────

class TestHarnessProjectRef:
    def test_harness_path_detected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
        d = _harness_dir(tmp_path, "chat-ea0e66f1")
        assert _is_harness_project_path(d) is True
        d2 = _harness_dir(tmp_path, "proj-7f3a1b2c")
        assert _is_harness_project_path(d2) is True

    def test_user_path_not_harness(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
        (tmp_path / "proj").mkdir()
        assert _is_harness_project_path(tmp_path / "proj") is False
        # Nested or non-conforming names under the output root are user dirs.
        nested = tmp_path / "output" / "sub" / "chat-ea0e66f1"
        nested.mkdir(parents=True)
        assert _is_harness_project_path(nested) is False

    def test_entry_uses_proj_ref_for_harness_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
        d = _harness_dir(tmp_path, "proj-ea0e66f1")
        entry = _project_entry(d)
        assert entry["id"].startswith("proj-")
        assert entry["id"] == entry["name"]
        assert len(entry["id"]) == len("proj-") + 4

    def test_entry_keeps_sha1_for_user_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
        d = tmp_path / "proj"
        d.mkdir()
        entry = _project_entry(d)
        assert entry["name"] == "proj"
        assert not entry["id"].startswith("proj-")

    def test_ref_is_stable(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
        d = _harness_dir(tmp_path, "proj-ea0e66f1")
        assert _harness_project_ref(d) == _harness_project_ref(d)


# ── chat- → proj- remap (I-13) ───────────────────────────────────────────────

class TestChatToProjRemap:
    def test_remaps_to_proj_sibling(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
        legacy = _harness_dir(tmp_path, "chat-ea0e66f1")
        new = _harness_dir(tmp_path, "proj-ea0e66f1")
        assert _remap_to_output_root(legacy) == new.resolve()

    def test_keeps_chat_when_no_sibling(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
        legacy = _harness_dir(tmp_path, "chat-ea0e66f1")
        assert _remap_to_output_root(legacy) == legacy.resolve()

    def test_ignores_non_harness_names(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
        d = _harness_dir(tmp_path, "chat-notahex8")
        assert _remap_to_output_root(d) == d.resolve()


# ── /api/projects extras (I-8 / I-10 / I-13) ────────────────────────────────

class TestListProjectsExtras:
    def test_counts_and_activity_sort(self, client, tmp_path):
        dir_a = tmp_path / "projA"
        dir_b = tmp_path / "projB"
        dir_a.mkdir()
        dir_b.mkdir()
        # Project B was added later, but project A's latest session is more
        # recent — activity sort must put A first (UI-10).
        project_a = {
            "id": "oldproject01", "path": str(dir_a), "name": "projA",
            "added_at": "2026-01-01T00:00:00+00:00",
        }
        project_b = {
            "id": "newproject01", "path": str(dir_b), "name": "projB",
            "added_at": "2026-02-01T00:00:00+00:00",
        }
        sessions = [
            {**SESSION, "id": "aaaa1111", "thread_id": "aaaa1111-rest",
             "project_path": str(dir_a), "updated_at": "2026-01-05T00:00:00+00:00"},
            {**SESSION, "id": "bbbb2222", "thread_id": "bbbb2222-rest",
             "project_path": str(dir_b), "updated_at": "2026-01-03T00:00:00+00:00"},
        ]
        _write_registry(tmp_path / "output", [project_a, project_b], sessions)
        res = client.get("/api/projects")
        assert res.status_code == 200
        projects = res.json()["projects"]
        assert [p["id"] for p in projects] == ["oldproject01", "newproject01"]
        first = projects[0]
        assert first["session_count"] == 1
        # No trace dirs exist on disk → trace counts are 0 but present.
        assert first["trace_count"] == 0
        assert first["sessions"][0]["id"] == "aaaa1111"

    def test_trace_count_sums_session_files(self, client, tmp_path):
        user_dir = tmp_path / "projB"
        user_dir.mkdir()
        project = {
            "id": "tracecnt0001", "path": str(user_dir), "name": "projB",
            "added_at": "2026-01-01T00:00:00+00:00",
        }
        sessions = [
            {**SESSION, "id": f"sess{i:04d}", "thread_id": f"sess{i:04d}-r",
             "project_path": str(user_dir)}
            for i in range(2)
        ]
        _write_registry(tmp_path / "output", [project], sessions)
        for i in range(2):
            folder = tmp_path / "traces" / f"ses-sess{i:04d}"
            folder.mkdir(parents=True)
            for n in range(i + 1):
                (folder / f"{n:03d}-planner.json").write_text("{}", encoding="utf-8")
        res = client.get("/api/projects")
        projects = res.json()["projects"]
        assert projects[0]["trace_count"] == 1 + 2

    def test_legacy_chat_dir_gets_proj_display_name(self, client, tmp_path):
        d = _harness_dir(tmp_path, "chat-ea0e66f1")
        project = {
            "id": "sha1id123456", "path": str(d), "name": "chat-ea0e66f1",
            "added_at": "2026-01-01T00:00:00+00:00",
        }
        _write_registry(tmp_path / "output", [project], [])
        res = client.get("/api/projects")
        card = res.json()["projects"][0]
        # Display name is healed to the proj- ref; the stored id/path are
        # untouched so DELETE/export lookups keep working.
        assert card["name"].startswith("proj-")
        assert len(card["name"]) == len("proj-") + 4
        assert card["id"] == "sha1id123456"


# ── context window helper (I-6) ──────────────────────────────────────────────

class TestContextWindow:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("HARNESS_CONTEXT_WINDOW", raising=False)
        assert _context_window() == 131072

    def test_override(self, monkeypatch):
        monkeypatch.setenv("HARNESS_CONTEXT_WINDOW", "200000")
        assert _context_window() == 200000

    def test_garbage_falls_back(self, monkeypatch):
        monkeypatch.setenv("HARNESS_CONTEXT_WINDOW", "not-a-number")
        assert _context_window() == 131072


# ── RAG "Update Index from marketplace" job (Settings → RAG) ────────────────

class TestRagUpdateIndex:
    def _reset_job(self):
        from backend import server
        with server._rag_update_lock:
            server._rag_update_job.clear()
            server._rag_update_job.update({"state": "idle"})

    def teardown_method(self):
        self._reset_job()

    def test_status_idle_by_default(self, client):
        self._reset_job()
        res = client.get("/rag/update-index/status")
        assert res.status_code == 200
        assert res.json()["state"] == "idle"

    def test_409_while_running(self, client):
        from backend import server
        with server._rag_update_lock:
            server._rag_update_job.clear()
            server._rag_update_job.update({
                "state": "running", "step": "fetch_marketplace", "log_tail": [],
            })
        res = client.post("/rag/update-index")
        assert res.status_code == 409

    def test_start_runs_background_job(self, client, monkeypatch):
        from backend import server
        started = threading.Event()
        release = threading.Event()

        def fake_runner():
            started.set()
            release.wait(timeout=10)
            server._rag_update_finish("success")

        monkeypatch.setattr(server, "_run_rag_update", fake_runner)
        self._reset_job()
        res = client.post("/rag/update-index")
        assert res.status_code == 200
        assert res.json() == {"status": "started"}
        assert started.wait(timeout=5)
        running = client.get("/rag/update-index/status").json()
        assert running["state"] in ("running", "success")
        release.set()
        deadline = time.time() + 5
        state = ""
        while time.time() < deadline:
            state = client.get("/rag/update-index/status").json()["state"]
            if state == "success":
                break
            time.sleep(0.05)
        assert state == "success"

    def test_runner_reports_step_failure_with_log_tail(self, tmp_path, monkeypatch):
        from backend import server
        ok_script = tmp_path / "ok_step.py"
        ok_script.write_text("print('step ok')\n", encoding="utf-8")
        bad_script = tmp_path / "bad_step.py"
        bad_script.write_text(
            "import sys\nprint('boom')\nsys.exit(3)\n", encoding="utf-8",
        )
        monkeypatch.setattr(server, "_RAG_UPDATE_STEPS", [
            ("ok", str(ok_script)),
            ("bad", str(bad_script)),
        ])
        self._reset_job()
        server._run_rag_update()
        with server._rag_update_lock:
            job = {**server._rag_update_job}
        assert job["state"] == "failed"
        assert job["step"] == "bad"
        assert "exited with code 3" in (job["error"] or "")
        assert any("step ok" in line for line in job["log_tail"])

        # A later passing run flips the job back to success.
        monkeypatch.setattr(server, "_RAG_UPDATE_STEPS", [("ok", str(ok_script))])
        server._run_rag_update()
        with server._rag_update_lock:
            job = {**server._rag_update_job}
        assert job["state"] == "success"
        assert job["error"] is None

    def test_runner_fails_on_missing_script(self, monkeypatch):
        from backend import server
        monkeypatch.setattr(server, "_RAG_UPDATE_STEPS", [
            ("missing", "scripts/definitely_not_here.py"),
        ])
        self._reset_job()
        server._run_rag_update()
        with server._rag_update_lock:
            job = {**server._rag_update_job}
        assert job["state"] == "failed"
        assert "Script not found" in (job["error"] or "")


# ── Marketplace token + last-updated (Settings → RAG) ───────────────────────

class TestRagToken:
    def test_get_reports_configured_state(self, client, monkeypatch):
        monkeypatch.delenv("ECO_API_TOKEN", raising=False)
        res = client.get("/rag/token")
        assert res.json() == {"configured": False, "masked": None}
        monkeypatch.setenv("ECO_API_TOKEN", "supersecrettoken123")
        res = client.get("/rag/token")
        body = res.json()
        assert body["configured"] is True
        # Masked preview only — the token itself must never be echoed back.
        assert "supersecrettoken123" not in json.dumps(body)
        assert body["masked"].endswith("123")

    def test_put_sets_env_and_persists(self, client, tmp_path, monkeypatch):
        from backend import server
        monkeypatch.setattr(server, "_env_file_path", lambda: tmp_path / ".env")
        monkeypatch.delenv("ECO_API_TOKEN", raising=False)
        res = client.put("/rag/token", json={"token": "tok_abc12345"})
        assert res.status_code == 200
        assert res.json()["configured"] is True
        import os
        assert os.environ["ECO_API_TOKEN"] == "tok_abc12345"
        assert (tmp_path / ".env").read_text() == "ECO_API_TOKEN=tok_abc12345\n"

        # A second PUT replaces the persisted line instead of duplicating it.
        res = client.put("/rag/token", json={"token": "tok_replaced99"})
        assert res.status_code == 200
        assert (tmp_path / ".env").read_text() == "ECO_API_TOKEN=tok_replaced99\n"

        # Empty token clears both the process env and the .env line.
        res = client.put("/rag/token", json={"token": "  "})
        assert res.json() == {"configured": False, "masked": None}
        import os
        assert "ECO_API_TOKEN" not in os.environ
        assert (tmp_path / ".env").read_text() == ""

    def test_upsert_env_file_preserves_other_lines(self, tmp_path, monkeypatch):
        from backend import server
        env_path = tmp_path / ".env"
        env_path.write_text(
            "HARNESS_CONTEXT_WINDOW=131072\nECO_API_TOKEN=old\n# comment\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(server, "_env_file_path", lambda: env_path)
        server._upsert_env_file("ECO_API_TOKEN", "new")
        text = env_path.read_text()
        assert "HARNESS_CONTEXT_WINDOW=131072" in text
        assert "# comment" in text
        assert "old" not in text
        assert "ECO_API_TOKEN=new" in text


class TestRagStatusLastUpdated:
    def test_last_updated_from_index_mtime(self, client, tmp_path, monkeypatch):
        import sqlite3
        import os
        from backend import server
        index = tmp_path / "marketplace_index.sqlite"
        monkeypatch.setenv("MARKETPLACE_INDEX_PATH", str(index))
        monkeypatch.setattr(server, "_fetch_summary_path", lambda: tmp_path / "no-summary.json")
        output = tmp_path / "output"
        output.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(index)
        connection.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO chunks DEFAULT VALUES")
        connection.commit()
        connection.close()
        os.utime(index, (1_700_000_000, 1_700_000_000))
        res = client.get("/rag/status")
        body = res.json()
        assert body["available"] is True
        assert body["chunks"] == 1
        assert body["last_updated"] is not None
        assert body["last_updated"].startswith("2023-11-14T22:13:20")
