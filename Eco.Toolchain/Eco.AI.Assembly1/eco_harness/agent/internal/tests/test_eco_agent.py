"""EcoAgent unit tests on the pi_ai-based core (no langchain)."""
from pydantic import BaseModel

from eco_harness.agent.pi_ai.types import ToolResultMessage
from eco_harness.agent.internal.eco_agent import (
    EcoAgent, EcoTool, EcoAgentEvent, EventType, ToolResult, _usage_data,
)
from eco_harness.agent.internal.tests.conftest import (
    ai_text, ai_tool, make_scripted_model_pair,
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


def _make_agent(script, tools, stop="submit", max_iters=10, **kw):
    model, stream_fn = make_scripted_model_pair(script)
    return EcoAgent(
        model=model,
        stream_fn=stream_fn,
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
    script = [
        ai_tool("read", {"path": "a.c"}, "c1"),
        ai_tool("submit", {"summary": "all good"}, "c2"),
    ]
    agent = _make_agent(script, [READ_TOOL, SUBMIT_TOOL])
    r = agent.run("go")
    assert r.status == "done"
    assert r.stop_tool_name == "submit"
    assert r.stop_payload == {"summary": "all good"}


# ── 2. model returns plain text → no_tool_call ─────────────────────────────
def test_no_tool_call():
    agent = _make_agent([ai_text("I'm done")], [READ_TOOL, SUBMIT_TOOL])
    r = agent.run("go")
    assert r.status == "no_tool_call"


# ── 3. infinite loop hits max_iters ────────────────────────────────────────
def test_max_iters_exhausted():
    script = [ai_tool("read", {"path": "x"}, f"c{i}") for i in range(10)]
    agent = _make_agent(script, [READ_TOOL, SUBMIT_TOOL], max_iters=3)
    r = agent.run("go")
    assert r.status == "max_iters"


# ── 4. tool exception → ToolResultMessage(error), loop continues to stop ───
def test_tool_exception_recoverable():
    script = [
        ai_tool("read", {"path": "x"}, "c1"),
        ai_tool("submit", {"summary": "recovered"}, "c2"),
    ]
    agent = _make_agent(script, [BOOM_TOOL, SUBMIT_TOOL])
    r = agent.run("go")
    assert r.status == "done"
    # The history should contain the error message in a ToolResultMessage
    tool_results = [m for m in r.history if isinstance(m, ToolResultMessage)]
    contents = [c.text for tr in tool_results for c in tr.content]
    assert any("disk on fire" in c for c in contents)


# ── 5. invalid args → ToolResultMessage(error), loop continues ─────────────
def test_args_validation_error_recoverable():
    script = [
        ai_tool("read", {"wrong_field": "x"}, "c1"),
        ai_tool("submit", {"summary": "got args right next time"}, "c2"),
    ]
    agent = _make_agent(script, [READ_TOOL, SUBMIT_TOOL])
    r = agent.run("go")
    assert r.status == "done"


# ── 6. before_tool_call blocks one call, loop continues ────────────────────
def test_before_tool_call_blocks():
    script = [
        ai_tool("read", {"path": "secrets.txt"}, "c1"),
        ai_tool("submit", {"summary": "blocked then done"}, "c2"),
    ]
    def gate(name, args):
        if name == "read" and args.path == "secrets.txt":
            return {"block": True, "reason": "not allowed"}
        return None
    agent = _make_agent(script, [READ_TOOL, SUBMIT_TOOL], before_tool_call=gate)
    r = agent.run("go")
    assert r.status == "done"
    tool_results = [m for m in r.history if isinstance(m, ToolResultMessage)]
    contents = [c.text for tr in tool_results for c in tr.content]
    assert any("not allowed" in c for c in contents)


# ── 7. prepare_arguments shim runs before validation ───────────────────────
def test_prepare_arguments_shim():
    script = [
        ai_tool("read", {"file_path": "x.c"}, "c1"),       # wrong key
        ai_tool("submit", {"summary": "shimmed"}, "c2"),
    ]
    def shim(name, raw):
        if name == "read" and "file_path" in raw:
            return {"path": raw["file_path"]}
        return raw
    agent = _make_agent(script, [READ_TOOL, SUBMIT_TOOL], prepare_arguments=shim)
    r = agent.run("go")
    assert r.status == "done"


# ── 8. on_event fires in order ─────────────────────────────────────────────
def test_on_event_ordering():
    script = [
        ai_tool("read", {"path": "x"}, "c1"),
        ai_tool("submit", {"summary": "s"}, "c2"),
    ]
    seen: list[EcoAgentEvent] = []
    agent = _make_agent(script, [READ_TOOL, SUBMIT_TOOL], on_event=seen.append)
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
    script = [ai_tool("rep_fail", {"why": "it crashed"}, "c1")]
    agent = _make_agent(script, [PASS_TOOL, FAIL_TOOL], stop=["rep_pass", "rep_fail"])
    r = agent.run("go")
    assert r.status == "done"
    assert r.stop_tool_name == "rep_fail"
    assert r.stop_payload == {"why": "it crashed"}


# ── 10. trace persistence — one JSON file per LLM request/response ─────────
def test_writes_call_trace_per_llm_call(tmp_path):
    """With trace_dir set, every LLM request/response is persisted as its own
    numbered JSON file — incrementally, before any stop tool is reached."""
    import json
    script = [
        ai_tool("read", {"path": "a.c"}, "c1"),
        ai_tool("submit", {"summary": "ok"}, "c2"),
    ]
    agent = _make_agent(
        script, [READ_TOOL, SUBMIT_TOOL],
        trace_dir=tmp_path, trace_label="architect",
    )
    r = agent.run("go")
    assert r.status == "done"

    files = sorted(tmp_path.glob("*.json"))
    assert len(files) == 2  # two LLM calls → two trace files

    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["meta"]["label"] == "architect"
    assert payload["meta"]["seq"] == 1
    assert payload["meta"]["call_no"] == 1
    assert "messages" in payload["request"]
    assert payload["response"] is not None


# ── 11. no trace_dir → no files written, agent still works ─────────────────
def test_no_trace_dir_is_silent(tmp_path):
    agent = _make_agent(
        [ai_tool("submit", {"summary": "s"}, "c1")], [READ_TOOL, SUBMIT_TOOL],
    )
    r = agent.run("go")
    assert r.status == "done"
    assert not list(tmp_path.glob("*.json"))


# ── 12. prompt prefix is append-only across calls (prefix-cache stability) ─
def test_history_prefix_is_append_only():
    """Regression for session 8c3431c2: the old _build_context re-elided a
    sliding window on EVERY call, so any message could flip full→placeholder
    and back as the window slid, invalidating the provider prefix cache
    repeatedly (three full ~40K-token re-reads in one 13-call run).

    New contract: elision happens at most ONCE per message (append time,
    full → placeholder, never recomputed), small results are never elided,
    and non-toolResult messages never change at all. So the serialized
    history between two calls is: identical prefix + at most one message
    shrinking to its final placeholder + appended messages.
    """
    import json as _json

    class _BigArgs(BaseModel):
        path: str

    def _big(a: _BigArgs) -> ToolResult:
        return ToolResult(content=("x" * 4096) + f":{a.path}")

    BIG_TOOL = EcoTool("readbig", "read a big file", _BigArgs, _big)

    script = [ai_tool("readbig", {"path": f"f{i}.c"}, f"c{i}") for i in range(8)]
    script.append(ai_tool("submit", {"summary": "ok"}, "c8"))
    agent = _make_agent(script, [BIG_TOOL, SUBMIT_TOOL], max_tool_results=3)

    snapshots: list[list[str]] = []
    original_stream = agent._stream_llm

    def _spy(history):
        snapshots.append(
            [_json.dumps(m.model_dump(mode="json"), sort_keys=True, default=str)
             for m in history],
        )
        return original_stream(history)

    agent._stream_llm = _spy
    r = agent.run("go")
    assert r.status == "done"

    assert len(snapshots) >= 4
    seen: dict[int, str] = {}
    mutations: dict[int, int] = {}
    for snap in snapshots:
        for idx, serialized in enumerate(snap):
            if idx not in seen:
                seen[idx] = serialized
                continue
            if seen[idx] == serialized:
                continue
            # A message may change at most ONCE during the whole run.
            mutations[idx] = mutations.get(idx, 0) + 1
            assert mutations[idx] == 1, (
                f"message {idx} mutated more than once — prefix cache busted"
            )
            old = _json.loads(seen[idx])
            new = _json.loads(serialized)
            assert old["role"] == "toolResult" and new["role"] == "toolResult", (
                f"non-toolResult message {idx} mutated"
            )
            old_text = old["content"][0]["text"]
            new_text = new["content"][0]["text"]
            assert "elided" in new_text and len(new_text) < len(old_text), (
                "tool result must shrink to its final placeholder exactly once"
            )
            seen[idx] = serialized

    # Surplus tool results were elided in place and the placeholder names
    # the tool.
    final_texts = [
        block.get("text", "")
        for snap in snapshots[-1]
        for m in [_json.loads(snap)]
        for block in (m.get("content") or [])
        if isinstance(block, dict) and "text" in block
    ]
    assert any("elided" in t for t in final_texts)


def test_small_tool_results_are_never_elided():
    """Size gate: one-line results stay verbatim forever — the coder run in
    8c3431c2 elided tiny list_dir/eco_wizard outputs and paid ~40K full-price
    tokens per broken prefix for nothing."""
    agent = _make_agent(
        [ai_tool("submit", {"summary": "s"}, "c1")], [READ_TOOL, SUBMIT_TOOL],
    )
    history = [
        ai_text("seed"),
    ]
    from eco_harness.agent.pi_ai.types import TextContent
    for i in range(10):
        history.append(ToolResultMessage(
            toolCallId=f"id{i}", toolName="read",
            content=[TextContent(text=f"tiny {i}")],  # 6 bytes < 2048 gate
            isError=False, timestamp=0,
        ))
    agent.max_tool_results = 3
    agent._elide_surplus_tool_results(history)
    texts = [c.text for m in history if isinstance(m, ToolResultMessage)
             for c in m.content]
    assert texts == [f"tiny {i}" for i in range(10)]


def test_tool_durations_recorded_and_cleared(tmp_path):
    """Tool wall-clock durations land in trace meta of the NEXT LLM call
    (tools run between calls) and the buffer is cleared after the write."""
    import json
    script = [
        ai_tool("read", {"path": "a.c"}, "c1"),
        ai_tool("submit", {"summary": "ok"}, "c2"),
    ]
    agent = _make_agent(
        script, [READ_TOOL, SUBMIT_TOOL],
        trace_dir=tmp_path, trace_label="coder",
    )
    r = agent.run("go")
    assert r.status == "done"
    # Buffer was flushed with the call-2 trace and cleared afterwards.
    assert agent._pending_tool_durations == []
    files = sorted(tmp_path.glob("*.json"))
    assert len(files) == 2
    payload = json.loads(files[1].read_text(encoding="utf-8"))
    durations = payload["meta"]["tool_durations"]
    assert any(d["name"] == "read" and "ms" in d for d in durations)
    assert payload["meta"]["tool_seconds"] >= 0


def test_usage_totals_accumulate():
    """Counters exist and only count responses that carry usage (the scripted
    test model carries none — the totals path is exercised in production)."""
    from eco_harness.agent.pi_ai.types import AssistantMessage, Usage

    script = [
        ai_tool("read", {"path": "a.c"}, "c1"),
        ai_tool("submit", {"summary": "ok"}, "c2"),
    ]
    agent = _make_agent(script, [READ_TOOL, SUBMIT_TOOL])
    agent.run("go")
    assert set(agent.usage_totals) == {"calls", "input", "output", "cacheRead", "cacheWrite"}
    assert agent.usage_totals["calls"] == 0
    for _ in range(2):
        usage = _usage_data(AssistantMessage(
            content=[], usage=Usage(input=100, output=10, cacheRead=50),
            api="openai-completions", provider="test", model="test",
            timestamp=0,
        ))
        assert usage["input"] == 100 and usage["cache_read"] == 50

