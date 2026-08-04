"""Handoff tool factory — destination encoded in tool NAME, payload is one str.

Three flavours of stop-tool an agent declares:
  - `to_<other_agent>(message)` — forward or backward handoff to a named peer
  - `done(message)`              — terminal success
  - `fail(reason)`               — terminal honest failure

The single `message`/`reason` field stays compatible with mid-tier providers
that break on nested pydantic schemas (Qwen/GLM/Sonnet). Destination is the
tool name, not an argument, so the orchestrator can route by `stop_tool_name`
without parsing payload structure.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from agent.internal.eco_agent import EcoTool, ToolResult


class _HandoffMessageArgs(BaseModel):
    message: str = Field(..., description="Markdown handoff context for the receiving agent")


class _HandoffReasonArgs(BaseModel):
    reason: str = Field(..., description="Plain-text explanation of the failure")


def make_handoff_tool(name: str, description: str) -> EcoTool:
    """Build a handoff stop-tool whose single arg is `message: str`.

    The execute callback is a no-op — EcoAgent short-circuits stop-tools
    before calling execute (`eco_agent.py:254-260`). Stub kept defensive.
    """
    return EcoTool(
        name=name,
        description=description,
        args_schema=_HandoffMessageArgs,
        execute=lambda _a: ToolResult(content="(stop tool — never executed)"),
    )


def make_fail_tool(name: str = "fail",
                    description: str = "Stop the run with an honest failure. Use when you cannot complete your task — do NOT fabricate success.") -> EcoTool:
    """Build a fail stop-tool whose single arg is `reason: str`."""
    return EcoTool(
        name=name,
        description=description,
        args_schema=_HandoffReasonArgs,
        execute=lambda _a: ToolResult(content="(stop tool — never executed)"),
    )


def message_from_payload(stop_payload: dict) -> str:
    """Extract the single text field a handoff/fail tool carries.

    Tolerates either `message` (handoff/done) or `reason` (fail). Uses
    `in` instead of `or`-chaining so an explicit empty `message=""` is
    returned as "" rather than falling through to `reason`.
    """
    if "message" in stop_payload:
        return stop_payload["message"]
    if "reason" in stop_payload:
        return stop_payload["reason"]
    return ""

