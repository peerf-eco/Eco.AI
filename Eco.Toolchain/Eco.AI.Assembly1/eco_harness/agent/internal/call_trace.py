"""Per-call LLM trace persistence for the EcoAgent path.

Unlike ``agent/internal/trace.py`` — which serializes a whole internal node attempt and
depends on a live LangGraph context — this module writes ONE file per LLM
request/response pair, with zero langchain/langgraph imports.

Design (per user request 2026-05-21):
  - every API request/response is persisted, so a trace exists even after a
    single LLM call and even if the agent loop never terminates;
  - each conversation gets its own folder (``traces/chat-<id>/``); files inside
    are numbered globally so architect/coder/tester calls interleave in
    chronological order.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _dump(obj: Any) -> Any:
    """Best-effort JSON-able representation of a pydantic model (or anything)."""
    if obj is None:
        return None
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        try:
            return model_dump(mode="json")
        except Exception:  # noqa: BLE001 — fall back to plain dump
            try:
                return model_dump()
            except Exception:  # noqa: BLE001
                pass
    return obj


def write_call_trace(
    *,
    trace_dir: Path,
    label: str,
    call_no: int,
    iteration: int,
    model_id: str,
    request_context: Any,
    response: Any = None,
    error: str = "",
) -> Optional[Path]:
    """Persist one LLM request/response to ``trace_dir/NNN-<label>.json``.

    NNN is a per-folder sequence (count of existing ``*.json`` + 1). Within a
    conversation the agents run strictly sequentially, so this is race-free.

    NEVER raises — trace persistence is observability and must not break the
    agent loop. Returns the written path, or ``None`` on failure.
    """
    try:
        trace_dir.mkdir(parents=True, exist_ok=True)
        seq = len(list(trace_dir.glob("*.json"))) + 1

        ctx = request_context
        request = {
            "systemPrompt": getattr(ctx, "systemPrompt", None),
            "messages": [_dump(m) for m in (getattr(ctx, "messages", None) or [])],
            # Tool JSON-schemas are static boilerplate — keep traces readable
            # by recording only name + description.
            "tools": [
                {
                    "name": getattr(t, "name", ""),
                    "description": getattr(t, "description", ""),
                }
                for t in (getattr(ctx, "tools", None) or [])
            ],
        }

        payload = {
            "meta": {
                "label": label,
                "seq": seq,
                "call_no": call_no,
                "iteration": iteration,
                "model": model_id,
                "stop_reason": getattr(response, "stopReason", "") or "",
                "error": error or (getattr(response, "errorMessage", None) or ""),
                "ts": datetime.now(timezone.utc).isoformat(),
            },
            "request": request,
            "response": _dump(response),
        }

        final = trace_dir / f"{seq:03d}-{label}.json"
        tmp = trace_dir / f"{seq:03d}-{label}.json.tmp"
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        os.replace(tmp, final)
        return final
    except Exception as e:  # never let trace persistence break the agent loop
        logger.warning(
            "write_call_trace failed (label=%s): %s", label, e, exc_info=True
        )
        return None

