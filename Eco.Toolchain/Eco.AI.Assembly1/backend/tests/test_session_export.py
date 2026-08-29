"""Tests for backend/session_export.py and the export / panel endpoints.

Covers: prompt marker splitting, trace turn grouping, stop-tool answer
extraction, metadata-only fallbacks, JSONL shape, TXT rendering, and the
FastAPI DELETE guards (404/409) + export happy paths against tmp_path
registries/traces wired through HARNESS_OUTPUT_ROOT / HARNESS_TRACES_DIR.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.session_export as se


# ── Trace fixtures ───────────────────────────────────────────────────────────

WORKSPACE = (
    "=== Workspace ===\n"
    "You are running in two locations:\n"
    "  project_dir (read-write):\n"
    "    /tmp/proj\n"
    "the result is already in your tool-result history above.\n"
    "\n"
)

ATTACHED = (
    "=== Attached files (user-provided session context) ===\n"
    "The user explicitly attached these files. They are available to you:\n"
    "- notes.txt [text, 5 bytes] — inline:\n"
    "hello\n"
    "- pic.png [image] — visual reference at .eco-attachments/pic.png\n"
    "\n"
)


def seed(user_req: str) -> str:
    return WORKSPACE + ATTACHED + user_req


def write_trace(
    folder: Path,
    seq: int,
    user_content,
    blocks: list[dict],
    label: str = "planner",
) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    messages = [{"role": "user", "content": user_content, "timestamp": 0}]
    payload = {
        "meta": {"label": label, "seq": seq},
        "request": {"systemPrompt": "sys", "messages": messages},
        "response": {
            "role": "assistant",
            "content": blocks,
            "stopReason": "toolUse" if any(b.get("type") == "toolCall" for b in blocks) else "stop",
        },
    }
    path = folder / f"{seq:03d}-{label}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def think_block(text: str) -> dict:
    return {"type": "thinking", "thinking": text}


def tool_block(name: str, args: dict) -> dict:
    return {"type": "toolCall", "id": f"c-{name}", "name": name, "arguments": args}


SESSION = {
    "id": "abc12345",
    "thread_id": "abc12345-rest",
    "project_path": "/tmp/proj",
    "title": "Build a calculator",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:10:00+00:00",
    "status": "success",
}

PROJECT = {"id": "proj1234abcd", "path": "/tmp/proj", "name": "proj", "added_at": "2026-01-01T00:00:00+00:00"}


# ── split_prompt ─────────────────────────────────────────────────────────────

class TestSplitPrompt:
    def test_no_markers_whole_text_is_question(self):
        q, c = se.split_prompt("What is ACOM?")
        assert q == "What is ACOM?"
        assert c == ""

    def test_workspace_and_attached_stripped(self):
        q, c = se.split_prompt(seed("Build me a calculator"))
        assert q == "Build me a calculator"
        assert "notes.txt" in c
        assert "pic.png" in c
        assert "Workspace" not in c
        assert "Attached files" not in c.split("\n")[0]

    def test_workspace_only(self):
        q, c = se.split_prompt(WORKSPACE + "just answer this")
        assert q == "just answer this"
        assert c == ""

    def test_attached_only_plain_chat(self):
        q, c = se.split_prompt(ATTACHED + "explain the bus")
        assert q == "explain the bus"
        assert "notes.txt" in c

    def test_multiline_question_preserved(self):
        req = "line one\n\nline two"
        q, _ = se.split_prompt(seed(req))
        assert q == req

    def test_context_header_line_stripped(self):
        _, c = se.split_prompt(ATTACHED + "go")
        assert not c.startswith("=== Attached files")


# ── session_turns ────────────────────────────────────────────────────────────

class TestSessionTurns:
    def test_missing_dir_yields_zero_turns(self, tmp_path):
        assert se.session_turns(SESSION, tmp_path / "traces") == []

    def test_malformed_files_skipped(self, tmp_path):
        traces = tmp_path / "traces"
        folder = traces / f"chat-{SESSION['id']}"
        folder.mkdir(parents=True)
        (folder / "001-broken.json").write_text("{not json", encoding="utf-8")
        assert se.session_turns(SESSION, traces) == []

    def test_turn_splitting_on_seed_change(self, tmp_path):
        traces = tmp_path / "traces"
        folder = traces / f"chat-{SESSION['id']}"
        # Turn 1: two responses sharing one seed; turn 2: new seed.
        write_trace(folder, 1, seed("task one"), [think_block("hmm"), text_block("working")])
        write_trace(folder, 2, seed("task one"), [tool_block("to_coder", {"message": "done one"})])
        write_trace(folder, 3, seed("task two"), [text_block("answer two")])

        turns = se.session_turns(SESSION, traces)
        assert len(turns) == 2
        assert turns[0]["question"] == "task one"
        assert turns[0]["turn_index"] == 0
        assert turns[1]["question"] == "task two"
        assert turns[1]["turn_index"] == 1

    def test_reasoning_chain_concatenated_in_order(self, tmp_path):
        folder = tmp_path / "traces" / f"chat-{SESSION['id']}"
        write_trace(folder, 1, seed("t"), [think_block("first thought")])
        write_trace(folder, 2, seed("t"), [think_block("second thought"), text_block("x")])
        turns = se.session_turns(SESSION, tmp_path / "traces")
        assert turns[0]["reasoning_chain"] == "first thought\n\nsecond thought"

    def test_stop_tool_message_preferred(self, tmp_path):
        folder = tmp_path / "traces" / f"chat-{SESSION['id']}"
        write_trace(folder, 1, seed("t"), [
            text_block("intermediate chatter"),
            tool_block("to_coder", {"message": "handoff plan body"}),
        ])
        turns = se.session_turns(SESSION, tmp_path / "traces")
        assert turns[0]["final_answer"] == "handoff plan body"

    def test_fail_reason_recovered(self, tmp_path):
        folder = tmp_path / "traces" / f"chat-{SESSION['id']}"
        write_trace(folder, 1, seed("t"), [
            tool_block("fail", {"reason": "missing SDK"}),
        ])
        turns = se.session_turns(SESSION, tmp_path / "traces")
        assert turns[0]["final_answer"] == "missing SDK"

    def test_text_fallback_when_no_stop_args(self, tmp_path):
        folder = tmp_path / "traces" / f"chat-{SESSION['id']}"
        write_trace(folder, 1, seed("t"), [
            text_block("earlier"),
            tool_block("read_file", {"path": "a.c"}),
        ])
        write_trace(folder, 2, seed("t"), [text_block("final visible answer")])
        turns = se.session_turns(SESSION, tmp_path / "traces")
        assert turns[0]["final_answer"] == "final visible answer"


# ── Path safety ──────────────────────────────────────────────────────────────

class TestPathSafety:
    def test_session_turns_refuses_folder_escaping_traces_root(self, tmp_path):
        """A registry id carrying ../ must never read outside the traces root."""
        outside = tmp_path / "evil"
        write_trace(outside, 1, seed("secret"), [text_block("leak")])
        escaping = {**SESSION, "id": "../../evil"}
        assert se.session_turns(escaping, tmp_path / "traces") == []

    def test_session_turns_refuses_separator_id(self, tmp_path):
        outside = tmp_path / "traces" / "chat-ok"
        write_trace(outside, 1, seed("secret"), [text_block("leak")])
        sneaky = {**SESSION, "id": "x/../chat-ok"}
        assert se.session_turns(sneaky, tmp_path / "traces") == []

    def test_export_of_escaping_session_is_metadata_only(self, client, tmp_path):
        """Endpoint level: an injected id exports as metadata-only, no leak."""
        outside = tmp_path / "evil"
        write_trace(outside, 1, seed("secret"), [text_block("leak")])
        _write_registry(tmp_path / "output", PROJECT,
                        [{**SESSION, "id": "../../evil"}])
        res = client.get(f"/api/projects/{PROJECT['id']}/export?format=jsonl")
        assert res.status_code == 200
        row = json.loads(res.text.splitlines()[0])
        assert row["turn_index"] is None
        assert "secret" not in res.text and "leak" not in res.text

    def test_safe_id_folds_path_characters(self):
        from backend.server import _safe_id
        for raw in ("../../etc", "..\\..\\win", "a/b/c", "", "...", "//"):
            folded = _safe_id(raw)
            assert "/" not in folded and "\\" not in folded and "." not in folded
        assert _safe_id("") == "x"
        assert _safe_id("abc-123_ABC") == "abc-123_ABC"


# ── build_project_export / JSONL / TXT ──────────────────────────────────────

class TestExportAssembly:
    def _export(self, tmp_path, with_traces=True):
        traces = tmp_path / "traces"
        if with_traces:
            folder = traces / f"chat-{SESSION['id']}"
            write_trace(folder, 1, seed("task"), [
                think_block("thought"),
                tool_block("to_coder", {"message": "handoff"}),
            ])
        return se.build_project_export(PROJECT, [SESSION], traces)

    def test_source_traces(self, tmp_path):
        export = self._export(tmp_path)
        assert export["project"]["id"] == PROJECT["id"]
        assert export["sessions"][0]["source"] == "traces"
        assert len(export["sessions"][0]["turns"]) == 1

    def test_metadata_only_fallback(self, tmp_path):
        export = self._export(tmp_path, with_traces=False)
        s = export["sessions"][0]
        assert s["source"] == "metadata_only"
        assert s["turns"] == []
        assert s["title"] == SESSION["title"]

    def test_jsonl_shape(self, tmp_path):
        export = self._export(tmp_path)
        lines = list(se.iter_project_jsonl(export))
        assert len(lines) == 1
        row = json.loads(lines[0])
        for key in ("project_id", "project_name", "session_id", "thread_id",
                    "session_title", "session_status", "created_at",
                    "updated_at", "turn_index", "question",
                    "additional_context", "reasoning_chain", "final_answer"):
            assert key in row
        assert row["project_id"] == PROJECT["id"]
        assert row["turn_index"] == 0
        assert row["question"] == "task"
        assert row["reasoning_chain"] == "thought"
        assert row["final_answer"] == "handoff"

    def test_jsonl_metadata_only_line(self, tmp_path):
        export = self._export(tmp_path, with_traces=False)
        lines = list(se.iter_project_jsonl(export))
        assert len(lines) == 1
        row = json.loads(lines[0])
        assert row["turn_index"] is None
        assert row["question"] == ""
        assert row["session_title"] == SESSION["title"]

    def test_txt_rendering_labels(self, tmp_path):
        export = self._export(tmp_path)
        txt = se.render_export_text(export)
        assert f"===== SESSION {SESSION['id']} [success] =====" in txt
        assert "Title: Build a calculator" in txt
        for label in ("QUESTION:", "ADDITIONAL CONTEXT:",
                      "MODEL REASONING CHAIN:", "FINAL ANSWER:"):
            assert label in txt
        assert "handoff" in txt

    def test_txt_empty_project_is_header_only(self, tmp_path):
        export = se.build_project_export(PROJECT, [], tmp_path / "traces")
        txt = se.render_export_text(export)
        assert "Project: proj" in txt
        assert "SESSION" not in txt.replace("EcoOS harness session export", "")

    def test_safe_export_name(self):
        assert se.safe_export_name("My Project v2") == "My-Project-v2"
        assert se.safe_export_name("Проект/1") == "1"
        assert se.safe_export_name("---") == "project"


# ── FastAPI endpoints ────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Server app pointed at a throwaway output root."""
    monkeypatch.setenv("HARNESS_OUTPUT_ROOT", str(tmp_path / "output"))
    monkeypatch.setenv("HARNESS_TRACES_DIR", str(tmp_path / "traces"))
    from backend import server
    with TestClient(server.app) as test_client:
        yield test_client


