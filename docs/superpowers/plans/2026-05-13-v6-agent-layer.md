# V6 Agent Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Python agent layer of V6 — `EcoAgent` class, five-node graph, all tools and tests — sufficient to run a full pipeline via `graph.invoke()` against a mocked or live LLM.

**Architecture:** LangGraph StateGraph (5 nodes + plan_gate + escalate) where each node runs an `EcoAgent` instance. Native function-calling via `llm.bind_tools()`. Plan-approve and max-retry-escalation through `interrupt()`. Single LLM_MODEL from `.env`.

**Tech Stack:** Python 3.11+, langchain-openai (for `ChatOpenAI` against OpenRouter), langgraph (StateGraph + SqliteSaver), pydantic v2 (tool schemas), pytest (tests).

**Spec:** `docs/superpowers/specs/2026-05-13-v6-pipeline-design.md`
**Branch:** `feat/v6-five-node-pipeline`
**Out of scope (separate plans):** `/ws/v6/chat` backend endpoint, frontend UI.

---

## File Structure

```
Eco.Toolchain/Eco.AI.Assembly1/agent/v6/
  __init__.py                            # marker only
  state.py                               # V6State, Phase, make_initial_v6_state
  eco_agent.py                           # EcoAgent + ToolResult + EcoTool + events
  graph.py                               # create_v6_graph + routing functions
  nodes/
    __init__.py
    planner.py                           # planner_node + system prompt
    plan_gate.py                         # plan_gate_node (wraps interrupt)
    setup.py                             # setup_node + system prompt
    coder.py                             # coder_node + system prompts (first/retry)
    builder.py                           # builder_node + system prompt
    tester.py                            # tester_node + system prompt
    escalate.py                          # escalate_node (wraps interrupt)
  tools/
    __init__.py
    common.py                            # path-traversal check, regex validators, helpers
    planner.py                           # read_component, list_components, submit_plan
    setup.py                             # ecoos_pull, list_dir, read_file, mark_setup_done
    coder.py                             # read_file, write_file, edit_file, list_dir, glob, grep, mark_code_done
    builder.py                           # run_make, read_file, list_dir, report_build_pass, report_build_fail
    tester.py                            # run_artifact, report_test_pass, report_test_fail
  tests/
    __init__.py
    conftest.py                          # FakeChatModel, ScriptedChatModel, tmp project_dir, mock subprocess
    test_eco_agent.py
    test_tools_common.py
    test_tools_planner.py
    test_tools_setup.py
    test_tools_coder.py
    test_tools_builder.py
    test_tools_tester.py
    test_planner_node.py
    test_setup_node.py
    test_coder_node.py
    test_builder_node.py
    test_tester_node.py
    test_graph_e2e.py
    test_live_e2e.py                     # @pytest.mark.live
```

---

## Phase A — Foundation

### Task A1: Create directory skeleton and conftest

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/__init__.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/__init__.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tools/__init__.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/__init__.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/conftest.py`

- [ ] **Step 1: Create the package files**

Create the four `__init__.py` files (empty content) and create `conftest.py`:

```python
"""V6 test fixtures and fake LLM helpers."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Sequence
from pathlib import Path

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeChatModel(BaseChatModel):
    """LLM stub returning a single scripted AIMessage on every invoke."""
    scripted: AIMessage = Field(...)

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self.scripted)])

    def bind_tools(self, tools, **kwargs):
        # Tools bound but never inspected — the scripted reply already encodes any tool_calls.
        return self


class ScriptedChatModel(BaseChatModel):
    """LLM stub returning AIMessages from a fixed list in order, one per invoke."""
    script: list[AIMessage] = Field(default_factory=list)
    _cursor: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted-chat-model"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if self._cursor >= len(self.script):
            raise AssertionError(f"ScriptedChatModel exhausted: {self._cursor} calls, "
                                 f"only {len(self.script)} scripted replies")
        msg = self.script[self._cursor]
        object.__setattr__(self, "_cursor", self._cursor + 1)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools, **kwargs):
        return self


def make_tool_call(name: str, args: dict, call_id: str = "call_1") -> dict:
    """Build a langchain tool_call dict in the shape AIMessage.tool_calls expects."""
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def ai_text(text: str) -> AIMessage:
    return AIMessage(content=text)


def ai_tool(name: str, args: dict, call_id: str = "call_1", text: str = "") -> AIMessage:
    return AIMessage(content=text, tool_calls=[make_tool_call(name, args, call_id)])


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Empty project dir under tmp_path."""
    d = tmp_path / "Project1"
    d.mkdir()
    return d
```

- [ ] **Step 2: Verify the package imports**

Run:
```bash
cd Eco.Toolchain/Eco.AI.Assembly1
python -c "import agent.v6; import agent.v6.nodes; import agent.v6.tools"
```
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add Eco.Toolchain/Eco.AI.Assembly1/agent/v6/__init__.py \
        Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/__init__.py \
        Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tools/__init__.py \
        Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/__init__.py \
        Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/conftest.py
git commit -m "feat(v6): scaffold agent.v6 package + test fixtures (FakeChatModel, ScriptedChatModel)"
```

---

### Task A2: V6 state module

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/state.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_state.py`:

```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd Eco.Toolchain/Eco.AI.Assembly1
pytest agent/v6/tests/test_state.py -v
```
Expected: `ModuleNotFoundError: No module named 'agent.v6.state'`.

- [ ] **Step 3: Implement state.py**

```python
"""V6 state schema — five-node pipeline."""
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


Phase = Literal[
    "planning",
    "awaiting_approval",
    "setup",
    "coding",
    "building",
    "testing",
    "failed_escalated",
    "done",
]


class V6State(TypedDict):
    user_request: str

    planner_messages: Annotated[list, add_messages]
    setup_messages:   Annotated[list, add_messages]
    coder_messages:   Annotated[list, add_messages]
    builder_messages: Annotated[list, add_messages]
    tester_messages:  Annotated[list, add_messages]

    plan_md:          str
    components:       list[dict]
    project_dir:      str
    project_name:     str
    downloaded_paths: list[str]
    coder_summary_md: str
    build_artifact:   str
    build_log:        str
    tester_report_md: str

    phase:               Phase
    retry_count:         int
    max_retries:         int
    last_failure_origin: Literal["", "builder", "tester"]
    last_status:         str


def make_initial_v6_state(user_request: str, max_retries: int = 3) -> V6State:
    return {
        "user_request": user_request,
        "planner_messages": [{"role": "user", "content": user_request}],
        "setup_messages": [],
        "coder_messages": [],
        "builder_messages": [],
        "tester_messages": [],
        "plan_md": "",
        "components": [],
        "project_dir": "",
        "project_name": "",
        "downloaded_paths": [],
        "coder_summary_md": "",
        "build_artifact": "",
        "build_log": "",
        "tester_report_md": "",
        "phase": "planning",
        "retry_count": 0,
        "max_retries": max_retries,
        "last_failure_origin": "",
        "last_status": "",
    }
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest agent/v6/tests/test_state.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/state.py agent/v6/tests/test_state.py
git commit -m "feat(v6): add V6State TypedDict + make_initial_v6_state factory"
```

---

### Task A3: EcoAgent data types

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/eco_agent.py` (types only — class added in A4)
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_eco_agent_types.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_eco_agent_types.py`:

```python
from pydantic import BaseModel
from agent.v6.eco_agent import (
    ToolResult, EcoTool, EventType, EcoAgentEvent, EcoAgentResult,
)


def test_tool_result_defaults():
    r = ToolResult(content="hello")
    assert r.content == "hello"
    assert r.details is None
    assert r.is_error is False


def test_tool_result_error_form():
    r = ToolResult(content="boom", is_error=True, details={"phase": "fetch"})
    assert r.is_error is True
    assert r.details == {"phase": "fetch"}


def test_eco_tool_holds_schema_and_executor():
    class Args(BaseModel):
        x: int
    def ex(a: Args) -> ToolResult:
        return ToolResult(content=str(a.x))
    t = EcoTool(name="t", description="d", args_schema=Args, execute=ex)
    assert t.name == "t"
    assert t.args_schema is Args
    assert t.execute(Args(x=5)).content == "5"


def test_event_type_values():
    assert EventType.DONE.value == "done"
    assert EventType.MAX_ITERS.value == "max_iters"
    assert EventType.TOOL_START.value == "tool_call_start"


def test_eco_agent_event_carries_payload():
    e = EcoAgentEvent(type=EventType.ITERATION, data={"i": 3})
    assert e.type == EventType.ITERATION
    assert e.data == {"i": 3}


