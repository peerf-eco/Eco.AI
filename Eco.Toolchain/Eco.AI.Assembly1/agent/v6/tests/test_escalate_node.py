"""Tests for escalate_node — interrupt with diagnostics."""
from langgraph.graph import StateGraph
from agent.v6.nodes.escalate import escalate_node
from agent.v6.state import V6State, make_initial_v6_state


def test_escalate_raises_interrupt_with_diagnostics():
    """escalate_node calls interrupt() which stores payload in __interrupt__."""
    builder = StateGraph(V6State)
    builder.add_node("escalate", escalate_node)
    builder.set_entry_point("escalate")
    graph = builder.compile()

    state = make_initial_v6_state("x")
    state["retry_count"] = 3
    state["max_retries"] = 3
    state["last_failure_origin"] = "tester"
    state["last_status"] = "tester_retry_limit"
    state["build_log"] = "## BUILD ERR"
    state["tester_report_md"] = "## TEST ERR"
    state["plan_md"] = "# Plan"
    state["coder_summary_md"] = "summary"

    result = graph.invoke(state)

    assert "__interrupt__" in result
    assert len(result["__interrupt__"]) == 1
    interrupt_obj = result["__interrupt__"][0]
    payload = interrupt_obj.value

    assert payload["failure_origin"] == "tester"
    assert payload["retry_count"] == 3
    assert payload["build_log"] == "## BUILD ERR"
    assert payload["tester_report_md"] == "## TEST ERR"
    assert payload["reason"] == "tester_retry_limit"


def test_escalate_reason_for_builder_retry_limit():
    """Builder failure with retry_count >= max_retries → reason='builder_retry_limit'."""
    builder = StateGraph(V6State)
    builder.add_node("escalate", escalate_node)
    builder.set_entry_point("escalate")
    graph = builder.compile()

    state = make_initial_v6_state("x")
    state["retry_count"] = 3
    state["max_retries"] = 3
    state["last_failure_origin"] = "builder"
    state["last_status"] = "builder_retry_limit"

    result = graph.invoke(state)
    payload = result["__interrupt__"][0].value
    assert payload["reason"] == "builder_retry_limit"


def test_escalate_reason_for_planner_max_iters():
    """Planner failure → reason='planner_max_iters' (NOT retry_limit)."""
    builder = StateGraph(V6State)
    builder.add_node("escalate", escalate_node)
    builder.set_entry_point("escalate")
    graph = builder.compile()

    state = make_initial_v6_state("x")
    state["retry_count"] = 0
    state["last_failure_origin"] = "planner"
    state["last_status"] = "planner_max_iters"

    result = graph.invoke(state)
    payload = result["__interrupt__"][0].value
    assert payload["reason"] == "planner_max_iters"


def test_escalate_reason_for_setup_no_tool_call():
    builder = StateGraph(V6State)
    builder.add_node("escalate", escalate_node)
    builder.set_entry_point("escalate")
    graph = builder.compile()

    state = make_initial_v6_state("x")
    state["last_failure_origin"] = "setup"
    state["last_status"] = "setup_no_tool_call"

    result = graph.invoke(state)
    payload = result["__interrupt__"][0].value
    assert payload["reason"] == "setup_no_tool_call"


def test_derive_reason_prefers_last_status():
    from agent.v6.nodes.escalate import _derive_reason
    state = make_initial_v6_state("x")
    state["last_status"] = "builder_retry_limit"
    state["last_failure_origin"] = "builder"
    assert _derive_reason(state) == "builder_retry_limit"


def test_derive_reason_falls_back_to_origin_unknown():
    from agent.v6.nodes.escalate import _derive_reason
    state = make_initial_v6_state("x")
    state["last_status"] = ""
    state["last_failure_origin"] = "builder"
    assert _derive_reason(state) == "builder_unknown"


def test_derive_reason_falls_back_to_unknown_when_nothing_set():
    from agent.v6.nodes.escalate import _derive_reason
    state = make_initial_v6_state("x")
    state["last_status"] = ""
    state["last_failure_origin"] = ""
    assert _derive_reason(state) == "unknown"


def test_derive_reason_strips_whitespace_in_last_status():
    """Defensive: accidental whitespace from string interpolation must not produce
    a stray reason like ' builder_retry_limit '."""
    from agent.v6.nodes.escalate import _derive_reason
    state = make_initial_v6_state("x")
    state["last_status"] = "  builder_retry_limit  "
    assert _derive_reason(state) == "builder_retry_limit"