def _write_registry(output_root: Path, project: dict, sessions: list[dict]):
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / ".harness-registry.json").write_text(
        json.dumps({"projects": [project], "sessions": sessions}),
        encoding="utf-8",
    )


class TestDeleteProjectEndpoint:
    def _registry(self, tmp_path, status="success"):
        sessions = [{**SESSION, "status": status}]
        _write_registry(tmp_path / "output", PROJECT, sessions)

    def test_404_unknown(self, client, tmp_path):
        res = client.delete("/api/projects/nope")
        assert res.status_code == 404

    def test_remove_keeps_sessions_and_traces(self, client, tmp_path):
        self._registry(tmp_path)
        folder = tmp_path / "traces" / f"chat-{SESSION['id']}"
        write_trace(folder, 1, seed("t"), [text_block("keepme")])
        res = client.delete(f"/api/projects/{PROJECT['id']}")
        assert res.status_code == 200
        assert res.json() == {"status": "ok", "removed": PROJECT["id"]}
        registry = json.loads(
            (tmp_path / "output" / ".harness-registry.json").read_text()
        )
        assert registry["projects"] == []
        assert [s["id"] for s in registry["sessions"]] == [SESSION["id"]]
        assert (folder / "001-planner.json").is_file()

    def test_409_while_running(self, client, tmp_path):
        self._registry(tmp_path, status="running")
        res = client.delete(f"/api/projects/{PROJECT['id']}")
        assert res.status_code == 409
        registry = json.loads(
            (tmp_path / "output" / ".harness-registry.json").read_text()
        )
        assert len(registry["projects"]) == 1

    def test_list_projects_whitelist_only(self, client, tmp_path):
        stray = {**SESSION, "id": "zzzz9999", "project_path": "/tmp/not-whitelisted"}
        _write_registry(tmp_path / "output", PROJECT, [SESSION, stray])
        res = client.get("/api/projects")
        assert res.status_code == 200
        projects = res.json()["projects"]
        assert [p["id"] for p in projects] == [PROJECT["id"]]
        assert [s["id"] for s in projects[0]["sessions"]] == [SESSION["id"]]


