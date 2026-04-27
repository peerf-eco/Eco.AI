# V4 Three-Node Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace V4 architect-ReAct with explicit three-node LangGraph pipeline (Planner → Coder → Executor) using Markdown-payload tool handoffs, no `with_structured_output`, no `interrupt()`.

**Architecture:** Three ReAct sub-agents stitched into one StateGraph. Routing via `state.phase` field updated by handoff tools using `Command(update=...)`. State persists across user messages via MemorySaver + single `thread_id` per session. Markdown payloads (`plan_md`, `coder_summary_md`, `feedback_md`) carry inter-node data; deterministic regex parsers extract structured info. Coder ↔ Executor loop bounded by `max_iterations`.

**Tech Stack:** Python 3.11, LangGraph 0.2+, langchain-core, langchain-openai, Pydantic v2, pytest, FastAPI, Next.js + React + TypeScript.

**Spec:** [`docs/superpowers/specs/2026-04-27-v4-three-node-design.md`](../specs/2026-04-27-v4-three-node-design.md)

**Working directory for all commands:** `H:\ai-hse-diploma-agent\Eco.Toolchain\Eco.AI.Assembly1\` (refer to as `<root>`).

---

## File Structure

**Created files:**
- `agent/state_v5.py` — `AppState` TypedDict.
- `agent/parsers.py` — `parse_plan()`, `parse_feedback()` (pure regex, no LLM).
- `agent/planner.py` — `create_planner_node(llm)` + planner tools.
- `agent/executor.py` — `create_executor_node(llm)` + executor tools.
- `agent/three_node_graph.py` — graph assembly + routing.
- `agent/test_state_v5.py`
- `agent/test_parsers.py`
- `agent/test_planner.py`
- `agent/test_executor.py`
- `agent/test_three_node_graph.py`
- `agent/test_v5_e2e.py`

**Modified files:**
- `agent/coder.py` — add `done` handoff tool, accept `plan_md`/`feedback_md` from `coder_messages` system message.
- `agent/chat_agent.py` — `create_chat_agent_v5()` wraps the new graph; old `create_chat_agent` (V4) kept as legacy.
- `backend/server.py` — new event types (`phase_change`, `plan_draft`, `coder_progress`, `executor_progress`, `final_result`).
- `frontend/components/chat/chat-interface.tsx` — render phase indicator, render `plan_md` Markdown with Approve button.

**Files unchanged but reused:** `agent/tools.py` (rag_query, list_all_components, download_component, build_node, run_tests), `agent/resolver.py`, `agent/header_parser.py`, `agent/skills/c.md`, `agent/prompts_v4.py` (CODER_SYSTEM_PROMPT extended).

---

## Task 1: State schema (`state_v5.py`)

**Files:**
- Create: `agent/state_v5.py`
- Test: `agent/test_state_v5.py`

- [ ] **Step 1: Write the failing test**

Create `agent/test_state_v5.py`:

```python
from agent.state_v5 import AppState, make_initial_state


def test_initial_state_has_planning_phase():
    state = make_initial_state(user_request="build calc", max_iterations=5)
    assert state["phase"] == "planning"
    assert state["iteration"] == 0
    assert state["max_iterations"] == 5
    assert state["plan_md"] == ""
    assert state["coder_summary_md"] == ""
    assert state["feedback_md"] == ""
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
```

- [ ] **Step 2: Run test to verify it fails**

```
cd <root>
python -m pytest agent/test_state_v5.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agent.state_v5'`.

- [ ] **Step 3: Implement `state_v5.py`**

Create `agent/state_v5.py`:

```python
"""V5 state — Three-Node Pipeline (Planner / Coder / Executor)."""

from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


Phase = Literal["planning", "coding", "executing", "done"]


class AppState(TypedDict):
    user_request: str

    planner_messages:  Annotated[list, add_messages]
    coder_messages:    Annotated[list, add_messages]
    executor_messages: Annotated[list, add_messages]

    plan_md:          str
    coder_summary_md: str
    feedback_md:      str

    phase: Phase

    project_dir:  str
    project_name: str

    iteration:      int
    max_iterations: int
    last_status:    str  # "" | "success" | "max_iterations_reached" | "parse_failure" | "user_aborted"


def make_initial_state(user_request: str, max_iterations: int = 5) -> AppState:
    return {
        "user_request": user_request,
        "planner_messages":  [{"role": "user", "content": user_request}],
        "coder_messages":    [],
        "executor_messages": [],
        "plan_md":          "",
        "coder_summary_md": "",
        "feedback_md":      "",
        "phase":         "planning",
        "project_dir":   "",
        "project_name":  "",
        "iteration":      0,
        "max_iterations": max_iterations,
        "last_status":    "",
    }
```

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest agent/test_state_v5.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/state_v5.py agent/test_state_v5.py
git commit -m "feat(v5): add AppState schema and initial-state factory"
```

---

## Task 2: PRD parser (`parsers.py::parse_plan`)

**Files:**
- Create: `agent/parsers.py`
- Test: `agent/test_parsers.py`

- [ ] **Step 1: Write the failing test**

Create `agent/test_parsers.py`:

```python
from agent.parsers import parse_plan


SAMPLE_PRD = """\
## Project: Calc1

A simple calculator with logging.

## Components

- **Eco.Math.C89** — source: sdk — provides arithmetic primitives
- **Eco.StdIO.C89** — source: sdk — provides stdin/stdout
- **Eco.Logger1** — source: marketplace — structured logging
- **CalcController** — source: develop — glue logic
  - spec: methods Add(a,b), Subtract(a,b); depends on Math.C89

## Build target

- Platform: Windows
- Output: calc.exe

## Acceptance criteria

- Reads two numbers from stdin
- Prints sum to stdout
"""


def test_parse_plan_extracts_project_name():
    result = parse_plan(SAMPLE_PRD)
    assert result["project_name"] == "Calc1"


def test_parse_plan_extracts_all_components():
    result = parse_plan(SAMPLE_PRD)
    names = [c["name"] for c in result["components"]]
    assert names == ["Eco.Math.C89", "Eco.StdIO.C89", "Eco.Logger1", "CalcController"]


def test_parse_plan_extracts_sources():
    result = parse_plan(SAMPLE_PRD)
    sources = [c["source"] for c in result["components"]]
    assert sources == ["sdk", "sdk", "marketplace", "develop"]


