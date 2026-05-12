"""Tests for plan_gate_node — interrupt wrapper."""
from langgraph.graph import StateGraph

from agent.v6.nodes.plan_gate import plan_gate_node
from agent.v6.state import V6State, make_initial_v6_state


def test_plan_gate_raises_interrupt_with_plan_payload():
    """plan_gate calls interrupt() which stores payload in __interrupt__."""
    # Build a minimal graph with plan_gate as entry
    builder = StateGraph(V6State)
    builder.add_node("plan_gate", plan_gate_node)
    builder.set_entry_point("plan_gate")
    graph = builder.compile()

    state = make_initial_v6_state("x")
    state["plan_md"] = "# Plan"
    state["components"] = [{"cid": "A" * 32, "version": "1.0.1.2", "name": "X"}]

    # Invoke the graph — interrupt() adds __interrupt__ to returned state
    result = graph.invoke(state)

    # Verify __interrupt__ is present
    assert "__interrupt__" in result
    assert len(result["__interrupt__"]) == 1

    # Extract payload from Interrupt object
    interrupt_obj = result["__interrupt__"][0]
    payload = interrupt_obj.value

    assert payload["plan_md"] == "# Plan"
    assert payload["components"][0]["cid"] == "A" * 32