class TestListProjectsEnrichesSessions:
    """Regression: /api/projects must include trace-bookkeeping fields on each
    session so the left panel can render the ses- chip + the copy-to-clipboard
    button WITHOUT a per-session /api/sessions/{id}/trace round trip.

    Bug history (minimal-first-cut follow-up): the original /api/projects
    response only had the raw session records from the registry, so
    `session.trace_dir` was always undefined on the panel and the
    copy-to-clipboard button was hidden behind `session.trace_dir && ...`
    → invisible to the user.
    """

    def test_sessions_carry_trace_meta(self, client, tmp_path):
        _write_registry(
            tmp_path / "output",
            PROJECT,
            [{**SESSION, "id": "abc12345"}],
        )
        folder = tmp_path / "traces" / "chat-abc12345"
        write_trace(folder, 1, seed("x"), [text_block("ok")])
        res = client.get("/api/projects")
        assert res.status_code == 200
        body = res.json()
        assert len(body["projects"]) == 1
        sessions = body["projects"][0]["sessions"]
        assert len(sessions) == 1
        s = sessions[0]
        # All four bookkeeping fields must be present in the response.
        assert s["trace_dir"].endswith("ses-abc12345")  # canonical new name
        assert s["trace_call_count"] == 1
        assert s["trace_last_file"].endswith("001-planner.json")
        # trace_last_error is None when the trace has no error.
        assert s["trace_last_error"] in (None, "")

    def test_sessions_without_trace_get_zero_count(self, client, tmp_path):
        """A session that has never produced a trace still appears in the
        response (the panel cannot tell the difference at render time) but
        trace_call_count is zero and trace_last_file is null.

        Uses a unique id ("ghost…") that no other test in this class uses,
        so a leftover chat-abc12345 dir from test_sessions_carry_trace_meta
        does not bleed into this one.
        """
        # Override BOTH id and thread_id so the canonical trace dir
        # (which uses thread_id[:8]) matches the new id and does not
        # pick up the leftover chat-abc12345 dir from the previous test.
        _write_registry(
            tmp_path / "output",
            PROJECT,
            [{**SESSION, "id": "ghost9999", "thread_id": "ghost9999-z"}],
        )
        res = client.get("/api/projects")
        assert res.status_code == 200
        sessions = res.json()["projects"][0]["sessions"]
        s = sessions[0]
        assert s["trace_dir"].endswith("ses-ghost999")
        assert s["trace_call_count"] == 0
        assert s["trace_last_file"] is None

    def test_legacy_chat_dir_still_surfaces_count(self, client, tmp_path):
        """Backward compat: a session with only the legacy chat-<id> dir is
        still discoverable (the panel must not show zero)."""
        _write_registry(
            tmp_path / "output",
            PROJECT,
            # 7-char id and 7-char thread_id; the legacy chat-<id> dir
            # matches the canonical ses-<thread_id[:8]> dir suffix.
            [{**SESSION, "id": "old7777", "thread_id": "old7777"}],
        )
        folder = tmp_path / "traces" / "chat-old7777"
        write_trace(folder, 1, seed("x"), [text_block("hi")])
        res = client.get("/api/projects")
        sessions = res.json()["projects"][0]["sessions"]
        s = sessions[0]
        assert s["trace_dir"].endswith("ses-old7777")
        assert s["trace_call_count"] == 1
        assert s["trace_last_file"].endswith("001-planner.json")


