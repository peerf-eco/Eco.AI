# Plan: Swarm Orchestrator Integration — Harness ↔ External Orchestration Module

Repo: `Eco.Toolchain/Eco.AI.Assembly1` (harness). External Python **Swarm Orchestrator** (`eco_swarm`) runs **in-process** as a separate Python package (decision D1), consumed only through the `SwarmBrain` protocol — never by importing harness internals.

**Decision log (resolved with user):**
- **D1 In-process package**: orchestrator is imported by the harness; no network transport in v1. `SwarmBrain`/`SwarmHost` Protocols remain transport-agnostic so a separate-process mode can be added later without contract changes.
- **D2 Full worktree isolation + base/integration branches**: every agent (each worker AND the integration/verify phase) runs in its own git worktree on its own branch (`swarm/<run8>/worker_k`, `swarm/<run8>/integration`), all forked from `swarm/<run8>/base`. The user's `project_dir` working tree is untouched until the terminal merge-back after success. Non-git `project_dir` → swarm mode refuses with an actionable error (no auto `git init`).
- **D3 Integrator-only verification**: workers run only the cheap `run_build` compile-sanity check in their own worktree; the single tester agent (acceptance criteria, `run_artifact`) runs once in the integration worktree on the merged tree.
- **D4 Session-per-worker UI**: each worker registers a real harness session (`.harness-registry.json`) under the same project card with its own worktree — the existing UI renders it; frontend changes limited to a small agent-id/status badge (and an optional later "active agents" panel).

## 1. Goal

In AUTO (loop) pipeline mode, after the architect's plan is approved by the human, delegate implementation to a **swarm of parallel coder agents** instead of the single coder/tester sub-orchestrator. The external orchestrator decomposes the approved plan into subtasks with **minimal file-intersection probability** (disjoint write scopes → clean git merges), runs workers in isolated git worktrees, then integrates and verifies the merged tree.

Split of responsibilities:
- **Harness** = execution: agents, tools, worktrees, builds, events, HITL gates.
- **Orchestrator** = decisions: decomposition, worker assignment, merge ordering, retry/conflict policy.

## 2. Current-state facts the design relies on (verified in code)

- Pipeline seam: `eco_harness/backend/server.py:3311-3464` — after plan approval (`plan_decision`, approved text at `server.py:3288`) the server builds coder+tester and runs `Orchestrator` (EXECUTION_EDGES) via `_run_agent(sub_orch.run, ev_queue, coder_seed)` at `server.py:3464`. **This is the single substitution point.**
- Duck-typed agent contract: any object with `run(seed) -> EcoAgentResult(stop_tool_name=edge, stop_payload={"message"})` can be driven by `Orchestrator` (`agent/internal/orchestrator.py:59-161`); external backends already plug in this way via `adapters/eco_agent_bridge.py`.
- Worktrees: `eco_harness/worktrees.py` — `create_worktree(repo_root, session_id, name, root)` only; **no merge-back, no cleanup, one worktree per session, detached HEAD at current commit**.
- Per-agent sandboxing: every tool is bounded by the `project_dir` baked in at `make_role_agent` (`eco_harness/roles.py:203-313`) — a per-worker worktree path is automatically the file-ownership boundary.
- Hooks: `EcoAgent.before_tool_call(name,args) → {block, reason}` (used by architect `_plan_gate`, `agents/architect.py:367-409`) and `after_tool_call` (used by coder memos) — the enforcement points for file ownership and touch auditing.
- Event contract: agent `EcoAgentEvent(EventType, data)` → marshaled by `_make_on_event`/`_drain_events_until_sentinel` (`server.py:2847-2939`) into WS frames `node_event/phase_change/node_done/usage/...`; name maps `PHASE_OF`/`NODE_OF` at `server.py:2836-2843`.
- Decomposition inputs already exist by design: approved plan string + per-component specs `project_dir/docs/specs/Eco<Name>.md` (written by architect `write_spec`, validated in `plan_validator.py:405-418`) + `_project_manifest(project_dir)` (`server.py:2665-2684`). The codebase explicitly anticipates "a future parallel-coder orchestrator can read one spec per worker" (`architect.py:321,379`).
- No cooperative cancellation: abort = WS close / registry flag only. Swarm must add a cancel token.
- Concurrency model: one worker thread per session via `asyncio.to_thread` (`server.py:2941-2956`); nothing parallelizes agents today.

