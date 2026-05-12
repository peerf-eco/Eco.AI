---
title: V6 — Five-Node Pipeline with Claude-Code-Style Agents
status: draft
created: 2026-05-13
authors: yan, claude (Opus 4.7)
branch: feat/v6-five-node-pipeline
supersedes: V5 (kept as fallback)
related-memory:
  - v5-architecture.md
  - feedback_model_portability.md
  - feedback_langgraph_command_parent.md
  - reference_eco_cli_token.md
related-wiki:
  - F:/obsidian/wiki/concepts/pi-harness-agent-building-guide.md
  - F:/obsidian/wiki/concepts/harness-design-pattern.md
  - F:/obsidian/wiki/concepts/plan-review-execute-agent-pattern.md
  - F:/obsidian/wiki/concepts/nested-meta-tool-vs-flat-tools.md
---

# V6 — Five-Node Pipeline with Claude-Code-Style Agents

## 1. Summary

V6 is the next generation of the EcoOS assembly agent. It replaces V5's three-node Planner/Coder/Executor pipeline with a **five-node** pipeline:

```
PLANNER → SETUP → CODER → BUILDER → TESTER
                    ▲                  │
                    └── retry (≤ 3) ───┘
```

Each node runs a **claude-code-style agent** with native function-calling via OpenRouter — a Python implementation of pi-harness principles, encapsulated in an `EcoAgent` class. LangGraph remains as the **outer state machine only**; all tool-use, history management, and retry logic live inside `EcoAgent`.

The pipeline preserves V5 unchanged as a fallback. V4 remains as a deeper fallback.

## 2. Goals

1. **Plan-then-confirm-then-execute UX** — explicit user approval gate between planning and any side-effecting work (file creation, downloads, builds).
2. **Model portability preserved** — single `LLM_MODEL` env var drives all five nodes; no `with_structured_output`; native function-calling via OpenAI-compatible `bind_tools()`.
3. **Per-node isolation** — each node has its own narrow tool-set, system prompt, and stop tool. No cross-contamination of context. Tester is fully isolated from coder's summary.
4. **Bounded retry** — `retry_count ≤ 3` for builder-fail and tester-fail combined. On exhaustion, escalate to user via `interrupt()` for continue/abort decision.
5. **pi-harness-equivalent agent contract** — `EcoAgent` class exposes hooks (`prepare_arguments`, `before_tool_call`, `after_tool_call`, `on_event`) mirroring pi-harness `Agent` semantics, in Python.

## 3. Non-Goals (V6 scope discipline)

- No streaming of `text_delta` events from the LLM (the API is reserved in `EcoAgentEvent.TEXT_DELTA` but unimplemented; use `.invoke()` not `.stream()` for now).
- No `AbortSignal`-style cancellation mid-cycle. Long subprocess calls have timeouts; we do not need finer-grained abort.
- No per-node model selection. One model from `LLM_MODEL`. (Optional refactor later — function `get_llm_for_role(role)` may be introduced as the seam.)
- No deletion or refactor of V5 / V4 code. V6 lives parallel.
- No nested meta-tool pattern (single outer tool with mandatory CoT fields). Flat per-operation tools chosen for model portability, per `nested-meta-tool-vs-flat-tools.md` matrix.

## 4. Design Decisions (table)

| # | Decision | Choice | Why |
|---|---|---|---|
| D1 | Placement | New branch `feat/v6-five-node-pipeline` | V5 untouched; rollback = branch switch |
| D2 | Loop budget | `max_retry = 3` (combined builder+tester fails) then `interrupt()` to user | Anthropic harness pattern requires explicit budget; 3 is empirically sufficient for fixable code issues without burning budget |
| D3 | LLM per node | Single `LLM_MODEL` for all nodes | Preserves model-portability constraint; configurable via env; per-role split deferred |
| D4 | SETUP type | Agentic with verification (LLM in loop with `ecoos_pull` + `list_dir` tools) | LLM verifies pulled files actually exist; deterministic Python rejected because eco-cli can silently produce partial state |
| D5 | TESTER semantics | LLM-judge against plan acceptance criteria + user_request, with **no access to coder_summary_md** | Behavior-only judgment; anchoring bias mitigated by isolation |
| D6 | Plan-approve mechanism | `interrupt()` + `SqliteSaver` checkpointer in `./.eco/v6_checkpoints.db` | Survives reconnect; same mechanism as V4 PRD review |
| D7 | Agent-loop implementation | Approach C: dedicated `EcoAgent` class with hooks API mirroring pi-harness | User priority: "works like pi"; +hooks for future extensions |
| D8 | Handoff format | Structured fields in state (`components: list[dict]`, paths, etc.) + Markdown blobs (`plan_md`, `tester_report_md`) | Validated at boundaries; aligned with pi-harness "validate at boundaries, trust the core" |
| D9 | Tester isolation | Tester seed includes `user_request` + `plan_md` (acceptance) + `build_artifact`, NOT `coder_summary_md`, NOT source code | Anchoring bias mitigation (see `harness-design-pattern.md`) |
| D10 | Coder retry seed | Includes feedback (`build_log` or `tester_report_md`) but NOT previous `coder_summary_md` | Avoid divergence between "summary I wrote" and actual files; force LLM to read current files |

