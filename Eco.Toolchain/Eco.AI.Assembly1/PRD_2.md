# PRD_2 — ACOM Meta-Harness: Bug Fixes and Setup Simplification

Status: APPROVED (2026-08-22)
Scope: findings from the 2026-08-22 harness audit; Phases 0–3.
Baseline: all phases validated by `pytest agent/internal/tests` + `python -m compileall agent backend eco_harness scripts`.

---

## Context

The audit found critical runtime bugs (dead import crashing every external
backend), a prompt-precedence defect that silently replaces the coder/tester
system prompts with placeholder stubs, container-path defaults that break host
runs, env-variable drift, and four conflicting binary-placement conventions.

## Phase 0 — Safety net (regression tests)

New tests capturing the desired behavior BEFORE the fixes:

1. **Bridge events** — `ExternalEcoAgent` with an external CLI backend emits
   harness events (`start` / `done`) through `on_event` without raising
   `ModuleNotFoundError` (the pre-fix code imported the event enum from a
   retired versioned module path), and an
   unknown event type maps to `EventType.ERROR` instead of crashing.
2. **Coder prompt override** — `make_role_agent("coder", ...)` resolves its
   system prompt from `config/prompts/coder.md`; the resolved prompt contains
   the full workflow markers ("STEP 1", stop-tool names) rather than the old
   self-referential placeholder sentence, and precedence is:
   workspace `.eco-harness/prompts/<role>.md` > `config/prompts/<role>.md`
   > built-in Python constant.
3. **Host-mode paths** — with no env vars set on a dev host,
   `paths.marketplace_index_path()` / `paths.marketplace_cache_root()` resolve
   repo-root artifacts; explicit env vars win; missing artifacts fall back
   deterministically (`/app/...` when present, else repo path).

## Phase 1 — Critical fixes

### P1.1 (was B1) — External bridge dead import
`eco_harness/adapters/eco_agent_bridge.py`:
- Import `EventType` from `agent.internal.eco_agent` (the module was
  previously imported from a retired versioned path).
- Map incoming event dicts defensively: known type names → matching
  `EventType`, unknown/missing → `EventType.ERROR`.
- Event marshalling must never kill a run: wrap `emit` body in try/except and
  log-and-drop on failure.

### P1.2 (was B2) — Prompt precedence + real config prompts
- `eco_harness/roles.py::_role_prompt` resolution order becomes:
  1. `<workspace>/prompts/<role>.md` (`.eco-harness/prompts/<role>.md`, or the
     dir of `ECO_HARNESS_WORKSPACE_CONFIG`)
  2. `config/<role_spec.prompt>` (default `config/prompts/<role>.md`)
  3. built-in constant fallback from `make_*_agent()`
  Empty files are skipped (treated as absent).
- Move the full CODER_SYSTEM_PROMPT text into `config/prompts/coder.md`;
  move TESTER_SYSTEM_PROMPT into `config/prompts/tester.md`. The Python
  constants remain as fallbacks. Placeholder sentences are removed.
- `architect.md` / `reviewer.md` already contain real content; unchanged.

### P1.3 (was B3) — Host-aware artifact paths
New module `agent/internal/tools/paths.py`:
- `repo_root()` — derived from `__file__` (equals `/app` inside the container).
- `marketplace_cache_root()` — `MARKETPLACE_CACHE_ROOT` env →
  `<repo_root>/marketplace_cache` if it exists → `/app/marketplace_cache` if it
  exists → `<repo_root>/marketplace_cache` (warn once when missing).
- `marketplace_index_path()` — same strategy for `MARKETPLACE_INDEX_PATH` /
  `marketplace_index.sqlite`.
Consumers rewired: `code_search.make_code_search_tools`,
`profile_cache` default root, `rag._DEFAULT_INDEX`, `server.py` chat handler.

### P1.4 (was B5) — Env hygiene
- `.env`: rename `V7_WARM_SEED` → `HARNESS_WARM_SEED` (code reads
  `HARNESS_WARM_SEED`; env.example already correct).
