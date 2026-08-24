"""Session export: turn-level records from chat traces (fine-tuning data).

Pure, stdlib-only functions that reconstruct Q/A training pairs from the
per-call LLM traces the harness writes under ``traces/chat-<id8>/``
(``agent/internal/call_trace.py``):

  - every conversation turn shares the SAME seeded last-user message
    (``workspace_header + attached_block + user_req``, plain chat:
    ``attached_block + user_req``); consecutive trace files with identical
    seeds belong to one turn;
  - each trace file's ``response`` holds exactly one assistant response,
    mixing ``text`` / ``thinking`` / ``toolCall`` content blocks (pi_ai dump
    shapes).

Export shape (per project):
    {"project": {id, name, path}, "exported_at",
     "sessions": [{id, thread_id, project_path, title, created_at,
                   updated_at, status, source: "traces"|"metadata_only",
                   turns: [{turn_index, question, additional_context,
                            reasoning_chain, final_answer}]}]}

Prompt splitting rules (see :func:`split_prompt`): the two stable markers
(``=== Workspace ===``, ``=== Attached files … ===``) delimit boilerplate.
Known limitation: an inline attachment snippet containing a blank line
followed by non-entry text truncates ``additional_context`` there — rare,
and the question itself is never lost.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

WORKSPACE_MARKER = "=== Workspace ==="
ATTACHED_FILES_MARKER = "=== Attached files (user-provided session context) ==="
# Fixed closing line of _workspace_header() — marks the end of the workspace
# section when no attached-files block follows it.
WORKSPACE_CLOSING = "the result is already in your tool-result history above."

# toolCall argument keys carrying a stop/handoff message (to_coder, fail, …).
STOP_TOOL_ANSWER_KEYS = ("message", "reason", "summary", "report")

SESSION_FIELDS = (
    "id", "thread_id", "project_path", "title",
    "created_at", "updated_at", "status",
)


def default_traces_root() -> Path:
    return Path(os.getenv("HARNESS_TRACES_DIR", "traces"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Prompt splitting ─────────────────────────────────────────────────────────

def split_prompt(text: str) -> tuple[str, str]:
    """Split a seeded turn prompt into ``(question, additional_context)``.

    Cuts on the two stable markers:
      * the leading ``=== Workspace ===`` section runs to its fixed closing
        line, or to the attached-files marker when one follows;
      * the attached-files block body becomes ``additional_context`` (the
        marker header line is stripped);
      * text with neither marker is returned untouched as the question.
    """
    ws_idx = text.find(WORKSPACE_MARKER)
    if ws_idx == -1 and text.find(ATTACHED_FILES_MARKER) == -1:
        return text.strip(), ""

    parts: list[str] = []
    cursor = 0
    if ws_idx != -1:
        parts.append(text[:ws_idx])
        att_idx = text.find(ATTACHED_FILES_MARKER, ws_idx)
        if att_idx != -1:
            cursor = att_idx
        else:
            closing = text.find(WORKSPACE_CLOSING, ws_idx)
            cursor = closing + len(WORKSPACE_CLOSING) if closing != -1 else len(text)

    context = ""
    att_idx = text.find(ATTACHED_FILES_MARKER, cursor)
    if att_idx != -1:
        parts.append(text[cursor:att_idx])
        block_len, context = _scan_attached_block(text[att_idx:])
        cursor = att_idx + block_len
    parts.append(text[cursor:])
    return "\n".join(parts).strip(), context.strip()


def _scan_attached_block(body: str) -> tuple[int, str]:
    """Scan ``body`` from the attached-files marker onward.

    Returns ``(block_length, context_body)``. The block spans the marker
    line, the intro line, and every ``- ``-entry including its continuation
    lines. A blank line ends the block unless another entry follows it —
    inline snippets may contain blank lines, but a blank line followed by
    ordinary prose is treated as the start of the user's request.
    """
    lines = body.split("\n")
    end_line = len(lines)
    seen_entry = False
    pending_gap = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if seen_entry:
                pending_gap = True
            continue
        if stripped.startswith("- "):
            seen_entry = True
            pending_gap = False
        elif seen_entry and pending_gap:
            end_line = i
            break
    block_lines = lines[:end_line]
    context = "\n".join(block_lines[1:]) if len(block_lines) > 1 else ""
    block_len = sum(len(line) + 1 for line in block_lines)
    return block_len, context


# ── Trace parsing ────────────────────────────────────────────────────────────

def _trace_files(folder: Path) -> list[Path]:
    """Trace JSON files sorted by their numeric NNN- prefix."""
    try:
        files = [p for p in folder.glob("*.json") if p.is_file()]
    except OSError:
        return []

    def order(p: Path) -> tuple[int, str]:
        m = re.match(r"(\d+)", p.name)
        return (int(m.group(1)) if m else 10**9, p.name)

    return sorted(files, key=order)


def _load_trace(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _last_user_text(request: Any) -> str | None:
    """Text of the request's last user message (the turn's shared seed).
    Returns None when no usable user message exists (malformed trace)."""
    messages = request.get("messages") if isinstance(request, dict) else None
    if not isinstance(messages, list):
        return None
    for msg in reversed(messages):
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                block.get("text") for block in content
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            ]
            return "\n".join(part for part in parts if part)
    return None


def _response_blocks(response: Any) -> list[dict]:
    content = response.get("content") if isinstance(response, dict) else None
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def _extract_turn_fields(responses: list[list[dict]]) -> tuple[str, str]:
    """(reasoning_chain, final_answer) across one turn's responses, in order."""
    thinking_parts: list[str] = []
    tool_calls: list[dict] = []
    texts: list[str] = []
    for blocks in responses:
        for block in blocks:
            btype = block.get("type")
            if btype == "thinking":
                value = block.get("thinking")
                if isinstance(value, str) and value.strip():
                    thinking_parts.append(value)
            elif btype == "toolCall":
                tool_calls.append(block)
            elif btype == "text":
                value = block.get("text")
                if isinstance(value, str):
                    texts.append(value)

    reasoning_chain = "\n\n".join(thinking_parts)
    final_answer = ""
    for call in reversed(tool_calls):
        args = call.get("arguments")
        if not isinstance(args, dict):
            continue
        for key in STOP_TOOL_ANSWER_KEYS:
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                final_answer = value
                break
        if final_answer:
            break
    if not final_answer:
        final_answer = next((t for t in reversed(texts) if t.strip()), "")
    return reasoning_chain, final_answer