## 5. Architecture

### 5.1. Graph

```
                  ┌─── interrupt(plan_md, components) ────┐
                  │                                       ▼
              ┌───┴──┐    Command(resume=approved)     ┌──────┐
              │PLAN  │─────────────────────────────────│SETUP │
              │NER   │                                 │(agent│
              └──────┘                                 │+veri │
                                                       │fy)   │
                                                       └──┬───┘
                                                          │
                                                          ▼
              ┌──── builder_fail/tester_fail ─────┐   ┌──────┐
              │                                   │   │CODER │
              │                                   └───┤(claud│
              │                                       │e-code│
              │                                       └──┬───┘
              │                                          │
              │                                          ▼
              │                                      ┌───────┐
              │  retry_count++                       │BUILDER│
              │                                      │(MSVC) │
              │                                      └──┬────┘
              │                                         │
              │              pass                       ▼
              │             ┌──────────────────────────────┐
              │             │           TESTER             │
              │             │   (LLM-judge, isolated)      │
              │             └───┬──────────────────────┬───┘
              │                 │ fail (retry < 3)     │ pass
              └─────────────────┘                      ▼
                                                  ┌─────┐
              retry >= 3 ──► interrupt(failure) ──┤ END │
                                                  └─────┘
```

### 5.2. State (`agent/v6/state.py`)

```python
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

    # Per-node histories (live inside each node; reset on entry)
    planner_messages: Annotated[list, add_messages]
    setup_messages:   Annotated[list, add_messages]
    coder_messages:   Annotated[list, add_messages]
    builder_messages: Annotated[list, add_messages]
    tester_messages:  Annotated[list, add_messages]

    # Structured handoffs between nodes
    plan_md:          str             # planner -> setup, coder, tester
    components:       list[dict]      # planner -> setup; each: {cid, version, name, reason}
    project_dir:      str             # setup -> coder, builder
    project_name:     str
    downloaded_paths: list[str]       # setup -> coder; verified by list_dir
    coder_summary_md: str             # coder -> builder (NOT to tester)
    build_artifact:   str             # builder -> tester; path to built .exe
    build_log:        str             # builder -> coder on fail
    tester_report_md: str             # tester -> coder on fail | tester -> done on pass

    # Loop control
    phase:               Phase
    retry_count:         int          # 0..max_retries; combined builder+tester fails
    max_retries:         int          # default 3; set via make_initial_state(max_retries=N); also configurable via V6_MAX_RETRIES env (read in graph.py at startup)
    last_failure_origin: Literal["", "builder", "tester"]
    last_status:         str          # "" | "success" | "max_retries_escalated" | "user_aborted" | "user_continue"
```

### 5.3. Checkpointer

```python
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("./.eco/v6_checkpoints.db")
```

`.eco/` is already in `.gitignore` (see git status). Sqlite chosen over Memory for: persistence across backend restart between user-approval rounds; small footprint (~1-2 KB per session); no extra deploy dependencies.

### 5.4. Handoff principle

**Per-node `_messages` live INSIDE the node.** Each node starts its message history fresh on entry (seed = system_prompt + user_seed_text). The history is for the node's internal claude-code-style loop only — it never leaves the node.

**Between nodes**: only structured state fields cross. Tester sees only `user_request` + `plan_md` + `build_artifact` — never `coder_summary_md` and never the source code.

## 6. EcoAgent contract

File: `agent/v6/eco_agent.py` (~250-300 lines).

### 6.1. Data types