def test_eco_agent_result_has_status_and_stop_payload():
    r = EcoAgentResult(
        status="done", stop_tool_name="submit", stop_payload={"x": 1},
        history=[], error="",
    )
    assert r.status == "done"
    assert r.stop_tool_name == "submit"
    assert r.stop_payload == {"x": 1}
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest agent/v6/tests/test_eco_agent_types.py -v
```
Expected: ImportError on `agent.v6.eco_agent`.

- [ ] **Step 3: Implement types (eco_agent.py — types section)**

```python
"""EcoAgent — claude-code-style agent loop for V6 nodes."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Literal, Optional, Union
from pydantic import BaseModel
from langchain_core.messages import BaseMessage


@dataclass(frozen=True)
class ToolResult:
    """Outcome of a single tool execution.

    `content` is sent to the LLM as ToolMessage.content. `details` is for
    UI/logs and is NOT sent to the model.
    """
    content: str
    details: Optional[dict] = None
    is_error: bool = False


@dataclass(frozen=True)
class EcoTool:
    """A tool the agent can call. Mirrors pi-harness `Tool`."""
    name: str
    description: str
    args_schema: type[BaseModel]
    execute: Callable[[BaseModel], ToolResult]


class EventType(str, Enum):
    START         = "start"
    TEXT_DELTA    = "text_delta"        # reserved for future streaming
    TOOL_START    = "tool_call_start"
    TOOL_END      = "tool_call_end"
    TOOL_UPDATE   = "tool_update"
    ITERATION     = "iteration"
    DONE          = "done"
    NO_TOOL_CALL  = "no_tool_call"
    MAX_ITERS     = "max_iters"
    ERROR         = "error"


@dataclass(frozen=True)
class EcoAgentEvent:
    type: EventType
    data: dict


@dataclass(frozen=True)
class EcoAgentResult:
    status: Literal["done", "no_tool_call", "max_iters", "error"]
    stop_tool_name: str
    stop_payload: dict
    history: list[BaseMessage]
    error: str
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest agent/v6/tests/test_eco_agent_types.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/eco_agent.py agent/v6/tests/test_eco_agent_types.py
git commit -m "feat(v6): add EcoAgent data types (ToolResult, EcoTool, events, result)"
```

---

### Task A4: EcoAgent class — loop, hooks, error policy

**Files:**
- Modify: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/eco_agent.py` (append `EcoAgent` class)
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_eco_agent.py`

- [ ] **Step 1: Write the failing tests (9 cases from spec section 11.4)**

`tests/test_eco_agent.py`:

```python
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
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest agent/v6/tests/test_eco_agent.py -v
```
Expected: ImportError on `EcoAgent`.

- [ ] **Step 3: Implement EcoAgent class (append to eco_agent.py)**

```python
# ── append below the data types ───────────────────────────────────────────
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import ValidationError


def _to_langchain_tool(t: EcoTool) -> StructuredTool:
    """Wrap an EcoTool as a LangChain StructuredTool — the model side only
    needs `name`/`description`/`args_schema` for bind_tools; we never let
    LangChain dispatch the execute (we do that manually in the loop)."""
    def _stub(**_kw):
        raise RuntimeError("EcoTool must be executed via EcoAgent loop, not StructuredTool")
    return StructuredTool.from_function(
        func=_stub,
        name=t.name,
        description=t.description,
        args_schema=t.args_schema,
    )


class EcoAgent:
    """Claude-code-style agent loop. Synchronous. Mirrors pi-harness Agent."""

    def __init__(
        self,
        *,
        llm: BaseChatModel,
        system_prompt: str,
        tools: list[EcoTool],
        stop_tool: Union[str, list[str], None] = None,
        max_iters: int = 25,
        prepare_arguments: Optional[Callable[[str, dict], dict]] = None,
        before_tool_call:  Optional[Callable[[str, BaseModel], Optional[dict]]] = None,
        after_tool_call:   Optional[Callable[[str, BaseModel, ToolResult], ToolResult]] = None,
        on_event:          Optional[Callable[[EcoAgentEvent], None]] = None,
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.tools = {t.name: t for t in tools}
        self.stop_tools = (
            set() if stop_tool is None
            else {stop_tool} if isinstance(stop_tool, str)
            else set(stop_tool)
        )
        self.max_iters = max_iters
        self.prepare_arguments = prepare_arguments
        self.before_tool_call = before_tool_call
        self.after_tool_call = after_tool_call
        self.on_event = on_event or (lambda _e: None)

        self._llm_bound = llm.bind_tools(
            [_to_langchain_tool(t) for t in tools]
        )

    # ── helpers ────────────────────────────────────────────────────────────
    def _emit(self, event_type: EventType, data: Optional[dict] = None):
        self.on_event(EcoAgentEvent(type=event_type, data=data or {}))

    def _normalize_seed(self, seed) -> list[BaseMessage]:
        if isinstance(seed, str):
            return [HumanMessage(content=seed)]
        return list(seed)

    # ── main entrypoint ────────────────────────────────────────────────────
    def run(self, seed) -> EcoAgentResult:
        self._emit(EventType.START)
        history: list[BaseMessage] = [SystemMessage(content=self.system_prompt)]
        history.extend(self._normalize_seed(seed))

        for i in range(self.max_iters):
            self._emit(EventType.ITERATION, {"i": i})

            try:
                resp = self._llm_bound.invoke(history)
            except Exception as e:
                self._emit(EventType.ERROR, {"reason": str(e)})
                return EcoAgentResult(
                    status="error", stop_tool_name="", stop_payload={},
                    history=history, error=str(e),
                )
            history.append(resp)

            tool_calls = getattr(resp, "tool_calls", None) or []
            if not tool_calls:
                self._emit(EventType.NO_TOOL_CALL)
                return EcoAgentResult(
                    status="no_tool_call", stop_tool_name="", stop_payload={},
                    history=history, error="",
                )

            for tc in tool_calls:
                name = tc["name"]
                raw_args = tc.get("args", {})
                call_id = tc["id"]
                self._emit(EventType.TOOL_START, {"name": name, "args": raw_args})

                if name not in self.tools and name not in self.stop_tools:
                    history.append(ToolMessage(
                        content=f"UNKNOWN TOOL: {name}",
                        tool_call_id=call_id,
                        status="error",
                    ))
                    continue

                # 1. prepare_arguments shim
                cooked = self.prepare_arguments(name, raw_args) if self.prepare_arguments else raw_args

                # 2. resolve schema (stop tool may or may not be in self.tools)
                tool = self.tools.get(name)
                schema = tool.args_schema if tool else None
                if schema is None:
                    # Stop-only tool with no schema — accept the raw dict
                    args_obj = type("StopArgs", (), {"model_dump": lambda self=cooked: cooked})()
                else:
                    try:
                        args_obj = schema.model_validate(cooked)
                    except ValidationError as ve:
                        history.append(ToolMessage(
                            content=f"ARGS ERROR: {ve}",
                            tool_call_id=call_id,
                            status="error",
                        ))
                        continue

                # 3. before_tool_call gate
                if self.before_tool_call:
                    gate = self.before_tool_call(name, args_obj)
                    if gate and gate.get("block"):
                        history.append(ToolMessage(
                            content=f"BLOCKED: {gate.get('reason', '')}",
                            tool_call_id=call_id,
                            status="error",
                        ))
                        continue

                # 4. stop tool — short-circuit return
                if name in self.stop_tools:
                    payload = args_obj.model_dump() if hasattr(args_obj, "model_dump") else dict(cooked)
                    self._emit(EventType.DONE, {"stop_tool": name, "payload": payload})
                    return EcoAgentResult(
                        status="done", stop_tool_name=name,
                        stop_payload=payload, history=history, error="",
                    )

                # 5. execute
                try:
                    result = tool.execute(args_obj)
                except Exception as e:
                    history.append(ToolMessage(
                        content=f"TOOL ERROR: {e}",
                        tool_call_id=call_id,
                        status="error",
                    ))
                    continue

                # 6. after_tool_call hook
                if self.after_tool_call:
                    result = self.after_tool_call(name, args_obj, result)

                self._emit(EventType.TOOL_END, {
                    "name": name, "is_error": result.is_error, "details": result.details,
                })
                history.append(ToolMessage(
                    content=result.content,
                    tool_call_id=call_id,
                    status="error" if result.is_error else "success",
                ))

        self._emit(EventType.MAX_ITERS)
        return EcoAgentResult(
            status="max_iters", stop_tool_name="", stop_payload={},
            history=history, error="",
        )
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest agent/v6/tests/test_eco_agent.py -v
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/eco_agent.py agent/v6/tests/test_eco_agent.py
git commit -m "feat(v6): implement EcoAgent loop with hooks (prepare/before/after/on_event)"
```

---

## Phase B — Tools (TDD per file)

### Task B1: tools/common.py — shared validators

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tools/common.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_tools_common.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_tools_common.py`:

```python
import pytest
from pathlib import Path
from agent.v6.tools.common import (
    is_valid_cid, is_valid_version, ensure_inside,
)


@pytest.mark.parametrize("cid,ok", [
    ("0123456789ABCDEF0123456789ABCDEF", True),
    ("0123456789abcdef0123456789abcdef", False),    # lowercase not allowed
    ("0123456789ABCDEF0123456789ABCDE",  False),    # 31 chars
    ("0123456789ABCDEF0123456789ABCDEFA", False),   # 33 chars
    ("0123456789ABCDEF0123456789ABCDEG", False),    # G is not hex
    ("",                                  False),
])
def test_is_valid_cid(cid, ok):
    assert is_valid_cid(cid) is ok


@pytest.mark.parametrize("v,ok", [
    ("1.0.1.2",  True),
    ("0.0.0.0",  True),
    ("10.20.30.40", True),
    ("1.0.1",    False),
    ("1.0.1.2.3", False),
    ("a.b.c.d",  False),
    ("",         False),
])
def test_is_valid_version(v, ok):
    assert is_valid_version(v) is ok


def test_ensure_inside_accepts_child(tmp_path):
    parent = tmp_path / "proj"
    parent.mkdir()
    child = parent / "src" / "main.c"
    assert ensure_inside(parent, child) is True


def test_ensure_inside_rejects_traversal(tmp_path):
    parent = tmp_path / "proj"
    parent.mkdir()
    outside = tmp_path / "other.c"
    assert ensure_inside(parent, outside) is False


def test_ensure_inside_rejects_dotdot_escape(tmp_path):
    parent = tmp_path / "proj"
    parent.mkdir()
    sneaky = parent / "src" / ".." / ".." / "other.c"
    assert ensure_inside(parent, sneaky) is False
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest agent/v6/tests/test_tools_common.py -v
```
Expected: ImportError on `agent.v6.tools.common`.

- [ ] **Step 3: Implement common.py**

```python
"""Shared validators for V6 tools."""
from __future__ import annotations
import re
from pathlib import Path

_CID_RE     = re.compile(r"^[0-9A-F]{32}$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")


def is_valid_cid(cid: str) -> bool:
    return bool(_CID_RE.match(cid))


def is_valid_version(version: str) -> bool:
    return bool(_VERSION_RE.match(version))


def ensure_inside(parent: Path, child: Path) -> bool:
    """True if `child` resolves inside `parent`. Rejects `..`-escape."""
    try:
        parent_r = Path(parent).resolve(strict=False)
        child_r  = Path(child).resolve(strict=False)
        child_r.relative_to(parent_r)
        return True
    except ValueError:
        return False
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest agent/v6/tests/test_tools_common.py -v
```
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/tools/common.py agent/v6/tests/test_tools_common.py
git commit -m "feat(v6): add tools.common — CID/version regex + path-traversal guard"
```

---

### Task B2: tools/planner.py — read_component, list_components, submit_plan

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tools/planner.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_tools_planner.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_tools_planner.py`:

```python
from pathlib import Path
import pytest
from agent.v6.tools.planner import (
    make_planner_tools, ReadComponentArgs, ListComponentsArgs, SubmitPlanArgs,
)


@pytest.fixture
def sdk_dir(tmp_path: Path) -> Path:
    """Mock SDK tree with two packages."""
    a = tmp_path / "Eco.Math.C89_DK_v.1.0.1.2"
    a.mkdir()
    (a / "SharedFiles").mkdir()
    (a / "SharedFiles" / "IEcoMath.h").write_text("/* math header */")
    b = tmp_path / "Eco.StdIO.C89_DK_v.1.0.1.2"
    b.mkdir()
    (b / "SharedFiles").mkdir()
    (b / "SharedFiles" / "IEcoStdIO.h").write_text("/* stdio header */")
    return tmp_path


def test_list_components_returns_packages(sdk_dir):
    tools = make_planner_tools(sdk_root=sdk_dir)
    list_t = next(t for t in tools if t.name == "list_components")
    r = list_t.execute(ListComponentsArgs())
    assert not r.is_error
    assert "Eco.Math.C89" in r.content
    assert "Eco.StdIO.C89" in r.content


def test_read_component_returns_headers(sdk_dir):
    tools = make_planner_tools(sdk_root=sdk_dir)
    read_t = next(t for t in tools if t.name == "read_component")
    r = read_t.execute(ReadComponentArgs(name="Eco.Math.C89"))
    assert not r.is_error
    assert "math header" in r.content


def test_read_component_not_found(sdk_dir):
    tools = make_planner_tools(sdk_root=sdk_dir)
    read_t = next(t for t in tools if t.name == "read_component")
    r = read_t.execute(ReadComponentArgs(name="Eco.Nonexistent"))
    assert r.is_error
    assert "not found" in r.content.lower()


def test_submit_plan_is_stop_tool_schema():
    args = SubmitPlanArgs(
        project_name="Calculator",
        plan_md="# Plan\n## Acceptance criteria\n- prints sum",
        components=[{"cid": "ABCD" * 8, "version": "1.0.1.2",
                     "name": "Eco.Math.C89", "reason": "math"}],
        acceptance_criteria=["stdout contains the sum"],
    )
    assert args.project_name == "Calculator"
    assert args.components[0]["cid"] == "ABCD" * 8
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_tools_planner.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement tools/planner.py**

```python
"""PLANNER tools — read_component, list_components, submit_plan."""
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult


class ReadComponentArgs(BaseModel):
    name: str = Field(..., description="Component name without _DK_v.* suffix (e.g. 'Eco.Math.C89')")


class ListComponentsArgs(BaseModel):
    pass


class SubmitPlanArgs(BaseModel):
    project_name: str = Field(..., description="Short project identifier (no spaces)")
    plan_md: str = Field(..., description="Full plan in Markdown, MUST include '## Acceptance criteria' section")
    components: list[dict] = Field(..., description="List of {cid, version, name, reason}")
    acceptance_criteria: list[str] = Field(..., description="Explicit pass/fail rules for tester")


def _read_component(args: ReadComponentArgs, sdk_root: Path) -> ToolResult:
    matches = sorted(sdk_root.glob(f"{args.name}_DK_v.*"))
    if not matches:
        return ToolResult(content=f"Component '{args.name}' not found in {sdk_root}", is_error=True)
    pkg = matches[-1]   # latest version
    shared = pkg / "SharedFiles"
    if not shared.exists():
        return ToolResult(content=f"{pkg.name}: no SharedFiles/ subdir", is_error=True)
    parts = []
    for f in sorted(shared.rglob("*.h")):
        parts.append(f"=== {f.relative_to(pkg)} ===\n{f.read_text(errors='replace')}")
    if not parts:
        return ToolResult(content=f"{pkg.name}: no .h files in SharedFiles/", is_error=True)
    return ToolResult(content="\n\n".join(parts), details={"package": pkg.name})


def _list_components(_args: ListComponentsArgs, sdk_root: Path) -> ToolResult:
    names = []
    for d in sorted(sdk_root.iterdir()):
        if d.is_dir() and "_DK_v." in d.name:
            base = d.name.split("_DK_v.")[0]
            if base not in names:
                names.append(base)
    return ToolResult(content="\n".join(names))


def make_planner_tools(sdk_root: Path) -> list[EcoTool]:
    return [
        EcoTool(
            name="read_component",
            description="Read the SharedFiles/*.h of an EcoOS SDK component package.",
            args_schema=ReadComponentArgs,
            execute=lambda a: _read_component(a, sdk_root),
        ),
        EcoTool(
            name="list_components",
            description="List available EcoOS SDK component packages by base name.",
            args_schema=ListComponentsArgs,
            execute=lambda a: _list_components(a, sdk_root),
        ),
        EcoTool(
            name="submit_plan",
            description="Submit the final plan. The agent stops after this.",
            args_schema=SubmitPlanArgs,
            execute=lambda _a: ToolResult(content="(stop tool — never executed)"),
        ),
    ]
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_tools_planner.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/tools/planner.py agent/v6/tests/test_tools_planner.py
git commit -m "feat(v6): add planner tools (read_component, list_components, submit_plan)"
```

---

### Task B3: tools/setup.py — ecoos_pull, list_dir, read_file, mark_setup_done

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tools/setup.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_tools_setup.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_tools_setup.py`:

```python
import subprocess
from pathlib import Path
import pytest
from agent.v6.tools.setup import (
    make_setup_tools, EcoosPullArgs, ListDirArgs, ReadFileArgs, MarkSetupDoneArgs,
)


@pytest.fixture
def fake_cli(tmp_path: Path, monkeypatch):
    """Mock eco-cli binary path + subprocess.run."""
    cli = tmp_path / "eco-cli.exe"
    cli.write_text("")  # only needs to exist
    captured = {"calls": []}
    def fake_run(cmd, **kw):
        captured["calls"].append({"cmd": cmd, "kw": kw})
        class R:
            returncode = 0
            stdout = "pulled OK"
            stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    return cli, captured


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_ecoos_pull_invokes_cli_with_argv_list(fake_cli, project_dir):
    cli, cap = fake_cli
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir,
                             allowed_components=[{"cid": "A"*32, "version": "1.0.1.2"}])
    r = _tool(tools, "ecoos_pull").execute(EcoosPullArgs(cid="A"*32, version="1.0.1.2"))
    assert not r.is_error
    call = cap["calls"][0]
    assert call["cmd"][0] == str(cli)
    assert "pull" in call["cmd"]
    assert call["kw"]["shell"] is False
    assert call["kw"]["timeout"] == 60


def test_ecoos_pull_rejects_invalid_cid(fake_cli, project_dir):
    cli, _ = fake_cli
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir,
                             allowed_components=[{"cid": "A"*32, "version": "1.0.1.2"}])
    r = _tool(tools, "ecoos_pull").execute(EcoosPullArgs(cid="not-hex", version="1.0.1.2"))
    assert r.is_error
    assert "invalid cid" in r.content.lower()


def test_ecoos_pull_rejects_unplanned_component(fake_cli, project_dir):
    cli, _ = fake_cli
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir,
                             allowed_components=[{"cid": "B"*32, "version": "1.0.1.2"}])
    r = _tool(tools, "ecoos_pull").execute(EcoosPullArgs(cid="A"*32, version="1.0.1.2"))
    assert r.is_error
    assert "not in plan" in r.content.lower()


def test_list_dir_inside_project_dir(project_dir, fake_cli):
    cli, _ = fake_cli
    (project_dir / "SharedFiles").mkdir()
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir, allowed_components=[])
    r = _tool(tools, "list_dir").execute(ListDirArgs(path=str(project_dir / "SharedFiles")))
    assert not r.is_error


def test_list_dir_rejects_outside(project_dir, fake_cli, tmp_path):
    cli, _ = fake_cli
    tools = make_setup_tools(cli_path=cli, project_dir=project_dir, allowed_components=[])
    r = _tool(tools, "list_dir").execute(ListDirArgs(path=str(tmp_path / "elsewhere")))
    assert r.is_error
    assert "outside" in r.content.lower()


def test_mark_setup_done_args():
    args = MarkSetupDoneArgs(downloaded_paths=["/path/a", "/path/b"])
    assert args.downloaded_paths == ["/path/a", "/path/b"]
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_tools_setup.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement tools/setup.py**

```python
"""SETUP tools — ecoos_pull, list_dir, read_file, mark_setup_done."""
from __future__ import annotations
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import is_valid_cid, is_valid_version, ensure_inside


class EcoosPullArgs(BaseModel):
    cid: str = Field(..., description="32-char uppercase hex component CID")
    version: str = Field(..., description="Version in N.N.N.N format")


class ListDirArgs(BaseModel):
    path: str


class ReadFileArgs(BaseModel):
    path: str


class MarkSetupDoneArgs(BaseModel):
    downloaded_paths: list[str] = Field(..., description="Verified package directories under project_dir")


def _ecoos_pull(args: EcoosPullArgs, cli_path: Path, project_dir: Path,
                allowed_components: list[dict]) -> ToolResult:
    if not is_valid_cid(args.cid):
        return ToolResult(content=f"Invalid CID: must be 32-char uppercase hex, got '{args.cid}'", is_error=True)
    if not is_valid_version(args.version):
        return ToolResult(content=f"Invalid version: must be N.N.N.N, got '{args.version}'", is_error=True)
    in_plan = any(c.get("cid") == args.cid and c.get("version") == args.version
                  for c in allowed_components)
    if not in_plan:
        return ToolResult(content=f"Component {args.cid} v{args.version} not in plan", is_error=True)

    cmd = [str(cli_path), "pull", "-c", args.cid, "-v", args.version, "-d", str(project_dir)]
    try:
        proc = subprocess.run(cmd, shell=False, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return ToolResult(content=f"eco-cli pull timed out after 60s", is_error=True)
    if proc.returncode != 0:
        return ToolResult(
            content=f"eco-cli failed (exit {proc.returncode}):\n{proc.stderr}",
            is_error=True,
            details={"stdout": proc.stdout, "stderr": proc.stderr},
        )
    return ToolResult(content=f"pulled {args.cid} v{args.version}", details={"stdout": proc.stdout})


def _list_dir(args: ListDirArgs, project_dir: Path) -> ToolResult:
    p = Path(args.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"Path '{args.path}' is outside project_dir", is_error=True)
    if not p.exists():
        return ToolResult(content=f"Path '{args.path}' does not exist", is_error=True)
    if not p.is_dir():
        return ToolResult(content=f"Path '{args.path}' is not a directory", is_error=True)
    entries = sorted([e.name for e in p.iterdir()])
    return ToolResult(content="\n".join(entries))


def _read_file(args: ReadFileArgs, project_dir: Path) -> ToolResult:
    p = Path(args.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"Path '{args.path}' is outside project_dir", is_error=True)
    if not p.exists():
        return ToolResult(content=f"File '{args.path}' does not exist", is_error=True)
    return ToolResult(content=p.read_text(errors="replace"))


def make_setup_tools(*, cli_path: Path, project_dir: Path,
                     allowed_components: list[dict]) -> list[EcoTool]:
    return [
        EcoTool(
            name="ecoos_pull",
            description="Pull an EcoOS SDK component into project_dir via eco-cli.",
            args_schema=EcoosPullArgs,
            execute=lambda a: _ecoos_pull(a, cli_path, project_dir, allowed_components),
        ),
        EcoTool(
            name="list_dir",
            description="List entries under a directory inside project_dir.",
            args_schema=ListDirArgs,
            execute=lambda a: _list_dir(a, project_dir),
        ),
        EcoTool(
            name="read_file",
            description="Read a file under project_dir.",
            args_schema=ReadFileArgs,
            execute=lambda a: _read_file(a, project_dir),
        ),
        EcoTool(
            name="mark_setup_done",
            description="Stop tool. Call when all components are verified.",
            args_schema=MarkSetupDoneArgs,
            execute=lambda _a: ToolResult(content="(stop tool — never executed)"),
        ),
    ]
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_tools_setup.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/tools/setup.py agent/v6/tests/test_tools_setup.py
git commit -m "feat(v6): add setup tools (ecoos_pull with argv-list + regex validation, list_dir, read_file, mark_setup_done)"
```

---

### Task B4: tools/coder.py — read/write/edit/list/glob/grep + mark_code_done

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tools/coder.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_tools_coder.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_tools_coder.py`:

```python
from pathlib import Path
from agent.v6.tools.coder import (
    make_coder_tools, WriteFileArgs, EditFileArgs, ReadFileArgs, GlobArgs, GrepArgs,
)


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_write_file_creates_file(project_dir):
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "write_file").execute(WriteFileArgs(path=str(project_dir / "EcoMain.c"),
                                                          content="int main(){}"))
    assert not r.is_error
    assert (project_dir / "EcoMain.c").read_text() == "int main(){}"


def test_write_file_rejects_outside(project_dir, tmp_path):
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "write_file").execute(WriteFileArgs(path=str(tmp_path / "evil.c"),
                                                          content="x"))
    assert r.is_error


def test_edit_file_replaces_substring(project_dir):
    f = project_dir / "x.c"
    f.write_text("hello world")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "edit_file").execute(EditFileArgs(path=str(f),
                                                        old="world", new="EcoOS"))
    assert not r.is_error
    assert f.read_text() == "hello EcoOS"


def test_edit_file_old_not_found(project_dir):
    f = project_dir / "x.c"
    f.write_text("hello")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "edit_file").execute(EditFileArgs(path=str(f),
                                                        old="missing", new="x"))
    assert r.is_error
    assert "not found" in r.content.lower()


def test_read_file_can_read_downloaded_paths(project_dir, tmp_path):
    sdk = tmp_path / "sdk_component"
    sdk.mkdir()
    (sdk / "header.h").write_text("/* sdk */")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[sdk])
    r = _tool(tools, "read_file").execute(ReadFileArgs(path=str(sdk / "header.h")))
    assert not r.is_error
    assert "sdk" in r.content


def test_glob_under_project_dir(project_dir):
    (project_dir / "a.c").write_text("")
    (project_dir / "b.c").write_text("")
    (project_dir / "x.h").write_text("")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "glob").execute(GlobArgs(pattern="*.c"))
    assert not r.is_error
    assert "a.c" in r.content and "b.c" in r.content


def test_grep_finds_match(project_dir):
    (project_dir / "f.c").write_text("int main() { return 0; }")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "grep").execute(GrepArgs(pattern="main", path=str(project_dir)))
    assert not r.is_error
    assert "f.c" in r.content
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_tools_coder.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement tools/coder.py**

```python
"""CODER tools — claude-code style file I/O (no bash, no shell)."""
from __future__ import annotations
from pathlib import Path
import re
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import ensure_inside


class ReadFileArgs(BaseModel):
    path: str


class WriteFileArgs(BaseModel):
    path: str
    content: str


class EditFileArgs(BaseModel):
    path: str
    old: str = Field(..., description="Exact substring to replace (must occur exactly once)")
    new: str


class ListDirArgs(BaseModel):
    path: str


class GlobArgs(BaseModel):
    pattern: str = Field(..., description="Glob pattern relative to project_dir, e.g. '**/*.c'")


class GrepArgs(BaseModel):
    pattern: str = Field(..., description="Regex to search for")
    path: str = Field(..., description="File or directory to search in")


class MarkCodeDoneArgs(BaseModel):
    summary_md: str = Field(..., description="Markdown summary of files created/modified")


def _allowed_for_read(p: Path, project_dir: Path, downloaded_paths: list[Path]) -> bool:
    if ensure_inside(project_dir, p):
        return True
    return any(ensure_inside(dp, p) for dp in downloaded_paths)


def _read_file(a: ReadFileArgs, project_dir: Path, downloaded_paths: list[Path]) -> ToolResult:
    p = Path(a.path)
    if not _allowed_for_read(p, project_dir, downloaded_paths):
        return ToolResult(content=f"Path '{a.path}' is outside project_dir and downloaded_paths",
                          is_error=True)
    if not p.exists():
        return ToolResult(content=f"File '{a.path}' does not exist", is_error=True)
    return ToolResult(content=p.read_text(errors="replace"))


def _write_file(a: WriteFileArgs, project_dir: Path) -> ToolResult:
    p = Path(a.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"write_file: path '{a.path}' must be inside project_dir",
                          is_error=True)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(a.content)
    return ToolResult(content=f"wrote {len(a.content)} bytes to {p.name}",
                      details={"bytes": len(a.content)})


def _edit_file(a: EditFileArgs, project_dir: Path) -> ToolResult:
    p = Path(a.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"edit_file: path '{a.path}' must be inside project_dir",
                          is_error=True)
    if not p.exists():
        return ToolResult(content=f"File '{a.path}' does not exist", is_error=True)
    text = p.read_text(errors="replace")
    if a.old not in text:
        return ToolResult(content=f"old string not found in {p.name}", is_error=True)
    occurrences = text.count(a.old)
    if occurrences > 1:
        return ToolResult(content=f"old string occurs {occurrences} times in {p.name} — not unique",
                          is_error=True)
    p.write_text(text.replace(a.old, a.new))
    return ToolResult(content=f"edited {p.name}")


def _list_dir(a: ListDirArgs, project_dir: Path, downloaded_paths: list[Path]) -> ToolResult:
    p = Path(a.path)
    if not _allowed_for_read(p, project_dir, downloaded_paths):
        return ToolResult(content=f"Path '{a.path}' is outside allowed roots", is_error=True)
    if not p.exists() or not p.is_dir():
        return ToolResult(content=f"'{a.path}' is not an existing directory", is_error=True)
    return ToolResult(content="\n".join(sorted(e.name for e in p.iterdir())))


def _glob(a: GlobArgs, project_dir: Path) -> ToolResult:
    matches = sorted([str(p.relative_to(project_dir)) for p in project_dir.rglob(a.pattern)])
    if not matches:
        return ToolResult(content=f"(no matches for '{a.pattern}')")
    return ToolResult(content="\n".join(matches))


def _grep(a: GrepArgs, project_dir: Path, downloaded_paths: list[Path]) -> ToolResult:
    p = Path(a.path)
    if not _allowed_for_read(p, project_dir, downloaded_paths):
        return ToolResult(content=f"Path '{a.path}' is outside allowed roots", is_error=True)
    try:
        rx = re.compile(a.pattern)
    except re.error as e:
        return ToolResult(content=f"invalid regex: {e}", is_error=True)
    found: list[str] = []
    targets = p.rglob("*") if p.is_dir() else [p]
    for f in targets:
        if not f.is_file():
            continue
        try:
            for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                if rx.search(line):
                    found.append(f"{f}:{n}: {line}")
        except (OSError, UnicodeDecodeError):
            continue
    return ToolResult(content="\n".join(found) if found else "(no matches)")


def make_coder_tools(*, project_dir: Path, downloaded_paths: list[Path]) -> list[EcoTool]:
    return [
        EcoTool("read_file",  "Read a text file under project_dir or downloaded SDK paths.",
                ReadFileArgs,  lambda a: _read_file(a, project_dir, downloaded_paths)),
        EcoTool("write_file", "Create or overwrite a file inside project_dir.",
                WriteFileArgs, lambda a: _write_file(a, project_dir)),
        EcoTool("edit_file",  "Replace a unique substring in a file inside project_dir.",
                EditFileArgs,  lambda a: _edit_file(a, project_dir)),
        EcoTool("list_dir",   "List a directory under project_dir or downloaded SDK paths.",
                ListDirArgs,   lambda a: _list_dir(a, project_dir, downloaded_paths)),
        EcoTool("glob",       "Glob files under project_dir.",
                GlobArgs,      lambda a: _glob(a, project_dir)),
        EcoTool("grep",       "Regex-search a file or directory under allowed roots.",
                GrepArgs,      lambda a: _grep(a, project_dir, downloaded_paths)),
        EcoTool("mark_code_done", "Stop tool. Call when implementation is complete.",
                MarkCodeDoneArgs, lambda _a: ToolResult(content="(stop tool)")),
    ]
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_tools_coder.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/tools/coder.py agent/v6/tests/test_tools_coder.py
git commit -m "feat(v6): add coder tools (read/write/edit/list/glob/grep, no bash)"
```

---

### Task B5: tools/builder.py — run_make + report_build_pass/fail

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tools/builder.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_tools_builder.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_tools_builder.py`:

```python
import subprocess
from pathlib import Path
from agent.v6.tools.builder import (
    make_builder_tools, RunMakeArgs, ReportBuildPassArgs, ReportBuildFailArgs,
)


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_run_make_invokes_cmd_with_vcvarsall(monkeypatch, project_dir):
    captured = {}
    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        captured["kw"] = kw
        class R: returncode = 0; stdout = "Build succeeded"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_builder_tools(project_dir=project_dir,
                               vcvarsall=Path(r"C:/vcvarsall.bat"),
                               make_exe=Path(r"C:/make.exe"))
    r = _tool(tools, "run_make").execute(RunMakeArgs())
    assert not r.is_error
    # cmd should be a list (argv), shell=False
    assert isinstance(captured["cmd"], list)
    assert captured["kw"]["shell"] is False
    assert captured["kw"]["timeout"] == 300
    assert captured["kw"]["env"]["MSYS_NO_PATHCONV"] == "1"


def test_run_make_failure_returns_is_error(monkeypatch, project_dir):
    def fake_run(cmd, **kw):
        class R: returncode = 1; stdout = "error C2065:"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_builder_tools(project_dir=project_dir,
                               vcvarsall=Path(r"C:/vcvarsall.bat"),
                               make_exe=Path(r"C:/make.exe"))
    r = _tool(tools, "run_make").execute(RunMakeArgs())
    assert r.is_error
    assert "C2065" in r.content


def test_report_pass_fail_args_schemas():
    p = ReportBuildPassArgs(artifact_path="C:/Project1/out.exe")
    f = ReportBuildFailArgs(error_md="## Error\nundefined symbol")
    assert p.artifact_path.endswith(".exe")
    assert "undefined" in f.error_md
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_tools_builder.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement tools/builder.py**

```python
"""BUILDER tools — run_make + report_build_pass/fail."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.common import ensure_inside