## 3. Architecture

```
Next.js UI ── /ws/chat (unchanged frames + new swarm_*) ── FastAPI server
   server.py (auto mode, approved plan) ──► SwarmGateway  [NEW, eco_harness/swarm/]
        │  (in-process Python API — D1)
        ▼
   SwarmOrchestrator  [eco_swarm package, in-process]
        │  decisions only: decompose → schedule → merge order
        ▼ calls back via SwarmHost protocol (implemented by gateway)
   SwarmExecutionHost (harness side)
        ├─ WorktreeMgr   (base + N worker + 1 integration worktree/branches — D2)
        ├─ WorkerPool    (make_role_agent("coder", project_dir=<worktree_i>) × N, threaded)
        ├─ OwnershipGate (before_tool_call write-scope enforcement)
        └─ Integrator    (merge waves → build + single tester loop on integration worktree — D3)
```

**Transport (D1, resolved):** the orchestrator is a normal Python package consumed in-process through two small Protocols (`SwarmBrain` called by harness; `SwarmHost` called by orchestrator). LLM calls, config, and tracing stay inside the single harness process; no serialization or network hop in v1. The Protocols are transport-agnostic, so a separate-process/REST mode can be added later by swapping one adapter class. The orchestrator gets its own LLM profile via `ECO_SWARM_*` env/`config/swarm.yaml`, not by importing harness internals.

**Preconditions enforced by `SwarmGateway.dispatch` (D2):** `project_dir` must be a git repo with a resolvable HEAD; the gateway creates branch `swarm/<run8>/base` from HEAD, auto-committing any dirty state (including the pre-seeded scaffold) so workers fork from a consistent commit; the user's current branch and working tree stay untouched. If the dir is not a repo, dispatch returns `SwarmRunResult(status="agent_failed", error="swarm mode requires a git repository: …")` and the server falls back to a plain actionable `error` frame — no auto `git init`.

## 4. Contracts (DTOs — pydantic, shared verbatim by both sides)

```python
class SubtaskSpec(BaseModel):
    id: str                       # "st-<run8>-01"
    title: str
    instructions_md: str          # self-contained brief: goal, acceptance criteria, spec refs
    spec_paths: list[str]         # docs/specs/Eco<Name>.md relevant to this subtask
    write_scope: list[str]        # path-prefix globs this worker may WRITE (enforced)
    read_scope: list[str]         # extra read hints beyond whole-tree read
    depends_on: list[str]         # DAG edges (empty = wave 0)
    est_files: list[str]          # files the planner expects to create/edit
    worker_backend: str = "internal"   # roles.yaml backend | external CLI name

class DecompositionPlan(BaseModel):
    run_id: str
    base_commit: str
    shared_files: dict[str, str]  # path → owner_subtask_id (EcoMain.c, Makefile: single owner or sequenced)
    subtasks: list[SubtaskSpec]   # waves implied by depends_on
    integration: IntegrationSpec  # merge order, final artifact path, acceptance criteria md

class WorkerReport(BaseModel):
    subtask_id: str
    status: Literal["done", "fail", "conflict"]
    files_touched: list[str]      # audited by OwnershipGate, not trusted from LLM
    summary_md: str
    error_md: str = ""

class MergeResult(BaseModel):
    subtask_id: str
    status: Literal["merged", "conflict", "build_failed"]
    conflicted_files: list[str] = []
    log_md: str = ""
```

### 4.1 Harness-side API — `eco_harness/swarm/gateway.py` (called by server.py)

```python
class SwarmGateway:
    def __init__(self, *, config: HarnessConfig, make_brain: Callable[[], SwarmBrain] | None = None): ...
    def enabled(self, mode: str) -> bool          # harness.yaml swarm.enabled + mode=="auto"
    def dispatch(self, job: SwarmJob, on_event: EventSink, cancel: CancelToken) -> SwarmRunResult
```
`SwarmJob = {thread_id, project_dir, approved_plan_md, manifest, specs: list[(path, md)], language, mode, scaffold_note, workspace_header}`. `SwarmRunResult` mirrors `OrchestratorResult` (`status/terminal_edge/last_message/hops`) so **server.py success/failure/escalation code after line 3474 works unchanged**.