def session_turns(session: dict, traces_root: Path) -> list[dict]:
    """Rebuild the session's turns from its trace folder.

    Consecutive files sharing the same last-user-message seed form one turn.
    Malformed files are skipped; a missing/empty folder yields zero turns."""
    # ``session["id"]`` derives from the caller-supplied thread_id; two guards
    # keep a crafted value from steering reads outside ``chat-<safe-id>``:
    # 1) the id itself must be path-safe ([A-Za-z0-9_-], no "." or separators
    #    — so no ".." segments and no cross-session "a/../b" aliases);
    # 2) the resolved folder must stay inside the resolved traces root
    #    (covers symlinked folders too).
    raw_id = str(session.get("id", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]+", raw_id):
        return []
    folder = (Path(traces_root) / f"chat-{raw_id}").resolve()
    root = Path(traces_root).resolve()
    if not str(folder).startswith(str(root) + os.sep):
        return []
    acc: list[dict] = []
    current_seed: str | None = None
    for path in _trace_files(folder):
        payload = _load_trace(path)
        if payload is None:
            continue
        seed = _last_user_text(payload.get("request"))
        if seed is None:
            continue
        blocks = _response_blocks(payload.get("response"))
        if seed != current_seed:
            question, context = split_prompt(seed)
            current_seed = seed
            acc.append({
                "question": question,
                "additional_context": context,
                "responses": [blocks],
            })
        else:
            acc[-1]["responses"].append(blocks)

    turns: list[dict] = []
    for item in acc:
        reasoning_chain, final_answer = _extract_turn_fields(item.pop("responses"))
        turns.append({
            "turn_index": len(turns),
            "question": item["question"],
            "additional_context": item["additional_context"],
            "reasoning_chain": reasoning_chain,
            "final_answer": final_answer,
        })
    return turns


# ── Export assembly ──────────────────────────────────────────────────────────

def build_project_export(
    project: dict, sessions: list[dict], traces_root: Path,
) -> dict:
    """Assemble the export document for one whitelisted project."""
    root = Path(traces_root)
    exported_sessions = []
    for session in sessions:
        turns = session_turns(session, root)
        exported_sessions.append({
            **{field: session.get(field, "") for field in SESSION_FIELDS},
            "source": "traces" if turns else "metadata_only",
            "turns": turns,
        })
    return {
        "project": {
            "id": project.get("id", ""),
            "name": project.get("name", ""),
            "path": project.get("path", ""),
        },
        "exported_at": _now_iso(),
        "sessions": exported_sessions,
    }


def iter_project_jsonl(export: dict) -> Iterator[str]:
    """One JSON object per turn per line (JSONL). Sessions without usable
    traces emit a single metadata-only line with empty turn fields so legacy
    sessions are never silently dropped."""
    project = export.get("project") or {}
    base = {
        "project_id": project.get("id", ""),
        "project_name": project.get("name", ""),
    }
    for session in export.get("sessions") or []:
        row = {
            **base,
            "session_id": session.get("id", ""),
            "thread_id": session.get("thread_id", ""),
            "session_title": session.get("title", ""),
            "session_status": session.get("status", ""),
            "created_at": session.get("created_at", ""),
            "updated_at": session.get("updated_at", ""),
        }
        turns = session.get("turns") or []
        if not turns:
            yield json.dumps(
                {**row, "turn_index": None, "question": "",
                 "additional_context": "", "reasoning_chain": "",
                 "final_answer": ""},
                ensure_ascii=False,
            )
            continue
        for turn in turns:
            yield json.dumps(
                {**row,
                 "turn_index": turn.get("turn_index"),
                 "question": turn.get("question", ""),
                 "additional_context": turn.get("additional_context", ""),
                 "reasoning_chain": turn.get("reasoning_chain", ""),
                 "final_answer": turn.get("final_answer", "")},
                ensure_ascii=False,
            )


def render_export_text(export: dict) -> str:
    """Human-readable TXT rendering, one labeled block per turn."""
    project = export.get("project") or {}
    lines = [
        "EcoOS harness session export",
        f"Project: {project.get('name', '')} ({project.get('path', '')})",
        f"Exported: {export.get('exported_at', '')}",
        "",
    ]
    for index, session in enumerate(export.get("sessions") or []):
        if index:
            lines += ["=" * 48, ""]
        lines += [
            f"===== SESSION {session.get('id', '')} "
            f"[{session.get('status', '')}] =====",
            f"Title: {session.get('title', '')}",
            f"Created: {session.get('created_at', '')}  "
            f"Updated: {session.get('updated_at', '')}",
            "",
        ]
        turns = session.get("turns") or []
        if not turns:
            lines += ["(no exported turns — session metadata only)", ""]
            continue
        for turn in turns:
            lines += [
                f"--- TURN {(turn.get('turn_index') or 0) + 1} ---",
                "QUESTION:",
                turn.get("question", "") or "(empty)",
                "",
                "ADDITIONAL CONTEXT:",
                turn.get("additional_context", "") or "(none)",
                "",
                "MODEL REASONING CHAIN:",
                turn.get("reasoning_chain", "") or "(none)",
                "",
                "FINAL ANSWER:",
                turn.get("final_answer", "") or "(empty)",
                "",
            ]
    return "\n".join(lines)


# ── Download filename helpers ────────────────────────────────────────────────

_EXPORT_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_export_name(name: str, fallback: str = "project") -> str:
    """ASCII-safe download filename stem: non-ASCII/space chars fold to '-'."""
    folded = _EXPORT_NAME_RE.sub("-", name).strip("-.")
    return folded[:64] or fallback
