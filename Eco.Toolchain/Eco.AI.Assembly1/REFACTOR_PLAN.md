# Eco.AI.Assembly1 — Architectural Audit & Meta-Harness Design Spec

**Scope:** Custom ACOM coding harness (EcoOS component assembly)  
**Active production path:** V7 three-agent orchestrator (`architect → coder → tester`) over `pi_ai` + FastAPI WebSocket `/ws/v7/chat` + Next.js UI  
**Audit date:** 2026-07-26  
**Status:** Read-only audit + design (no code changes applied)

---

## Executive summary

The repo is a **V7-only** ACOM assembly harness after a large 2026-06-22 retirement of LangGraph/LangChain V1–V6 and ChromaDB. The live stack is small and coherent (~3.7k LOC core agent + 663-line backend + Next.js chat UI), but it still carries:

1. **Historical docs and templates** that describe dead pipelines (V3–V5 chat mode, verification graph, V4 superpowers).
2. **Scattered hardcoding** (models, paths, prompts, magic numbers, Windows personal paths).
3. **Critical runtime/data defects** — empty Docker bind-mounts for marketplace, frontend WS defaulting to `/ws/v6/chat`, layout prompt vs scaffold conflict, single shared model, no token budgets.
4. **UI “tens of seconds” latency** with multiple independent root causes (compose health gate, Next cold start, WS version/port mismatch, Google Fonts, empty marketplace thrash on first agent turn).

Recommended evolution: **thin meta-orchestrator** (this repo) that owns ACOM domain knowledge + marketplace tools, and **pluggable agent backends** (internal EcoAgent, Claude/Codex/Grok/Pi CLIs) with per-role model/budget config — rather than rewriting everything as a Pi plugin (though a Pi plugin is a viable secondary path for CLI power users).

---

## Current architecture (ground truth)

```
┌──────────── Frontend (Next 14) ────────────┐
│  chat-interface → use-v6-socket.ts         │
│  WS: /ws/${NEXT_PUBLIC_PIPELINE_VERSION}/  │
└──────────────────┬─────────────────────────┘
                   │
┌──────────────────▼─────────────────────────┐
│  backend/server.py  FastAPI                │
│  only: GET /health, WS /ws/v7/chat         │
│  HITL plan review → coder⇄tester orch      │
└──────────────────┬─────────────────────────┘
                   │
┌──────────────────▼─────────────────────────┐
│  agent/v6/  (name is historical; code=V7)  │
│  EcoAgent loop (pi_ai streaming)           │
│  architect | coder | tester                │
│  tools: rag, eco_cli, grep/glob/read,      │
│         build, runtime, handoff            │
└──────────────────┬─────────────────────────┘
                   │
     marketplace_index.sqlite + marketplace_cache
     + eco-cli (+ optional wine)
```

| Layer | Path | Role |
|---|---|---|
| Model factory | `agent/main.py::get_model()` | Single OpenRouter `pi_ai.Model` |
| Orchestrator | `agent/v6/orchestrator.py`, `entry.py` | Flat declared edges, max_hops=8 |
| Agent loop | `agent/v6/eco_agent.py` | Tool loop + dedup + traces |
| Domain tools | `agent/v6/tools/*` | Marketplace, build, sandbox IO |
| RAG | `agent/rag/*` | sqlite-vec + AST chunker |
| UI | `frontend/components/chat/*` | Streaming plan/code/test UX |
| Scaffold | `backend/scaffold/*` | Pre-seeded `src/EcoMain.c` + Makefile |

---

## A User wishlist for refactoring