### 4.2 Orchestrator-facing API — `SwarmHost` protocol (implemented by gateway, injected into brain)

```python
class SwarmHost(Protocol):
    def prepare_workers(self, plan: DecompositionPlan) -> list[WorkerHandle]     # worktrees + agents
    def run_worker(self, handle: WorkerHandle, task: SubtaskSpec,
                   on_event: EventSink, cancel: CancelToken) -> WorkerReport     # blocking, threadpool
    def merge(self, handle: WorkerHandle, *, strategy: str = "no-ff") -> MergeResult
    def cleanup(self, run_id: str, *, keep_on_failure: bool = True) -> None
    def build_integrated(self, artifact_hint: str) -> tuple[bool, str]           # run_build on merged tree
    def run_integrator(self, plan: DecompositionPlan, on_event: EventSink) -> OrchestratorResult
```

### 4.3 Orchestrator-side API — `SwarmBrain` protocol (implemented by external module)

```python
class SwarmBrain(Protocol):
    def decompose(self, job: SwarmJob) -> DecompositionPlan        # LLM + file-intersection minimization
    def on_worker_report(self, report: WorkerReport) -> str        # next action: proceed | retry | replan | abort
    def plan_merge_order(self, plan: DecompositionPlan,
                         reports: list[WorkerReport]) -> list[str] # subtask ids, dependency-respecting
    def on_merge_result(self, result: MergeResult) -> str          # continue | fix_worker | escalate
```
Recommended decomposition algorithm inside the brain (implementation guidance for the coder): (1) LLM proposes subtasks with `est_files`; (2) deterministic checker builds a file×subtask incidence matrix, computes pairwise intersections; (3) greedy reassignment/merge of subtasks sharing files until pairwise intersection = 0 (shared files move to `shared_files` with a single owner or become a sequenced wave-0 subtask); (4) LLM finalizes `instructions_md` per subtask. Decomposition quality gate: reject any plan where two subtasks share a write_scope path.

## 5. Harness changes (the actual work items)

### 5.1 `eco_harness/swarm/` (new package)
- `gateway.py` — SwarmGateway, SwarmHost impl, run loop: git preconditions (D2) → base branch/worktree → brain.decompose → waves from `depends_on` with parallel workers via `ThreadPoolExecutor` sized `swarm.max_workers` (default 4) → merges into `swarm/<run8>/integration` worktree → `run_build` sanity is worker-side (D3), acceptance build+tester happen only in the integration worktree → on terminal success, merge `swarm/<run8>/integration` into the user's checked-out branch (the only write to `project_dir`) → cleanup. Also registers each worker as a real harness session (D4, see §5.4).
- `ownership.py` — `make_ownership_gate(write_scope, project_dir, audit_log)`: a `before_tool_call` hook denying `write_file`/`write_spec`/any tool whose args resolve (via `tools/common.py::ensure_inside` semantics) outside `write_scope`; returns `{block: True, reason: "outside your assigned file scope: ..."}`. Also an `after_tool_call` auditor recording normalized touched paths into the run dir (`<project_dir>/.swarm/<run_id>/`).
- `merge.py` — merge worker branch `swarm/<run8>/<worker_k>` into integration branch `swarm/<run8>/integration` (checked out in its own worktree; merges never touch the main tree — D2), conflict detection → `MergeResult(conflict)`; on conflict the brain decides: spawn a fixer worker whose worktree checks out the integration branch and whose `write_scope` is exactly the conflicted files. Terminal success → single `git merge --no-ff swarm/<run8>/integration` into the user's branch in `project_dir`.
- `cancel.py` — `CancelToken` (threading.Event-based), checked between agent iterations by passing an optional `cancel_check` callback into `EcoAgent.run` (small signature addition at `eco_agent.py:244-262` loop; check per iteration, abort tool loop with status `"cancelled"`). The WS `abort` message and `POST /api/sessions/{id}/abort` both set the token.

