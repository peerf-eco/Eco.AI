def test_create_v5_graph_returns_compiled_graph():
    from agent.three_node_graph import create_v5_graph
    from langchain_core.runnables import Runnable
    from langchain_core.messages import AIMessage

    class _LLMStub(Runnable):
        def bind_tools(self, tools, **kw): return self
        def invoke(self, input, config=None, **kw): return AIMessage(content="ok")

    graph = create_v5_graph(_LLMStub())
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "stream")


def test_router_drives_phase_to_correct_node():
    from agent.three_node_graph import _route_by_phase

    assert _route_by_phase({"phase": "planning"}) == "planning"
    assert _route_by_phase({"phase": "coding"}) == "coding"
    assert _route_by_phase({"phase": "executing"}) == "executing"
    assert _route_by_phase({"phase": "done"}) == "done"


def test_route_after_planner_routes_to_coder_when_phase_changed():
    from agent.three_node_graph import _route_after_planner
    assert _route_after_planner({"phase": "coding"}) == "coding"
    assert _route_after_planner({"phase": "planning"}) == "wait_user"
