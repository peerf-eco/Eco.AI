"""Test V6 graph routing functions."""
import pytest
from langgraph.graph import END
from agent.v6.graph import (
    route_after_planner,
    route_after_plan_gate,
    route_after_setup,
    route_after_coder,
    route_after_builder,
    route_after_tester,
    route_after_escalate,
)


# ── planner / setup / coder failure → escalate ────────────────────────────
def test_route_after_planner_happy():
    assert route_after_planner({"phase": "awaiting_approval"}) == "plan_gate"


def test_route_after_planner_failure_goes_to_escalate():
    assert route_after_planner({"phase": "failed_escalated"}) == "escalate"


def test_route_after_setup_happy():
    assert route_after_setup({"phase": "coding"}) == "coder"


def test_route_after_setup_failure_goes_to_escalate():
    assert route_after_setup({"phase": "failed_escalated"}) == "escalate"


def test_route_after_coder_happy():
    assert route_after_coder({"phase": "building"}) == "builder"


def test_route_after_coder_failure_goes_to_escalate():
    assert route_after_coder({"phase": "failed_escalated"}) == "escalate"


def test_route_after_planner_unexpected_phase_raises():
    with pytest.raises(RuntimeError):
        route_after_planner({"phase": "coding"})


# ── original happy-path tests ─────────────────────────────────────────────


def test_route_after_plan_gate_setup():
    assert route_after_plan_gate({"phase": "setup"}) == "setup"


def test_route_after_plan_gate_aborted():
    assert route_after_plan_gate({"phase": "done"}) == END


def test_route_after_builder_testing():
    assert route_after_builder({"phase": "testing"}) == "tester"


def test_route_after_builder_coding():
    assert route_after_builder({"phase": "coding"}) == "coder"


def test_route_after_builder_escalate():
    assert route_after_builder({"phase": "failed_escalated"}) == "escalate"


def test_route_after_tester_done():
    assert route_after_tester({"phase": "done"}) == END


def test_route_after_tester_coding():
    assert route_after_tester({"phase": "coding"}) == "coder"


def test_route_after_escalate_continue():
    assert route_after_escalate({"last_status": "user_continue", "phase": "coding"}) == "coder"


def test_route_after_escalate_abort():
    assert route_after_escalate({"last_status": "user_aborted", "phase": "done"}) == END
