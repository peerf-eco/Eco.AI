from agent.v6.state import V6State, make_initial_v6_state


def test_initial_state_has_user_request():
    s = make_initial_v6_state("build a calculator")
    assert s["user_request"] == "build a calculator"
    assert s["phase"] == "planning"


def test_initial_state_defaults():
    s = make_initial_v6_state("x")
    assert s["plan_md"] == ""
    assert s["components"] == []
    assert s["downloaded_paths"] == []
    assert s["coder_summary_md"] == ""
    assert s["build_log"] == ""
    assert s["tester_report_md"] == ""
    assert s["retry_count"] == 0
    assert s["max_retries"] == 3
    assert s["last_failure_origin"] == ""
    assert s["last_status"] == ""


def test_initial_state_custom_max_retries():
    s = make_initial_v6_state("x", max_retries=5)
    assert s["max_retries"] == 5


def test_initial_state_planner_messages_seeded_with_user():
    s = make_initial_v6_state("hello")
    assert s["planner_messages"] == [{"role": "user", "content": "hello"}]
    assert s["setup_messages"] == []
    assert s["coder_messages"] == []
    assert s["builder_messages"] == []
    assert s["tester_messages"] == []
