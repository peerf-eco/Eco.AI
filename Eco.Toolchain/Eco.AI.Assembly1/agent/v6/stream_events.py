"""Bridge between EcoAgent on_event hook and LangGraph custom stream channel.

Each V6 node calls `make_on_event("<node-name>", writer)` where writer comes
from `langgraph.config.get_stream_writer()`. The writer emits dicts on the
`custom` channel; the backend WebSocket forwards them verbatim to the
frontend as `node_event` messages.

Truncation: tool args can be large (file paths, plan_md). We cap each arg's
serialized form at ~2 KiB so a single tool call doesn't dominate the WS budget.
"""
from __future__ import annotations
import json
from typing import Callable, Optional
from agent.v6.eco_agent import EcoAgentEvent, EventType


_ARG_CAP = 2000  # chars after json.dumps; soft cap (no streaming-back loop)


def _truncate_value(v):
    if isinstance(v, str) and len(v) > _ARG_CAP:
        return v[:_ARG_CAP] + f"...<+{len(v) - _ARG_CAP} chars>"
    if isinstance(v, (list, tuple)):
        return [_truncate_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _truncate_value(x) for k, x in v.items()}
    return v


def _safe_args(args: dict) -> dict:
    """Run per-value truncation; fall back to a sentinel if the payload is
    still too big or not JSON-serializable.

    Two sentinel shapes the frontend may receive:
      {"__truncated__": True,    "keys": [...]} — too large even after truncation
      {"__unserializable__": True,"keys": [...]} — TypeError/ValueError on json.dumps
    """
    truncated = {k: _truncate_value(v) for k, v in args.items()}
    try:
        if len(json.dumps(truncated)) > _ARG_CAP * 2:
            return {"__truncated__": True, "keys": list(args.keys())}
    except (TypeError, ValueError):
        return {"__unserializable__": True, "keys": list(args.keys())}
    return truncated


def event_to_dict(node: str, ev: EcoAgentEvent) -> dict:
    """Convert an EcoAgentEvent to a JSON-safe dict for the custom channel.

    Three keys in `ev.data` can carry LLM-controlled payloads and are routed
    through the truncation/safety filter:
      - `args` — input to a tool call (TOOL_START)
      - `payload` — output of a stop tool call (DONE), e.g. submit_plan's plan_md
      - `details` — opaque tool result details (TOOL_END), often a dict
    """
    data = dict(ev.data)
    if "args" in data and isinstance(data["args"], dict):
        data["args"] = _safe_args(data["args"])
    if "payload" in data and isinstance(data["payload"], dict):
        data["payload"] = _safe_args(data["payload"])
    if "details" in data and not isinstance(data.get("details"), (dict, type(None))):
        data["details"] = str(data["details"])
    return {
        "type": "node_event",
        "node": node,
        "event": ev.type.value,
        "data": data,
    }


def make_on_event(node: str, writer: Optional[Callable[[dict], None]]) -> Callable[[EcoAgentEvent], None]:
    """Build an on_event callback that pushes node events to `writer`.

    If `writer` is None (e.g. running EcoAgent outside a LangGraph context),
    events are silently dropped. Exceptions from `writer` are swallowed —
    losing a telemetry frame must never abort an agent run.
    """
    def _on(ev: EcoAgentEvent) -> None:
        if writer is None:
            return
        try:
            writer(event_to_dict(node, ev))
        except Exception:
            return
    return _on
