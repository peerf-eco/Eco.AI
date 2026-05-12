from pydantic import BaseModel
import pytest
from agent.v6.eco_agent import (
    EcoAgent, EcoTool, ToolResult, EcoAgentEvent, EventType,
)
from agent.v6.tests.conftest import (
    ScriptedChatModel, ai_text, ai_tool,
)


# ── shared tool fixtures ───────────────────────────────────────────────────
class _ReadArgs(BaseModel):
    path: str


class _SubmitArgs(BaseModel):
    summary: str


def _read_ok(a: _ReadArgs) -> ToolResult:
    return ToolResult(content=f"file:{a.path}", details={"size": 10})


def _read_boom(_a: _ReadArgs) -> ToolResult:
    raise RuntimeError("disk on fire")


def _make_agent(llm, tools, stop="submit", max_iters=10, **kw):
    return EcoAgent(
        llm=llm,
        system_prompt="you are a test agent",
        tools=tools,
        stop_tool=stop,
        max_iters=max_iters,
        **kw,
    )


READ_TOOL = EcoTool("read", "read a file", _ReadArgs, _read_ok)
BOOM_TOOL = EcoTool("read", "read a file", _ReadArgs, _read_boom)
SUBMIT_TOOL = EcoTool(
    "submit", "stop", _SubmitArgs,
    lambda a: ToolResult(content="ok"),  # never executed (it's the stop tool)
)


# ── 1. happy: read → submit → done ─────────────────────────────────────────
def test_happy_path_reaches_stop_tool():
    llm = ScriptedChatModel(script=[
        ai_tool("read", {"path": "a.c"}, "c1"),
        ai_tool("submit", {"summary": "all good"}, "c2"),
    ])
    agent = _make_agent(llm, [READ_TOOL, SUBMIT_TOOL])
    r = agent.run("go")
    assert r.status == "done"
    assert r.stop_tool_name == "submit"
    assert r.stop_payload == {"summary": "all good"}


# ── 2. model returns plain text → no_tool_call ─────────────────────────────
def test_no_tool_call():
    llm = ScriptedChatModel(script=[ai_text("I'm done")])
    agent = _make_agent(llm, [READ_TOOL, SUBMIT_TOOL])
    r = agent.run("go")
    assert r.status == "no_tool_call"


# ── 3. infinite loop hits max_iters ────────────────────────────────────────
def test_max_iters_exhausted():
    llm = ScriptedChatModel(script=[
        ai_tool("read", {"path": "x"}, f"c{i}") for i in range(10)
    ])
    agent = _make_agent(llm, [READ_TOOL, SUBMIT_TOOL], max_iters=3)
    r = agent.run("go")
    assert r.status == "max_iters"


# ── 4. tool exception → ToolMessage(error), loop continues to stop ─────────
def test_tool_exception_recoverable():
    llm = ScriptedChatModel(script=[
        ai_tool("read", {"path": "x"}, "c1"),
        ai_tool("submit", {"summary": "recovered"}, "c2"),
    ])
    agent = _make_agent(llm, [BOOM_TOOL, SUBMIT_TOOL])
    r = agent.run("go")
    assert r.status == "done"
    # The history should contain the error message
    contents = [m.content for m in r.history if hasattr(m, "tool_call_id")]
    assert any("disk on fire" in c for c in contents)


# ── 5. invalid args → ToolMessage(error), loop continues ───────────────────
def test_args_validation_error_recoverable():
    llm = ScriptedChatModel(script=[
        ai_tool("read", {"wrong_field": "x"}, "c1"),
        ai_tool("submit", {"summary": "got args right next time"}, "c2"),
    ])
    agent = _make_agent(llm, [READ_TOOL, SUBMIT_TOOL])
    r = agent.run("go")
    assert r.status == "done"


# ── 6. before_tool_call blocks one call, loop continues ────────────────────
def test_before_tool_call_blocks():
    llm = ScriptedChatModel(script=[
        ai_tool("read", {"path": "secrets.txt"}, "c1"),
        ai_tool("submit", {"summary": "blocked then done"}, "c2"),
    ])
    def gate(name, args):
        if name == "read" and args.path == "secrets.txt":
            return {"block": True, "reason": "not allowed"}
        return None
    agent = _make_agent(llm, [READ_TOOL, SUBMIT_TOOL], before_tool_call=gate)
    r = agent.run("go")
    assert r.status == "done"
    contents = [m.content for m in r.history if hasattr(m, "tool_call_id")]
    assert any("not allowed" in c for c in contents)


# ── 7. prepare_arguments shim runs before validation ───────────────────────
def test_prepare_arguments_shim():
    llm = ScriptedChatModel(script=[
        ai_tool("read", {"file_path": "x.c"}, "c1"),       # wrong key
        ai_tool("submit", {"summary": "shimmed"}, "c2"),
    ])
    def shim(name, raw):
        if name == "read" and "file_path" in raw:
            return {"path": raw["file_path"]}
        return raw
    agent = _make_agent(llm, [READ_TOOL, SUBMIT_TOOL], prepare_arguments=shim)
    r = agent.run("go")
    assert r.status == "done"


# ── 8. on_event fires in order ─────────────────────────────────────────────
def test_on_event_ordering():
    llm = ScriptedChatModel(script=[
        ai_tool("read", {"path": "x"}, "c1"),
        ai_tool("submit", {"summary": "s"}, "c2"),
    ])
    seen: list[EcoAgentEvent] = []
    agent = _make_agent(llm, [READ_TOOL, SUBMIT_TOOL], on_event=seen.append)
    agent.run("go")
    types = [e.type for e in seen]
    assert types[0] == EventType.START
    assert EventType.ITERATION in types
    assert EventType.TOOL_START in types
    assert EventType.TOOL_END in types
    assert types[-1] == EventType.DONE


# ── 9. multiple stop tools — which one fired is recorded ───────────────────
def test_multi_stop_tools():
    class PassArgs(BaseModel):
        why: str
    class FailArgs(BaseModel):
        why: str
    PASS_TOOL = EcoTool("rep_pass", "pass", PassArgs, lambda a: ToolResult(content="x"))
    FAIL_TOOL = EcoTool("rep_fail", "fail", FailArgs, lambda a: ToolResult(content="x"))
    llm = ScriptedChatModel(script=[
        ai_tool("rep_fail", {"why": "it crashed"}, "c1"),
    ])
    agent = _make_agent(llm, [PASS_TOOL, FAIL_TOOL], stop=["rep_pass", "rep_fail"])
    r = agent.run("go")
    assert r.status == "done"
    assert r.stop_tool_name == "rep_fail"
    assert r.stop_payload == {"why": "it crashed"}