### 5.2 `worktrees.py` extensions
- `create_worker_worktree(repo_root, run_id, worker_id, *, base_ref, root)` → branch `swarm/<run8>/<worker_id>` created from `base_ref` (`swarm/<run8>/base`), checked out in a dedicated worktree `<root>/<repo>-<run8>-<worker_id>` (full file isolation per D2 — one worktree per agent, named branches, not detached).
- `create_base_worktree(...)` / `create_integration_worktree(...)` — same pattern for the `swarm/<run8>/base` snapshot and `swarm/<run8>/integration` merge target.
- `remove_worktree(path)`, `list_worker_worktrees(run_id)`.
- Keep existing `create_worktree` untouched (single-session flow unchanged).

### 5.3 `server.py` seam (minimal diff)
At `server.py:3323` (after scaffold, before building coder/tester):
```python
swarm = SwarmGateway(config=connection_config)
if swarm.enabled(mode):
    result = await _run_agent(swarm.dispatch, ev_queue, swarm_job, cancel_token)
else:
    ... existing coder/tester sub-orchestrator ...
```
Downstream code (success check `terminal_edge=="done"`, artifact sweep, failure cards, escalation gate) is reused by making `SwarmRunResult` shape-compatible. In swarm mode the artifact sweep must target the integration worktree until merge-back, then `project_dir`. Add `swarm` entries to `PHASE_OF`/`NODE_OF` and new WS frames. The scaffold note stays as-is: it runs before the seam, and the D2 base-commit step captures it.

### 5.4 Event contract additions + worker sessions (server → UI; frontend `use-harness-socket.ts` handles them)
| type | payload | when |
|---|---|---|
| `swarm_decomposed` | `{run_id, subtasks:[{id,title,write_scope,depends_on,worker_backend}], shared_files}` | after brain.decompose |
| `swarm_worker_started` | `{run_id, subtask_id, worker, worktree, wave, session_id}` | worker launch |
| `swarm_worker_done` / `swarm_worker_failed` | `{run_id, subtask_id, summary_md, files_touched, session_id}` | worker exit |
| `swarm_merge_result` | `{run_id, subtask_id, status, conflicted_files}` | each merge |
| `swarm_integrating` | `{run_id, merged_count}` | before integrator tester loop |

Worker-level agent events reuse existing `node_event` with `node = f"coder#{worker_id}"` (add a pass-through node-name param to `_make_on_event`).

**Worker sessions (D4):** the gateway calls the existing `_record_session_start` / `_record_session_end` registry helpers (`server.py:1195-1256`) once per worker — `{thread_id: <worker_session_id>, project_path: <parent project>, title: subtask title, status, worktree: <worktree path>}` — so each agent appears as its own session card under the same project in the projects pane, with per-session traces and the existing session-export/JSONL replay working unchanged. Frontend changes stay minimal: render the `node` label (`coder#3`) already present in `node_event` frames and add a small status badge; a dedicated "active agents" panel is a possible later addition, not v1 scope.

### 5.5 Config
- `harness.yaml`: `swarm: {enabled: false, max_workers: 4, merge_strategy: no-ff, keep_worktrees_on_fail: true}`; env `ECO_SWARM_ENABLED`, `ECO_SWARM_MAX_WORKERS`.
- `config/swarm.yaml` (orchestrator-owned, loaded by the external module): LLM profile, decomposition limits (max subtasks, min files per subtask), retry policy.

## 6. Sequence of calls / events