class RunMakeArgs(BaseModel):
    target: str = Field(default="all")


class ReadFileArgs(BaseModel):
    path: str


class ListDirArgs(BaseModel):
    path: str


class ReportBuildPassArgs(BaseModel):
    artifact_path: str = Field(..., description="Absolute path to the built executable")


class ReportBuildFailArgs(BaseModel):
    error_md: str = Field(..., description="Markdown summary of the key error(s) — NOT raw log")


def _run_make(args: RunMakeArgs, project_dir: Path, vcvarsall: Path, make_exe: Path) -> ToolResult:
    cmd_line = f'"{vcvarsall}" x64 && "{make_exe}" {args.target}'
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    try:
        proc = subprocess.run(
            ["cmd.exe", "/c", cmd_line],
            cwd=str(project_dir),
            env=env,
            shell=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content="build timed out after 300s", is_error=True)
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    if proc.returncode != 0:
        return ToolResult(content=f"build failed (exit {proc.returncode}):\n{out}",
                          is_error=True, details={"exit_code": proc.returncode})
    return ToolResult(content=f"build succeeded:\n{out}",
                      details={"exit_code": 0})


def _read_file(args: ReadFileArgs, project_dir: Path) -> ToolResult:
    p = Path(args.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"'{args.path}' is outside project_dir", is_error=True)
    if not p.exists():
        return ToolResult(content=f"'{args.path}' does not exist", is_error=True)
    return ToolResult(content=p.read_text(errors="replace"))