- Does it make sense to use Pydantic AI v2 framework (link: https://pydantic.dev/articles/pydantic-ai-v2 ) and its agent capabilities feature to structure the various agents / roles and their turns hand-off?
- Consider the possibility to add a preferred programming language selector on the UI next to platform selection. Allow for option to have a specific prompt and skill versions per programming language selected.
- Add an option to upload documents to RAG (from the folder) by a button in the UI (run available script)
- Add setting option to specify AI ​​coder harness, its model, and reasoning level per each Role supported (Architect, Coder, Reviewer, etc.) both in the UI settings and config files.
- We need to eliminate version confusion and remove all references to versions in file names and documentation.
- Combine all findings scattered in multiple markdown files, RELEVANT and useful decisions, and discussions into a single document, WORKING_DOCUMENTATION.md, and create a separate README.md at the root, describing: Setup/build steps (how to deploy and run the project), Configuration (how to customize prompts and models for each agent/node), User customization (by using / adding own Skills and AGENT.md) and where to put rules, skills, and AGENTS.md for each agent type.


# Phase 1 — Deprecation audit

## 1.1 Definitely deprecated / remove or archive

| Item | Why flagged | Recommended action |
|---|---|---|
| `CHAT_MODE_IMPL.md` (~835 LOC) | Documents LangGraph chat-first ReAct + V3/V4 graphs; stack retired 2026-06-22 | Move to `docs/archive/` or delete |
| `CHAT_MODE_PLAN.md` (~373 LOC) | Plan for chat mode on dead LangGraph stack | Archive/delete |
| `VERIFICATION_IMPL.md` (~867 LOC) | Static verification pipeline not wired into V7 | Archive; reintroduce only if formal verifier returns |
| `docs/superpowers/plans/2026-04-27-v4-three-node-pipeline.md` | V4 design/plan; superseded by V7 | Archive |
| `docs/superpowers/specs/2026-04-27-v4-three-node-design.md` | V4 design; superseded | Archive |
| `agent/skills/c.md` (~2081 LOC) | Full ACOM *component generation* templates (factory, connection points, sinks). **Not imported by any V7 agent.** V7 assembles apps from marketplace, not full COM component codegen | Keep as **reference corpus** under `docs/acom-templates/` or load only when role=`component_author`; do not treat as live skill |
| Dockerfile `CMD ["agent","--help"]` + entrypoint branch `python -m agent.main "$@"` | `agent/main.py` is **only** `get_model()` now; CLI entry removed | Fix entrypoint to `uvicorn backend.server:app` only |
| Frontend labels / defaults: “V6 Five-Node Pipeline”, `use-v6-socket`, default `pipelineVersion="v6"` | V6 endpoint **does not exist**; only `/ws/v7/chat` | Rename + default to `v7` |
| `frontend/components/chat/types.ts` comments referencing `agent/v6/state.py` / `/ws/v6/chat` | Files gone | Update comments |
| `docs/V7_ARCHITECTURE.md` table still describing dual V6/V7 endpoints | V6 purged | Update doc to V7-only |
| `docs/RAG_SETUP.md` mention of legacy `agent/nodes/retrieve.py` | File gone | Fix historical note |
| Empty Docker-created dirs: `marketplace_cache/`, `marketplace_index.sqlite/` (both are **directories** owned by root, size 4K) | Classic Docker bind-mount footgun when host file/dir missing; app mounts empty shells | Delete empty dirs; create real cache + sqlite **file** before compose |
| `source/` (26MB DEVKIT + Lessons) | Parallel corpus to `marketplace_cache`; not used by V7 tools (which point at marketplace) | Treat as **SDK reference/training data** or migrate into marketplace_cache; drop Lessons binaries from runtime image |
| `rag_storage/` | Documented as Chroma-era corpus; **absent in current tree** (already purged) | Confirm gone; ignore |
| `experiments/chunking_eval/` | Research harness, not production | Keep under experiments; exclude from runtime images |

## 1.2 Partially obsolete but still live (cleanup, not delete)

| Item | Issue |
|---|---|
| Directory name `agent/v6/` | Contains only V7; confuses contributors |
| Naming: `V6_CLI_PATH`, `V6_MAKE_EXE`, `use-v6-socket`, `ecov6.*` storage keys | V7 runtime with V6 names |
| Dual layout semantics | Scaffold + server say `src/EcoMain.c` + `run_build(project_subdir='src')`; taxonomy + coder examples still teach `SourceFiles/EcoMain.c` / `Eco.Calc/MSVC_v140` |
| Legacy tools `read_file` / `list_dir` | Kept “so old prompt references still work” alongside primary `read`/`glob`/`grep` — doubles tool surface |
| `agent/pi_ai/models.py` hardcoded catalog (`kimi-k2-thinking`, `glm-4.5`) | Parallel to env-driven `get_model()` |
| `scripts/fetch_marketplace.py` Windows absolute defaults (`H:/ai-hse-diploma-agent/...`) | Machine-specific; breaks Linux clones |
| `env.example` `OPENROUTER_PROVIDER_PIN=z-ai` | Only correct for GLM family; wrong pin silently kills cache / routing for other models |
| Frontend escalation UI / types | V7 plan-review only; escalation path is residual V6 protocol |

## 1.3 Active (do not deprecate)

- `agent/v6/{eco_agent,orchestrator,entry,agents,tools,call_trace}`
- `agent/pi_ai/*`, `agent/rag/*`
- `backend/server.py` (`/ws/v7/chat`), `backend/scaffold/*`
- `frontend` chat stack (after renames)
- `scripts/{build_marketplace_index,fetch_marketplace,analyze_tokens}.py`
- `docs/{V7_ARCHITECTURE,RAG_SETUP,PROMPT_HARDENING_SPEC}.md` (after fact fixes)
- `backend/OPTIMIZATION.md` (still accurate for V7 token work)

---

# Phase 2 — Configuration & hardcoding extraction

## 2.1 Findings catalog

### A. Models & LLM routing

| Location | Hardcoded value |
|---|---|
| `agent/main.py` | Default `LLM_MODEL=moonshotai/kimi-k2-thinking`, OpenRouter base URL, `thinkingFormat="openrouter"`, `reasoning=True` |
| `agent/pi_ai/models.py` | Static model registry entries |
| `agent/rag/embedder.py` | `qwen/qwen3-embedding-8b`, dim implicit, timeout 60s |
| All three agents | **Same** `model` instance — no per-role model |
| `env.example` | Provider pin `z-ai` (model-family specific) |

### B. Prompts (largest config debt)

| Location | Content |
|---|---|
| `architect.py` | `ARCHITECT_SYSTEM_PROMPT` + taxonomy blocks |
| `coder.py` | Large `CODER_SYSTEM_PROMPT` (~12KB file) with step procedures |
| `tester.py` | Tester system prompt |
| `_taxonomy.py` | Shared ACOM taxonomy / conventions / layout |
| `backend/server.py` | `_workspace_header()`, scaffold seed notes, plan-feedback template |
| `agent/skills/c.md` | Unused full component templates |

### C. Paths & environment

| Location | Hardcoded / default |
|---|---|
| `server.py` | `MARKETPLACE_CACHE_ROOT=/app/marketplace_cache`, `V7_OUTPUT_ROOT=./output`, Windows make `C:/Users/gaevy/gcc/bin/make.exe` |
| `tools/code_search.py` | Default cache `/app/marketplace_cache` |
| `tools/rag.py` | Index `/app/marketplace_index.sqlite` |
| `fetch_marketplace.py` | `H:/ai-hse-diploma-agent/...` for CLI + cache |
| `docker-compose.yml` | Ports `8100:8000`, `3100:3000`, eco-cli mounts |
| Frontend | `API_URL` default `http://localhost:8000` (compose publishes **8100**) |

### D. Magic numbers / budgets (mostly absent as policy)

| Location | Value | Notes |
|---|---|---|
| Orchestrator | `max_hops=8` | Loop ceiling only |
| Agents | `max_iters=None` (unlimited) | `AGENT_MAX_ITERATIONS` in env **unused** by V7 |
| eco_cli | timeout 180s, trunc 8192 | |
| build | make timeout (in build.py) | |
| runtime | 30s run, 16KB out | |
| code_search | list_dir cap 200, read page 32KB | |
| UI | tool preview 500 chars, reconnect max 15s | |
| RAG | k default 5, target_chars 400, dim 4096 | |
| Framework prepull | 5 fixed component names + Linux StaticRelease path | |
| CORS | `allow_origins=["*"]` | Security |

### E. Feature flags (env-scattered)

`V7_SCAFFOLD`, `V7_PREPULL_FRAMEWORK`, `V7_TOOL_DEDUP`, `V7_WARM_SEED`, `OPENROUTER_PROVIDER_PIN`, `V6_CLI_PATH`, `V6_MAKE_EXE`, `V6_CLI_PREFIX`, `MARKETPLACE_*`, `LLM_MODEL`, `EMBEDDINGS_MODEL`.

No unified schema, no validation, no typed config object.

## 2.2 Target unified config layout

```
config/
  harness.yaml              # top-level: modes, paths, dual interface
  models.yaml               # named model profiles (provider, id, reasoning, cost)
  roles.yaml                # architect/coder/tester → model profile + budgets + tools
  agents/
    internal.yaml           # EcoAgent backend settings
    external/               # claude, codex, grok, pi adapters
  prompts/
    architect.md
    coder.md
    tester.md
    taxonomy/
      eco_ids.md
      framework.md
      c_conventions.md
      project_layout.md
      static_link.md
      trust_model.md
    workspace_header.md.j2  # Jinja: project_dir, marketplace_cache
    scaffold_note.md.j2
  tools.yaml                # timeouts, truncations, whitelists, caps
  marketplace.yaml          # component catalog list, framework set, index paths
  budgets.yaml              # per-role token/query/day limits
  ui.yaml                   # ports, pipeline version, examples, feature flags
  security.yaml             # CORS, path roots, CLI subcommand allowlist
```

### Migration plan (ordered)

1. **Introduce `config/` + loader** (`agent/config/loader.py`) with pydantic models; load once at process start; fail fast on invalid schema.
2. **Env override rule:** `ENV` > `config/*.yaml` > code defaults. Keep OpenRouter key **only** in env/secrets.
3. **Extract prompts** from Python string constants into markdown files; agents load by role name.
4. **Extract model factory** to `config/models.yaml` + multi-model `get_model(profile)`.
5. **Wire `roles.yaml`** so architect/coder/tester can differ.
6. **Centralize magic numbers** in `tools.yaml` / `budgets.yaml`.
7. **Deprecate flat `.env` sprawl** — keep secrets + thin overrides only; document mapping in `env.example`.
8. **CLI/UI both read same config** (single source of truth).

---

# Phase 3 — Optimization, bugs, security, UI latency

## 3.1 Critical bugs / logical inconsistencies

| ID | Severity | Issue | Fix direction |
|---|---|---|---|
| B1 | **P0** | `marketplace_cache` and `marketplace_index.sqlite` are empty **directories** (Docker created them). RAG + prepull + exploration all fail or thrash. | Remove empty dirs; build real index **file** + populate cache; add compose preflight check that fails if mount is wrong type |
| B2 | **P0** | Frontend defaults `NEXT_PUBLIC_PIPELINE_VERSION` to **`v6`**; backend only serves **`/ws/v7/chat`**. | Default to `v7`; rename hook; fail loudly if version mismatch |
| B3 | **P0** | Frontend default API `localhost:8000` vs compose host port **8100**. | Default `http://localhost:8100` in dev; document; health probe before WS |
| B4 | **P1** | Layout conflict: scaffold/`server` use `src/`; taxonomy/coder examples use `SourceFiles/` and MSVC paths. Models get contradictory instructions. | Single canonical app layout (`src/` for assembly apps); update taxonomy; keep `SourceFiles/` only for *new component* authoring mode |
| B5 | **P1** | `AGENT_MAX_ITERATIONS` env ignored; agents unlimited. | Wire to EcoAgent `max_iters` + orchestrator hop policy |
| B6 | **P1** | `thread_id` query param on WS client is never honored by server (always new UUID). | Implement resume or drop client resume UX |
| B7 | **P1** | `build_artifact` always `""` in `pipeline_done`. | Detect `src/app` (or platform binary) and return path |
| B8 | **P2** | `coder.to_architect` edge forced to `None` in WS handler (escalation disabled) while agent tools still expose it. | Either re-enable plan re-HITL or remove tool to avoid dead ends |
| B9 | **P2** | Typo preserved: `MemoryManger1` in taxonomy — correct for EcoOS but easy for models to “fix”. | Explicit “do not correct spelling” line already partial; strengthen |
| B10 | **P2** | Dockerfile entrypoint still advertises dead CLI | Align with uvicorn |
| B11 | **P2** | `fetch_marketplace` hardcoded Windows paths | Portable defaults relative to repo root |
| B12 | **P3** | Dual tool sets (legacy `read_file` + modern `read`) inflate tool schemas/tokens | Gate legacy tools behind config flag default off |

## 3.2 Performance bottlenecks

| Area | Observation |
|---|---|
| Architect phase | OPTIMIZATION.md: still 29–45 LLM calls / 5–7+ min; taxonomy did not cut plan time |
| Single model for all roles | Expensive reasoning model used for simple handoffs |
| Unlimited agent loops | Can burn tokens forever without budget |
| Tool results | Partially slimmed; still large header dumps via read |
| Wine eco-cli | First-call lag mitigated by wineboot in image; still heavy vs native Linux CLI |
| Frontend bundle | framer-motion + markdown + highlight always loaded; mermaid is dynamic (good) |
| Compose | `npm run dev` + bind mounts slower than prod `next start` |
| API | `get_model()` + agent factory per connection (OK); no connection pooling concern |

## 3.3 Security vulnerabilities

| ID | Issue | Risk | Fix |
|---|---|---|---|
| S1 | CORS `allow_origins=["*"]` | Any origin can talk to API | Restrict to UI origin(s) from config |
| S2 | No auth on WebSocket | Local-dev OK; LAN/prod dangerous | Optional token / mTLS for non-localhost |
| S3 | `run_artifact` executes built binary | Intended but sandbox is only path-based | cgroups/timeout already partial; consider firejail/nsjail for prod |
| S4 | `eco_cli` subprocess with args from model | Subcommand whitelist helps; still trust CLI binary | Keep whitelist; never shell=True (already good) |
| S5 | Absolute paths accepted then validated | Mostly OK via `ensure_inside` | Audit code_search roots carefully |
| S6 | API keys in process env / traces | Traces may contain prompts | Redact secrets in `call_trace` |
| S7 | `.env` present in workspace | Ensure never committed (gitignored — OK) | Add CI secret scan |

## 3.4 Deep-dive: UI loading latency (tens of seconds)

### Measured architecture of “load”

User perception of “UI loading” is the time until **Connected** and interactive. That path is:

```
docker compose up
  → api image start + wine prefix already primed
  → healthcheck: start_period 40s, interval 30s
  → frontend waits depends_on: service_healthy   ← can wait ~40s+
  → npm run dev cold compile                     ← 5–20s typical in container
  → browser loads page
       → Google Fonts Inter (network)            ← 0–several s if slow/offline
       → JS hydrate (framer-motion, markdown…)
       → useV6Socket connect
            → default /ws/v6/chat if env missing ← FAIL → reconnect backoff
            → or wrong port 8000 vs 8100         ← FAIL → reconnect 0.5→15s
            → or api not ready                   ← FAIL → reconnect
       → onopen → “Connected”
```

### Ranked root causes

| Rank | Cause | Why it costs tens of seconds | Evidence |
|---|---|---|---|
| **1** | Compose `frontend.depends_on.api.condition: service_healthy` + `start_period: 40s` | UI container intentionally delayed ~40s even if API is up earlier | `docker-compose.yml` |
| **2** | WS version/port mismatch → exponential reconnect (0.5s … **15s** cap) | Default client `v6` + default port `8000`; only `v7` on `8100` exists | `use-v6-socket.ts:395`, `chat-interface.tsx:20`, compose ports |
| **3** | Next.js `npm run dev` in Docker with bind mounts | Cold compilation + filesystem overlay latency | compose frontend command |
| **4** | Empty marketplace mounts (runtime after connect) | First agent turn thrashing / errors — feels like “stuck loading” after send | empty root-owned dirs |
| **5** | Google Fonts `Inter` from `next/font/google` | Blocks or delays first paint on restricted networks | `layout.tsx` |
| **6** | Heavy client components all eager | Larger TTI; mermaid OK (dynamic) | package.json + chat-interface imports |
| **7** | Wine (historical) | First eco-cli call 10–30s — **mitigated** by Dockerfile wineboot; residual on misconfig | Dockerfile comments |

### Latency fix plan (step-by-step)

1. **Preflight script** `scripts/dev_preflight.py`: verify marketplace index is a **file**, cache non-empty, ports free, `.env` keys present; refuse compose otherwise.
2. **Fix client defaults:** pipeline `v7`, API `http://localhost:8100`.
3. **Healthcheck tighten:** lighter `/health` (already), reduce `start_period` to ~10s; or let frontend start immediately and show “API warming” instead of blocking container start.
4. **Dev UX:** optional `compose.dev.yaml` without health dependency; use `next dev --turbo` if available.
5. **Self-host font** or `display: swap` / system font stack for offline.
6. **Code-split** settings panel + mermaid already dynamic; lazy `framer-motion` if needed.
7. **Connection status UX:** show last WS error + attempted URL (today only “Reconnecting…”).
8. **Warm API:** import agent modules at startup (background) so first WS is not cold — optional.
9. **Prod path:** `next build && next start` without source bind-mount for demos.

### Instrumentation (do first, 1 day)

- Frontend: `performance.mark` for hydration, first WS open, first heartbeat.
- Backend: log time-to-accept WS, time-to-first-event.
- Compose: `docker compose events` + health timestamps.
- Document p50/p95 “Connected” time before/after.

---

# Phase 3 continued — Implementation roadmap (bugs + perf)

### Sprint A — Stabilize (1 week)

1. Fix B1 marketplace mounts + preflight.
2. Fix B2/B3 frontend defaults + rename labels to V7.
3. Fix B4 single layout contract.
4. Wire B5 max_iters from config.
5. Archive dead docs (Phase 1 list).
6. Latency instrumentation + Sprint A latency fixes 1–3, 7.

### Sprint B — Config unification (1–2 weeks)

1. Add `config/` schema + loader.
2. Extract prompts to markdown.
3. Per-role model profiles (even if all point to same model initially).
4. Centralize tool timeouts/caps.
5. Token/cost budget hooks in EcoAgent (soft warn + hard stop).

### Sprint C — Correctness & security (1 week)

1. `build_artifact` detection; thread resume decision.
2. CORS lockdown; optional WS auth.
3. Trace redaction; secret scan CI.
4. Remove or re-enable `to_architect` consistently.

### Sprint D — Meta-harness (see Phase 4)

---

# Phase 4 — Meta-harness technical design

## 4.1 Goals

Evolve from “one internal EcoAgent pipeline” to a **meta-harness** that:

1. Orchestrates **internal** agents **and** **third-party CLI agents** (Claude Code, Codex, Grok CLI, Pi).
2. Assigns **per-role** model, reasoning level, and **token budgets** (per query + per period).
3. Runs as **CLI-first** with **optional GUI**.
4. Exposes **extension points**: AST parsing, custom UI panels, external CLI execution.

## 4.2 Proposed architecture

```
                    ┌─────────────────────────────┐
                    │     Meta-Orchestrator       │
                    │  (role graph + HITL + $)    │
                    └──────────┬──────────────────┘
           ┌───────────────────┼───────────────────┐
           ▼                   ▼                   ▼
    Role: architect      Role: coder         Role: tester
    backend: internal|   backend: ...        backend: ...
    model profile        budget              tools allowlist
           │                   │                   │
           ▼                   ▼                   ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │ AgentAdapter│     │ AgentAdapter│     │ AgentAdapter│
    │  - internal │     │  - claude   │     │  - codex    │
    │  - pi       │     │  - grok     │     │  - internal │
    └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
           │                   │                   │
           └────────────┬──────┴────────┬──────────┘
                        ▼               ▼
              ┌─────────────────┐  ┌──────────────┐
              │  Tool Runtime   │  │  Event Bus   │
              │  ACOM domain    │  │  → CLI TUI   │
              │  AST, RAG, make │  │  → Web UI    │
              └─────────────────┘  └──────────────┘
```

### Core packages (target layout)

```
eco_harness/
  config/                 # from Phase 2
  orchestrator/           # generalize agent/v6/orchestrator.py
  adapters/
    internal_eco.py       # current EcoAgent
    claude_cli.py
    codex_cli.py
    grok_cli.py
    pi_cli.py
  tools/                  # current tools + extension API
  extensions/
    ast_service.py
    ui_panels/
    cli_exec.py
  interfaces/
    cli/                  # primary
    api/                  # FastAPI (optional UI backend)
  ui/                     # optional Next app
```

## 4.3 Multi-agent integration (adapters)

Each adapter implements:

```python
class AgentBackend(Protocol):
    name: str
    async def run(self, role: RoleSpec, seed: str, tools: ToolRouter,
                  budget: Budget, on_event: EventSink) -> AgentResult: ...
    def supports_tools(self) -> bool: ...  # native tools vs prompt-only
```

| Backend | Integration style | Pros for ACOM |
|---|---|---|
| **internal** (current) | In-process EcoAgent + pi_ai | Full tool control, streaming thinking, known behavior |
| **Claude CLI** | `claude` subprocess + MCP or tool bridge | Strong coding; need tool bridge for eco_cli/RAG |
| **Codex CLI** | `codex exec` / app-server | Good for patches; sandbox differs |
| **Grok CLI** | grok build / API | Native to this environment |
| **Pi** | pi coding agent + extensions | Excellent extension model; see Phase 5 |

**Tool bridge pattern for external CLIs:** expose ACOM tools as:
- MCP server (`eco-acom-mcp`) — preferred for Claude/Codex/Pi, or
- HTTP tool sidecar, or
- prompt-injected “run `eco-tool <name> --json`” CLI wrapper (lowest common denominator).

Handoffs stay **edge-labeled stop tools** (`to_coder`, `to_tester`, `done`, `fail`) so external agents must emit a structured final message the meta-orchestrator parses.

## 4.4 Role-based model configuration

```yaml
# config/roles.yaml
roles:
  architect:
    backend: internal
    model: reasoning_heavy        # models.yaml profile
    reasoning: high
    budgets:
      per_query_tokens: 200000
      per_query_usd: 1.50
      per_day_usd: 20
      max_iters: 40
      max_wall_s: 900
    tools: [search_marketplace, eco_cli, grep, glob, read, to_coder, fail]
  coder:
    backend: internal             # or claude_cli
    model: coding_balanced
    reasoning: medium
    budgets: { per_query_tokens: 300000, max_iters: 60, ... }
    tools: [write_file, run_build, grep, glob, read, to_tester, to_architect, fail]
  tester:
    backend: internal
    model: cheap_fast
    reasoning: low
    budgets: { per_query_tokens: 80000, max_iters: 20 }
    tools: [read, run_artifact, done, to_coder, fail]
```

Enforcement points:
- **Pre-call:** estimate/reserve tokens.
- **Post-call:** debit from `usage` (already captured in pi_ai OpenRouter path).
- **Hard stop:** `BudgetExceeded` → force `fail` with report.
- **Period budgets:** SQLite ledger `budget_ledger.sqlite`.

## 4.5 Dual interface (CLI + optional UI)

| Mode | Entry | Behavior |
|---|---|---|
| **CLI (primary)** | `eco-harness run "…" --config config/harness.yaml` | Rich TUI or plain logs; HITL plan approve in terminal |
| **CLI headless** | `--yes` / `--approve-plan path` | CI / batch |
| **UI (optional)** | `eco-harness serve --ui` | Current FastAPI+Next; feature-flagged |
| **API only** | `eco-harness serve --api` | WS/HTTP for custom clients |

Shared event schema (already close to V7 WS events) becomes the **only** UI contract. CLI and GUI are event consumers.

## 4.6 Tools extension points

### A. AST parsing endpoint

- Reuse `agent/rag/chunker_ast.py` (tree-sitter-c).
- Expose:
  - Tool: `parse_c_ast(path) → symbols, interfaces, vtables`
  - HTTP: `POST /ext/ast/parse`
  - Library API for adapters
- Purpose: give coder/architect structured ACOM interface extraction without dumping full headers.

### B. Custom UI panel rendering

- Extension manifest:
  ```yaml
  panels:
    - id: component_graph
      event_types: [plan_review_required, node_done]
      entry: extensions/ui_panels/component_graph.js
  ```
- UI hosts a panel slot; panels receive sanitized events.
- CLI renders textual fallback.

### C. External CLI execution

- Generalize `eco_cli` → `run_cli(profile, args)` with:
  - per-profile binary path, prefix (wine), cwd, env, timeout
  - subcommand allowlist
  - output truncation
- Profiles: `eco`, `make`, `git` (optional), user-defined.

### D. MCP export

- Package domain tools as MCP server so **any** external agent can call marketplace/build without forking harness logic.

---

# Phase 5 — Alternative: Pi-as-meta-harness (feasibility)

## 5.1 Idea

Instead of growing a custom meta-orchestrator, implement ACOM assembly as a **Pi extension/plugin**: skills, tools, and workflows that turn Pi into an ACOM marketplace assembler.

## 5.2 Pros

| Pro | Detail |
|---|---|
| Less orchestration code to maintain | Pi already has agent loop, tools, sessions, possibly multi-agent |
| Faster CLI UX | Pi is CLI-native; dual UI is optional later |
| Extension ecosystem | Skills/tools model fits `c.md` templates + marketplace tools |
| Model flexibility | Pi already multi-provider |
| Alignment with `agent/pi_ai` | You already vendored a Python pi-ai client — conceptual kinship |
| Lower product surface | One agent runtime vs N adapters |

## 5.3 Cons

| Con | Detail |
|---|---|
| **Domain ownership risk** | HITL plan review, three-role topology, scaffold/prepull, warm seeds are **your** proven product logic — must be re-expressed as Pi workflows |
| **Multi-agent handoffs** | V7’s flat edge orchestrator + stop tools may not map 1:1 to Pi’s control flow |
| **UI investment** | Current Next streaming UI (thinking, tools, plan review, mermaid) would need Pi-compatible event bridging or rewrite |
| **Budget/role matrix** | Need Pi support or a wrapper for per-role models + period budgets |
| **Windows/wine eco-cli** | Still your problem; Pi doesn’t know EcoOS |
| **Lock-in** | Deep Pi plugin API coupling; upgrades can break ACOM extension |
| **Tester honesty / capability gating** | Your structural tool gating (architect no write, tester no write) must be reimplemented carefully in Pi permissions |
| **Not a pure plugin** | Marketplace RAG (sqlite-vec), prepull, Makefile scaffold remain custom services the plugin calls |

## 5.4 Hybrid recommendation (preferred)

**Do not choose pure custom vs pure Pi.** Use a layered approach:

1. **Extract ACOM Tool Runtime + RAG + scaffold as a standalone library/MCP** (`eco-acom-runtime`) — usable by anyone.
2. **Keep a thin Meta-Orchestrator** (generalize current V7) as the default product — owns roles, budgets, HITL, event bus.
3. **Add Pi (and Claude/Codex) as backends** that call the same MCP/runtime.
4. Optionally ship a **Pi skill pack** for users who want “just Pi + ACOM tools” without the full GUI.

This preserves your hard-won V7 optimizations (scaffold, prepull, dedup, provider pin) while enabling multi-agent backends.

### Decision matrix

| Criterion | Custom meta-harness | Pi plugin only | Hybrid (recommended) |
|---|---|---|---|
| Time to multi-CLI agents | Medium | Fast for Pi only | Medium |
| Preserve V7 quality bar | High | Risk of regression | High |
| UI continuity | High | Low | High |
| Maintenance load | Medium-high | Low-medium | Medium |
| ACOM marketplace fit | Best | Good if tools solid | Best |
| Token budgets per role | First-class | Depends on Pi | First-class |

---

# Deliverables checklist (when implementing)

- [ ] Archive deprecated docs; fix Dockerfile entrypoint
- [ ] Fix marketplace mount preflight + frontend v7/port defaults
- [ ] Unify `src/` layout in prompts
- [ ] Introduce `config/` with pydantic loader
- [ ] Extract prompts; per-role models + budgets
- [ ] Latency instrumentation + compose/font/WS fixes
- [ ] MCP tool server for ACOM domain tools
- [ ] Agent adapters interface + first external backend
- [ ] CLI entry `eco-harness` dual-mode with optional UI
- [ ] Extension API: AST, panels, run_cli
- [ ] Security: CORS, optional auth, trace redaction

---

# Out of scope for this audit document

- Rewriting EcoOS component marketplace itself
- Training custom models
- Full component-codegen mode restoration from `c.md` (possible future role `component_author`)

---

# Appendix — Active vs dead path quick map

| User action | Active code path |
|---|---|
| Open UI, chat, approve plan | `frontend` → `/ws/v7/chat` → architect → HITL → coder⇄tester |
| Programmatic V7 | `agent/v6/entry.py::build_v7_pipeline` |
| Build RAG index | `scripts/build_marketplace_index.py` |
| Fetch components | `scripts/fetch_marketplace.py` |
| Dead | LangGraph graphs, chat_agent, Chroma init_rag, `/ws/v6/*`, `python -m agent.main` CLI |
