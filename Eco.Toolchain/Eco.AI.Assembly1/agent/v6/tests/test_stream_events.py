"""Tests for the node-level event writer wrapper."""
import json
from agent.v6.eco_agent import EcoAgentEvent, EventType
from agent.v6.stream_events import event_to_dict, make_on_event


def test_event_to_dict_serializable():
    ev = EcoAgentEvent(type=EventType.TOOL_START,
                       data={"name": "read_component", "args": {"name": "Eco.Math.C89"}})
    d = event_to_dict("planner", ev)
    assert d["type"] == "node_event"
    assert d["node"] == "planner"
    assert d["event"] == "tool_call_start"
    assert d["data"]["name"] == "read_component"
    # Round-trip JSON serialisable.
    assert json.loads(json.dumps(d)) == d


def test_event_to_dict_redacts_huge_args():
    """Tool args >2 KiB are truncated so the WS payload doesn't blow up."""
    big = "x" * 5000
    ev = EcoAgentEvent(type=EventType.TOOL_START, data={"name": "read_component", "args": {"name": big}})
    d = event_to_dict("planner", ev)
    serialized = json.dumps(d["data"]["args"])
    assert len(serialized) <= 2200  # 2 KiB cap + a little overhead


def test_make_on_event_forwards_to_writer():
    sink = []
    on_ev = make_on_event("planner", writer=sink.append)
    on_ev(EcoAgentEvent(type=EventType.ITERATION, data={"i": 3}))
    assert len(sink) == 1
    assert sink[0]["type"] == "node_event"
    assert sink[0]["event"] == "iteration"
    assert sink[0]["data"]["i"] == 3


def test_make_on_event_swallows_writer_exceptions():
    """A failing writer (e.g. WS gone) must NOT crash the agent loop."""
    def boom(_): raise RuntimeError("nope")
    on_ev = make_on_event("planner", writer=boom)
    on_ev(EcoAgentEvent(type=EventType.ITERATION, data={"i": 0}))  # must not raise


def test_make_on_event_no_writer_is_silent():
    """If writer is None (running outside a graph context), event is dropped."""
    on_ev = make_on_event("planner", writer=None)
    on_ev(EcoAgentEvent(type=EventType.ITERATION, data={"i": 0}))  # must not raise
