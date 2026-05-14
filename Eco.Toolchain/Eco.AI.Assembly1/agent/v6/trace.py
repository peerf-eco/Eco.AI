"""write_trace — persist a V6 node's full ReAct message history to disk.

Each call writes one node-attempt's EcoAgentResult.history to
traces/<thread_id>/NN-<node>.json. See
docs/superpowers/specs/2026-05-14-trace-persistence-design.md.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessage, messages_to_dict
from langgraph.config import get_config

from agent.v6.eco_agent import EcoAgentResult
from agent.v6.state import V6State

logger = logging.getLogger(__name__)


def write_trace(
    result: EcoAgentResult,
    *,
    node: str,
    state: V6State,
    traces_root: Path | None = None,
) -> Path | None:
    """Serialize one node-attempt's full message history to
    traces/<thread_id>/NN-<node>.json.

    Returns the written path, or None if writing was skipped (no graph
    context) or failed. NEVER raises — trace persistence is observability
    and must not break the pipeline.

    The seq counter (NN) is len(existing *.json) + 1. This is race-free
    because the V6 pipeline runs nodes strictly sequentially within a thread.
    """
    try:
        root = traces_root or Path(os.getenv("V6_TRACES_DIR", "traces"))

        try:
            cfg = get_config()
        except RuntimeError:
            # No active LangGraph context (e.g. node called from a unit test).
            logger.debug("write_trace: no graph context, skipping (node=%s)", node)
            return None

        raw_thread_id = (cfg.get("configurable") or {}).get("thread_id")
        if not raw_thread_id:
            logger.warning(
                "write_trace: no thread_id in config, skipping (node=%s)", node
            )
            return None

        # thread_id originates from a client-supplied WebSocket query param and
        # is used as a path component. Path().name strips directory separators;
        # the explicit check rejects the remaining traversal/degenerate tokens —
        # note Path("..").name returns ".." (truthy), so `or "unknown"` alone is
        # not enough. (Added in Task 1's security review cycle.)
        thread_id = Path(raw_thread_id).name
        if thread_id in ("", ".", ".."):
            thread_id = "unknown"

        thread_dir = root / thread_id
        thread_dir.mkdir(parents=True, exist_ok=True)

        seq = len(list(thread_dir.glob("*.json"))) + 1

        payload = {
            "meta": {
                "thread_id": thread_id,
                "node": node,
                "seq": seq,
                "phase": state.get("phase", ""),
                "status": result.status,
                "error": result.error,
                "retry_count": state.get("retry_count", 0),
                "last_failure_origin": state.get("last_failure_origin", ""),
                "iters": sum(
                    1 for m in result.history if isinstance(m, AIMessage)
                ),
                "ts_written": datetime.now(timezone.utc).isoformat(),
            },
            "messages": messages_to_dict(result.history),
        }

        final = thread_dir / f"{seq:02d}-{node}.json"
        tmp = thread_dir / f"{seq:02d}-{node}.json.tmp"
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        os.replace(tmp, final)
        return final
    except Exception as e:  # never let trace persistence break the pipeline
        logger.warning(
            "write_trace failed (node=%s): %s", node, e, exc_info=True
        )
        return None