```python
@dataclass(frozen=True)
class ToolResult:
    content: str                # becomes ToolMessage.content (sent to LLM)
    details: dict | None = None # for UI/logs, NOT sent to LLM
    is_error: bool = False

@dataclass(frozen=True)
class EcoTool:
    name: str
    description: str
    args_schema: type[BaseModel]    # pydantic — both JSON Schema and validator
    execute: Callable[[BaseModel], ToolResult]  # throw on hard error; return is_error=True on soft

class EventType(str, Enum):
    START         = "start"
    TEXT_DELTA    = "text_delta"      # reserved for future streaming
    TOOL_START    = "tool_call_start"
    TOOL_END      = "tool_call_end"
    TOOL_UPDATE   = "tool_update"     # progress from within a tool
    ITERATION     = "iteration"
    DONE          = "done"
    NO_TOOL_CALL  = "no_tool_call"
    MAX_ITERS     = "max_iters"
    ERROR         = "error"

@dataclass
class EcoAgentEvent:
    type: EventType
    data: dict

@dataclass
class EcoAgentResult:
    status: Literal["done", "no_tool_call", "max_iters", "error"]
    stop_tool_name: str             # which stop tool fired (empty if status != "done")
    stop_payload: dict              # args of the stop tool (empty if status != "done")
    history: list[BaseMessage]
    error: str
```

### 6.2. Class

```python
class EcoAgent:
    def __init__(
        self,
        *,
        llm: BaseChatModel,
        system_prompt: str,
        tools: list[EcoTool],
        stop_tool: str | list[str] | None = None,
        max_iters: int = 25,
        prepare_arguments: Callable[[str, dict], dict] | None = None,
        before_tool_call:  Callable[[str, BaseModel], dict | None] | None = None,
        after_tool_call:   Callable[[str, BaseModel, ToolResult], ToolResult] | None = None,
        on_event:          Callable[[EcoAgentEvent], None] | None = None,
    ):
        ...

    def run(self, seed: str | list[BaseMessage]) -> EcoAgentResult:
        """
        Run the agent loop synchronously. Returns when:
        - a stop_tool was called (status='done')
        - model responded without tool_calls (status='no_tool_call')
        - max_iters reached (status='max_iters')
        - exception in the loop itself (status='error')
        """
```

### 6.3. Loop (pseudocode)

```
emit(START)
history = [SystemMessage(system_prompt)] + normalize(seed)
llm_bound = llm.bind_tools([tool_to_langchain(t) for t in tools])

for i in 0..max_iters:
    emit(ITERATION, {"i": i})
    resp = llm_bound.invoke(history)
    history.append(resp)

    if not resp.tool_calls:
        emit(NO_TOOL_CALL); return EcoAgentResult(status="no_tool_call", ...)

    for tc in resp.tool_calls:
        emit(TOOL_START, {"name": tc.name, "args": tc.args})

        raw = prepare_arguments(tc.name, tc.args) if prepare_arguments else tc.args
        try:
            args = tool.args_schema.model_validate(raw)
        except ValidationError as e:
            history.append(ToolMessage(f"ARGS ERROR: {e}", tc.id, status="error"))
            continue

        gate = before_tool_call(tc.name, args) if before_tool_call else None
        if gate and gate.get("block"):
            history.append(ToolMessage(f"BLOCKED: {gate.get('reason')}", tc.id, status="error"))
            continue

        if tc.name in (stop_tool if isinstance(stop_tool, list) else [stop_tool]):
            emit(DONE, {"stop_tool_name": tc.name, "payload": args.model_dump()})
            return EcoAgentResult(status="done", stop_tool_name=tc.name, ...)

        try:
            result = tool.execute(args)
        except Exception as e:
            history.append(ToolMessage(f"TOOL ERROR: {e}", tc.id, status="error"))
            continue

        if after_tool_call:
            result = after_tool_call(tc.name, args, result)

        emit(TOOL_END, {"name": tc.name, "details": result.details, "is_error": result.is_error})
        history.append(ToolMessage(
            content=result.content,
            tool_call_id=tc.id,
            status="error" if result.is_error else "success",
        ))

emit(MAX_ITERS); return EcoAgentResult(status="max_iters", ...)
```

### 6.4. Error policy

