"""Tests for escalate_node — interrupt with diagnostics."""
from langgraph.graph import StateGraph
from agent.v6.nodes.escalate import escalate_node
from agent.v6.state import V6State, make_initial_v6_state


def test_escalate_raises_interrupt_with_diagnostics():
    """escalate_node calls interrupt() which stores payload in __interrupt__."""
    # Build a minimal graph with escalate as entry
    builder = StateGraph(V6State)
    builder.add_node("escalate", escalate_node)
    builder.set_entry_point("escalate")
    graph = builder.compile()

    state = make_initial_v6_state("x")
    state["retry_count"] = 3
    state["last_failure_origin"] = "tester"
    state["build_log"] = "## BUILD ERR"
    state["tester_report_md"] = "## TEST ERR"
    state["plan_md"] = "# Plan"
    state["coder_summary_md"] = "summary"

    # Invoke the graph — interrupt() adds __interrupt__ to returned state
    result = graph.invoke(state)

    # Verify __interrupt__ is present
    assert "__interrupt__" in result
    assert len(result["__interrupt__"]) == 1

    # Extract payload from Interrupt object
    interrupt_obj = result["__interrupt__"][0]
    payload = interrupt_obj.value

    assert payload["failure_origin"] == "tester"
    assert payload["retry_count"] == 3
    assert payload["build_log"] == "## BUILD ERR"
    assert payload["tester_report_md"] == "## TEST ERR"