def _list_dir(args: ListDirArgs, project_dir: Path) -> ToolResult:
    p = Path(args.path)
    if not ensure_inside(project_dir, p):
        return ToolResult(content=f"'{args.path}' is outside project_dir", is_error=True)
    if not p.exists() or not p.is_dir():
        return ToolResult(content=f"'{args.path}' is not a directory", is_error=True)
    return ToolResult(content="\n".join(sorted(e.name for e in p.iterdir())))


def make_builder_tools(*, project_dir: Path, vcvarsall: Path, make_exe: Path) -> list[EcoTool]:
    return [
        EcoTool("run_make", "Build the project: vcvarsall.bat x64 && make <target>.",
                RunMakeArgs, lambda a: _run_make(a, project_dir, vcvarsall, make_exe)),
        EcoTool("read_file", "Read a file under project_dir (e.g. Makefile or log).",
                ReadFileArgs, lambda a: _read_file(a, project_dir)),
        EcoTool("list_dir", "List a directory under project_dir.",
                ListDirArgs, lambda a: _list_dir(a, project_dir)),
        EcoTool("report_build_pass", "Stop tool. Call on successful build.",
                ReportBuildPassArgs, lambda _a: ToolResult(content="(stop)")),
        EcoTool("report_build_fail", "Stop tool. Call on failed build with error_md.",
                ReportBuildFailArgs, lambda _a: ToolResult(content="(stop)")),
    ]
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_tools_builder.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/tools/builder.py agent/v6/tests/test_tools_builder.py
git commit -m "feat(v6): add builder tools (run_make wrapper with vcvarsall + reports)"
```

---

### Task B6: tools/tester.py — run_artifact + report_test_pass/fail

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tools/tester.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_tools_tester.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_tools_tester.py`:

```python
import json
import subprocess
from pathlib import Path
from agent.v6.tools.tester import (
    make_tester_tools, RunArtifactArgs, ReportTestPassArgs, ReportTestFailArgs,
)


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_run_artifact_captures_output(monkeypatch, project_dir):
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    def fake_run(cmd, **kw):
        class R: returncode = 0; stdout = "Result: 5\n"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_tester_tools(build_artifact=artifact)
    r = _tool(tools, "run_artifact").execute(RunArtifactArgs(timeout_s=5))
    assert not r.is_error
    payload = json.loads(r.content)
    assert payload["exit_code"] == 0
    assert "Result: 5" in payload["stdout"]
    assert payload["timed_out"] is False


def test_run_artifact_timeout(monkeypatch, project_dir):
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    def fake_run(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=kw.get("timeout"))
    monkeypatch.setattr(subprocess, "run", fake_run)
    tools = make_tester_tools(build_artifact=artifact)
    r = _tool(tools, "run_artifact").execute(RunArtifactArgs(timeout_s=2))
    assert not r.is_error  # timeout is a tested outcome, not a tool error
    payload = json.loads(r.content)
    assert payload["timed_out"] is True


def test_no_read_file_tool(project_dir):
    """Tester MUST NOT have read_file (anchoring-bias structural mitigation)."""
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    tools = make_tester_tools(build_artifact=artifact)
    assert all(t.name != "read_file" for t in tools)
    assert all(t.name != "list_dir" for t in tools)
    assert all(t.name != "glob"      for t in tools)
    assert all(t.name != "grep"      for t in tools)


def test_report_pass_fail_schemas():
    p = ReportTestPassArgs(reason_md="output matches acceptance")
    f = ReportTestFailArgs(reason_md="stdout was empty")
    assert "acceptance" in p.reason_md
    assert "empty" in f.reason_md
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_tools_tester.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement tools/tester.py**

```python
"""TESTER tools — run_artifact + report_test_pass/fail. No read_file by design."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult


class RunArtifactArgs(BaseModel):
    timeout_s: int = Field(default=10, ge=1, le=60)


class ReportTestPassArgs(BaseModel):
    reason_md: str = Field(..., description="Why the artifact satisfies the user request")


class ReportTestFailArgs(BaseModel):
    reason_md: str = Field(..., description="Specifically what does not match expectations")


def _run_artifact(args: RunArtifactArgs, build_artifact: Path) -> ToolResult:
    if not build_artifact.exists():
        return ToolResult(content=f"artifact does not exist: {build_artifact}", is_error=True)
    try:
        proc = subprocess.run(
            [str(build_artifact)],
            shell=False,
            capture_output=True,
            text=True,
            timeout=args.timeout_s,
        )
        payload = {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        payload = {
            "exit_code": None,
            "stdout": (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            "stderr": (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or ""),
            "timed_out": True,
        }
    return ToolResult(content=json.dumps(payload, ensure_ascii=False), details=payload)


def make_tester_tools(*, build_artifact: Path) -> list[EcoTool]:
    return [
        EcoTool("run_artifact", "Run the built artifact and capture stdout/stderr/exit/timeout.",
                RunArtifactArgs, lambda a: _run_artifact(a, build_artifact)),
        EcoTool("report_test_pass", "Stop tool. Call when the artifact behaves as the user asked.",
                ReportTestPassArgs, lambda _a: ToolResult(content="(stop)")),
        EcoTool("report_test_fail", "Stop tool. Call when the artifact does NOT match expectations.",
                ReportTestFailArgs, lambda _a: ToolResult(content="(stop)")),
    ]
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_tools_tester.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/tools/tester.py agent/v6/tests/test_tools_tester.py
git commit -m "feat(v6): add tester tools (run_artifact + reports; deliberately no read_file)"
```

---

## Phase C — Nodes

Each node is a function `(state) -> dict` that builds an `EcoAgent` from `state`, calls `agent.run(seed)`, and returns the state delta. The fixture `node_llm` is the model passed when building the graph.

### Task C1: nodes/planner.py

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/planner.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_planner_node.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_planner_node.py`:

```python
from pathlib import Path
from agent.v6.nodes.planner import planner_node, PLANNER_SYSTEM_PROMPT
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


def test_planner_node_writes_plan_md_and_components(tmp_path):
    # SDK with one mock package
    sdk = tmp_path / "sdk"
    sdk.mkdir()
    pkg = sdk / "Eco.Math.C89_DK_v.1.0.1.2"
    (pkg / "SharedFiles").mkdir(parents=True)
    (pkg / "SharedFiles" / "IEcoMath.h").write_text("/*math*/")

    llm = ScriptedChatModel(script=[
        ai_tool("submit_plan", {
            "project_name": "Calc",
            "plan_md": "# Plan\n## Acceptance criteria\n- prints 5",
            "components": [{"cid": "AB"*16, "version": "1.0.1.2", "name": "Eco.Math.C89", "reason": "math"}],
            "acceptance_criteria": ["stdout contains 5"],
        })
    ])
    state = make_initial_v6_state("build a calculator")
    delta = planner_node(state, llm=llm, sdk_root=sdk)
    assert delta["phase"] == "awaiting_approval"
    assert delta["project_name"] == "Calc"
    assert "Acceptance" in delta["plan_md"]
    assert delta["components"][0]["cid"] == "AB" * 16


def test_planner_node_max_iters_escalates(tmp_path):
    sdk = tmp_path / "sdk"
    sdk.mkdir()
    # LLM keeps calling list_components, never submits
    llm = ScriptedChatModel(script=[
        ai_tool("list_components", {}, f"c{i}") for i in range(40)
    ])
    state = make_initial_v6_state("x")
    delta = planner_node(state, llm=llm, sdk_root=sdk, max_iters=3)
    assert delta["phase"] == "failed_escalated"
    assert delta["last_status"].startswith("planner_")


def test_planner_system_prompt_mentions_acceptance_criteria():
    assert "acceptance" in PLANNER_SYSTEM_PROMPT.lower()
    assert "submit_plan" in PLANNER_SYSTEM_PROMPT
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_planner_node.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement nodes/planner.py**

```python
"""PLANNER node — produces plan_md + components."""
from __future__ import annotations
from pathlib import Path
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.planner import make_planner_tools
from agent.v6.state import V6State


PLANNER_SYSTEM_PROMPT = """\
You are the EcoOS Planner.

Read available SDK components via `list_components` and `read_component`. \
Then design an application that satisfies the user request using ONLY existing \
SDK components.

Produce a final plan via `submit_plan` (stop tool). The plan MUST contain:
- a `## Acceptance criteria` section listing observable behaviors (stdout strings, \
  exit codes, what the tester will check)
- a `components` list with cid, version, base name, and a one-sentence reason for each
- a narrative `plan_md` describing the application

Always use `list_components` first if you don't know what's available."""


def planner_node(state: V6State, *, llm, sdk_root: Path, max_iters: int = 30) -> dict:
    tools = make_planner_tools(sdk_root=sdk_root)
    agent = EcoAgent(
        llm=llm,
        system_prompt=PLANNER_SYSTEM_PROMPT,
        tools=tools,
        stop_tool="submit_plan",
        max_iters=max_iters,
    )
    result = agent.run(state["user_request"])

    if result.status == "done":
        return {
            "phase": "awaiting_approval",
            "plan_md":      result.stop_payload["plan_md"],
            "components":   result.stop_payload["components"],
            "project_name": result.stop_payload["project_name"],
            "planner_messages": result.history,
        }
    # max_iters or no_tool_call or error
    return {
        "phase": "failed_escalated",
        "last_status": f"planner_{result.status}",
        "planner_messages": result.history,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_planner_node.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/nodes/planner.py agent/v6/tests/test_planner_node.py
git commit -m "feat(v6): add planner_node + PLANNER_SYSTEM_PROMPT"
```

---

### Task C2: nodes/plan_gate.py

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/plan_gate.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_plan_gate_node.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_plan_gate_node.py`:

```python
import pytest
from langgraph.errors import GraphInterrupt
from agent.v6.nodes.plan_gate import plan_gate_node
from agent.v6.state import make_initial_v6_state


def test_plan_gate_raises_interrupt_with_plan_payload():
    state = make_initial_v6_state("x")
    state["plan_md"] = "# Plan"
    state["components"] = [{"cid": "A" * 32, "version": "1.0.1.2", "name": "X"}]
    # plan_gate calls interrupt() which raises GraphInterrupt outside a graph
    with pytest.raises(GraphInterrupt) as ei:
        plan_gate_node(state)
    payload = ei.value.args[0][0].value
    assert payload["plan_md"] == "# Plan"
    assert payload["components"][0]["cid"] == "A" * 32
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_plan_gate_node.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement nodes/plan_gate.py**

```python
"""PLAN_GATE — pure interrupt() wrapper. No agent."""
from __future__ import annotations
from langgraph.types import interrupt
from agent.v6.state import V6State


def plan_gate_node(state: V6State) -> dict:
    resume = interrupt({
        "plan_md":    state["plan_md"],
        "components": state["components"],
        "project_name": state.get("project_name", ""),
    })
    # resume value: {"approved": bool, "modified_plan_md"?: str, "reason"?: str}
    if not resume.get("approved", False):
        return {"phase": "done", "last_status": "user_aborted"}
    delta = {"phase": "setup"}
    if "modified_plan_md" in resume and resume["modified_plan_md"]:
        delta["plan_md"] = resume["modified_plan_md"]
    return delta
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_plan_gate_node.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/nodes/plan_gate.py agent/v6/tests/test_plan_gate_node.py
git commit -m "feat(v6): add plan_gate_node (interrupt + resume handling)"
```

---

### Task C3: nodes/setup.py

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/setup.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_setup_node.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_setup_node.py`:

```python
import subprocess
from pathlib import Path
import json
import pytest
from agent.v6.nodes.setup import setup_node, SETUP_SYSTEM_PROMPT
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


@pytest.fixture
def fake_cli_path(tmp_path):
    cli = tmp_path / "eco-cli.exe"
    cli.write_text("")
    return cli


def test_setup_node_happy_path(monkeypatch, project_dir, fake_cli_path):
    def fake_run(cmd, **kw):
        class R: returncode = 0; stdout = "ok"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)

    state = make_initial_v6_state("x")
    state["components"] = [{"cid": "A" * 32, "version": "1.0.1.2", "name": "Eco.X", "reason": "r"}]
    state["plan_md"] = "# Plan"
    state["project_dir"] = str(project_dir)

    llm = ScriptedChatModel(script=[
        ai_tool("ecoos_pull", {"cid": "A" * 32, "version": "1.0.1.2"}, "c1"),
        ai_tool("mark_setup_done", {"downloaded_paths": [str(project_dir)]}, "c2"),
    ])
    delta = setup_node(state, llm=llm, cli_path=fake_cli_path)
    assert delta["phase"] == "coding"
    assert str(project_dir) in delta["downloaded_paths"]


def test_setup_node_prompt_mentions_verification():
    assert "verify" in SETUP_SYSTEM_PROMPT.lower()
    assert "list_dir" in SETUP_SYSTEM_PROMPT
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_setup_node.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement nodes/setup.py**

```python
"""SETUP node — pulls SDK components and verifies their directories."""
from __future__ import annotations
import json
from pathlib import Path
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.setup import make_setup_tools
from agent.v6.state import V6State


SETUP_SYSTEM_PROMPT = """\
You are the EcoOS Setup agent.

You receive an approved plan with a list of components and a project_dir. \
For EACH component, call `ecoos_pull` with its cid and version. After EACH pull, \
call `list_dir` on the expected component directory under project_dir to verify \
the package actually landed (look for SharedFiles/, BuildFiles/).

