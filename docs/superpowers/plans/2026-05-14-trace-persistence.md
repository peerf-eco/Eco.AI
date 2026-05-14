# Trace Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist every V6 node's full ReAct message history to `traces/<thread_id>/NN-<node>.json` so agent runs can be analyzed after the process restarts.

**Architecture:** A new `agent/v6/trace.py` module exposes one function, `write_trace`, which each of the 5 LLM nodes calls right after `agent.run()`. It serializes `EcoAgentResult.history` via `messages_to_dict()` to a JSON file under a central `traces/` dir (host-mounted into the `api` container). `write_trace` never raises — trace persistence is observability and must not break the pipeline.

**Tech Stack:** Python 3.11, LangChain core (`messages_to_dict`/`messages_from_dict`), LangGraph (`get_config`), pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-05-14-trace-persistence-design.md`

**Working directory note:** Code/test paths below are relative to `Eco.Toolchain/Eco.AI.Assembly1/` (that is the pytest + python working root — `agent/` is a top-level package there). Git commands run from the repo root `H:/ai-hse-diploma-agent`.

---

### Task 1: `write_trace` core — serialization + seq numbering

**Files:**
- Create: `agent/v6/trace.py`
- Test: `agent/v6/tests/test_trace.py`

- [ ] **Step 1: Write the failing tests**

Create `agent/v6/tests/test_trace.py`:

```python
"""Tests for write_trace — V6 node execution trace persistence."""
import json

import pytest
from langchain_core.messages import (
    SystemMessage, HumanMessage, AIMessage, ToolMessage, messages_from_dict,
)

from agent.v6.eco_agent import EcoAgentResult
from agent.v6.state import make_initial_v6_state
from agent.v6 import trace as trace_mod
from agent.v6.trace import write_trace


def _fake_history():
    return [
        SystemMessage(content="system prompt"),
        HumanMessage(content="seed request"),
        AIMessage(content="thinking...", tool_calls=[
            {"name": "read_file", "args": {"path": "x.c"}, "id": "c1"}
        ]),
        ToolMessage(content="file contents", tool_call_id="c1", status="success"),
    ]


def _result(status="done", error=""):
    return EcoAgentResult(
        status=status, stop_tool_name="", stop_payload={},
        history=_fake_history(), error=error,
    )


def test_write_trace_happy_path(monkeypatch, tmp_path):
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": "test-thread-1"}},
    )
    state = make_initial_v6_state("build a calculator")
    state["phase"] = "coding"

    path = write_trace(_result(status="max_iters"), node="coder",
                       state=state, traces_root=tmp_path)

    assert path is not None
    assert path.name == "01-coder.json"
    assert path.parent.name == "test-thread-1"

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["meta"]["thread_id"] == "test-thread-1"
    assert payload["meta"]["node"] == "coder"
    assert payload["meta"]["seq"] == 1
    assert payload["meta"]["phase"] == "coding"
    assert payload["meta"]["status"] == "max_iters"
    assert payload["meta"]["iters"] == 1  # one AIMessage in history

    # messages round-trip — proves the trace is semantically faithful
    restored = messages_from_dict(payload["messages"])
    assert len(restored) == 4
    assert restored[0].content == "system prompt"
    assert restored[2].tool_calls[0]["name"] == "read_file"


def test_write_trace_seq_increments(monkeypatch, tmp_path):
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": "test-thread-2"}},
    )
    state = make_initial_v6_state("x")

    p1 = write_trace(_result(), node="planner", state=state, traces_root=tmp_path)
    p2 = write_trace(_result(), node="setup", state=state, traces_root=tmp_path)

    assert p1.name == "01-planner.json"
    assert p2.name == "02-setup.json"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest agent/v6/tests/test_trace.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.v6.trace'`

- [ ] **Step 3: Write the minimal implementation**

Create `agent/v6/trace.py`:

```python
"""write_trace — persist a V6 node's full ReAct message history to disk.

Each call writes one node-attempt's EcoAgentResult.history to
traces/<thread_id>/NN-<node>.json. See
docs/superpowers/specs/2026-05-14-trace-persistence-design.md.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessage, messages_to_dict
from langgraph.config import get_config

from agent.v6.eco_agent import EcoAgentResult
from agent.v6.state import V6State


def write_trace(
    result: EcoAgentResult,
    *,
    node: str,
    state: V6State,
    traces_root: Path | None = None,
) -> Path | None:
    """Serialize one node-attempt's full message history to
    traces/<thread_id>/NN-<node>.json.

    Returns the written path, or None if writing was skipped.

    The seq counter (NN) is len(existing *.json) + 1. This is race-free
    because the V6 pipeline runs nodes strictly sequentially within a thread.
    """
    root = traces_root or Path(os.getenv("V6_TRACES_DIR", "traces"))

    cfg = get_config()
    thread_id = cfg["configurable"]["thread_id"]

    thread_dir = root / thread_id
    thread_dir.mkdir(parents=True, exist_ok=True)

    seq = len(list(thread_dir.glob("*.json"))) + 1

    payload = {
        "meta": {
            "thread_id": thread_id,
            "node": node,
            "seq": seq,
            "phase": state.get("phase", ""),
            "status": result.status,
            "error": result.error,
            "retry_count": state.get("retry_count", 0),
            "last_failure_origin": state.get("last_failure_origin", ""),
            "iters": sum(1 for m in result.history if isinstance(m, AIMessage)),
            "ts_written": datetime.now(timezone.utc).isoformat(),
        },
        "messages": messages_to_dict(result.history),
    }

    final = thread_dir / f"{seq:02d}-{node}.json"
    tmp = thread_dir / f"{seq:02d}-{node}.json.tmp"
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    os.replace(tmp, final)
    return final
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest agent/v6/tests/test_trace.py -v`
Expected: PASS — 2 passed

- [ ] **Step 5: Commit**

```bash
git add Eco.Toolchain/Eco.AI.Assembly1/agent/v6/trace.py Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_trace.py
git commit -m "feat(v6/trace): add write_trace — serialize node history to JSON"
```

---

### Task 2: `write_trace` resilience — never-raises + no-context + safety-net

**Files:**
- Modify: `agent/v6/trace.py` (rewrite the function body with error handling)
- Test: `agent/v6/tests/test_trace.py` (append 3 tests)

- [ ] **Step 1: Write the failing tests**

Append to `agent/v6/tests/test_trace.py`:

```python
def test_write_trace_no_graph_context_returns_none(monkeypatch, tmp_path):
    """No active LangGraph context (e.g. a unit test) — skip silently."""
    def _boom():
        raise RuntimeError("Called get_config outside of a runnable context")
    monkeypatch.setattr(trace_mod, "get_config", _boom)
    state = make_initial_v6_state("x")

    path = write_trace(_result(), node="coder", state=state, traces_root=tmp_path)

    assert path is None
    assert list(tmp_path.glob("**/*.json")) == []


def test_write_trace_never_raises_on_bad_root(monkeypatch, tmp_path):
    """A broken traces_root must not propagate an exception to the node."""
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": "t"}},
    )
    # traces_root points at a FILE, so mkdir under it will fail
    bad_root = tmp_path / "i-am-a-file"
    bad_root.write_text("not a dir")
    state = make_initial_v6_state("x")

    path = write_trace(_result(), node="coder", state=state, traces_root=bad_root)

    assert path is None  # no exception propagated


def test_write_trace_default_str_safety_net(monkeypatch, tmp_path):
    """A non-JSON-serializable object in additional_kwargs is coerced, not fatal."""
    monkeypatch.setattr(
        trace_mod, "get_config",
        lambda: {"configurable": {"thread_id": "t-safety"}},
    )
    history = [
        SystemMessage(content="s"),
        AIMessage(content="a", additional_kwargs={"weird": object()}),
    ]
    result = EcoAgentResult(
        status="done", stop_tool_name="", stop_payload={},
        history=history, error="",
    )
    state = make_initial_v6_state("x")

    path = write_trace(result, node="coder", state=state, traces_root=tmp_path)

    assert path is not None
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["meta"]["node"] == "coder"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest agent/v6/tests/test_trace.py -v`
Expected: FAIL — `test_write_trace_no_graph_context_returns_none` raises `RuntimeError`; `test_write_trace_never_raises_on_bad_root` raises `NotADirectoryError` (or similar). The first two new tests error out instead of asserting.