class TestSessionTraceEndpoint:
    """GET /api/sessions/{id}/trace — minimal-first-cut trace-bookkeeping.

    The endpoint returns the trace dir, the last-file summary, and a per-file
    list. Tests cover the happy path (existing chat-* legacy trace dir), the
    new ses-* path, and the unknown-session 404.
    """

    def _registry(self, tmp_path, session_id="abc12345"):
        _write_registry(
            tmp_path / "output",
            PROJECT,
            [{**SESSION, "id": session_id}],
        )

    def test_404_unknown(self, client):
        res = client.get("/api/sessions/nope/trace")
        assert res.status_code == 404

    def test_400_invalid_id(self, client):
        res = client.get("/api/sessions/has%20space/trace")
        assert res.status_code == 400

    def test_session_with_no_trace_folder(self, client, tmp_path):
        self._registry(tmp_path)
        res = client.get(f"/api/sessions/{SESSION['id']}/trace")
        assert res.status_code == 200
        body = res.json()
        assert body["trace_dir"].endswith(f"ses-{SESSION['id']}")
        assert body["trace_last_file"] is None
        assert body["trace_call_count"] == 0

    def test_session_with_legacy_chat_dir(self, client, tmp_path):
        """The minimal-first-cut endpoint must also read legacy chat-* dirs
        (otherwise all pre-existing sessions look empty after the rename)."""
        self._registry(tmp_path)
        folder = tmp_path / "traces" / f"chat-{SESSION['id']}"
        write_trace(folder, 1, seed("x"), [text_block("hi")])
        res = client.get(f"/api/sessions/{SESSION['id']}/trace")
        assert res.status_code == 200
        body = res.json()
        # Helper scans BOTH the new ses-* dir and the legacy chat-* dir.
        assert body["trace_call_count"] == 1
        assert body["trace_last_file"].endswith("001-planner.json")

    def test_messages_endpoint_surfaces_trace_meta(self, client, tmp_path):
        self._registry(tmp_path)
        folder = tmp_path / "traces" / f"chat-{SESSION['id']}"
        write_trace(folder, 1, seed("x"), [text_block("ok")])
        res = client.get(f"/api/sessions/{SESSION['id']}/messages")
        assert res.status_code == 200
        body = res.json()
        assert "trace_dir" in body["session"]
        assert body["session"]["trace_call_count"] == 1
        assert body["session"]["trace_last_file"].endswith("001-planner.json")


