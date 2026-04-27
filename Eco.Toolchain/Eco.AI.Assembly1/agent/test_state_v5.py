from agent.state_v5 import AppState, make_initial_state


def test_initial_state_has_planning_phase():
    state = make_initial_state(user_request="build calc", max_iterations=5)
    assert state["phase"] == "planning"
    assert state["iteration"] == 0
    assert state["max_iterations"] == 5
    assert state["plan_md"] == ""
    assert state["coder_summary_md"] == ""
    assert state["feedback_md"] == ""
    assert state["executor_summary_md"] == ""
    assert state["last_status"] == ""


def test_initial_state_seeds_planner_with_user_request():
    state = make_initial_state(user_request="build calc")
    assert len(state["planner_messages"]) == 1
    msg = state["planner_messages"][0]
    role = msg.get("role") if isinstance(msg, dict) else msg.type
    content = msg.get("content") if isinstance(msg, dict) else msg.content
    assert role == "user"
    assert content == "build calc"


def test_initial_state_uses_default_max_iterations():
    state = make_initial_state(user_request="x")
    assert state["max_iterations"] == 5