def test_parse_plan_extracts_spec_for_develop():
    result = parse_plan(SAMPLE_PRD)
    develop = [c for c in result["components"] if c["source"] == "develop"][0]
    assert "Add(a,b)" in develop["spec"]


def test_parse_plan_extracts_platform_and_output():
    result = parse_plan(SAMPLE_PRD)
    assert result["platform"] == "Windows"
    assert result["output"] == "calc.exe"


def test_parse_plan_returns_empty_components_on_garbage():
    result = parse_plan("just some prose, no markdown structure")
    assert result["components"] == []
    assert result["project_name"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest agent/test_parsers.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `parse_plan`**

Create `agent/parsers.py`:

```python
"""Pure-Python regex parsers for inter-node Markdown handoffs (V5)."""

import re
from typing import Any


_PROJECT_RE = re.compile(r"^##\s*Project:\s*(?P<name>.+?)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(
    r"^-\s+\*\*(?P<name>[^*]+?)\*\*\s*[—\-]\s*"
    r"source:\s*(?P<source>sdk|marketplace|develop)"
    r"(?:\s*[—\-]\s*(?P<reason>.+?))?$",
    re.MULTILINE,
)
_SPEC_RE = re.compile(r"^\s+-\s*spec:\s*(?P<spec>.+?)$", re.MULTILINE)
_PLATFORM_RE = re.compile(r"^-\s*Platform:\s*(?P<platform>\S+)\s*$", re.MULTILINE)
_OUTPUT_RE = re.compile(r"^-\s*Output:\s*(?P<output>\S+)\s*$", re.MULTILINE)


def parse_plan(plan_md: str) -> dict[str, Any]:
    """Extract structured plan from Markdown PRD.

    Returns dict with keys: project_name, components (list), platform, output.
    On unparseable input, returns empty/default values rather than raising.
    """
    project_match = _PROJECT_RE.search(plan_md)
    project_name = project_match["name"].strip() if project_match else ""

    components: list[dict[str, Any]] = []
    for m in _BULLET_RE.finditer(plan_md):
        components.append({
            "name": m["name"].strip(),
            "source": m["source"],
            "reason": (m["reason"] or "").strip(),
            "spec": None,
        })

    # Attach spec to immediately-preceding develop bullet (if line below is "  - spec: ...")
    bullet_positions = [(m.start(), m.end()) for m in _BULLET_RE.finditer(plan_md)]
    spec_matches = list(_SPEC_RE.finditer(plan_md))
    for i, (b_start, b_end) in enumerate(bullet_positions):
        next_bullet_start = bullet_positions[i + 1][0] if i + 1 < len(bullet_positions) else len(plan_md)
        for sm in spec_matches:
            if b_end < sm.start() < next_bullet_start:
                components[i]["spec"] = sm["spec"].strip()
                break

    platform_match = _PLATFORM_RE.search(plan_md)
    platform = platform_match["platform"] if platform_match else ""
    output_match = _OUTPUT_RE.search(plan_md)
    output = output_match["output"] if output_match else ""

    return {
        "project_name": project_name,
        "components": components,
        "platform": platform,
        "output": output,
    }
```

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest agent/test_parsers.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/parsers.py agent/test_parsers.py
git commit -m "feat(v5): add parse_plan regex extractor with unit tests"
```

---

## Task 3: Feedback parser (`parsers.py::parse_feedback`)

**Files:**
- Modify: `agent/parsers.py`
- Modify: `agent/test_parsers.py`

- [ ] **Step 1: Add the failing test**

Append to `agent/test_parsers.py`:

```python
from agent.parsers import parse_feedback


SAMPLE_FEEDBACK_BUILD = """\
## Stage: build
## Status: FAIL

## Errors
- src/EcoMain.c:42: error C2065: 'IEcoMath' undeclared identifier
- src/EcoMain.c:55: error C2143: missing ';' before identifier

## Suggested focus
- Forgot #include "IEcoMath.h"
"""

SAMPLE_FEEDBACK_TEST = """\
## Stage: test
## Status: FAIL

## Test failures
- test_calc_add: expected 5, got 4
- test_calc_sub: expected 2, got 0
"""


def test_parse_feedback_build_stage():
    result = parse_feedback(SAMPLE_FEEDBACK_BUILD)
    assert result["stage"] == "build"
    assert result["status"] == "FAIL"
    assert len(result["errors"]) == 2
    assert result["errors"][0]["file"] == "src/EcoMain.c"
    assert result["errors"][0]["line"] == 42
    assert "C2065" in result["errors"][0]["message"]


def test_parse_feedback_test_stage():
    result = parse_feedback(SAMPLE_FEEDBACK_TEST)
    assert result["stage"] == "test"
    assert len(result["test_failures"]) == 2
    assert result["test_failures"][0]["test"] == "test_calc_add"
    assert "expected 5" in result["test_failures"][0]["message"]


def test_parse_feedback_empty_input():
    result = parse_feedback("")
    assert result["errors"] == []
    assert result["test_failures"] == []
    assert result["stage"] == ""
```

- [ ] **Step 2: Run tests, see new ones fail**

```
python -m pytest agent/test_parsers.py -v
```

Expected: 3 new tests fail with `ImportError`.

- [ ] **Step 3: Implement `parse_feedback`**

Append to `agent/parsers.py`:

```python
_STAGE_RE = re.compile(r"^##\s*Stage:\s*(?P<stage>\w+)\s*$", re.MULTILINE)
_STATUS_RE = re.compile(r"^##\s*Status:\s*(?P<status>\w+)\s*$", re.MULTILINE)
_ERROR_LINE_RE = re.compile(
    r"^-\s*(?P<file>[^:]+):(?P<line>\d+):\s*(?P<message>.+?)$",
    re.MULTILINE,
)
_TEST_FAIL_RE = re.compile(
    r"^-\s*(?P<test>\w+):\s*(?P<message>.+?)$",
    re.MULTILINE,
)


def parse_feedback(feedback_md: str) -> dict[str, Any]:
    """Extract structured failure info from Executor's back_to_code Markdown."""
    stage_match = _STAGE_RE.search(feedback_md)
    stage = stage_match["stage"] if stage_match else ""

    status_match = _STATUS_RE.search(feedback_md)
    status = status_match["status"] if status_match else ""

    errors_section = _section(feedback_md, "Errors")
    errors = [
        {"file": m["file"].strip(), "line": int(m["line"]), "message": m["message"].strip()}
        for m in _ERROR_LINE_RE.finditer(errors_section)
    ]

    tests_section = _section(feedback_md, "Test failures")
    test_failures = [
        {"test": m["test"], "message": m["message"].strip()}
        for m in _TEST_FAIL_RE.finditer(tests_section)
    ]

    return {
        "stage": stage,
        "status": status,
        "errors": errors,
        "test_failures": test_failures,
    }


def _section(md: str, heading: str) -> str:
    """Return everything between '## <heading>' and the next '## ' heading (or EOF)."""
    pattern = re.compile(rf"^##\s*{re.escape(heading)}\s*$", re.MULTILINE)
    m = pattern.search(md)
    if not m:
        return ""
    start = m.end()
    next_h = re.search(r"^##\s+", md[start:], re.MULTILINE)
    end = start + next_h.start() if next_h else len(md)
    return md[start:end]
```

- [ ] **Step 4: Run tests to verify all pass**

```
python -m pytest agent/test_parsers.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/parsers.py agent/test_parsers.py
git commit -m "feat(v5): add parse_feedback regex extractor"
```

---

## Task 4: Planner tools — `read_component` + `assign`

**Files:**
- Create: `agent/planner.py`
- Test: `agent/test_planner.py`

- [ ] **Step 1: Write the failing test for `read_component`**

Create `agent/test_planner.py`:

```python
import os
import tempfile
from pathlib import Path

from agent.planner import build_planner_tools


def test_read_component_returns_header_content(tmp_path, monkeypatch):
    # Mock SOURCE_DIR with a fake DK structure
    dk = tmp_path / "Eco.Math.C89_DK_v.1.0.1.2"
    shared = dk / "SharedFiles"
    shared.mkdir(parents=True)
    (shared / "IEcoMathC89.h").write_text("// math interface\nint Add(int a, int b);\n")
    (shared / "IdEcoMathC89.h").write_text("// component id\n#define CID_ECO_MATH_C89 0x...\n")

    monkeypatch.setattr("agent.planner.SOURCE_DIR", tmp_path)

    tools = build_planner_tools(llm=None)
    read_component = next(t for t in tools if t.name == "read_component")
    result = read_component.invoke({"name": "Eco.Math.C89"})

    assert "math interface" in result
    assert "Add(int a, int b)" in result
    assert "CID_ECO_MATH_C89" in result


def test_read_component_returns_error_for_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.planner.SOURCE_DIR", tmp_path)
    tools = build_planner_tools(llm=None)
    read_component = next(t for t in tools if t.name == "read_component")
    result = read_component.invoke({"name": "Eco.Nope"})
    assert "ERROR" in result or "not found" in result.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest agent/test_planner.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement planner tools (read_component + assign stub)**

Create `agent/planner.py`:

```python
"""V5 Planner node — search-only ReAct, single handoff via assign()."""

import logging
from pathlib import Path

from langchain_core.tools import tool
from langgraph.types import Command

from .tools import list_all_components, rag_query, SOURCE_DIR

logger = logging.getLogger(__name__)


def build_planner_tools(llm):
    """Return list of tools for the Planner node. `llm` is unused for now (kept for symmetry)."""

    @tool
    def read_component(name: str) -> str:
        """Read interface (IEco*.h) and ID (IdEco*.h) headers for a known SDK component.

        Args:
            name: Component name like 'Eco.Math.C89'.
        """
        matches = list(Path(SOURCE_DIR).glob(f"{name}_DK_v.*"))
        if not matches:
            return f"ERROR: Component '{name}' not found in local SDK."
        dk = matches[0]
        shared = dk / "SharedFiles"
        if not shared.exists():
            return f"ERROR: SharedFiles missing for '{name}'."
        out = []
        for header in sorted(shared.glob("IEco*.h")) + sorted(shared.glob("IdEco*.h")):
            try:
                content = header.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                content = f"<read error: {e}>"
            out.append(f"// === {header.name} ===\n{content}")
        if not out:
            return f"ERROR: No headers in SharedFiles for '{name}'."
        return "\n\n".join(out)

    @tool
    def assign(plan_md: str) -> Command:
        """HANDOFF: user approved the plan. Pass the FULL approved PRD as Markdown."""
        return Command(update={"plan_md": plan_md, "phase": "coding"})

    return [list_all_components, rag_query, read_component, assign]
```

- [ ] **Step 4: Run test to verify it passes**

```
python -m pytest agent/test_planner.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/planner.py agent/test_planner.py
git commit -m "feat(v5): add planner tools (read_component, assign)"
```

---

## Task 5: Planner node assembly (`create_planner_node`)

**Files:**
- Modify: `agent/planner.py`
- Modify: `agent/test_planner.py`

- [ ] **Step 1: Add the failing test**

Append to `agent/test_planner.py`:

```python
def test_create_planner_node_returns_callable():
    from agent.planner import create_planner_node

    class _LLMStub:
        def bind_tools(self, tools, **kw):
            return self
        def invoke(self, messages, **kw):
            from langchain_core.messages import AIMessage
            return AIMessage(content="stub")

    node = create_planner_node(_LLMStub())
    assert callable(node)


def test_planner_node_writes_to_planner_messages_only(monkeypatch):
    """Smoke test: planner node should not touch coder/executor message lists."""
    from agent.planner import create_planner_node
    from langchain_core.messages import AIMessage

    class _LLMStub:
        def bind_tools(self, tools, **kw):
            return self
        def invoke(self, messages, **kw):
            return AIMessage(content="hi user, what's the project?")

    node = create_planner_node(_LLMStub())
    state = {
        "planner_messages": [{"role": "user", "content": "build x"}],
        "coder_messages": [],
        "executor_messages": [],
        "phase": "planning",
        "iteration": 0,
        "max_iterations": 5,
        "user_request": "build x",
        "plan_md": "", "coder_summary_md": "", "feedback_md": "",
        "project_dir": "", "project_name": "", "last_status": "",
    }
    update = node(state)
    assert "planner_messages" in update
    assert "coder_messages" not in update
    assert "executor_messages" not in update
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest agent/test_planner.py -v
```

Expected: 2 new tests fail with `ImportError: cannot import name 'create_planner_node'`.

- [ ] **Step 3: Implement `create_planner_node`**

Append to `agent/planner.py`:

```python
PLANNER_SYSTEM_PROMPT = """\
You are the EcoOS Planner. Your job is to talk with the user, search the local
EcoOS SDK via RAG, and converge on a Product Requirements Document (PRD)
describing what to build.

You have these tools:
- list_all_components()  — see the full local SDK catalog.
- rag_query(query)       — semantic search over headers + docs.
- read_component(name)   — read full IEco/IdEco headers for a known component.
- assign(plan_md)        — HANDOFF: ONLY call when the user has explicitly approved
                            the plan. Pass the full PRD in Markdown.

You DO NOT download anything, you DO NOT write files. That's the Coder's job
in the next phase.

PRD format (use exactly these headers when calling assign):

## Project: <ProjectName>

<one-paragraph description>

## Components

- **<name>** — source: sdk — <reason>
- **<name>** — source: marketplace — <reason>
- **<name>** — source: develop — <reason>
  - spec: <interface methods, dependencies>

## Build target

- Platform: <Windows|Linux>
- Output: <executable name>

## Acceptance criteria

- <criterion>

While planning, respond conversationally. Show drafts. Ask for feedback. Only
call `assign` when the user explicitly approves (e.g. "yes, build it",
"ok start", "approved"). Always reply in the user's language.
"""


def create_planner_node(llm):
    """Return a node function for the Planner phase."""
    from langgraph.prebuilt import create_react_agent

    tools = build_planner_tools(llm)
    react = create_react_agent(llm, tools=tools, prompt=PLANNER_SYSTEM_PROMPT)

    def planner_node(state):
        result = react.invoke({"messages": state["planner_messages"]})
        new_msgs = result["messages"][len(state["planner_messages"]):]
        return {"planner_messages": new_msgs}

    return planner_node
```

- [ ] **Step 4: Run tests to verify all pass**

```
python -m pytest agent/test_planner.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/planner.py agent/test_planner.py
git commit -m "feat(v5): assemble planner node as ReAct sub-agent"
```

---

## Task 6: Coder modifications — `done` tool + state-aware prompt

**Files:**
- Modify: `agent/coder.py`
- Test: `agent/test_coder_v5.py`

- [ ] **Step 1: Write the failing test**

Create `agent/test_coder_v5.py`:

```python
def test_coder_has_done_tool():
    from agent.coder import build_coder_tools_v5

    tools = build_coder_tools_v5(work_dir="/tmp/whatever")
    names = [t.name for t in tools]
    assert "done" in names


def test_done_tool_returns_command_to_executing():
    from agent.coder import build_coder_tools_v5
    from langgraph.types import Command

    tools = build_coder_tools_v5(work_dir="/tmp/whatever")
    done = next(t for t in tools if t.name == "done")
    result = done.invoke({"summary_md": "wrote files"})
    assert isinstance(result, Command)
    assert result.update["coder_summary_md"] == "wrote files"
    assert result.update["phase"] == "executing"


def test_create_coder_node_v5_seeds_with_plan_md():
    from agent.coder import create_coder_node_v5
    from langchain_core.messages import AIMessage

    class _LLMStub:
        def bind_tools(self, tools, **kw): return self
        def invoke(self, messages, **kw): return AIMessage(content="ack")

    node = create_coder_node_v5(_LLMStub())
    state = {
        "planner_messages": [],
        "coder_messages": [],
        "executor_messages": [],
        "plan_md": "## Project: X\n\n## Components\n- **A** — source: sdk — r1",
        "feedback_md": "",
        "phase": "coding",
        "iteration": 0, "max_iterations": 5,
        "user_request": "x",
        "coder_summary_md": "", "project_dir": "", "project_name": "",
        "last_status": "",
    }
    update = node(state)
    assert "coder_messages" in update
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest agent/test_coder_v5.py -v
```

Expected: FAIL with `ImportError: cannot import name 'build_coder_tools_v5'`.

- [ ] **Step 3: Add `done` tool + V5 node factory to `coder.py`**

Open `agent/coder.py`. Append at end of file (do not modify existing `create_coder_agent` — it stays for V4 fallback):

```python
def build_coder_tools_v5(work_dir: str):
    """V5 Coder toolset: existing file ops + download_component + done handoff."""
    from langgraph.types import Command
    from .tools import download_component

    legacy = create_coder_agent.__globals__  # reuse closures? no — we just rebuild here
    # Build the same tools that create_coder_agent does, but as a flat list:
    work_path = Path(work_dir)

    @tool
    def write_file(relative_path: str, content: str) -> str:
        """Write a file relative to the project working directory."""
        target = work_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: Written {relative_path} ({len(content)} bytes)"

    @tool
    def read_file(relative_path: str) -> str:
        """Read a file relative to the project working directory."""
        target = work_path / relative_path
        if not target.exists():
            return f"ERROR: File not found: {relative_path}"
        return target.read_text(encoding="utf-8")

    @tool
    def list_files() -> str:
        """List all files under the project working directory."""
        if not work_path.exists():
            return "(empty)"
        return "\n".join(sorted(str(p.relative_to(work_path)) for p in work_path.rglob("*") if p.is_file()))

    @tool
    def load_skill(language: str) -> str:
        """Load component-development templates for a language ('c', 'cpp', 'asm')."""
        skill_file = SKILLS_DIR / f"{language}.md"
        if not skill_file.exists():
            available = [f.stem for f in SKILLS_DIR.glob("*.md")]
            return f"ERROR: No skill for '{language}'. Available: {available}"
        return skill_file.read_text(encoding="utf-8")

    @tool
    def done(summary_md: str) -> Command:
        """HANDOFF: all files written. Pass a Markdown summary of what was done."""
        return Command(update={"coder_summary_md": summary_md, "phase": "executing"})

    return [write_file, read_file, list_files, load_skill, download_component, done]


def create_coder_node_v5(llm):
    """V5 Coder node — receives plan_md (and feedback_md on retries) via system prompt."""
    from langgraph.prebuilt import create_react_agent
    from langchain_core.messages import SystemMessage

    base_prompt = (CODER_SYSTEM_PROMPT_V5 if "CODER_SYSTEM_PROMPT_V5" in globals() else CODER_SYSTEM_PROMPT)

    def coder_node(state):
        work_dir = state.get("project_dir") or "output/_v5_default"
        Path(work_dir).mkdir(parents=True, exist_ok=True)

        tools = build_coder_tools_v5(work_dir)
        ctx_lines = [base_prompt, "", "## Approved Plan", state["plan_md"]]
        if state.get("feedback_md"):
            ctx_lines += ["", "## Previous build/test feedback (you must address these)", state["feedback_md"]]
        prompt = "\n".join(ctx_lines)

        react = create_react_agent(llm, tools=tools, prompt=prompt)
        seed = state["coder_messages"] or [{"role": "user", "content": "Implement the plan above."}]
        result = react.invoke({"messages": seed})
        new_msgs = result["messages"][len(seed):]
        return {"coder_messages": new_msgs}

    return coder_node


CODER_SYSTEM_PROMPT_V5 = """\
You are the EcoOS Coder. You receive an approved PRD and must produce all the
files for the project: download SDK components listed under source: sdk or
marketplace, write custom components from scratch (source: develop), and write
the EcoMain.c that wires them together.

Tools:
- write_file(path, content)
- read_file(path)
- list_files()
- load_skill(language)        — load C/C++ component templates BEFORE writing custom components.
- download_component(name)    — pull from marketplace into DependenciesFiles/.
- done(summary_md)            — HANDOFF when all files are in place. List what
                                 you wrote/modified.

If feedback is provided (retry loop), focus your edits on the listed files and
errors. Do not redo work that succeeded.

Always reply in the user's language for any human-facing summary.
"""
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest agent/test_coder_v5.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/coder.py agent/test_coder_v5.py
git commit -m "feat(v5): add coder node with done handoff and feedback awareness"
```

---

## Task 7: Executor node + tools

**Files:**
- Create: `agent/executor.py`
- Test: `agent/test_executor.py`

- [ ] **Step 1: Write the failing test**

Create `agent/test_executor.py`:

```python
def test_success_tool_returns_command_to_done():
    from agent.executor import build_executor_tools
    from langgraph.types import Command

    tools = build_executor_tools(project_dir="/tmp/p", iteration=1, max_iterations=5)
    success = next(t for t in tools if t.name == "success")
    result = success.invoke({"summary_md": "all green"})
    assert isinstance(result, Command)
    assert result.update["phase"] == "done"
    assert result.update["last_status"] == "success"


def test_back_to_code_returns_command_to_coding_with_increment():
    from agent.executor import build_executor_tools
    from langgraph.types import Command

    tools = build_executor_tools(project_dir="/tmp/p", iteration=2, max_iterations=5)
    back = next(t for t in tools if t.name == "back_to_code")
    result = back.invoke({"feedback_md": "## Stage: build\n## Status: FAIL\n## Errors\n- a.c:1: bad"})
    assert isinstance(result, Command)
    assert result.update["phase"] == "coding"
    assert result.update["iteration"] == 3
    assert "FAIL" in result.update["feedback_md"]


def test_back_to_code_at_max_iterations_marks_done():
    from agent.executor import build_executor_tools
    from langgraph.types import Command

    tools = build_executor_tools(project_dir="/tmp/p", iteration=5, max_iterations=5)
    back = next(t for t in tools if t.name == "back_to_code")
    result = back.invoke({"feedback_md": "## Stage: test\n## Status: FAIL"})
    assert result.update["phase"] == "done"
    assert result.update["last_status"] == "max_iterations_reached"
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest agent/test_executor.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `executor.py`**

Create `agent/executor.py`:

```python
"""V5 Executor node — build + test, with bounded retry loop."""

import logging

from langchain_core.tools import tool
from langgraph.types import Command

from .tools import build_makefile, run_tests

logger = logging.getLogger(__name__)


EXECUTOR_SYSTEM_PROMPT = """\
You are the EcoOS Executor. You receive a coder summary and must:
1. Run build() to compile and link the project.
2. If build fails, immediately call back_to_code(feedback_md) with structured errors.
3. If build succeeds, call run_tests().
4. If tests fail, call back_to_code(feedback_md) with the failures.
5. If everything passes, call success(summary_md) with a short user-facing report.

Feedback Markdown format (use EXACTLY these headers):

## Stage: build|test
## Status: FAIL

## Errors
- {file}:{line}: {message}

## Test failures
- {test_name}: expected {expected}, got {actual}

## Suggested focus
- {short hint, optional}

You DO NOT modify files. Just build, test, and hand off.
"""


def build_executor_tools(project_dir: str, iteration: int, max_iterations: int):

    @tool
    def build() -> str:
        """Compile and link the project. Returns full compiler/linker output."""
        return build_makefile.invoke({"project_dir": project_dir})

    @tool
    def run_tests_tool() -> str:
        """Run tests against the built executable. Returns full test output."""
        return run_tests.invoke({"project_dir": project_dir})

    @tool
    def success(summary_md: str) -> Command:
        """HANDOFF (success path): everything green. Pass a user-facing summary."""
        return Command(update={"phase": "done", "last_status": "success", "executor_summary_md": summary_md})

    @tool
    def back_to_code(feedback_md: str) -> Command:
        """HANDOFF (failure path): pass structured Markdown feedback to the Coder.

        If max_iterations is reached, this transitions to 'done' with status
        'max_iterations_reached' instead of looping back.
        """
        next_iter = iteration + 1
        if next_iter > max_iterations:
            return Command(update={
                "phase": "done",
                "last_status": "max_iterations_reached",
                "feedback_md": feedback_md,
            })
        return Command(update={
            "phase": "coding",
            "iteration": next_iter,
            "feedback_md": feedback_md,
        })

    # rename to match contract; ReAct discovers tools by .name
    run_tests_tool.name = "run_tests"
    return [build, run_tests_tool, success, back_to_code]


def create_executor_node(llm):
    """V5 Executor node — receives coder_summary_md, builds, tests, handoffs."""
    from langgraph.prebuilt import create_react_agent

    def executor_node(state):
        project_dir = state.get("project_dir") or "output/_v5_default"
        tools = build_executor_tools(project_dir, state["iteration"], state["max_iterations"])
        ctx = (
            EXECUTOR_SYSTEM_PROMPT
            + "\n\n## Coder summary\n"
            + state.get("coder_summary_md", "")
        )
        react = create_react_agent(llm, tools=tools, prompt=ctx)
        seed = state["executor_messages"] or [{"role": "user", "content": "Build and test the project."}]
        result = react.invoke({"messages": seed})
        new_msgs = result["messages"][len(seed):]
        return {"executor_messages": new_msgs}

    return executor_node
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest agent/test_executor.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/executor.py agent/test_executor.py
git commit -m "feat(v5): add executor node with bounded retry loop"
```

---

## Task 8: Three-node graph assembly

**Files:**
- Create: `agent/three_node_graph.py`
- Test: `agent/test_three_node_graph.py`

- [ ] **Step 1: Write the failing test**

Create `agent/test_three_node_graph.py`:

```python
def test_create_v5_graph_returns_compiled_graph():
    from agent.three_node_graph import create_v5_graph
    from langchain_core.messages import AIMessage

    class _LLMStub:
        def bind_tools(self, tools, **kw): return self
        def invoke(self, messages, **kw): return AIMessage(content="ok")

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
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest agent/test_three_node_graph.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `three_node_graph.py`**

Create `agent/three_node_graph.py`:

```python
"""V5 Three-Node Graph: Planner → Coder → Executor."""

import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state_v5 import AppState
from .planner import create_planner_node
from .coder import create_coder_node_v5
from .executor import create_executor_node

logger = logging.getLogger(__name__)


def _route_by_phase(state) -> str:
    return state["phase"]


def _route_after_planner(state) -> str:
    return "coding" if state["phase"] == "coding" else "wait_user"


def _route_after_coder(state) -> str:
    return "executing" if state["phase"] == "executing" else "wait_user"


def _route_after_executor(state) -> str:
    if state["phase"] == "coding":
        return "coding"
    return "done"


def create_v5_graph(llm):
    """Compile the V5 three-node graph with MemorySaver checkpointer."""
    builder = StateGraph(AppState)
    builder.add_node("planner",  create_planner_node(llm))
    builder.add_node("coder",    create_coder_node_v5(llm))
    builder.add_node("executor", create_executor_node(llm))

    builder.add_conditional_edges(START, _route_by_phase, {
        "planning":  "planner",
        "coding":    "coder",
        "executing": "executor",
        "done":      END,
    })
    builder.add_conditional_edges("planner", _route_after_planner, {
        "coding":   "coder",
        "wait_user": END,
    })
    builder.add_conditional_edges("coder", _route_after_coder, {
        "executing": "executor",
        "wait_user": END,
    })
    builder.add_conditional_edges("executor", _route_after_executor, {
        "coding":  "coder",
        "done":    END,
    })

    return builder.compile(checkpointer=MemorySaver())
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest agent/test_three_node_graph.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/three_node_graph.py agent/test_three_node_graph.py
git commit -m "feat(v5): assemble three-node graph with phase-based routing"
```

---

## Task 9: chat_agent integration — `create_chat_agent_v5`

**Files:**
- Modify: `agent/chat_agent.py`

- [ ] **Step 1: Write the failing test**

Create `agent/test_chat_agent_v5.py`:

```python
def test_create_chat_agent_v5_returns_callable_graph():
    from agent.chat_agent import create_chat_agent_v5
    from langchain_core.messages import AIMessage

    class _LLMStub:
        def bind_tools(self, tools, **kw): return self
        def invoke(self, messages, **kw): return AIMessage(content="hi")

    g = create_chat_agent_v5(_LLMStub())
    assert hasattr(g, "stream")


def test_chat_agent_v5_initial_state_seeds_planning_phase():
    from agent.chat_agent import make_chat_agent_initial_state
    state = make_chat_agent_initial_state("build calc")
    assert state["phase"] == "planning"
    assert state["planner_messages"][0]["content"] == "build calc"
```

- [ ] **Step 2: Run test to verify it fails**

```
python -m pytest agent/test_chat_agent_v5.py -v
```

Expected: FAIL.

- [ ] **Step 3: Add V5 functions to `chat_agent.py`**

Append to `agent/chat_agent.py` (do NOT remove existing `create_chat_agent` — it stays as legacy V4):

```python
def create_chat_agent_v5(llm):
    """V5: returns the three-node graph directly. Caller manages thread_id and state."""
    from .three_node_graph import create_v5_graph
    return create_v5_graph(llm)


def make_chat_agent_initial_state(user_request: str, max_iterations: int = 5):
    from .state_v5 import make_initial_state
    return make_initial_state(user_request, max_iterations)
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest agent/test_chat_agent_v5.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add agent/chat_agent.py agent/test_chat_agent_v5.py
git commit -m "feat(v5): expose create_chat_agent_v5 + initial state helper"
```

---

## Task 10: Backend WebSocket events for V5

**Files:**
- Modify: `backend/server.py`

- [ ] **Step 1: Inspect current event emission patterns**

```
python -c "import re; print('\n'.join(re.findall(r'\"type\":\s*\"(\w+)\"', open('backend/server.py').read())))"
```

Expected: lists current event types so you can mirror style.

- [ ] **Step 2: Add V5 endpoint sketch**

Open `backend/server.py`. Locate the existing WebSocket handler `websocket_endpoint`. Below it, add a new handler that uses the V5 graph:

```python
from agent.chat_agent import create_chat_agent_v5, make_chat_agent_initial_state


@app.websocket("/ws/v5/chat")
async def v5_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    llm = get_llm()  # existing helper
    graph = create_chat_agent_v5(llm)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}

    state = None
    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            user_msg = payload["content"]

            if state is None:
                state = make_chat_agent_initial_state(user_msg, max_iterations=5)
            else:
                state["planner_messages"] = state.get("planner_messages", []) + [{"role": "user", "content": user_msg}]

            async for event in graph.astream(state, config, stream_mode=["updates", "custom"]):
                kind, data = event
                if kind == "updates":
                    for node, update in data.items():
                        if "phase" in update:
                            await websocket.send_json({"type": "phase_change", "phase": update["phase"]})
                        if node == "planner" and "planner_messages" in update:
                            for m in update["planner_messages"]:
                                content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else None)
                                if content:
                                    await websocket.send_json({"type": "planner_message", "content": content})
                        if node == "coder":
                            await websocket.send_json({"type": "coder_progress", "data": str(update)[:500]})
                        if node == "executor":
                            await websocket.send_json({"type": "executor_progress", "data": str(update)[:500]})
                elif kind == "custom":
                    await websocket.send_json(data)

            # Refresh state from checkpointer to keep our local copy current
            state = graph.get_state(config).values

            # If terminal, send final
            if state.get("phase") == "done":
                await websocket.send_json({
                    "type": "final_result",
                    "status": state.get("last_status", ""),
                    "summary": state.get("executor_summary_md", "") or state.get("coder_summary_md", ""),
                })
                break

    except WebSocketDisconnect:
        logger.info(f"[V5 WS] disconnected thread_id={thread_id}")
```

- [ ] **Step 3: Smoke-run the FastAPI server**

```
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8100 --reload
```

Expected: starts without ImportError. Hit Ctrl+C after seeing "Application startup complete."

- [ ] **Step 4: Commit**

```bash
git add backend/server.py
git commit -m "feat(v5): add /ws/v5/chat WebSocket endpoint streaming phase events"
```

---

## Task 11: Frontend phase rendering + Approve UI

**Files:**
- Modify: `frontend/components/chat/chat-interface.tsx`

- [ ] **Step 1: Inspect current chat-interface structure**

```
python -c "print(open('frontend/components/chat/chat-interface.tsx', encoding='utf-8').read()[:2000])"
```

Note: the user already has skipHtml on ReactMarkdown (PR #10).

- [ ] **Step 2: Add V5 message types to interface**

Open `frontend/components/chat/chat-interface.tsx`. Find the `Message` type definition. Add fields:

```typescript
type V5Phase = "planning" | "coding" | "executing" | "done";

type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  // V5 additions
  phase?: V5Phase;
  isPlanDraft?: boolean;
};
```

- [ ] **Step 3: Add phase indicator + plan-approve button**

In the JSX render of message bubbles, after the existing `<ReactMarkdown ...>` block, add:

```tsx
{msg.phase && (
  <div className="text-xs uppercase tracking-wide text-muted-foreground mt-2">
    Phase: {msg.phase}
  </div>
)}
{msg.isPlanDraft && (
  <button
    type="button"
    className="mt-2 px-3 py-1 rounded bg-emerald-600 text-white text-sm hover:bg-emerald-700"
    onClick={() => sendMessage("Approve and start building.")}
  >
    Approve plan
  </button>
)}
```

- [ ] **Step 4: Wire WebSocket event handler**

Find the existing `useEffect` where `onmessage` is set. Add cases:

```typescript
ws.onmessage = (ev) => {
  const event = JSON.parse(ev.data);
  switch (event.type) {
    case "phase_change":
      setCurrentPhase(event.phase);
      break;
    case "planner_message":
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: event.content,
          phase: "planning",
          isPlanDraft: /^##\s*Project:/m.test(event.content),
        },
      ]);
      break;
    case "coder_progress":
    case "executor_progress":
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "system", content: event.data, phase: event.type === "coder_progress" ? "coding" : "executing" },
      ]);
      break;
    case "final_result":
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: `**${event.status}**\n\n${event.summary}`, phase: "done" },
      ]);
      break;
    default:
      // existing handlers (V3 progress etc.)
      break;
  }
};
```

(Add `const [currentPhase, setCurrentPhase] = useState<V5Phase | null>(null);` near other useState calls.)

- [ ] **Step 5: Smoke-test in dev**

In two terminals:

```
# Terminal 1
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8100 --reload
```

```
# Terminal 2
cd frontend
npm run dev
```

Open http://localhost:3000 → enter "build a calculator" → expect:
- WebSocket connects to /ws/v5/chat (manual switch — see Step 6).
- Planner messages appear with "Phase: planning".
- When PRD is shown ("## Project: ..."), an Approve button appears.

- [ ] **Step 6: Add toggle to use V5 endpoint**

In the WebSocket connect URL builder, add an env switch:

```typescript
const useV5 = process.env.NEXT_PUBLIC_USE_V5 === "true";
const wsUrl = `${baseUrl.replace("http", "ws")}/ws/${useV5 ? "v5/chat" : "chat"}`;
```

- [ ] **Step 7: Commit**

```bash
git add frontend/components/chat/chat-interface.tsx
git commit -m "feat(v5): add phase indicator and plan-approve UI to chat-interface"
```

---

## Task 12: E2E integration test

**Files:**
- Create: `agent/test_v5_e2e.py`

- [ ] **Step 1: Write the integration test**

Create `agent/test_v5_e2e.py`:

```python
"""E2E integration test for the V5 three-node pipeline.

Uses real LLM (env: OPENAI_API_KEY, LLM_MODEL). Skips if not configured.
"""

import os
import uuid

import pytest


pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set; skipping E2E",
)


def _get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=os.environ.get("LLM_MODEL", "z-ai/glm-5.1"),
        temperature=0,
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_api_base=os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
        timeout=120,
        max_retries=1,
    )


def test_v5_pipeline_planning_to_handoff_smoke():
    """Smoke: enter planning, send approval message, observe phase transition."""
    from agent.chat_agent import create_chat_agent_v5, make_chat_agent_initial_state

    graph = create_chat_agent_v5(_get_llm())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 80}

    # Turn 1: initial request
    state = make_chat_agent_initial_state(
        "Make a tiny EcoOS calculator: read two integers, print their sum. Use Eco.Math.C89 and Eco.StdIO.C89. No custom components. Approve immediately."
    )
    final_state = graph.invoke(state, config)

    assert final_state["phase"] in ("planning", "coding", "executing", "done")
    # Planner must have produced *some* response
    assert len(final_state["planner_messages"]) > 1


def test_v5_parser_robust_across_models():
    """Run parse_plan on synthetic Markdown that 3 models produced in earlier tests."""
    from agent.parsers import parse_plan
    samples = [
        # glm-5.1-style
        "## Project: TestApp\n\n## Components\n- **Eco.Math.C89** — source: sdk — math",
        # kimi-k2.6-style with em-dashes
        "## Project: Test2\n\n## Components\n- **Eco.StdIO.C89** — source: sdk — io",
        # minimal
        "## Project: Tiny\n\n## Components\n- **A** — source: develop\n  - spec: x",
    ]
    for s in samples:
        result = parse_plan(s)
        assert result["project_name"]
        assert len(result["components"]) >= 1
```

- [ ] **Step 2: Run the parser cross-model test (no network)**

```
python -m pytest agent/test_v5_e2e.py::test_v5_parser_robust_across_models -v
```

Expected: PASS.

- [ ] **Step 3: Run the smoke test with real LLM**

Set `LLM_MODEL=z-ai/glm-5.1` in `.env`, then:

```
python -m pytest agent/test_v5_e2e.py::test_v5_pipeline_planning_to_handoff_smoke -v -s
```

Expected: PASS within ~3 minutes. May reach `phase=="coding"` if planner approves quickly; may stay `phase=="planning"` if it asks clarifying questions — both acceptable.

- [ ] **Step 4: Commit**

```bash
git add agent/test_v5_e2e.py
git commit -m "test(v5): add E2E pipeline smoke test and cross-model parser test"
```

---

## Task 13: Update memory and documentation

**Files:**
- Modify: `C:\Users\gaevy\.claude\projects\H--ai-hse-diploma-agent\memory\v4-architecture.md`
- Modify: `C:\Users\gaevy\.claude\projects\H--ai-hse-diploma-agent\memory\MEMORY.md`

- [ ] **Step 1: Add V5 entry to architecture memory**

Open `v4-architecture.md`. At the top, add a section:

```markdown
## V5 Status (added 2026-04-27)

V5 replaces V4's architect-ReAct with explicit three-node graph (Planner / Coder / Executor).
- Spec: `Eco.Toolchain/Eco.AI.Assembly1/docs/superpowers/specs/2026-04-27-v4-three-node-design.md`
- Plan: `Eco.Toolchain/Eco.AI.Assembly1/docs/superpowers/plans/2026-04-27-v4-three-node-pipeline.md`
- Key files: `agent/state_v5.py`, `agent/parsers.py`, `agent/planner.py`, `agent/executor.py`, `agent/three_node_graph.py`.
- Coder reuses existing `agent/coder.py` with new V5 helpers (`build_coder_tools_v5`, `create_coder_node_v5`).
- Entry point: `chat_agent.create_chat_agent_v5(llm)`. WebSocket: `/ws/v5/chat`.
- V4 architect kept as legacy fallback; V3 graph kept inside `chat_agent_v3` for emergency use.
```

- [ ] **Step 2: Update MEMORY.md index pointer**

In `MEMORY.md`, find the "Architecture (V4 — current as of 2026-04-26)" header and replace the first line with:

```markdown
## Architecture (V5 — current as of 2026-04-27)

Five generations: V1, V2 (deprecated); V3 (rigid graph, kept as emergency fallback); V4 (architect-ReAct, deprecated by V5); V5 (current — Planner/Coder/Executor three-node graph with Markdown handoffs).
```

- [ ] **Step 3: Commit (memory only — separate from code commits)**

The memory directory is outside the project git repo, so no `git commit` is needed; the memory files are tracked by the auto-memory system itself. Just save the file edits.

---

## Self-Review

**1. Spec coverage check (against `docs/superpowers/specs/2026-04-27-v4-three-node-design.md`):**
- §3 Architecture (3-node graph) → Tasks 4–8. ✅
- §4 State schema → Task 1. ✅
- §5.1 Planner tools → Task 4 + 5. ✅
- §5.2 Coder modifications → Task 6. ✅
- §5.3 Executor → Task 7. ✅
- §6 Routing & handoff via Command → Task 8. ✅
- §7 PRD parser → Task 2. ✅
- §8 Life-cycle (E2E run) → Task 12. ✅
- §9 Failure modes (max_iterations, parse_failure) → Task 7 (max_iterations covered); parse_failure handling NOT covered as a dedicated task — Coder's prompt says to retry on parse failure, but no dedicated test. **Add Task 6.5? See gap below.**
- §10 Implementation file list → covered by Tasks 1–11.
- Backend events → Task 10. ✅
- Frontend → Task 11. ✅

**Gap fix:** Coder's parse-failure handling is implicit (LLM is asked to retry on bad plan_md). The spec admits this is an LLM-prompted fallback. The system prompt in Task 6 mentions feedback handling but doesn't call out plan-parsing retry. **Decision:** acceptable for Phase 1; if first E2E reveals issue, add dedicated task in follow-up plan. Documented this trade-off in the Open Questions section of the spec already (§11).

**2. Placeholder scan:** No "TBD", no "implement later". Each step has either runnable command or full code. ✅

**3. Type consistency:**
- `assign(plan_md: str)` consistent in spec §5.1 and Tasks 4, 5.
- `done(summary_md: str)` consistent in spec §5.2 and Task 6.
- `success(summary_md: str)`, `back_to_code(feedback_md: str)` consistent in spec §5.3 and Task 7.
- `phase` literal values: "planning" | "coding" | "executing" | "done" — used identically across Tasks 1, 7, 8.
- `iteration` increments at `back_to_code` (Task 7), check happens at executor entry (Task 7) — consistent.
- `last_status` enum updated to include `parse_failure` per spec §4 (already fixed in spec inline review).
- Field name `executor_summary_md` appears in Task 7 (`success` Command update) and Task 10 (`final_result` event reads it). Was NOT in state schema (Task 1). **Type inconsistency → fix:** Either add `executor_summary_md` to AppState, or have `success` write to `coder_summary_md` (overloading is ugly). Adding to schema is cleaner.

**Type-fix applied below in addendum.**

---

## Type Consistency Addendum

After self-review found `executor_summary_md` used but not declared:

**Patch to Task 1:** Add to AppState TypedDict and `make_initial_state` return value:

```python
# In agent/state_v5.py AppState:
    executor_summary_md: str   # set by Executor.success()

# In make_initial_state:
        "executor_summary_md": "",
```

**Patch to Task 1 test** (`test_initial_state_has_planning_phase`): add assertion:

```python
    assert state["executor_summary_md"] == ""
```

This is a one-line edit; apply during Task 1 execution.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-27-v4-three-node-pipeline.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