```mermaid
sequenceDiagram
    participant U as UI (WebSocket)
    participant S as server.py /ws/chat
    participant A as Architect (planner)
    participant G as SwarmGateway (harness)
    participant O as SwarmOrchestrator (external)
    participant W as WorktreeMgr
    participant C as Coder#k (worker agent, worktree_k)
    participant T as Integrator (tester loop)

    U->>S: user_request (mode=auto)
    S->>A: planner.run(seed)
    A-->>S: stop_tool to_coder (plan_md)
    S-->>U: plan_review_required
    U->>S: plan_decision approved (+modified_plan_md)
    S->>G: dispatch(SwarmJob, ev_queue, cancel)
    G->>W: git preconditions (D2): repo? → branch swarm/run8/base from HEAD (auto-commit dirty state incl. scaffold)
    Note over G,W: non-git project_dir → actionable error, swarm refused (no auto git-init)
    G->>O: brain.decompose(job)  [plan + specs + manifest]
    O-->>G: DecompositionPlan (disjoint write_scopes, waves)
    G-->>U: swarm_decomposed + worker sessions registered (D4)
    loop each wave (depends_on satisfied, ≤ max_workers parallel)
        G->>W: create_worker_worktree(swarm/run8/worker_k ← swarm/run8/base) — own worktree
        W-->>G: WorktreeInfo(path, branch)
        G->>C: make_role_agent("coder", project_dir=worktree_k) + OwnershipGate
        G-->>U: swarm_worker_started (session card under project)
        C->>C: implements subtask (writes blocked outside write_scope; run_build sanity in worktree_k — D3)
        C-->>G: WorkerReport(done, files_touched) via stop_tool done/to_tester
        G-->>U: swarm_worker_done (+node_event stream during run)
        G->>O: brain.on_worker_report(report)
        O-->>G: proceed | retry | replan | abort
        G->>W: merge(worker branch → swarm/run8/integration worktree, never main tree)
        W-->>G: MergeResult
        G->>O: brain.on_merge_result(MergeResult)
        O-->>G: continue | fix_worker | escalate
        G-->>U: swarm_merge_result
    end
    G->>T: run_integrator (build + coder/tester EXECUTION_EDGES in integration worktree)
    T-->>G: OrchestratorResult(terminal "done" | fail)
    G-->>U: test_fail / build_fail cards (replayed from hops)
    G->>W: on success: git merge --no-ff swarm/run8/integration → user branch in project_dir (only main-tree write)
    G-->>S: SwarmRunResult (OrchestratorResult-shaped)
    S->>S: success check, artifact sweep (unchanged code)
    S-->>U: pipeline_done(success|failed)
    G->>W: cleanup(run_id) [drop worker/integration worktrees on success; keep per keep_worktrees_on_fail]
```

Escalation path: any `abort` → cancel token set → workers finish current iteration → gateway returns `status="agent_failed"` → existing `escalation_required` gate at `server.py:3552` handles the HITL decision unchanged.

## 7. Task list (ordered, for the implementing coder)

1. **Worktrees**: add `create_worker_worktree` / `create_base_worktree` / `create_integration_worktree` (named branches off `swarm/<run8>/base`), `remove_worktree`, `list_worker_worktrees` to `eco_harness/worktrees.py`; unit tests for branch naming, fork-from-base, re-merge idempotence.
2. **DTOs**: `eco_harness/swarm/contracts.py` — pydantic models from §4 (no harness-internal imports; this file is later copied into the orchestrator repo or published as a tiny shared package `eco-swarm-contracts`).
3. **Ownership gate**: `swarm/ownership.py` — `before_tool_call` write-scope enforcement + `after_tool_call` touch auditor; tests proving `write_file` outside scope is blocked and `read/grep/glob` unaffected.
4. **Cancel token**: optional `cancel_check` param through `EcoAgent.run` iteration loop; status `"cancelled"`; no behavior change when absent. Wire WS `abort` + `POST /api/sessions/{id}/abort` to set it.
5. **Git base/merge module**: `swarm/merge.py` — preconditions + base-branch auto-commit (dirty state incl. scaffold), merge worker branches into the integration worktree, conflict → `MergeResult`, terminal merge-back into the user's branch only on success; tests with a repo fixture (dirty tree, two workers editing disjoint files → clean merge; overlapping file → conflict detected; failure leaves main tree untouched).
6. **Gateway + host**: `swarm/gateway.py` implementing `SwarmGateway.dispatch` (preconditions, waves, ThreadPoolExecutor, event sink fan-out, worker session registration per D4, cleanup) and the `SwarmHost` protocol; result shaped as `OrchestratorResult`.
7. **Server seam**: substitute at `server.py:3323` behind `swarm.enabled(mode)`; add `PHASE_OF`/`NODE_OF` entries, worker node names, new WS frames from §5.4; artifact sweep target = integration worktree until merge-back.
8. **Frontend (minimal, D4)**: handle new frames in `frontend/components/chat/use-harness-socket.ts`; render worker session cards (data already lands in the registry) and surface the `coder#k` node label with a status badge. Optional later: dedicated active-agents panel — out of v1 scope.
9. **Config**: `harness.yaml` swarm block, env vars, `config/swarm.yaml` template, `env.example` + README matrix entries.
10. **Stub brain + golden test**: in-repo `swarm/stub_brain.py` (deterministic decomposition for tests); end-to-end test driving the full auto pipeline with 2–3 parallel workers on a fixture git project, asserting: disjoint merges, main tree untouched on failure, single merge-back on success, and `pipeline_done(success)`.
11. **External orchestrator package (`eco_swarm`)**: implement `SwarmBrain` (decomposer LLM + intersection minimizer, merge-order planner, retry/conflict policy) against a `SwarmHost` mock, then integration-test in-process against the harness gateway. Location: sibling package in the workspace (default `Eco.Toolchain/Eco.Swarm`) or in-repo subpackage — confirm at implementation start.