class TestExportEndpoints:
    def _setup(self, client, tmp_path):
        _write_registry(tmp_path / "output", PROJECT, [SESSION])
        folder = tmp_path / "traces" / f"chat-{SESSION['id']}"
        write_trace(folder, 1, seed("build it"), [
            think_block("step by step"),
            text_block("partial"),
            tool_block("to_coder", {"message": "the handoff"}),
        ])

    def test_404_unknown_project(self, client):
        assert client.get("/api/projects/nope/export").status_code == 404

    def test_400_bad_format(self, client):
        assert client.get("/api/projects/x/export?format=xml").status_code == 400

    def test_per_project_jsonl(self, client, tmp_path):
        self._setup(client, tmp_path)
        res = client.get(f"/api/projects/{PROJECT['id']}/export?format=jsonl")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("application/x-ndjson")
        assert "attachment" in res.headers["content-disposition"]
        assert "proj-sessions.jsonl" in res.headers["content-disposition"]
        rows = [json.loads(line) for line in res.text.splitlines() if line]
        assert len(rows) == 1
        assert rows[0]["question"] == "build it"
        assert rows[0]["final_answer"] == "the handoff"

    def test_per_project_txt(self, client, tmp_path):
        self._setup(client, tmp_path)
        res = client.get(f"/api/projects/{PROJECT['id']}/export?format=txt")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/plain")
        assert "FINAL ANSWER:" in res.text
        assert "the handoff" in res.text

    def test_export_all_combines_projects(self, client, tmp_path):
        self._setup(client, tmp_path)
        second = {**PROJECT, "id": "second0000003", "path": "/tmp/proj2",
                  "name": "proj two"}
        second_session = {**SESSION, "id": "def67890", "thread_id": "def-t",
                          "project_path": "/tmp/proj2"}
        registry_path = tmp_path / "output" / ".harness-registry.json"
        registry = json.loads(registry_path.read_text())
        registry["projects"].append(second)
        registry["sessions"].append(second_session)
        registry_path.write_text(json.dumps(registry))

        res = client.get("/api/export/all?format=jsonl")
        assert res.status_code == 200
        rows = [json.loads(line) for line in res.text.splitlines() if line]
        assert [r["project_id"] for r in rows] == [PROJECT["id"], second["id"]]

        res_txt = client.get("/api/export/all?format=txt")
        assert res_txt.status_code == 200
        assert res_txt.text.count("===== SESSION") >= 2