Only when ALL components are verified do you call `mark_setup_done` with the \
list of verified directories. If any pull or verification fails, do NOT mark \
done — the loop will exit with max_iters and escalate."""


def setup_node(state: V6State, *, llm, cli_path: Path, max_iters: int = 30) -> dict:
    project_dir = Path(state["project_dir"]) if state["project_dir"] else Path("./output") / state["project_name"]
    project_dir.mkdir(parents=True, exist_ok=True)

    tools = make_setup_tools(
        cli_path=cli_path,
        project_dir=project_dir,
        allowed_components=state["components"],
    )
    seed = (
        f"Plan:\n{state['plan_md']}\n\n"
        f"Components to download:\n{json.dumps(state['components'], indent=2)}\n\n"
        f"Project dir (already created): {project_dir}\n\n"
        "Pull each component, verify with list_dir, then call mark_setup_done."
    )
    agent = EcoAgent(
        llm=llm,
        system_prompt=SETUP_SYSTEM_PROMPT,
        tools=tools,
        stop_tool="mark_setup_done",
        max_iters=max_iters,
    )
    result = agent.run(seed)

    if result.status == "done":
        return {
            "phase": "coding",
            "project_dir": str(project_dir),
            "downloaded_paths": result.stop_payload["downloaded_paths"],
            "setup_messages": result.history,
        }
    return {
        "phase": "failed_escalated",
        "last_status": f"setup_{result.status}",
        "setup_messages": result.history,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_setup_node.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/nodes/setup.py agent/v6/tests/test_setup_node.py
git commit -m "feat(v6): add setup_node (agentic pull + verify)"
```

---

### Task C4: nodes/coder.py

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/coder.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_coder_node.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_coder_node.py`:

```python
from pathlib import Path
from agent.v6.nodes.coder import coder_node, _build_coder_seed
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


def test_coder_node_happy_writes_file(project_dir):
    state = make_initial_v6_state("calc")
    state["plan_md"] = "# Plan\nWrite EcoMain.c"
    state["project_dir"] = str(project_dir)
    state["downloaded_paths"] = []
    state["retry_count"] = 0

    target = project_dir / "EcoMain.c"
    llm = ScriptedChatModel(script=[
        ai_tool("write_file", {"path": str(target), "content": "int main(){return 0;}"}, "c1"),
        ai_tool("mark_code_done", {"summary_md": "wrote EcoMain.c"}, "c2"),
    ])
    delta = coder_node(state, llm=llm)
    assert delta["phase"] == "building"
    assert "wrote EcoMain.c" in delta["coder_summary_md"]
    assert target.exists()


def test_coder_seed_first_attempt_excludes_feedback():
    state = make_initial_v6_state("x")
    state["plan_md"] = "P"
    state["project_dir"] = "/tmp/p"
    state["retry_count"] = 0
    seed = _build_coder_seed(state)
    assert "retry" not in seed.lower()


def test_coder_seed_retry_includes_build_log():
    state = make_initial_v6_state("x")
    state["plan_md"] = "P"
    state["project_dir"] = "/tmp/p"
    state["retry_count"] = 1
    state["last_failure_origin"] = "builder"
    state["build_log"] = "## Error\nundefined symbol foo"
    seed = _build_coder_seed(state)
    assert "retry" in seed.lower()
    assert "undefined symbol foo" in seed


def test_coder_seed_retry_includes_tester_report():
    state = make_initial_v6_state("x")
    state["plan_md"] = "P"
    state["project_dir"] = "/tmp/p"
    state["retry_count"] = 2
    state["last_failure_origin"] = "tester"
    state["tester_report_md"] = "expected 5, got 8"
    seed = _build_coder_seed(state)
    assert "expected 5, got 8" in seed
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_coder_node.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement nodes/coder.py**

```python
"""CODER node — claude-code-style writer with retry-aware seed."""
from __future__ import annotations
from pathlib import Path
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.coder import make_coder_tools
from agent.v6.state import V6State


CODER_SYSTEM_PROMPT = """\
You are the EcoOS Coder.

You receive a plan and a project_dir. Write the implementation as files inside \
project_dir using `write_file`, `edit_file`. You can read SDK headers under the \
`downloaded_paths`. You DO NOT have shell or build tools — your only job is files.

On retry, READ the current files first (`read_file`, `grep`) to understand the \
state before modifying. Don't blindly rewrite — locate the issue and fix it.

When the implementation is complete and consistent, call `mark_code_done` with \
a short Markdown summary of files created/modified."""


def _build_coder_seed(state: V6State) -> str:
    base = (
        f"User request:\n{state['user_request']}\n\n"
        f"Plan:\n{state['plan_md']}\n\n"
        f"Project dir: {state['project_dir']}\n"
        f"Available components: {state.get('downloaded_paths', [])}\n"
    )
    if state.get("retry_count", 0) == 0:
        return base + "\nImplement the plan from scratch. Use write_file to create files."

    fb = []
    origin = state.get("last_failure_origin", "")
    if origin == "builder":
        fb.append(f"## Previous build failed\n{state.get('build_log', '')}")
    elif origin == "tester":
        fb.append(f"## Previous test failed\n{state.get('tester_report_md', '')}")
    return (
        base
        + f"\nThis is retry #{state['retry_count']}. Existing files are in project_dir — "
        + "READ them first via read_file/grep, then fix the issue:\n\n"
        + "\n\n".join(fb)
    )


def coder_node(state: V6State, *, llm, max_iters: int = 50) -> dict:
    project_dir = Path(state["project_dir"])
    downloaded = [Path(p) for p in state.get("downloaded_paths", [])]
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=downloaded)

    agent = EcoAgent(
        llm=llm,
        system_prompt=CODER_SYSTEM_PROMPT,
        tools=tools,
        stop_tool="mark_code_done",
        max_iters=max_iters,
    )
    result = agent.run(_build_coder_seed(state))

    if result.status == "done":
        return {
            "phase": "building",
            "coder_summary_md": result.stop_payload["summary_md"],
            "coder_messages": result.history,
        }
    return {
        "phase": "failed_escalated",
        "last_status": f"coder_{result.status}",
        "coder_messages": result.history,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_coder_node.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/nodes/coder.py agent/v6/tests/test_coder_node.py
git commit -m "feat(v6): add coder_node with retry-aware seed (build_log / tester_report)"
```

---

### Task C5: nodes/builder.py

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/builder.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_builder_node.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_builder_node.py`:

```python
import subprocess
from pathlib import Path
from agent.v6.nodes.builder import builder_node
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


def test_builder_node_pass_transitions_to_testing(monkeypatch, project_dir):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "ok", "stderr": ""})())
    state = make_initial_v6_state("x")
    state["project_dir"] = str(project_dir)
    state["coder_summary_md"] = "x"
    state["retry_count"] = 0
    state["max_retries"] = 3

    llm = ScriptedChatModel(script=[
        ai_tool("run_make", {}, "c1"),
        ai_tool("report_build_pass", {"artifact_path": str(project_dir / "app.exe")}, "c2"),
    ])
    delta = builder_node(state, llm=llm,
                         vcvarsall=Path("C:/vc.bat"), make_exe=Path("C:/make.exe"))
    assert delta["phase"] == "testing"
    assert delta["build_artifact"].endswith("app.exe")


def test_builder_node_fail_increments_retry_and_returns_to_coding(monkeypatch, project_dir):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "boom", "stderr": ""})())
    state = make_initial_v6_state("x")
    state["project_dir"] = str(project_dir)
    state["retry_count"] = 0
    state["max_retries"] = 3

    llm = ScriptedChatModel(script=[
        ai_tool("run_make", {}, "c1"),
        ai_tool("report_build_fail", {"error_md": "## Error\nboom"}, "c2"),
    ])
    delta = builder_node(state, llm=llm,
                         vcvarsall=Path("C:/vc.bat"), make_exe=Path("C:/make.exe"))
    assert delta["phase"] == "coding"
    assert delta["retry_count"] == 1
    assert delta["last_failure_origin"] == "builder"
    assert "boom" in delta["build_log"]


def test_builder_node_fail_at_max_retries_escalates(monkeypatch, project_dir):
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": ""})())
    state = make_initial_v6_state("x")
    state["project_dir"] = str(project_dir)
    state["retry_count"] = 2     # one away from max
    state["max_retries"] = 3

    llm = ScriptedChatModel(script=[
        ai_tool("run_make", {}, "c1"),
        ai_tool("report_build_fail", {"error_md": "## Err"}, "c2"),
    ])
    delta = builder_node(state, llm=llm,
                         vcvarsall=Path("C:/vc.bat"), make_exe=Path("C:/make.exe"))
    assert delta["phase"] == "failed_escalated"
    assert delta["retry_count"] == 3
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_builder_node.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement nodes/builder.py**

```python
"""BUILDER node — runs build via vcvarsall+make; routes on pass/fail."""
from __future__ import annotations
from pathlib import Path
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.builder import make_builder_tools
from agent.v6.state import V6State


BUILDER_SYSTEM_PROMPT = """\
You are the EcoOS Builder.

You receive a project_dir with the source files prepared by the Coder. Invoke \
`run_make` to build it. Inspect output via `read_file` / `list_dir` if helpful.

On SUCCESS: call `report_build_pass` with the absolute path to the built \
executable.

On FAILURE: read the build output, extract the KEY error(s) (not the raw log), \
and call `report_build_fail` with a Markdown summary that the Coder can act on."""


def builder_node(state: V6State, *, llm, vcvarsall: Path, make_exe: Path,
                 max_iters: int = 15) -> dict:
    project_dir = Path(state["project_dir"])
    tools = make_builder_tools(project_dir=project_dir, vcvarsall=vcvarsall, make_exe=make_exe)

    seed = (
        f"Build the project at {project_dir}.\n"
        f"Available components: {state.get('downloaded_paths', [])}\n\n"
        f"Coder summary:\n{state.get('coder_summary_md', '')}\n\n"
        "Run the build, then report pass or fail."
    )
    agent = EcoAgent(
        llm=llm,
        system_prompt=BUILDER_SYSTEM_PROMPT,
        tools=tools,
        stop_tool=["report_build_pass", "report_build_fail"],
        max_iters=max_iters,
    )
    result = agent.run(seed)

    if result.status != "done":
        return {
            "phase": "failed_escalated",
            "last_status": f"builder_{result.status}",
            "builder_messages": result.history,
        }

    if result.stop_tool_name == "report_build_pass":
        return {
            "phase": "testing",
            "build_artifact": result.stop_payload["artifact_path"],
            "builder_messages": result.history,
        }

    # report_build_fail
    new_retry = state.get("retry_count", 0) + 1
    return {
        "build_log": result.stop_payload["error_md"],
        "retry_count": new_retry,
        "last_failure_origin": "builder",
        "phase": "failed_escalated" if new_retry >= state.get("max_retries", 3) else "coding",
        "builder_messages": result.history,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_builder_node.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/nodes/builder.py agent/v6/tests/test_builder_node.py
git commit -m "feat(v6): add builder_node (run_make + pass/fail routing + retry counter)"
```

---

### Task C6: nodes/tester.py

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/tester.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_tester_node.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_tester_node.py`:

```python
import subprocess
from pathlib import Path
from agent.v6.nodes.tester import tester_node, _build_tester_seed
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


def test_tester_seed_does_not_include_coder_summary():
    state = make_initial_v6_state("calc")
    state["plan_md"] = "# Plan\n## Acceptance criteria\n- prints 5"
    state["coder_summary_md"] = "I wrote main.c with broken logic"
    state["build_artifact"] = "/tmp/app.exe"
    seed = _build_tester_seed(state)
    assert "broken logic" not in seed
    assert "Acceptance criteria" in seed
    assert "/tmp/app.exe" in seed


def test_tester_node_pass(monkeypatch, project_dir):
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "5", "stderr": ""})())
    state = make_initial_v6_state("calc")
    state["build_artifact"] = str(artifact)
    state["plan_md"] = "# Plan\n## Acceptance criteria\n- prints 5"
    state["retry_count"] = 0
    state["max_retries"] = 3

    llm = ScriptedChatModel(script=[
        ai_tool("run_artifact", {"timeout_s": 5}, "c1"),
        ai_tool("report_test_pass", {"reason_md": "stdout contains 5"}, "c2"),
    ])
    delta = tester_node(state, llm=llm)
    assert delta["phase"] == "done"
    assert delta["last_status"] == "success"


def test_tester_node_fail_returns_to_coding(monkeypatch, project_dir):
    artifact = project_dir / "app.exe"
    artifact.write_text("")
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "8", "stderr": ""})())
    state = make_initial_v6_state("calc")
    state["build_artifact"] = str(artifact)
    state["plan_md"] = "# Plan\n## Acceptance criteria\n- prints 5"
    state["retry_count"] = 0
    state["max_retries"] = 3

    llm = ScriptedChatModel(script=[
        ai_tool("run_artifact", {"timeout_s": 5}, "c1"),
        ai_tool("report_test_fail", {"reason_md": "expected 5, got 8"}, "c2"),
    ])
    delta = tester_node(state, llm=llm)
    assert delta["phase"] == "coding"
    assert delta["retry_count"] == 1
    assert delta["last_failure_origin"] == "tester"
    assert "expected 5" in delta["tester_report_md"]
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_tester_node.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement nodes/tester.py**

```python
"""TESTER node — LLM-judge isolated from coder_summary."""
from __future__ import annotations
import re
from pathlib import Path
from agent.v6.eco_agent import EcoAgent
from agent.v6.tools.tester import make_tester_tools
from agent.v6.state import V6State


TESTER_SYSTEM_PROMPT = """\
You are the EcoOS Tester. You CANNOT see the source code or any coder notes — \
only the user's original request, the plan's acceptance criteria, and the \
built artifact at a given path.