## 8. Risks / failure modes

- **LLM drifts outside its file scope** → mitigated by hard OwnershipGate block (not prompt-only), plus auditor report for post-mortem.
- **Hidden shared files** (EcoMain.c, Makefiles, generated glue) → decomposition contract forces `shared_files` with single owner; validator rejects overlapping write_scopes deterministically.
- **Git state edge cases** → dirty working tree and scaffold writes are captured by the `swarm/<run8>/base` auto-commit before any worker forks; non-repo dirs refuse swarm mode; failure never touches the main tree; user's branch advances only via the single terminal merge-back.
- **Build only works on integrated tree** → workers may `run_build` inside their own worktree for sanity (D3), but acceptance verification happens only in the integrator phase in the integration worktree.
- **Merge conflicts despite disjoint scopes** (renames, shared headers) → conflict path is first-class: brain spawns fixer worker scoped to conflicted files; keep_worktrees_on_fail preserves state.
- **Thread safety**: `make_role_agent` does `os.environ.setdefault` for binary paths (`roles.py:220-223`) — set env vars once at gateway init before spawning the pool.
- **No cancellation today** → cancel token (task 4) is a prerequisite, not optional.
- **Registry/session explosion** with many workers → per-worker session entries are small; cap `max_workers` (default 4) and sweep `swarm/<run8>/*` worktrees on success.
- **Trace bloat**: per-worker trace dirs under `traces/ses-<id8>/swarm/<run_id>/<worker>/`.

## 9. Validation

- Unit: worktree branch/fork-from-base/merge, ownership gate, contracts round-trip, base-commit capture of dirty trees.
- Integration: stub-brain e2e (task 10) — 3 workers, disjoint specs, merged build passes, main tree untouched on injected worker failure, single merge-back on success, UI receives all new frames, worker sessions appear under the project card.
- Manual: real auto-mode run with `swarm.enabled: true`; verify existing single-coder path untouched when disabled (default off → zero-risk rollout).

## 10. Resolved questions

1. ~~Deployment shape~~ → **D1: in-process package**; Protocols keep a future REST/WS mode additive.
2. ~~Merge target / git policy~~ → **D2: base + integration branches, one worktree per agent, merge-back only on success, refuse non-repos**.
3. ~~Verification placement~~ → **D3: integrator-only tester; per-worker run_build sanity only**.
4. ~~UI surface~~ → **D4: session-per-worker in the projects pane + timeline cards; minimal badge change; dedicated active-agents panel deferred**.
5. Orchestrator LLM provider/config — default: `config/swarm.yaml` profile owned by `eco_swarm` (same OpenRouter env, distinct model id). Non-blocking.
6. Shared `eco-swarm-contracts` package vs file-copy sync — default: file-copy for v1, extract package when `eco_swarm` stabilizes. Non-blocking.
7. `eco_swarm` repo location — default sibling package `Eco.Toolchain/Eco.Swarm`; confirm at implementation start. Non-blocking.