| Situation | Behavior |
|---|---|
| Tool raises exception | Caught; `ToolMessage(error)` appended; loop continues (model may try another approach) |
| Tool args fail validation | `ToolMessage(error)` with validation message; loop continues |
| `before_tool_call` returns `{"block": True}` | `ToolMessage(error)` with `reason`; loop continues |
| LLM/network error during `.invoke()` | Propagated to caller (node decides whether to retry or fail) |
| `max_iters` exhausted | `EcoAgentResult(status="max_iters")`; node decides next move |

## 7. Per-node specifications

### 7.1. PLANNER

| | |
|---|---|
| File | `agent/v6/nodes/planner.py` + `agent/v6/tools/planner.py` |
| Seed | `state.user_request` |
| System prompt | "You are an EcoOS Planner. Read available SDK components via `read_component`. Produce a plan in Markdown including: project_name, narrative description, component list with cid/version/reason, and explicit acceptance criteria (what stdout should look like, exit code, etc.). End by calling `submit_plan`." |
| Tools | `read_component(name)`, `list_components()`, `submit_plan(...)` |
| Stop tool | `submit_plan` |
| Stop args | `project_name: str`, `plan_md: str`, `components: list[{cid: str, version: str, name: str, reason: str}]`, `acceptance_criteria: list[str]` |
| Writes state | `plan_md`, `components`, `project_name`, `phase = "awaiting_approval"` |
| Then | LangGraph routes to `plan_gate` → `interrupt({"plan_md", "components"})` |

### 7.2. PLAN_GATE (no agent — wraps `interrupt()`)

| | |
|---|---|
| File | `agent/v6/nodes/plan_gate.py` |
| Behavior | Pure `interrupt({"plan_md": state["plan_md"], "components": state["components"]})` |
| Resume value | `{"approved": bool, "modified_plan_md"?: str, "reason"?: str}` |
| Routing | `approved=True` → `phase="setup"` → SETUP; `approved=False` → `phase="done"`, `last_status="user_aborted"` → END |

### 7.3. SETUP

| | |
|---|---|
| File | `agent/v6/nodes/setup.py` + `agent/v6/tools/setup.py` |
| Seed | `f"Plan:\n{plan_md}\n\nComponents to download:\n{json.dumps(components, indent=2)}\n\nCreate project at: {project_dir} and pull each component there. After each pull, verify the package directory exists. When all components are verified, call mark_setup_done."` |
| Tools | `ecoos_pull(cid, version)`, `list_dir(path)`, `read_file(path)`, `mark_setup_done(downloaded_paths)` |
| Stop tool | `mark_setup_done` |
| Stop args | `downloaded_paths: list[str]` |
| Writes state | `project_dir`, `downloaded_paths`, `phase = "coding"` |
| Tool safety: `ecoos_pull` | argv-list to `eco.sli/eco-cli.exe pull -c CID -v VERSION -d <project_dir>`; **no shell**; CID regex `^[0-9A-F]{32}$`; version regex `^\d+\.\d+\.\d+\.\d+$`; CID+version must exist in `state.components` (cross-check); `subprocess.run(timeout=60, shell=False)` |
| Tool safety: `list_dir`/`read_file` | path must be under `project_dir` OR under `eco.sli/` (for SDK headers) |

### 7.4. CODER

| | |
|---|---|
| File | `agent/v6/nodes/coder.py` + `agent/v6/tools/coder.py` |
| Seed (first attempt) | `f"User request:\n{user_request}\n\nPlan:\n{plan_md}\n\nProject dir: {project_dir}\nAvailable components in: {downloaded_paths}\n\nImplement the plan. Use write_file to create EcoMain.c, Makefile, etc. Call mark_code_done when complete."` |
| Seed (retry) | Above + appended: `f"\n\nThis is retry #{retry_count}. Previous attempt failed:\n\n## {failure_origin} log\n{build_log or tester_report_md}\n\nRead the existing files via read_file/grep, locate the issue, and fix it. You can edit_file or rewrite via write_file."` |
| Tools | `read_file`, `write_file`, `edit_file`, `list_dir`, `glob`, `grep`, `mark_code_done(summary_md)` |
| **NO `bash`** | By design — build is BUILDER's responsibility |
| Stop tool | `mark_code_done` |
| Stop args | `summary_md: str` |
| Writes state | `coder_summary_md`, `phase = "building"` |
| Tool safety | `write_file`/`edit_file`: path must be inside `project_dir` (resolved-path check; reject `..`); `read_file`/`glob`/`grep` may also read `downloaded_paths`; reject all other paths with `is_error` |