Call `run_artifact` to execute the binary and capture stdout/stderr/exit. \
Compare the runtime behavior against the acceptance criteria. Decide pass/fail \
based on OBSERVABLE behavior only — not assumptions about what the code might do.

Then call either `report_test_pass(reason_md)` or `report_test_fail(reason_md)`. \
On fail, be specific: what did you expect, what did you see, what should be fixed."""


def _extract_acceptance(plan_md: str) -> str:
    """Extract the '## Acceptance criteria' section if present."""
    match = re.search(r"##\s+Acceptance\s+criteria.*?(?=\n##\s|\Z)",
                      plan_md, re.IGNORECASE | re.DOTALL)
    return match.group(0).strip() if match else "(no acceptance criteria section found)"


def _build_tester_seed(state: V6State) -> str:
    return (
        f"User request:\n{state['user_request']}\n\n"
        f"Acceptance criteria from plan:\n{_extract_acceptance(state['plan_md'])}\n\n"
        f"Built artifact: {state['build_artifact']}\n\n"
        "Run the artifact and judge by behavior only. You cannot read source files."
    )


def tester_node(state: V6State, *, llm, max_iters: int = 10) -> dict:
    artifact = Path(state["build_artifact"])
    tools = make_tester_tools(build_artifact=artifact)

    agent = EcoAgent(
        llm=llm,
        system_prompt=TESTER_SYSTEM_PROMPT,
        tools=tools,
        stop_tool=["report_test_pass", "report_test_fail"],
        max_iters=max_iters,
    )
    result = agent.run(_build_tester_seed(state))

    if result.status != "done":
        return {
            "phase": "failed_escalated",
            "last_status": f"tester_{result.status}",
            "tester_messages": result.history,
        }

    if result.stop_tool_name == "report_test_pass":
        return {
            "phase": "done",
            "last_status": "success",
            "tester_report_md": result.stop_payload["reason_md"],
            "tester_messages": result.history,
        }

    new_retry = state.get("retry_count", 0) + 1
    return {
        "tester_report_md": result.stop_payload["reason_md"],
        "retry_count": new_retry,
        "last_failure_origin": "tester",
        "phase": "failed_escalated" if new_retry >= state.get("max_retries", 3) else "coding",
        "tester_messages": result.history,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_tester_node.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/nodes/tester.py agent/v6/tests/test_tester_node.py
git commit -m "feat(v6): add tester_node (LLM-judge, isolated from coder_summary)"
```

---

### Task C7: nodes/escalate.py

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/escalate.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_escalate_node.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_escalate_node.py`:

```python
import pytest
from langgraph.errors import GraphInterrupt
from agent.v6.nodes.escalate import escalate_node
from agent.v6.state import make_initial_v6_state


def test_escalate_raises_interrupt_with_diagnostics():
    state = make_initial_v6_state("x")
    state["retry_count"] = 3
    state["last_failure_origin"] = "tester"
    state["build_log"] = "## BUILD ERR"
    state["tester_report_md"] = "## TEST ERR"
    state["plan_md"] = "# Plan"
    state["coder_summary_md"] = "summary"
    with pytest.raises(GraphInterrupt) as ei:
        escalate_node(state)
    payload = ei.value.args[0][0].value
    assert payload["failure_origin"] == "tester"
    assert payload["retry_count"] == 3
    assert payload["build_log"] == "## BUILD ERR"
    assert payload["tester_report_md"] == "## TEST ERR"
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_escalate_node.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement nodes/escalate.py**

```python
"""ESCALATE — interrupt() asking user to continue or abort."""
from __future__ import annotations
from langgraph.types import interrupt
from agent.v6.state import V6State


def escalate_node(state: V6State) -> dict:
    resume = interrupt({
        "failure_origin":   state.get("last_failure_origin", ""),
        "retry_count":      state.get("retry_count", 0),
        "build_log":        state.get("build_log", ""),
        "tester_report_md": state.get("tester_report_md", ""),
        "plan_md":          state.get("plan_md", ""),
        "coder_summary_md": state.get("coder_summary_md", ""),
    })
    # resume value: {"continue": bool}
    if resume.get("continue", False):
        return {
            "retry_count": 0,
            "last_status": "user_continue",
            "phase": "coding",
        }
    return {"phase": "done", "last_status": "user_aborted"}
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_escalate_node.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/nodes/escalate.py agent/v6/tests/test_escalate_node.py
git commit -m "feat(v6): add escalate_node (interrupt with full diagnostic payload)"
```

---

## Phase D — Graph wiring

### Task D1: graph.py — routing + create_v6_graph

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/graph.py`
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_graph_routing.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_graph_routing.py`:

```python
from langgraph.graph import END
from agent.v6.graph import (
    route_after_plan_gate, route_after_builder, route_after_tester, route_after_escalate,
)


def test_route_after_plan_gate_setup():
    assert route_after_plan_gate({"phase": "setup"}) == "setup"


def test_route_after_plan_gate_aborted():
    assert route_after_plan_gate({"phase": "done"}) == END


def test_route_after_builder_testing():
    assert route_after_builder({"phase": "testing"}) == "tester"


def test_route_after_builder_coding():
    assert route_after_builder({"phase": "coding"}) == "coder"


def test_route_after_builder_escalate():
    assert route_after_builder({"phase": "failed_escalated"}) == "escalate"


def test_route_after_tester_done():
    assert route_after_tester({"phase": "done"}) == END


def test_route_after_tester_coding():
    assert route_after_tester({"phase": "coding"}) == "coder"


def test_route_after_escalate_continue():
    assert route_after_escalate({"last_status": "user_continue", "phase": "coding"}) == "coder"


def test_route_after_escalate_abort():
    assert route_after_escalate({"last_status": "user_aborted", "phase": "done"}) == END
```

- [ ] **Step 2: Run tests, verify fail**

```bash
pytest agent/v6/tests/test_graph_routing.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement graph.py**

```python
"""V6 graph wiring."""
from __future__ import annotations
from pathlib import Path
from langgraph.graph import StateGraph, END
from agent.v6.state import V6State
from agent.v6.nodes.planner import planner_node
from agent.v6.nodes.plan_gate import plan_gate_node
from agent.v6.nodes.setup import setup_node
from agent.v6.nodes.coder import coder_node
from agent.v6.nodes.builder import builder_node
from agent.v6.nodes.tester import tester_node
from agent.v6.nodes.escalate import escalate_node


def route_after_plan_gate(s: V6State) -> str:
    return "setup" if s["phase"] == "setup" else END


def route_after_builder(s: V6State) -> str:
    return {"testing": "tester", "coding": "coder", "failed_escalated": "escalate"}.get(s["phase"], END)


def route_after_tester(s: V6State) -> str:
    return {"done": END, "coding": "coder", "failed_escalated": "escalate"}.get(s["phase"], END)


def route_after_escalate(s: V6State) -> str:
    return "coder" if s.get("last_status") == "user_continue" else END


def create_v6_graph(
    llm,
    *,
    sdk_root: Path,
    cli_path: Path,
    vcvarsall: Path,
    make_exe: Path,
    checkpointer=None,
):
    """Build the V6 graph. All node-specific config (paths) is captured by closures."""
    g = StateGraph(V6State)

    g.add_node("planner",   lambda s: planner_node(s, llm=llm, sdk_root=sdk_root))
    g.add_node("plan_gate", plan_gate_node)
    g.add_node("setup",     lambda s: setup_node(s, llm=llm, cli_path=cli_path))
    g.add_node("coder",     lambda s: coder_node(s, llm=llm))
    g.add_node("builder",   lambda s: builder_node(s, llm=llm, vcvarsall=vcvarsall, make_exe=make_exe))
    g.add_node("tester",    lambda s: tester_node(s, llm=llm))
    g.add_node("escalate",  escalate_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "plan_gate")
    g.add_conditional_edges("plan_gate", route_after_plan_gate,
                            {"setup": "setup", END: END})
    g.add_edge("setup", "coder")
    g.add_edge("coder", "builder")
    g.add_conditional_edges("builder", route_after_builder,
                            {"tester": "tester", "coder": "coder", "escalate": "escalate", END: END})
    g.add_conditional_edges("tester",  route_after_tester,
                            {END: END, "coder": "coder", "escalate": "escalate"})
    g.add_conditional_edges("escalate", route_after_escalate,
                            {"coder": "coder", END: END})

    return g.compile(checkpointer=checkpointer)
```

- [ ] **Step 4: Run tests**

```bash
pytest agent/v6/tests/test_graph_routing.py -v
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/v6/graph.py agent/v6/tests/test_graph_routing.py
git commit -m "feat(v6): wire 5-node graph + routing functions"
```

---

## Phase E — Graph E2E with mocked LLM

### Task E2: test_graph_e2e.py — 5 scenarios

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_graph_e2e.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_graph_e2e.py`:

```python
"""End-to-end graph tests with ScriptedChatModel + mocked subprocess.

These tests verify the FULL flow through the LangGraph compiled graph:
- happy path
- user rejects plan
- build fail -> retry -> success
- max retries -> escalate -> continue -> success
- max retries -> escalate -> abort
"""
from __future__ import annotations
import subprocess
from pathlib import Path
import pytest
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from agent.v6.graph import create_v6_graph
from agent.v6.state import make_initial_v6_state
from agent.v6.tests.conftest import ScriptedChatModel, ai_tool


@pytest.fixture
def sdk_root(tmp_path):
    root = tmp_path / "sdk"
    pkg = root / "Eco.X_DK_v.1.0.1.2" / "SharedFiles"
    pkg.mkdir(parents=True)
    (pkg / "IEcoX.h").write_text("/*x*/")
    return root


@pytest.fixture
def fake_paths(tmp_path):
    cli = tmp_path / "eco-cli.exe"; cli.write_text("")
    vc  = tmp_path / "vcvarsall.bat"; vc.write_text("")
    mk  = tmp_path / "make.exe"; mk.write_text("")
    return {"cli_path": cli, "vcvarsall": vc, "make_exe": mk}


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Default: every subprocess.run succeeds. Tests can override via the dict."""
    state = {"runs": []}
    def fake_run(cmd, **kw):
        state["runs"].append(cmd)
        class R: returncode = 0; stdout = "ok"; stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    return state


def _planner_script(project_dir: Path):
    """Script: planner immediately calls submit_plan."""
    return ai_tool("submit_plan", {
        "project_name": "App",
        "plan_md": f"# Plan\n## Acceptance criteria\n- runs",
        "components": [{"cid": "X" * 32, "version": "1.0.1.2", "name": "Eco.X", "reason": "r"}],
        "acceptance_criteria": ["runs"],
    }, "p1")


def _setup_script():
    return [
        ai_tool("ecoos_pull", {"cid": "X" * 32, "version": "1.0.1.2"}, "s1"),
        ai_tool("mark_setup_done", {"downloaded_paths": []}, "s2"),
    ]


def _coder_script(project_dir: Path):
    target = project_dir / "EcoMain.c"
    return [
        ai_tool("write_file", {"path": str(target), "content": "int main(){return 0;}"}, "c1"),
        ai_tool("mark_code_done", {"summary_md": "wrote main"}, "c2"),
    ]


def _builder_pass_script(project_dir: Path):
    return [
        ai_tool("run_make", {}, "b1"),
        ai_tool("report_build_pass", {"artifact_path": str(project_dir / "app.exe")}, "b2"),
    ]


def _builder_fail_script():
    return [
        ai_tool("run_make", {}, "b1"),
        ai_tool("report_build_fail", {"error_md": "## Err\nundefined ref"}, "b2"),
    ]