- [ ] **Step 3: Rewrite `agent/v6/trace.py` with error handling**

Replace the entire file content of `agent/v6/trace.py` with:

```python
"""write_trace — persist a V6 node's full ReAct message history to disk.

Each call writes one node-attempt's EcoAgentResult.history to
traces/<thread_id>/NN-<node>.json. See
docs/superpowers/specs/2026-05-14-trace-persistence-design.md.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import AIMessage, messages_to_dict
from langgraph.config import get_config

from agent.v6.eco_agent import EcoAgentResult
from agent.v6.state import V6State

logger = logging.getLogger(__name__)


def write_trace(
    result: EcoAgentResult,
    *,
    node: str,
    state: V6State,
    traces_root: Path | None = None,
) -> Path | None:
    """Serialize one node-attempt's full message history to
    traces/<thread_id>/NN-<node>.json.

    Returns the written path, or None if writing was skipped (no graph
    context) or failed. NEVER raises — trace persistence is observability
    and must not break the pipeline.

    The seq counter (NN) is len(existing *.json) + 1. This is race-free
    because the V6 pipeline runs nodes strictly sequentially within a thread.
    """
    try:
        root = traces_root or Path(os.getenv("V6_TRACES_DIR", "traces"))

        try:
            cfg = get_config()
        except RuntimeError:
            # No active LangGraph context (e.g. node called from a unit test).
            logger.debug("write_trace: no graph context, skipping (node=%s)", node)
            return None

        thread_id = (cfg.get("configurable") or {}).get("thread_id")
        if not thread_id:
            logger.warning(
                "write_trace: no thread_id in config, skipping (node=%s)", node
            )
            return None

        thread_dir = root / thread_id
        thread_dir.mkdir(parents=True, exist_ok=True)

        seq = len(list(thread_dir.glob("*.json"))) + 1

        payload = {
            "meta": {
                "thread_id": thread_id,
                "node": node,
                "seq": seq,
                "phase": state.get("phase", ""),
                "status": result.status,
                "error": result.error,
                "retry_count": state.get("retry_count", 0),
                "last_failure_origin": state.get("last_failure_origin", ""),
                "iters": sum(
                    1 for m in result.history if isinstance(m, AIMessage)
                ),
                "ts_written": datetime.now(timezone.utc).isoformat(),
            },
            "messages": messages_to_dict(result.history),
        }

        final = thread_dir / f"{seq:02d}-{node}.json"
        tmp = thread_dir / f"{seq:02d}-{node}.json.tmp"
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        os.replace(tmp, final)
        return final
    except Exception as e:  # never let trace persistence break the pipeline
        logger.warning("write_trace failed (node=%s): %s", node, e)
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest agent/v6/tests/test_trace.py -v`
Expected: PASS — 5 passed (2 from Task 1 still pass, 3 new ones pass)

- [ ] **Step 5: Commit**

```bash
git add Eco.Toolchain/Eco.AI.Assembly1/agent/v6/trace.py Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_trace.py
git commit -m "feat(v6/trace): make write_trace never raise + handle no-context"
```

---

### Task 3: Wire `write_trace` into the 5 LLM nodes

**Files:**
- Modify: `agent/v6/nodes/planner.py`, `agent/v6/nodes/setup.py`, `agent/v6/nodes/coder.py`, `agent/v6/nodes/builder.py`, `agent/v6/nodes/tester.py`
- Test: `agent/v6/tests/test_setup_node.py` (append one wiring test)

- [ ] **Step 1: Write the failing wiring test**

Append to `agent/v6/tests/test_setup_node.py`:

