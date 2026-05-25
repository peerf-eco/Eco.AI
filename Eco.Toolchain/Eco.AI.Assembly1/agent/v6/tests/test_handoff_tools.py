"""Tests for the handoff tool factory."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.v6.tools.handoff import (
    make_handoff_tool,
    make_fail_tool,
    message_from_payload,
)


# ── 1. make_handoff_tool: shape + single str arg ───────────────────────────
def test_handoff_tool_basic_shape():
    t = make_handoff_tool("to_coder", "Hand off control to the coder agent.")
    assert t.name == "to_coder"
    assert "coder" in t.description
    # args_schema must accept {message: <str>} and reject everything else
    parsed = t.args_schema.model_validate({"message": "do the thing"})
    assert parsed.message == "do the thing"


def test_handoff_tool_requires_message():
    t = make_handoff_tool("to_x", "x")
    with pytest.raises(ValidationError):
        t.args_schema.model_validate({})


def test_handoff_tool_rejects_extra_fields_silently():
    # pydantic by default ignores unknown fields — we tolerate that since
    # the model is responsible for matching the schema. Just verify message
    # still parses when extras are present.
    t = make_handoff_tool("to_x", "x")
    parsed = t.args_schema.model_validate({"message": "m", "destination": "x"})
    assert parsed.message == "m"


def test_handoff_tool_execute_is_noop():
    # Execute should never be invoked by EcoAgent for stop-tools — but if
    # someone calls it directly, it must return a safe ToolResult.
    t = make_handoff_tool("to_x", "x")
    res = t.execute(t.args_schema(message="anything"))
    assert "stop tool" in res.content.lower()


# ── 2. make_fail_tool: single str `reason` arg ─────────────────────────────
def test_fail_tool_default_name_and_schema():
    t = make_fail_tool()
    assert t.name == "fail"
    parsed = t.args_schema.model_validate({"reason": "compilation never converges"})
    assert parsed.reason == "compilation never converges"


def test_fail_tool_requires_reason():
    t = make_fail_tool()
    with pytest.raises(ValidationError):
        t.args_schema.model_validate({})


def test_fail_tool_custom_name():
    t = make_fail_tool(name="abort", description="Abort the run.")
    assert t.name == "abort"
    assert "abort" in t.description.lower()


# ── 3. message_from_payload: tolerates both shapes ─────────────────────────
def test_extract_message_field():
    assert message_from_payload({"message": "hello"}) == "hello"


def test_extract_reason_field():
    assert message_from_payload({"reason": "broken"}) == "broken"


def test_extract_message_wins_over_reason():
    # If both are present (shouldn't happen for well-formed tools) prefer message.
    assert message_from_payload({"message": "m", "reason": "r"}) == "m"


def test_extract_returns_empty_when_neither():
    assert message_from_payload({}) == ""
    assert message_from_payload({"unrelated": "x"}) == ""


def test_explicit_empty_message_does_not_fall_through_to_reason():
    # If the caller deliberately passed message="" we must NOT silently
    # use `reason` instead — that would hide a programming bug.
    assert message_from_payload({"message": "", "reason": "r"}) == ""