def _tester_pass_script():
    return [
        ai_tool("run_artifact", {"timeout_s": 5}, "t1"),
        ai_tool("report_test_pass", {"reason_md": "ok"}, "t2"),
    ]


def test_happy_path(sdk_root, fake_paths, mock_subprocess, project_dir):
    script = [
        _planner_script(project_dir),
        *_setup_script(),
        *_coder_script(project_dir),
        *_builder_pass_script(project_dir),
        *_tester_pass_script(),
    ]
    llm = ScriptedChatModel(script=script)
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-happy"}}
    initial = make_initial_v6_state("build x")
    initial["project_dir"] = str(project_dir)

    # First run — should pause at plan_gate
    list(graph.stream(initial, config))
    state = graph.get_state(config).values
    assert state["phase"] == "awaiting_approval"

    # Resume with approval
    list(graph.stream(Command(resume={"approved": True}), config))
    final = graph.get_state(config).values
    assert final["last_status"] == "success"
    assert final["phase"] == "done"


def test_user_rejects_plan(sdk_root, fake_paths, mock_subprocess, project_dir):
    llm = ScriptedChatModel(script=[_planner_script(project_dir)])
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-reject"}}
    initial = make_initial_v6_state("x")
    initial["project_dir"] = str(project_dir)
    list(graph.stream(initial, config))

    list(graph.stream(Command(resume={"approved": False, "reason": "no"}), config))
    final = graph.get_state(config).values
    assert final["last_status"] == "user_aborted"


def test_build_fail_retry_success(sdk_root, fake_paths, mock_subprocess, project_dir):
    script = [
        _planner_script(project_dir),
        *_setup_script(),
        *_coder_script(project_dir),           # coder #1
        *_builder_fail_script(),               # builder fails
        *_coder_script(project_dir),           # coder #2 (retry)
        *_builder_pass_script(project_dir),    # builder passes
        *_tester_pass_script(),
    ]
    llm = ScriptedChatModel(script=script)
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-retry"}}
    initial = make_initial_v6_state("x")
    initial["project_dir"] = str(project_dir)

    list(graph.stream(initial, config))
    list(graph.stream(Command(resume={"approved": True}), config))
    final = graph.get_state(config).values
    assert final["last_status"] == "success"
    assert final["retry_count"] == 1


def test_max_retry_user_continue_then_pass(sdk_root, fake_paths, mock_subprocess, project_dir):
    script = [
        _planner_script(project_dir),
        *_setup_script(),
        *_coder_script(project_dir),  # iter 1
        *_builder_fail_script(),
        *_coder_script(project_dir),  # iter 2
        *_builder_fail_script(),
        *_coder_script(project_dir),  # iter 3
        *_builder_fail_script(),       # retry 3 -> escalate
        *_coder_script(project_dir),  # after user_continue: retry resets, iter 1
        *_builder_pass_script(project_dir),
        *_tester_pass_script(),
    ]
    llm = ScriptedChatModel(script=script)
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-max-cont"}}
    initial = make_initial_v6_state("x", max_retries=3)
    initial["project_dir"] = str(project_dir)

    list(graph.stream(initial, config))                                      # planner -> gate
    list(graph.stream(Command(resume={"approved": True}), config))           # -> escalate
    list(graph.stream(Command(resume={"continue": True}), config))           # continue -> pass
    final = graph.get_state(config).values
    assert final["last_status"] == "success"


def test_max_retry_user_aborts(sdk_root, fake_paths, mock_subprocess, project_dir):
    script = [
        _planner_script(project_dir),
        *_setup_script(),
        *_coder_script(project_dir),
        *_builder_fail_script(),
        *_coder_script(project_dir),
        *_builder_fail_script(),
        *_coder_script(project_dir),
        *_builder_fail_script(),     # -> escalate
    ]
    llm = ScriptedChatModel(script=script)
    graph = create_v6_graph(llm, sdk_root=sdk_root, **fake_paths,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "t-max-abort"}}
    initial = make_initial_v6_state("x", max_retries=3)
    initial["project_dir"] = str(project_dir)

    list(graph.stream(initial, config))
    list(graph.stream(Command(resume={"approved": True}), config))
    list(graph.stream(Command(resume={"continue": False}), config))
    final = graph.get_state(config).values
    assert final["last_status"] == "user_aborted"
```

- [ ] **Step 2: Run tests**

```bash
pytest agent/v6/tests/test_graph_e2e.py -v
```
Expected: 5 passed. If any fail, fix the relevant node/graph code (don't rewrite tests) and rerun.

- [ ] **Step 3: Commit**

```bash
git add agent/v6/tests/test_graph_e2e.py
git commit -m "test(v6): graph E2E — happy, reject, retry, escalate-continue, escalate-abort"
```

---

## Phase F — Live E2E (optional, manual)

### Task F1: test_live_e2e.py — real LLM, calculator app

**Files:**
- Create: `Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_live_e2e.py`

- [ ] **Step 1: Write the live test**

`tests/test_live_e2e.py`:

```python
"""Live E2E — real OpenRouter LLM, real subprocess.

Run manually with: pytest agent/v6/tests/test_live_e2e.py -v --live -s
NOT in CI. Requires:
  - OPENAI_API_KEY (OpenRouter token) in .env
  - eco-cli.exe present at H:/ai-hse-diploma-agent/eco.sli/eco-cli.exe
  - MSVC vcvarsall.bat at the known path
  - make.exe at C:/Users/gaevy/gcc/bin/make.exe
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import pytest
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver


def pytest_collection_modifyitems(config, items):
    """--live gate."""
    if not config.getoption("--live", default=False):
        skip = pytest.mark.skip(reason="needs --live")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip)


@pytest.mark.live
@pytest.mark.timeout(600)
def test_calculator_app():
    from agent.main import get_llm
    from agent.v6.graph import create_v6_graph
    from agent.v6.state import make_initial_v6_state

    project_root = Path(__file__).resolve().parents[4]   # repo root
    sdk_root  = project_root / "source"
    cli_path  = project_root / "eco.sli" / "eco-cli.exe"
    vcvarsall = Path(r"C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvarsall.bat")
    make_exe  = Path(r"C:/Users/gaevy/gcc/bin/make.exe")
    out_dir   = project_root / "output" / "v6_live_calc"
    out_dir.mkdir(parents=True, exist_ok=True)

    llm = get_llm()
    graph = create_v6_graph(llm, sdk_root=sdk_root, cli_path=cli_path,
                            vcvarsall=vcvarsall, make_exe=make_exe,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "live-calc-1"}, "recursion_limit": 100}
    initial = make_initial_v6_state("калькулятор: сложение двух чисел")
    initial["project_dir"] = str(out_dir)

    # 1. planner runs until interrupt
    for ev in graph.stream(initial, config):
        if "__interrupt__" in ev:
            break
    state = graph.get_state(config).values
    assert state["phase"] == "awaiting_approval"
    assert state["plan_md"], "planner produced no plan_md"
    assert state["components"], "planner produced no components"
    print(f"\n[plan]\n{state['plan_md']}\n")

    # 2. approve
    for _ in graph.stream(Command(resume={"approved": True}), config):
        pass
    final = graph.get_state(config).values
    print(f"\n[status] {final['last_status']}, phase={final['phase']}")
    print(f"[artifact] {final.get('build_artifact', '(none)')}")
    assert final["last_status"] == "success", f"pipeline failed: {final}"
    assert Path(final["build_artifact"]).exists()
```

Also add to repo `conftest.py` at project root (or `Eco.Toolchain/Eco.AI.Assembly1/conftest.py`):

```python
def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False,
                     help="enable @pytest.mark.live tests")
```

- [ ] **Step 2: Verify the test is skipped without `--live`**

```bash
pytest agent/v6/tests/test_live_e2e.py -v
```
Expected: 1 skipped.

- [ ] **Step 3: (manual) run with `--live` once everything's connected**

```bash
pytest agent/v6/tests/test_live_e2e.py -v --live -s
```
Expected: long-running test that ends in `last_status=success` and produces a real .exe.

- [ ] **Step 4: Commit**

```bash
git add agent/v6/tests/test_live_e2e.py Eco.Toolchain/Eco.AI.Assembly1/conftest.py
git commit -m "test(v6): live E2E — real OpenRouter LLM + real subprocess (manual)"
```

---

## Phase G — Wrap-up

### Task G1: Final pytest sweep + coverage check

- [ ] **Step 1: Run the full V6 test suite**

```bash
cd Eco.Toolchain/Eco.AI.Assembly1
pytest agent/v6/tests/ -v --ignore=agent/v6/tests/test_live_e2e.py
```
Expected: ~50 tests passing (some counts: state=4, eco_agent_types=6, eco_agent=9, common=11, planner_tools=4, setup_tools=6, coder_tools=7, builder_tools=3, tester_tools=4, planner_node=3, plan_gate=1, setup_node=2, coder_node=4, builder_node=3, tester_node=3, escalate_node=1, graph_routing=9, graph_e2e=5).

- [ ] **Step 2: Check coverage of EcoAgent**

```bash
pip install pytest-cov
pytest agent/v6/tests/test_eco_agent.py --cov=agent/v6/eco_agent --cov-report=term-missing
```
Expected: 95%+ coverage on `eco_agent.py`.

- [ ] **Step 3: Add a short README to `agent/v6/`**

Create `agent/v6/README.md`:

```markdown
# V6 — Five-Node Pipeline

Spec: `docs/superpowers/specs/2026-05-13-v6-pipeline-design.md`
Plan: `docs/superpowers/plans/2026-05-13-v6-agent-layer.md`

## Entry point

```python
from agent.v6.graph import create_v6_graph
from agent.v6.state import make_initial_v6_state
from langgraph.checkpoint.sqlite import SqliteSaver

graph = create_v6_graph(
    llm,
    sdk_root=Path("source"),
    cli_path=Path("eco.sli/eco-cli.exe"),
    vcvarsall=Path(r"C:/.../vcvarsall.bat"),
    make_exe=Path("C:/Users/gaevy/gcc/bin/make.exe"),
    checkpointer=SqliteSaver.from_conn_string("./.eco/v6_checkpoints.db"),
)

initial = make_initial_v6_state("build a calculator")
initial["project_dir"] = "./output/Calc1"
```

## Tests

`pytest agent/v6/tests/` — unit + integration, ~50 tests, no network.
`pytest agent/v6/tests/test_live_e2e.py --live -s` — real LLM, real build.
```

- [ ] **Step 4: Commit**

```bash
git add agent/v6/README.md
git commit -m "docs(v6): add agent.v6 README pointing to spec + plan"
```

- [ ] **Step 5: Final branch state**

```bash
git log --oneline feat/v5-three-node-pipeline..HEAD
```
Expected: ~22 commits, one per task, all green.

---

## Coverage check vs spec

| Spec section | Plan task(s) |
|---|---|
| §5.2 V6State | A2 |
| §5.3 Checkpointer | D1 (`create_v6_graph(..., checkpointer)`) + F1 (live uses MemorySaver) |
| §5.4 Handoff principle | enforced by per-node tests (C1–C7) — each node only writes its declared state fields |
| §6 EcoAgent contract | A3, A4 |
| §7.1 PLANNER | C1, B2 |
| §7.2 PLAN_GATE | C2 |
| §7.3 SETUP | C3, B3 |
| §7.4 CODER | C4, B4 |
| §7.5 BUILDER | C5, B5 |
| §7.6 TESTER (isolation) | C6 (explicit test that seed excludes coder_summary), B6 (explicit test no read_file in tools) |
| §7.7 ESCALATE | C7 |
| §8 Data flow / routing | D1 |
| §11 Testing strategy | A4 (9 EcoAgent tests), B1–B6 (tool tests), C1–C7 (node tests), E2 (graph E2E), F1 (live) |
| §9, §10 Backend + Frontend | OUT OF SCOPE (separate plans) |

No spec section is uncovered within the agent-layer scope.