```python
def test_setup_node_writes_trace(monkeypatch, project_dir, fake_cli_path):
    """setup_node calls write_trace with its EcoAgentResult after agent.run()."""
    def fake_run(cmd, **kw):
        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)

    calls = []
    import agent.v6.nodes.setup as setup_mod
    monkeypatch.setattr(
        setup_mod, "write_trace",
        lambda result, *, node, state: calls.append((result, node)),
    )

    state = make_initial_v6_state("x")
    state["components"] = [
        {"cid": "A" * 32, "version": "1.0.1.2", "name": "Eco.X", "reason": "r"}
    ]
    state["plan_md"] = "# Plan"
    state["project_dir"] = str(project_dir)

    llm = ScriptedChatModel(script=[
        ai_tool("ecoos_pull", {"cid": "A" * 32, "version": "1.0.1.2"}, "c1"),
        ai_tool("mark_setup_done", {"downloaded_paths": [str(project_dir)]}, "c2"),
    ])
    setup_node(state, llm=llm, cli_path=fake_cli_path)

    assert len(calls) == 1
    result, node = calls[0]
    assert node == "setup"
    assert result.status == "done"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest agent/v6/tests/test_setup_node.py::test_setup_node_writes_trace -v`
Expected: FAIL — `AttributeError: <module 'agent.v6.nodes.setup'> does not have the attribute 'write_trace'` (the name does not exist in the module yet, so monkeypatch.setattr fails)

- [ ] **Step 3: Wire `setup.py`**

In `agent/v6/nodes/setup.py`, add the import next to the other `agent.v6` imports near the top of the file:

```python
from agent.v6.trace import write_trace
```

Then find the line `result = agent.run(seed)` and change it to:

```python
    result = agent.run(seed)
    write_trace(result, node="setup", state=state)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest agent/v6/tests/test_setup_node.py::test_setup_node_writes_trace -v`
Expected: PASS — 1 passed

- [ ] **Step 5: Wire the remaining 4 nodes (mechanical — same one-liner)**

For each node file: add `from agent.v6.trace import write_trace` next to the other `agent.v6` imports, and append the `write_trace(...)` call immediately after the `result = agent.run(...)` line.

`agent/v6/nodes/planner.py` — change:
```python
    result = agent.run(state["user_request"])
```
to:
```python
    result = agent.run(state["user_request"])
    write_trace(result, node="planner", state=state)
```

`agent/v6/nodes/coder.py` — change:
```python
    result = agent.run(_build_coder_seed(state))
```
to:
```python
    result = agent.run(_build_coder_seed(state))
    write_trace(result, node="coder", state=state)
```

`agent/v6/nodes/builder.py` — change:
```python
    result = agent.run(seed)
```
to:
```python
    result = agent.run(seed)
    write_trace(result, node="builder", state=state)
```

`agent/v6/nodes/tester.py` — change:
```python
    result = agent.run(_build_tester_seed(state))
```
to:
```python
    result = agent.run(_build_tester_seed(state))
    write_trace(result, node="tester", state=state)
```

- [ ] **Step 6: Run the full V6 test suite to verify no regressions**

Run: `python -m pytest agent/v6/tests/ -q`
Expected: PASS — all tests pass (the 5 node modules import cleanly, `test_trace.py` and the new wiring test pass)

- [ ] **Step 7: Commit**

```bash
git add Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/planner.py Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/setup.py Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/coder.py Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/builder.py Eco.Toolchain/Eco.AI.Assembly1/agent/v6/nodes/tester.py Eco.Toolchain/Eco.AI.Assembly1/agent/v6/tests/test_setup_node.py
git commit -m "feat(v6/nodes): call write_trace after agent.run in all 5 LLM nodes"
```

---

### Task 4: docker-compose mount + .gitignore + integration verification

**Files:**
- Modify: `docker-compose.yml`
- Modify: `Eco.Toolchain/Eco.AI.Assembly1/.gitignore`

- [ ] **Step 1: Add the `traces/` bind mount to `docker-compose.yml`**

In `Eco.Toolchain/Eco.AI.Assembly1/docker-compose.yml`, find the `api` service `volumes:` block and change:

```yaml
      - ./output:/app/output
      - ./source:/app/source:ro
```
to:
```yaml
      - ./output:/app/output
      - ./traces:/app/traces
      - ./source:/app/source:ro
```

- [ ] **Step 2: Add `traces/` to `.gitignore`**

Append a line to `Eco.Toolchain/Eco.AI.Assembly1/.gitignore`:

```
traces/
```

(Read the file first, then append — do not duplicate if a `traces/` entry somehow already exists.)

- [ ] **Step 3: Create the host `traces/` dir and commit the config changes**