### 7.5. BUILDER

| | |
|---|---|
| File | `agent/v6/nodes/builder.py` + `agent/v6/tools/builder.py` |
| Seed | `f"Build the project at {project_dir}. Components are in: {downloaded_paths}. Coder summary:\n{coder_summary_md}\n\nInvoke run_make. Inspect output. If success, call report_build_pass with the artifact path. If fail, extract the key error from the log and call report_build_fail."` |
| Tools | `run_make(target='all')`, `read_file`, `list_dir`, `report_build_pass(artifact_path)`, `report_build_fail(error_md)` |
| Stop tool | `["report_build_pass", "report_build_fail"]` |
| `run_make` impl | Subprocess wrapper: `cmd.exe /c "vcvarsall.bat x64 && make"` with `cwd=project_dir`, `env={"MSYS_NO_PATHCONV": "1", "MSYS2_ARG_CONV_EXCL": "*"}` (from V5 build gotcha #2), `timeout=300`, capture stdout+stderr |
| Writes state on pass | `build_artifact = artifact_path`, `phase = "testing"` |
| Writes state on fail | `build_log = error_md`, `retry_count += 1`, `last_failure_origin = "builder"`; `phase = "coding"` if `retry_count < max_retries` else `"failed_escalated"` |

### 7.6. TESTER (isolated)

| | |
|---|---|
| File | `agent/v6/nodes/tester.py` + `agent/v6/tools/tester.py` |
| Seed | `f"User request:\n{user_request}\n\nAcceptance criteria from plan:\n{extract_acceptance_section(plan_md)}\n\nBuilt artifact: {build_artifact}\n\nYour job: run the artifact and decide if it behaves as the user asked. You CANNOT see the source code — judge by observable behavior only."` |
| **Does NOT see** | `coder_summary_md` (anchoring bias mitigation); also **no source-file read tool** — TESTER has no `read_file` |
| Tools | `run_artifact(timeout_s=10)`, `report_test_pass(reason_md)`, `report_test_fail(reason_md)` |
| Why no `read_file` | Removing the read capability **enforces** behavior-only judgment at the tool layer. If TESTER could `read_file(project_dir/main.c)`, the anchoring-bias mitigation would be only a prompt instruction — fragile. Removing the tool makes it structurally impossible. If we later discover the artifact writes a result file the tester needs to inspect, we add a narrowly-scoped tool (e.g., `read_artifact_output(filename)` restricted to runtime output files). |
| Stop tool | `["report_test_pass", "report_test_fail"]` |
| `run_artifact` impl | `subprocess.run([build_artifact], timeout=timeout_s, capture_output=True, text=True)`; returns `{stdout, stderr, exit_code, timed_out}` as JSON string |
| Writes state on pass | `tester_report_md`, `phase = "done"`, `last_status = "success"` |
| Writes state on fail | `tester_report_md`, `retry_count += 1`, `last_failure_origin = "tester"`; `phase = "coding"` if `retry_count < max_retries` else `"failed_escalated"` |

### 7.7. ESCALATE (no agent — wraps `interrupt()`)

| | |
|---|---|
| File | `agent/v6/nodes/escalate.py` |
| Behavior | `interrupt({"failure_origin": ..., "build_log": ..., "tester_report_md": ..., "retry_count": ..., "plan_md": ..., "coder_summary_md": ...})` |
| Resume value | `{"continue": bool}` |
| Routing on `continue=True` | `retry_count = 0`, `last_status = "user_continue"`, `phase = "coding"` → CODER |
| Routing on `continue=False` | `phase = "done"`, `last_status = "user_aborted"` → END |

## 8. Data flow

### 8.1. LangGraph wiring

```python
g = StateGraph(V6State)

g.add_node("planner",   planner_node)
g.add_node("plan_gate", plan_gate_node)
g.add_node("setup",     setup_node)
g.add_node("coder",     coder_node)
g.add_node("builder",   builder_node)
g.add_node("tester",    tester_node)
g.add_node("escalate",  escalate_node)

g.set_entry_point("planner")
g.add_edge("planner", "plan_gate")
g.add_conditional_edges("plan_gate", route_after_plan_gate, {"setup": "setup", END: END})
g.add_edge("setup",   "coder")
g.add_edge("coder",   "builder")
g.add_conditional_edges("builder",  route_after_builder,
    {"tester": "tester", "coder": "coder", "escalate": "escalate"})
g.add_conditional_edges("tester",   route_after_tester,
    {END: END, "coder": "coder", "escalate": "escalate"})
g.add_conditional_edges("escalate", route_after_escalate, {"coder": "coder", END: END})
```

### 8.2. Routing functions

```python
def route_after_plan_gate(s: V6State) -> str:
    return "setup" if s["phase"] == "setup" else END

def route_after_builder(s: V6State) -> str:
    return {"testing": "tester", "coding": "coder", "failed_escalated": "escalate"}[s["phase"]]

def route_after_tester(s: V6State) -> str:
    return {"done": END, "coding": "coder", "failed_escalated": "escalate"}[s["phase"]]

def route_after_escalate(s: V6State) -> str:
    return "coder" if s.get("last_status") == "user_continue" else END
```

## 9. Backend integration

### 9.1. WebSocket endpoint `/ws/v6/chat`

New endpoint in `backend/server.py` mirroring the existing `/ws/v5/chat` pattern. Reuses `PipelineSession` infrastructure (asyncio.Lock + event queue, hardened in PR #10).

```python
@app.websocket("/ws/v6/chat")
async def v6_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    llm = get_llm()
    from agent.v6.graph import create_v6_graph
    from langgraph.checkpoint.sqlite import SqliteSaver
    checkpointer = SqliteSaver.from_conn_string("./.eco/v6_checkpoints.db")
    graph = create_v6_graph(llm, checkpointer=checkpointer)
    # ... use PipelineSession pattern from /ws/v5/chat
```

### 9.2. WebSocket events (server → client)

| Event type | When | Payload |
|---|---|---|
| `phase_change` | After every `state.phase` mutation | `{"phase": "..."}` |
| `node_started` | Before `agent.run()` in each node | `{"node": "planner"\|"setup"\|...}` |
| `node_event` | Inside `EcoAgent.on_event` callback | `{"node": ..., "event": {type, data}}` |
| `node_done` | After `agent.run()` returns done | `{"node": ..., "stop_tool": ..., "summary": ...}` |
| `plan_review_required` | On `plan_gate` entry | `{"plan_md", "components"}` |
| `build_fail` / `test_fail` | After respective `report_*_fail` | `{"error_md", "retry_count"}` |
| `max_retry_escalation` | On `escalate` entry | `{"failure_origin", "build_log", "tester_report_md", "retry_count"}` |
| `pipeline_done` | On END | `{"status": "success"\|"user_aborted", "build_artifact"?, "tester_report_md"?}` |

### 9.3. WebSocket messages (client → server)

| Message type | When | Server action |
|---|---|---|
| `user_request` | Session start | `graph.stream({"user_request": ...}, config={"thread_id"})` |
| `plan_decision` | After `plan_review_required` | `graph.stream(Command(resume={"approved", "modified_plan_md"?}), config)` |
| `escalation_decision` | After `max_retry_escalation` | `graph.stream(Command(resume={"continue": True\|False}), config)` |
| `abort` | Any time | Cancel session, cleanup |

## 10. Frontend integration

### 10.1. Feature flag

`NEXT_PUBLIC_USE_V6 > NEXT_PUBLIC_USE_V5 > V4` priority. V6 is opt-in via env.

### 10.2. UI elements (in `frontend/components/chat/chat-interface.tsx`)

- **Phase indicator**: 5 stages — Planning → Setup → Coding → Building → Testing. Animated transitions on `phase_change`.
- **Per-node progress block**: shows current tool / iteration / last `tool_end` summary.
- **Plan approval block**: Markdown viewer + edit-toggle + Approve/Reject. Renders on `plan_review_required`.
- **Max retry escalation block**: failure summary + Continue/Abort. Renders on `max_retry_escalation`.

V5 and V4 UI remain for their respective feature flags.

## 11. Testing strategy

### 11.1. Pyramid

```
                  ┌──────────────────────────┐
                  │  Live E2E (real LLM)     │  1-3 tests, @pytest.mark.live
                  │  test_live_e2e.py        │  ~30s each, NOT in CI
                  └──────────────────────────┘
              ┌──────────────────────────────────┐
              │  Graph integration (mock LLM)    │  ~5 tests
              │  test_graph_e2e.py               │
              └──────────────────────────────────┘
         ┌────────────────────────────────────────────┐
         │  Per-node integration (mock LLM)           │  ~15 tests
         │  test_{planner,setup,coder,builder,tester} │  (3 per node)
         └────────────────────────────────────────────┘
    ┌──────────────────────────────────────────────────────┐
    │  Unit (EcoAgent + tools)                             │  ~30 tests
    │  test_eco_agent.py, test_tools_{planner,setup,...}.py│
    └──────────────────────────────────────────────────────┘
```

### 11.2. Mock strategy

- **`FakeChatModel`**: returns a single scripted `AIMessage` (text + optional `tool_calls`). For unit tests.
- **`ScriptedChatModel`**: holds a list of scripted `AIMessage`s and returns them one-per-`.invoke()`. For integration tests.
- **subprocess**: `monkeypatch` on `subprocess.run` in tool tests.
- **filesystem**: pytest `tmp_path` fixture as project_dir.

### 11.3. Coverage targets

| Module | Coverage |
|---|---|
| `eco_agent.py` | 95%+ |
| `tools/*.py` | 80%+ |
| `nodes/*.py` | 70%+ (happy + main fail path each) |
| Graph integration | 5 paths covered (see 11.5) |

### 11.4. EcoAgent unit tests (`test_eco_agent.py`)

| Test | Mechanism |
|---|---|
| Happy: loop reaches stop_tool | `FakeChatModel` → `tool_calls=[read]` then `tool_calls=[submit]` |
| No tool_call: model returns plain text → `status="no_tool_call"` | `FakeChatModel` returns text without `tool_calls` |
| Max iters: model loops forever → `status="max_iters"` | Infinite `tool_calls=[read]`, `max_iters=3` |
| Tool exception → `ToolMessage(error)`, loop continues to stop | Tool with `execute=lambda: raise RuntimeError("boom")` then stop in next step |
| Validation error → `ToolMessage(error)` re args, loop continues | LLM returns args violating schema |
| `before_tool_call` → `{"block": True}` blocks the call | Hook blocks one step; loop continues to stop |
| `prepare_arguments` shim runs before validation | Hook renames `file_path → path` |
| `on_event` fires for every stage | Hook collects events; verify ordering |
| Two stop_tools (`list`) — correctly identified | `stop_tool=["pass", "fail"]`; assert `result.stop_tool_name` |

### 11.5. Graph E2E (`test_graph_e2e.py`)

| Test | What it verifies |
|---|---|
| `test_happy_path` | planner → setup → coder → builder → tester → done, no retry |
| `test_user_rejects_plan` | planner → plan_gate → END with `last_status="user_aborted"` |
| `test_build_fail_retry_success` | build fail #1 → coder retry → build pass → done |
| `test_max_retry_escalation_continue` | 3 build fails → escalate → user continues → another attempt → pass |
| `test_max_retry_user_aborts` | 3 fails → escalate → user aborts → END |

### 11.6. Live E2E (`test_live_e2e.py`)

```python
@pytest.mark.live  # skip by default; pytest --live to enable
@pytest.mark.timeout(300)
def test_calculator_app(live_llm):
    graph = create_v6_graph(live_llm, checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-live-1"}}

    plan_event = None
    for ev in graph.stream(
        {"user_request": "калькулятор: сложение двух чисел"},
        config,
    ):
        if "__interrupt__" in ev:
            plan_event = ev["__interrupt__"][0]
            break
    assert plan_event is not None
    assert "components" in plan_event.value

    for _ in graph.stream(Command(resume={"approved": True}), config):
        pass

    state = graph.get_state(config).values
    assert state["last_status"] == "success"
    assert os.path.exists(state["build_artifact"])
```

## 12. File map

```
agent/v6/
  __init__.py
  state.py                     # V6State + Phase + make_initial_state
  eco_agent.py                 # EcoAgent class + ToolResult + EcoTool + events
  graph.py                     # create_v6_graph() + routing functions
  nodes/
    __init__.py
    planner.py
    plan_gate.py
    setup.py
    coder.py
    builder.py
    tester.py
    escalate.py
  tools/
    __init__.py
    common.py                  # shared: path-traversal check, regex validators
    planner.py
    setup.py                   # includes ecoos_pull wrapper
    coder.py
    builder.py                 # includes run_make wrapper
    tester.py                  # includes run_artifact wrapper
  tests/
    __init__.py
    conftest.py                # FakeChatModel, ScriptedChatModel, tmp project_dir fixtures
    test_eco_agent.py
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
    test_live_e2e.py           # @pytest.mark.live
```

Outside `agent/v6/`:
- `backend/server.py` — add `/ws/v6/chat` endpoint (~200 lines)
- `frontend/components/chat/chat-interface.tsx` — V6 conditional UI (~300 lines)

## 13. Open risks and mitigations

| Risk | Mitigation |
|---|---|
| LLM-judge tester accepts buggy code as "looks right" | Isolated context (no source / no coder_summary); strict acceptance criteria in plan; live tests will surface this empirically |
| `eco-cli.exe` silently produces partial output | SETUP-node verifies via `list_dir` after each pull before declaring done |
| `vcvarsall.bat` env spill between sessions | Each `run_make` call invokes fresh `cmd.exe /c "vcvarsall.bat x64 && make"`; no env leakage |
| 5 nodes × tools = lots of code to maintain | Single `EcoAgent` infrastructure shared; per-node code is essentially `seed + tools + system_prompt` (small) |
| SqliteSaver db growth | Negligible (~1-2 KB per session); cleanup script can be added later if needed |
| Coder gets stuck in retry loop on architectural mistake | `max_retries=3` then `interrupt()` to user — user decides whether to continue or restart |
| OpenRouter routes to a model that breaks `bind_tools()` | `LLM_MODEL` env is user-controlled; documented set of known-good models (kimi-k2-thinking, glm-4.6, deepseek-v3.2-exp) |

## 14. Migration & rollout

1. **Phase 0** (this spec) — design approved.
2. **Phase 1** — implement `EcoAgent` + unit tests. Land on `feat/v6-five-node-pipeline`.
3. **Phase 2** — implement tools + per-node tests.
4. **Phase 3** — wire graph + integration tests with mock LLM.
5. **Phase 4** — backend endpoint + frontend feature flag.
6. **Phase 5** — live E2E with real OpenRouter + simple "calculator" request.
7. **Phase 6** — merge to main behind feature flag. V5 stays as default until V6 is validated on multiple model variants (kimi, glm, deepseek minimum).

V6 does NOT delete V5 or V4 on merge. Cleanup of V5 is a separate decision after V6 has run reliably for ≥1 month.

## 15. Glossary

| Term | Definition |
|---|---|
| EcoAgent | Python class implementing claude-code-style agent loop with hooks API, mirroring pi-harness `Agent` |
| Stop tool | A tool whose invocation ends the node's `EcoAgent.run()` and writes structured output to state |
| Handoff | Structured data passed between nodes via `V6State` fields (not via in-node message history) |
| Anchoring bias | LLM-judge oversight tendency when it has seen the candidate's reasoning (mitigated in TESTER) |
| Loop budget | `max_retries` (default 3) combined cap on builder-fail and tester-fail retries before escalation |
| Plan-approve gate | `interrupt()` between PLANNER and SETUP; user reviews `plan_md` and explicit `components` list |
| Max-retry escalation | `interrupt()` after `retry_count >= max_retries`; user decides continue (resets count) or abort |

## 16. References

### Internal
- `Eco.Toolchain/Eco.AI.Assembly1/agent/state_v5.py` — V5 state schema (V6 extends)
- `Eco.Toolchain/Eco.AI.Assembly1/agent/main.py:get_llm` — OpenRouter ChatOpenAI factory (V6 reuses)
- `Eco.Toolchain/Eco.AI.Assembly1/backend/server.py` — V5 WebSocket pattern (V6 extends with `/ws/v6/chat`)
- `Eco.Toolchain/Eco.AI.Assembly1/agent/chat_agent.py:create_chat_agent` — V4 PRD-review interrupt pattern (V6 uses same)

### Cross-project wiki
- `F:/obsidian/wiki/concepts/pi-harness-agent-building-guide.md` — pi-harness principles being ported
- `F:/obsidian/wiki/concepts/harness-design-pattern.md` — Anthropic harness pattern (Planner/Generator/Evaluator)
- `F:/obsidian/wiki/concepts/plan-review-execute-agent-pattern.md` — PRE pattern (plan-approval gate)
- `F:/obsidian/wiki/concepts/nested-meta-tool-vs-flat-tools.md` — why we choose flat tools for model portability