- `backend/server.py`: remove duplicated `os.getenv("ECO_MAKE_EXE") or
  os.getenv("ECO_MAKE_EXE")`; remove hard-coded personal path
  `C:/Users/gaevy/gcc/bin/make.exe` — resolution becomes `ECO_MAKE_EXE` env →
  `"make"`.
- `env.example`: document that `AGENT_MAX_ITERATIONS` applies only to
  `build_pipeline` runs, while `/ws/chat` uses `budgets.max_iters`
  (`config/roles.yaml`); the tool-dedup kill-switch is named
  `HARNESS_TOOL_DEDUP` consistently across code, `.env`, and env.example.

### P1.5 — CLI one-shot mode wiring (discovered during Phase 0)
`eco_harness/interfaces/cli.py` defaulted to `--mode create`, but
`config/modes.yaml` has no `create` entry, so every bare `eco-harness run`
crashed with `ValueError: Unsupported mode: create`; `--mode code` also
silently routed to the architect instead of the coder. Fixed:
- modes accepted by the CLI are now the one-shot subset
  `plan | code | test | review` mapped to their roles explicitly;
- `auto` / `migrate` are rejected with an actionable message pointing at the
  websocket pipeline (the CLI executes a single role; it never implemented
  the HITL gate).

Out of scope for Phase 1 (scheduled later): binary-discovery unification,
skill cleanup, dead YAML wiring/removal, external-role prompt parity,
orchestrator topology convergence, DX tooling (Phases 2–3).

## Phase 2 — Consistency (planned)

6. Single binary-resolution module `resolve_binary(name)`:
   `ECO_<NAME>_PATH` → `<repo>/bin/<name>` (gitignored, canonical home) →
   platform-suffixed siblings → PATH. Refactor
   `server.resolve_executable_path`, `eco_cli._resolve_cli_path`,
   `eco_wizard._resolve_wizard`, `factory.make_external_backend`,
   `scripts/fetch_marketplace.py`, `scripts/dev_preflight.py`. Update README /
   RAG_SETUP / docker-compose to describe only `<repo>/bin/`. Fix the
   `libaws-crt-jni.so ` stray-space bind mount in docker-compose.yml.
7. Skills: remove phantom `language` skill key from roles.yaml/languages.yaml;
   relocate `agent/skills/c.md` → `config/skills/component_author/v1.md`;
   de-duplicate `prompts/languages/C.md` vs `skills/languages/C.md`; fix the
   "Eco.System1 for EcoMain" contradiction in the C language profile.
8. Wire or delete dead YAMLs: `marketplace.yaml.framework_components` →
   `_prepull_framework`; `budgets.yaml.retained_tool_outputs` →
   `max_tool_results`; `agents/external/*.yaml` flags → `ExternalCliBackend`.
9. External-role parity: pass `config/prompts/<role>.md` content into
   `ExternalEcoAgent.system_prompt` (internal and external coders see the same
   instructions).
10. Converge `build_pipeline` with server topology (accept `trace_dir`,
    share edge-map constant); refresh stale doc references.

## Phase 3 — Onboarding polish (planned)

11. `pyproject.toml` console entry point `eco-harness`; Makefile targets
    `setup` / `index` / `preflight` / `up`; `dev_preflight.py --fix` hints;
    one canonical env-var matrix table in README.

## Acceptance criteria

- All new Phase 0 tests pass after the fixes; existing 126 tests stay green.
- A role configured `backend: pi|claude|codex|grok` starts and streams events
  without ImportError.
- With a fresh clone on a host (no env vars), `search_marketplace` and
  `read_component_profile` locate repo-root index/cache; grep/glob/read expose
  `marketplace_cache` when it exists.
- The coder's runtime system prompt contains the STEP workflow and stop-tool
  discipline (no placeholder text).
- No personal machine paths in source; `.env` var names match code reads.
- `eco-harness run "<request>" --mode plan|code|test|review` starts the correct
  single role without a mode-validation crash.