```bash
mkdir -p Eco.Toolchain/Eco.AI.Assembly1/traces
git add Eco.Toolchain/Eco.AI.Assembly1/docker-compose.yml Eco.Toolchain/Eco.AI.Assembly1/.gitignore
git commit -m "chore(v6): mount traces/ into api container, gitignore it"
```

- [ ] **Step 4: Recreate the `api` container (CHECKPOINT — requires user confirmation)**

This is a deploy action: changing `docker-compose.yml` is NOT picked up by `uvicorn --reload`; the container must be recreated. **Ask the user before running this** — it briefly stops the running `api` container.

Run (from `Eco.Toolchain/Eco.AI.Assembly1/`):
```bash
docker compose up -d
```
Expected: `ecoos-api` recreated, `ecoos-frontend` unchanged. Confirm with:
```bash
docker compose exec api ls -ld /app/traces
```
Expected: the directory exists inside the container.

- [ ] **Step 5: Integration verification (manual UI run)**

1. Open http://localhost:3100, clear `ecov6.thread_id` in DevTools → Application → Local Storage.
2. Send a request, e.g. `Собери калькулятор с pow и sqrt`. Let the pipeline run at least through planner + setup.
3. On the **host**, verify traces landed:
   ```bash
   ls -la Eco.Toolchain/Eco.AI.Assembly1/traces/
   ```
   Expected: a `<thread_id>/` directory containing `01-planner.json`, `02-setup.json`, ... — one file per node attempt.
4. Validate one file is well-formed JSON with the expected shape:
   ```bash
   python -c "import json,sys; d=json.load(open(sys.argv[1])); print(d['meta'])" Eco.Toolchain/Eco.AI.Assembly1/traces/<thread_id>/01-planner.json
   ```
   Expected: prints the `meta` dict with `thread_id`, `node`, `seq`, `phase`, `status`, `iters`, etc.

- [ ] **Step 6: Final commit (if Step 5 surfaced any fixes)**

If integration verification was clean, there is nothing to commit here — the work is already committed in Steps 1-3 of this task and Tasks 1-3. If verification surfaced a bug, fix it, add a regression test, and commit with a `fix(v6/trace): ...` message.

---

## Self-Review

**1. Spec coverage:**
- Spec §3.1 (file layout, NN prefix) → Task 1 Step 3 (`seq` logic), Task 1 test `test_write_trace_seq_increments`. ✓
- Spec §3.2 (JSON schema, `messages_to_dict`) → Task 1 Step 3 (`payload` dict), Task 1 test (round-trip assert). ✓
- Spec §3.3 (`write_trace` module, algorithm) → Task 1 + Task 2. ✓
- Spec §3.4 (node integration, 5 nodes, 2 orchestration nodes skipped) → Task 3 (only the 5 LLM nodes; plan_gate/escalate not touched). ✓
- Spec §3.5 (docker-compose mount, `docker compose up -d`) → Task 4 Steps 1, 4. ✓
- Spec §4 (never-raises, no-context DEBUG, no-thread_id WARNING, default=str, atomic .tmp→replace) → Task 2 Step 3 (all handled in rewritten function); atomic write already in Task 1 Step 3. ✓
- Spec §5 (unit tests 1-5, integration) → Task 1 tests (happy path, seq), Task 2 tests (no-context, never-raises, default=str), Task 4 Step 5 (integration). ✓
- Spec §7 (.gitignore +`traces/`) → Task 4 Step 2. ✓

**2. Placeholder scan:** No "TBD"/"TODO"/"add error handling"-style placeholders. Every code step shows complete code. Task 4 Step 6 is conditional but explicit about what to do in each branch.

**3. Type consistency:** `write_trace(result, *, node, state, traces_root=None)` signature is identical across Task 1 Step 3, Task 2 Step 3, the Task 3 call sites, and the Task 3 wiring-test spy. `EcoAgentResult(status, stop_tool_name, stop_payload, history, error)` constructor matches `eco_agent.py:52-58`. `messages_to_dict` / `messages_from_dict` are the paired LangChain functions. `meta` keys are identical between Task 1 and Task 2 implementations.

**4. Note for executor:** Task 2 Step 3 rewrites the whole of `trace.py` (not a surgical edit) because the error-handling wrapper changes the function's control-flow structure. This is intentional — show the complete file.
