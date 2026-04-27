def test_create_chat_agent_v5_returns_callable_graph():
    from agent.chat_agent import create_chat_agent_v5
    from langchain_core.runnables import Runnable
    from langchain_core.messages import AIMessage

    class _LLMStub(Runnable):
        def bind_tools(self, tools, **kw): return self
        def invoke(self, input, config=None, **kw): return AIMessage(content="hi")

    g = create_chat_agent_v5(_LLMStub())
    assert hasattr(g, "stream")


def test_chat_agent_v5_initial_state_seeds_planning_phase():
    from agent.chat_agent import make_chat_agent_initial_state
    state = make_chat_agent_initial_state("build calc")
    assert state["phase"] == "planning"
    assert state["planner_messages"][0]["content"] == "build calc"
