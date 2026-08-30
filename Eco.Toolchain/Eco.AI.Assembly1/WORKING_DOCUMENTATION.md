# Eco.AI Assembly Working Documentation

## 1. Product boundary

This repository is the ACOM domain harness, not the EcoOS marketplace itself.
It assembles applications and components from marketplace packages, provides
RAG over the shared SDK corpus, invokes `eco-cli` and `eco-wizard`, and
orchestrates configurable agent roles.

The current default roles are:

```text
architect → coder → tester
                 ↑      │
                 └──────┘
```

The graph is explicit and bounded. A role stops through a named handoff edge;
the orchestrator never guesses an unknown edge and never permits an unlimited
mutual-handoff loop. Both topologies are declared once, in
`eco_harness/agent/internal/entry.py`: `PIPELINE_EDGES` (full architect→coder↔tester
graph used by scripted `build_pipeline` runs) and `EXECUTION_EDGES`
(the post-approval coder↔tester sub-graph used by the `/ws/chat` server,
with `coder.to_architect` terminated).

## 2. Backend architecture

`eco_harness` contains the product-facing boundaries:

- `adapters/` — built-in and external agent backends
- `roles.py` — role configuration and backend construction
- `permissions.py` — role permission enforcement (tool-group filtering +
  command allowlist; see §5)
- `interfaces/cli.py` — headless runner
- `interfaces/mcp.py` — MCP-compatible tool-provider boundary
- `tools/router.py` — domain-tool registration boundary
- `extensions/ast_service.py` — AST extraction library endpoint
- `extensions/cli_exec.py` — safe profile-based subprocess execution
- `capabilities.py` — Pydantic AI capability descriptions

`eco_harness/agent/internal/` contains the active built-in agent implementation. It is not
a versioned product generation. New modules must not add numbered agent paths
or dead-pipeline terminology; Git history provides implementation versioning.

## 3. Pydantic AI decision

Pydantic AI capabilities are adopted as an optional composition layer.
Capabilities are appropriate for stable bundles of instructions, tools,
hooks, model settings, and language/role behavior. They are not the authority
for the top-level workflow.

The meta-orchestrator remains responsible for:

- explicit role topology and terminal edges
- human plan approval
- retries and hop ceilings
- token/cost/wall-clock policy
- external subprocess adapters
- the shared UI/CLI event protocol

This separation preserves the proven internal `pi_ai` loop and keeps future
Pydantic AI upgrades from changing the ACOM workflow contract.

## 4. Prompt-cache contract

### How the initial context is assembled

Every role's initial context (system prompt) is ONE deterministic string,
built once per agent construction. Call chain:

```text
make_role_agent(role, mode, language)          eco_harness/roles.py
  ├─ make_architect()/make_coder()/…           built-in prompt constants +
  │                                            toolset (eco_harness/agent/internal/agents/)
  ├─ _role_prompt()                            workspace > config > built-in (§5)
  └─ _configure_context() → _static_prompt()   composition below
       ├─ _mode_prompt()                       config/prompts/modes/<mode>.md
       ├─ _language_prompt()                   config/prompts/languages/<lang>.md
       ├─ load_custom_instructions()           eco_harness/agent/context/customization.py:
       │    AGENTS.md layers + selected skills + language skill
       └─ build_static_system_prompt()         eco_harness/agent/context/assembler.py
```

Final concatenation order is FIXED and must not be reordered:

```text
# SYSTEM HEADER                          config/prompts/acom_system_header.md
                                         (HARNESS_SYSTEM_HEADER overrides path)
=== STATIC ACOM DOMAIN KNOWLEDGE ===     config/prompts/acom_domain.md
                                         (load_acom_domain)
=== STATIC TOOL CONTRACT ===             config/prompts/tool_contract.md
                                         (load_tool_contract)
=== ROLE INSTRUCTIONS ===                composed block:
                                           === MODE: <MODE> ===
                                             config/prompts/modes/<mode>.md
                                           <role prompt>        (precedence, §5)
                                           <language prompt>
                                             config/prompts/languages/<lang>.md
                                           <custom instructions>
                                             root/role AGENTS.md layers
                                             + selected skill profiles
                                             + config/skills/languages/<lang>.md
                                           === ROLE CONFIGURATION ===
                                             backend / model / reasoning
=== IMMUTABLE SOURCE CODEBASE ===        curated stitch of
                                         Eco.Core1/SharedFiles only
```

Selection inputs and their effect:

- **Mode** (`config/modes.yaml`) — injects the mode prompt and selects which
  roles may run. `auto` and `migrate` drive the full HITM pipeline (server
  only); `plan`, `code`, `test`, `review` load exactly one role.
- **Active role** (`config/roles.yaml`) — selects the backend/model/reasoning,
  budgets, `prompt:` pointer (default `prompts/<role>.md`) and the
  `skill_versions` map merged over the language's map.
- **Language** (`config/languages.yaml`) — selects the language prompt file,
  language skill profile, and the `eco_wizard` template family.

Role-prompt precedence (first non-empty wins; empty/whitespace files are
treated as absent so a stub can never blank out real instructions):

```text
1. <workspace>/prompts/<role>.md        i.e. .eco-harness/prompts/<role>.md,
                                        or prompts/ next to the file named by
                                        ECO_HARNESS_WORKSPACE_CONFIG
2. config/<roles.<role>.prompt>         normally config/prompts/<role>.md —
                                        the editable source of truth
3. built-in constant                    CODER_SYSTEM_PROMPT etc. in
                                        eco_harness/agent/internal/agents/<role>.py
```

Skill resolution (`load_custom_instructions` / `resolve_custom_instructions`):
for every entry of the merged `skill_versions` map, candidates are probed in
root order `.eco-harness/skills/ → config/skills/` (workspace overrides repo —
the historical inverted order that silently disabled workspace skill overrides
was fixed with the on-demand skills work) and name order
`v<N>.md → SKILL.md → <skill>.md`. Names that match nothing resolve silently
to nothing (the phantom `language` key was removed from all YAML
`skill_versions` maps in PRD_2 Phase 2; the legacy `agent/skills/` root was
retired). The language skill (`config/skills/languages/<lang>.md`) is always
appended last when present.

On-demand skills: a `SKILL.md` whose body begins with a YAML frontmatter
block carrying at least `description:` is NOT injected as text. Its one-line
description is appended to the prompt as an `=== ON-DEMAND SKILLS ===`
manifest entry (name, description, source path), and the full body is fetched
only when relevant — internal agents call the automatically-wired `read_skill`
EcoTool (`eco_harness/agent/internal/tools/skill_reader.py`, whitelisted to the two skill
roots, frontmatter stripped, size-capped); external CLI backends read the
listed source path with their own file tools. `roles.py` attaches
`read_skill` whenever the role's merged map resolves at least one dynamic
skill. Plain `v<N>.md` files and frontmatter-less `SKILL.md` files keep the
eager full-text behavior. First live dynamic skill:
`config/skills/component_author/SKILL.md` (referenced by the coder role).

### The workspace-level override layer

`.eco-harness/` (or the directory of `ECO_HARNESS_WORKSPACE_CONFIG`) is the
operator's per-workspace customization layer. It never modifies git-tracked
config; it overrides or extends it at load time. Per artifact type:

| Artifact | Repo default (read-only convention) | Workspace override | Same-name behavior |
| --- | --- | --- | --- |
| Role prompt | `config/prompts/<role>.md` | `.eco-harness/prompts/<role>.md` | Workspace **replaces** repo prompt entirely (first non-empty wins) |
| Skill body (eager) | `config/skills/<skill>/v<N>.md` | `.eco-harness/skills/<skill>/v<N>.md` | Workspace **replaces** the repo skill with the same name (workspace root probed first) |
| Skill body (on-demand) | `config/skills/<skill>/SKILL.md` + frontmatter | same override rule | Only the manifest description enters the prompt; full body via `read_skill` / direct file read |
| Skill, new name | — | `.eco-harness/skills/<skill>/…` | Additional skill — but ONLY if a `skill_versions` entry references it |
| Role settings | `config/roles.yaml`, `languages.yaml`, `harness.yaml` | `.eco-harness/workspace.yaml` | Deep-merged per role/language; `budgets` merge key-by-key |
| Model registry | `config/models.yaml` | `workspace.yaml` `models:` | Per-key deep-merge over repo profiles; `models: {name: null}` **removes** a profile; `default` is re-created from `LLM_MODEL` when absent |
| Permission policy | `config/roles.yaml` `permissions:` per-role baseline | `workspace.yaml` `permissions:` (`defaults` + `roles` deltas) | Layered key-by-key — see §5 for the chain |
| AGENTS.md rules | `config/agents/<role>/AGENTS.md` | `.eco-harness/agents/<role>/AGENTS.md` | All layers found are concatenated (repo root first), not either/or |

Two mechanics matter and are easy to get wrong:

1. **Skill selection vs skill content are separate decisions.** Dropping a
   file into `.eco-harness/skills/` does NOT activate it — activation always
   goes through the merged `skill_versions` map (`languages.yaml` map merged
   under `roles.yaml` map). A workspace `workspace.yaml` can override the map:
   `roles.<role>.skill_versions` there replaces the repo map WHOLESALE
   (dict-spread merge at the role level), so to ADD one skill you repeat the
   entries you want to keep. Only `budgets` gets a special key-by-key deep
   merge.
2. **Empty files lose.** Both for prompts and skills, an empty/whitespace
   workspace file is treated as absent and the lower layer wins — a stub can
   never blank out real instructions (regression-tested).

Example — override `acom_framework` and add an operator skill for coders:

```yaml
# .eco-harness/workspace.yaml
roles:
  coder:
    skill_versions:            # wholesale replacement — re-list kept skills
      acom_framework: "1"      # body resolved from .eco-harness/skills/
      eco_wizard: "1"          #   acom_framework/v1.md (override wins)
      team_style: "1"          # new name → .eco-harness/skills/team_style/v1.md
```

Content split rule introduced with PRD_2 Phase 2 follow-ups:
`config/prompts/acom_domain.md` is LANGUAGE-AGNOSTIC domain knowledge shared
by every role and language (identifier taxonomy, framework stack, dev-kit
boundary, EcoMain flow, trust model); all language-specific coding
conventions live ONCE in `config/skills/languages/<lang>.md`. Do not restate
C rules in the domain block or vice versa — the two cross-reference each other
by section instead of duplicating.

Source stitch: `_core1_sharedfiles(source_roots)` locates
`Eco.Core1/SharedFiles` and `stitch_source_files` emits it as one continuous
payload with `START_FILE`/`END_FILE` anchors, capped at
`min(HARNESS_SOURCE_MAX_BYTES, 120_000)` bytes. Only Eco.Core1 is stitched;
other components are discovered on demand via RAG / `grep` / `eco-cli pull`.

Discovery handles both layouts — flat (`<root>/Eco.Core1/SharedFiles`) and
the versioned development-kit layout the marketplace ships and
`eco-cli pull -d $ECO_FRAMEWORK` deposits
(`<root>/Eco.Core1_DK_v.<ver>/Eco.Core1/SharedFiles`, highest version wins).
The standard ACOM `ECO_FRAMEWORK` environment variable is consulted FIRST
(via `paths.framework_root()`), then the configured `harness.yaml:source_roots`.

The stitch is C-only (`.h` files; `.hpp` C++ wrappers excluded): agents author
C89, the wrappers duplicate the same declarations, and dropping them cuts the
byte-identical block ~29% (~85 KB → ~60 KB on the shipped DK) while keeping
the KV-cache prefix intact.

Artifact locations (cache, index) resolve via
`eco_harness/agent/internal/tools/paths.py`:
env var → repo-root artifact if present → `<ECO_HOME>/data` (installed
layout) if present → `/app` mount if present → deterministic repo-root
fallback with a one-time warning. Host checkouts, containers and installed
wheels therefore need no env vars (PRD_2 Phase 1 fixed the hard-coded
`/app` defaults that broke host runs; the packaging work added the
installed-mode candidates).

External tool binaries (eco-cli, eco-wizard, external sub-agents) resolve via
`eco_harness/agent/internal/tools/binaries.py::resolve_binary` — the single policy since
PRD_2 Phase 2: explicit config → `ECO_<NAME>_PATH` env → `<repo>/bin/<name>`
(canonical, gitignored) → `$ECO_HOME/bin/<name>` (installed home,
`<name>.exe` on Windows) → `/opt/<name>` (container mounts) → legacy
platform-suffixed siblings → `PATH`. All former per-consumer resolvers
(server, eco_cli, eco_wizard, factory, scripts) delegate to it.

### Cache utilization rules

The ordering above exists to maximize provider-side implicit prompt-cache
(KV-cache) reuse and minimize billed tokens:

- Blocks 1–3 (header, domain, tool contract) are byte-identical for **every**
  role, mode, language, and backend → they form the longest shared prefix.
- The stitched Eco.Core1 block is constant across turns, tasks, and threads.
- The ROLE INSTRUCTIONS block differs per role but is stable for a given
  role+mode+language combination, so an iterating agent loop replays its own
  prefix verbatim on every LLM call.
- NOTHING dynamic enters the system prompt: RAG snippets, tool outputs, the
  user request, and handoff messages live in the message HISTORY.
  `EcoAgent._build_context` elides all but the newest `max_tool_results`
  (= `harness.yaml:dynamic_tail_items`, default 12) tool results, replacing
  older payloads with one-line placeholders. `build_dynamic_tail` remains
  available for non-loop callers only.
- Implicit caching requires a warm upstream route: the model profile's
  `provider_pin` (`config/models.yaml`) takes precedence over the global
  `OPENROUTER_PROVIDER_PIN`; `OPENROUTER_ALLOW_FALLBACKS=true` (default) keeps
  the pin preferred-but-not-required. Measured on a pinned provider: 99.6%
  cached tokens, −81% cost per call.
- Maintainer rules: never interpolate timestamps, thread ids, absolute
  project paths, or marketplace listings into blocks 1–5 — they belong in the
  seed or history. Keep additions to `acom_domain.md` / `tool_contract.md`
  small; they multiply across every role. `acom_domain.md` stays
  language-agnostic — C/C++ coding rules belong in the per-language skills.
  Edit role behavior in `config/prompts/<role>.md` (no code change) and
  operator specialization in `.eco-harness/prompts/<role>.md`.

The framework header explicitly requires:

- exact EcoOS ACOM ABI spellings
- `ECOCALLMETHOD`
- typed `me` parameters
- `int16_t` status returns
- manual reference counting and allocator use
- retrieved tools' output treated as data, not policy

`eco-wizard` is to be used for ACOM components, object boilerplate / template generation.

## 5. Configuration and user rules

Repository configuration is stable and reviewable under `config/`. UI changes
go to `.eco-harness/workspace.yaml`. Environment variables override both.
Secrets remain outside repository configuration.

Overall precedence:

```text
environment variables > .eco-harness/workspace.yaml > config/*.yaml > code defaults
```

### workspace.yaml schema (Settings panel write path)

`PUT /config/workspace` is the single writer. It validates every provided
section against the loader's pydantic models (`RoleSpec`, `LanguageSpec`,
`ModelProfile`, `PermissionSpec` → 400 on garbage), merges section-wise into
the existing file (absent sections are preserved — the UI never sends
`harness`), reloads the config off the event loop, and only then publishes
the new in-memory global. A rejected save never leaves a broken state.

```yaml
roles:                      # UI sends ONLY backend/model/reasoning per role —
  coder:                    # budgets, prompt, skill_versions and permissions
    backend: internal       # snapshots are deliberately NOT pinned, so repo
    model: coding_balanced  # config stays authoritative for what the UI does
    reasoning: medium       # not manage
languages: {…}              # full language specs (prompt, skill_versions, eco_wizard)
models:                     # user-added/edited profiles only (diff vs baseline)
  my_model:
    id: provider/model-id   # required; provider, reasoning, temperature,
    provider_pin: tencent   # max_tokens optional; pin is an OpenRouter
  retired_model: null       # ROUTING hint, not a secret; null = delete marker
permissions:
  defaults: {fs_write: false, commands: ["make"]}   # harness-wide layer
  roles:                    # per-role DELTAS over the defaults (key-by-key)
    architect: {fs_write: true}
harness: {…}                # never written by the UI; preserved on merge
```

Model-registry merge (`load_config`): workspace profiles deep-merge over
`config/models.yaml` per key; a `null` value removes the profile; the
`default` profile is re-created from `LLM_MODEL` when missing, so deleting it
resets to the env model instead of breaking resolution. `GET /config` returns
the merged registry, which becomes the UI's next diff baseline — so repo
profiles the UI never touched stay owned by `config/models.yaml`.

### Permission model (roles are the trust boundary)

Permissions are configured per ROLE with harness-level defaults — models are
interchangeable providers and must not carry policy. Resolution per role
(`eco_harness/agent/config/loader.py::_resolve_permissions`, later wins key-by-key,
unknown keys filtered so typos can neither crash nor silently alter policy):

```text
code defaults < workspace permissions.defaults
             < repo roles.yaml roles.<role>.permissions   (specific beats general)
             < workspace permissions.roles.<role>         (UI delta)
```

`PermissionSpec` fields: `fs_read`, `fs_write`, `build`, `execute`,
`rag_search`, `skills`, `network` (booleans) and `commands` (allowlist,
default `["*"]`).

Enforcement (`eco_harness/permissions.py::apply_role_permissions`, called
from `make_role_agent` AFTER skill wiring and BEFORE prompt assembly, so the
tool contract the model sees matches the enforced toolset):

1. **Tool-group filtering** — denied groups remove concrete tools from
   `agent.tools` before the system prompt is built: the model never sees a
   tool it may not call (no injection surface, no wasted tokens).
   `fs_read` → grep/glob/read/read_file/list_dir/read_component_profile;
   `fs_write` → write_file; `build` → run_build; `execute` → run_artifact;
   `rag_search` → search_marketplace; `skills` → read_skill;
   `network` → eco_cli/eco_wizard.
2. **Command allowlist** — `run_build`, `run_artifact`, `eco_cli` are wrapped
   (frozen-dataclass `replace`) with a token check. Tokens: run_build → the
   make TARGET (or `"make"` for a default build), run_artifact → the artifact
   BASENAME, eco_cli → the SUBCOMMAND. `["*"]` allows everything; an EMPTY
   list denies every gated command; `None`/blank tokens are tool no-ops and
   pass. Handoff/stop tools are never gated.

This is a POLICY layer on top of the tools' own sandboxes (project_dir
containment, eco-cli's internal subcommand whitelist), not a replacement for
them. It applies to INTERNAL backends only: external CLI backends
(pi/codex/claude/grok) execute in their own process with their own tool
policy — the settings UI marks those roles `ext` instead of pretending.

Prompt and skill resolution order is stable (§4 has the detailed logic):

1. framework header
2. stable tool contract
3. role prompt — `.eco-harness/prompts/<role>.md` >
   `config/prompts/<role>.md` > built-in constant; empty files skipped
4. language prompt and selected skill profiles
5. project/root and role `AGENTS.md`
6. stitched Eco.Core1 source block
7. dynamic history tail (RAG/tool outputs live in message history, not here)

Root `AGENTS.md` applies to all roles. Role-specific rules belong in
`config/agents/<role>/AGENTS.md` or `.eco-harness/agents/<role>/AGENTS.md`.
Role-prompt overrides belong in `.eco-harness/prompts/<role>.md`. Reusable
skills belong under `config/skills/`; Git commits provide their version
history. Same-name vs different-name override semantics for prompts, skills,
and settings are detailed in §4 ("The workspace-level override layer").

## 6. Agent backends

The external adapter invokes installed local harnesses exactly as follows:

```text
codex -p "<prompt>"
pi -e "<prompt>"
claude -p "<prompt>"
grok -p "<prompt>"
```

The adapter resolves the executable via the shared `resolve_binary` policy
(`ECO_CODEX_PATH`, `ECO_PI_PATH`, `ECO_CLAUDE_PATH`, `ECO_GROK_PATH` →
`<repo>/bin/<name>` → `/opt` → `PATH`). The invocation flag comes from
`config/agents/external/<name>.yaml` (`flag:`), wired into
`ExternalCliBackend` in PRD_2 Phase 2. Missing executables produce an
explicit role failure. There is no silent fallback.

External agents must return one structured marker:

```text
<eco-handoff edge="to_coder|to_tester|done|fail|to_architect">
concise handoff
</eco-handoff>
```

This keeps external agents compatible with the same declared-edge topology.
Native tool support can later be added through MCP while retaining the
adapter protocol.

External roles receive the SAME statically assembled prompt as internal ones,
flattened into the seed (`<static system prompt>` + `=== DYNAMIC SEED ===` +
task), because local CLIs have no system-prompt API in this adapter. Since
PRD_2 Phase 2 the static prompt is resolved with the full role-prompt
precedence chain (workspace > `config/prompts/<role>.md` > placeholder), so
external coders/testers see the same STEP workflow and stop-tool discipline
as internal agents. Backend events (`start`, `done`, …) are mapped onto the
shared `EventType`; unknown types degrade to `ERROR`, and event-sink failures
are logged and dropped — they never abort a run (regression-tested, see
`eco_harness/agent/internal/tests/test_prd2_regressions.py`).

## 7. Language support

The UI and request protocol support `C`, `CPP`, `Python`, and `Java`.
Language-specific prompt and skill profiles are configured in
`config/languages.yaml`, `config/prompts/languages/`, and
`config/skills/languages/`.

`eco-wizard` remains the source of truth for language-specific project
templates. Until its Python and Java support ships, the harness must not
invent those layouts.

## 8. Generator and CLI execution

The generator tool exposes the generator with:

- executable lookup via the shared `resolve_binary` policy
  (`ECO_WIZARD_PATH` → `<repo>/bin/eco-wizard` → `$ECO_HOME/bin/eco-wizard`
  → `/opt` → legacy siblings → `PATH`)
- `eco-wizard new`
- language, type, output, environment, and option arguments
- bounded output
- explicit missing-binary and failure results

The marketplace CLI tool uses an
allowlist, `shell=False`, bounded output, timeout control, and portable
`ECO_CLI_PATH`/`ECO_CLI_PREFIX` overrides. When the standard ACOM
`ECO_FRAMEWORK` variable is set, every `pull` is routed into that
development-kit tree automatically (eco-cli's `-d` flag is appended unless
the caller already passed one); read-only subcommands are untouched.

## 9. Shared RAG lifecycle

The shared RAG is a portable SQLite file containing chunk metadata, FTS5,
sqlite-vec vectors, and provenance metadata. Sources can be:

- marketplace cache files (`scripts/build_marketplace_index.py`, default)
- the standard ACOM `ECO_FRAMEWORK` development-kit tree
  (`scripts/build_marketplace_index.py --source framework`; versioned
  `<Component>_DK_v.<ver>/` directories are normalized to marketplace
  component names during ingest)
- developer documentation
- developer documentation
- C/C++/IDL source
- Markdown/text documentation
- compatible SQLite index dumps

The UI supports individual files and browser directory selection, shows live
index stats, and can export the index. The import endpoint stages uploads,
calls `scripts/import_rag.py`, updates `marketplace_index.sqlite`, and
reports chunk statistics. The status endpoint reports chunk count, file size,
and the stored `last_import` meta (read-only SQLite connection). The export
endpoint downloads the current index — the download is itself a valid import
source (dump re-import re-extracts `chunks.text`), which makes the UI
round-trip a usable backup/restore path; `scripts/export_rag.py` creates a
named team copy.

The architecture intentionally leaves room for:

- a separate developer/project index
- remote centralized MCP retrieval
- index federation or read-through retrieval

None of these change the static source-cache contract because their results
remain dynamic tail data.

## 10. UI/API contract

The UI resolves its API base from `NEXT_PUBLIC_API_URL` (set by the dev
stack, historically `http://localhost:8100`); when the variable is unset —
the static-export bundle served by FastAPI — it falls back to same-origin
(`window.location.origin`), so the installed single-port flow needs no
CORS or env var. The server exposes:

- `GET /health`
- `GET /config` — full config snapshot (platforms, roles incl. resolved
  permissions, permission defaults, languages, merged model registry, modes).
  Serves the in-memory global; the global is swapped ONLY by a successful
  `PUT /config/workspace`, never mid-request, so in-flight WS pipelines
  cannot observe a config change underneath them. Out-of-band workspace.yaml
  edits show up on the next save, the next WS connect (per-connection
  snapshot with last-known-good fallback), or a restart.
- `PUT /config/workspace` — single writer of workspace.yaml. Section-wise
  merge (`exclude_unset`: absent sections preserved), pydantic validation of
  every provided section (400 on invalid), then reload + publish. See §5 for
  the schema and merge semantics.
- `GET /rag/status` — index availability, chunk count, size, last import
- `POST /rag/import`
- `GET /rag/export`
- `GET /api/fs/browse` — directory listing for the folder/project picker; pass
  `files=1` to also list files (used by the attachment file picker). Root must
  resolve within the allowed roots.
- `GET /api/fs/search` — filename/path substring search backing the `@`-mention
  autocomplete. See "File search" below.
- `WS /ws/chat`

### File search (@-mention backend)

`GET /api/fs/search?q=<str>&root=<path>&limit=50&depth=8&backend=os_walk`
returns `{root, truncated, backend, results:[{name,path,size,mtime}]}`
(files only). The `root` defaults to the first allowed root (home); when given
it must resolve within the allowed roots (`_is_within_allowed` /
`_ensure_allowed`). A path that is **not a directory** (e.g. a file) returns
`400`. Home-root walks are the heaviest path, so when `root` is omitted the
query requires **≥ 2 characters**; an explicit root requires ≥ 1.

Two swappable backends behind one endpoint:

- **`os_walk` (default, zero-dependency)** — `_search_os_walk` does a recursive
  `os.walk` with a hard `_SEARCH_FILE_CAP` (20 000 files) and `limit` cap (max
  200) and `depth` cap (max 16). It prunes hidden dirs, `__`-prefixed dirs,
  symlinks, and a skip-list (`_SEARCH_SKIP_DIRS`: `.git`, `node_modules`,
  `__pycache__`, `.venv`, `marketplace_cache`, `.eco-attachments`) to mirror
  `fs_browse` / `read` behavior. Each directory's `iterdir()` is wrapped in its
  own try/except so a single unreadable directory is skipped instead of
  aborting the whole walk. Results are ranked: basename substring (rank 0)
  beats relative-path substring (rank 1), then sorted by rank + path.
- **`fff` (opt-in)** — `FILE_SEARCH_BACKEND=fff` selects the `fff-search` wheel
  (typo-tolerant / frecency-ranked). The index builds lazily on first query and
  is cached per root. If the wheel is absent or errors, the call falls back to
  `os_walk` and the `backend` field reflects the actual backend used.

**Server owns backend selection (D1):** `FILE_SEARCH_BACKEND` (env) wins over
the query `backend` param (which is only a hint). This keeps the lean,
dependency-free default in force unless an operator explicitly opts into `fff`.
The default image is `python:3.11-slim-bookworm` with **no Rust toolchain**, so
`fff-search` must stay an opt-in prebuilt `abi3` wheel (no build step) to avoid
breaking the image.

### Attachment delivery

The chat input sends session-scoped attachments on every `user_request` via
`UserRequestMessage.attached_files`, an array of
`{name, path?, kind: "text"|"image", mime?, size?, content?}`. `path` is set for
`@`-mention and `+`-picker attachments; `content` carries pasted text or a
base64 data URL for pasted images. The server builds a prompt block with
`_build_attached_block(attached, project_dir)` — computed **once after
`project_dir` is finalized** (post worktree) so both the planner and coder seeds
see it — and injects it into **every** seed in the fixed order
`workspace + attached_block + user_req` (the workspace header must lead; volatile
attachment content follows it, then the task). The five injection sites are the
one-shot run, the chat-reply branch, the AUTO planner seed, the planner-retry
seed, and the coder seed.

Delivery rules (security-first):

1. **File already inside `project_dir`** → referenced by its real relative path
   `read(path='<rel>')`; no copy (the agent's `read` anchors relative paths at
   `project_dir`).
2. **Small pasted text** (≤ `ATTACH_INLINE_LIMIT` 40 KB, within the session-wide
   `ATTACH_TOTAL_INLINE_LIMIT` 200 KB) → **inlined** into the prompt (and a copy
   is still stashed in `.eco-attachments/` so `read(path=...)` yields the full
   content if the model wants it).
3. **Large text / images** → copied into `project_dir/.eco-attachments/` and
   referenced by path (`read(path='.eco-attachments/<name>')`); images get a
   visual-reference note.

Hard limits: `ATTACH_MAX_CONTENT` (~25 MB) caps what is **written to disk**
(server-side, because the 5 MB client paste cap is trivially bypassable); larger
items are skipped with a warning. **Basename collisions** are de-duplicated on
write (`a.txt` → `a-2.txt`) so a mention `src/a.txt` and a pasted `a.txt` never
clobber the same file. **Re-send optimization:** the copy is skipped when an
identical file (size + mtime) already exists in `.eco-attachments`, since the
block is rebuilt on every request.

**Security (mandatory):** every item carrying a `path` is validated through
`_ensure_allowed(Path(path).expanduser().resolve())` before any read/copy; paths
outside the allowed roots (home / output root / `HARNESS_ALLOWED_ROOTS`) are
**skipped with a warning** — never read, never errored — so one bad path can't
sink the request. Pasted `content` is client-provided bytes written without a
disk read. `_safe_attach_name` strips directory components and defuses `..` /
`/` so attachment writes can't escape `.eco-attachments/`.

Frontend settings live in `components/chat/agent-settings.tsx`
(`AgentSettings`, four tabs: Roles / Models / Access / RAG; sticky save bar
with dirty-state Discard) with the RAG tab implemented in
`components/chat/rag-import.tsx` (`RagSection`). Per-role permission
overrides are stored as DELTAS over the harness defaults in the UI state, so
resolved values always follow later default changes instead of freezing a
stale snapshot.

The event schema remains compatible with the current streaming UI:
heartbeats, phase changes, node events, plan review, and pipeline completion.
The neutral `use-socket.ts` export is the preferred frontend import.

## 11. Worktree isolation

When enabled from the UI or CLI, `eco_harness.worktrees.create_worktree`
resolves the repository root, creates a detached worktree under the configured
worktree root, and passes that path to every role/tool in the session. The
primary checkout is not used for generated code or agent mutations. Creation
fails loudly if Git is unavailable or the destination exists.

## 12. Working modes

`config/modes.yaml` defines mode-specific prompts, role lists, and
capabilities:

- `auto`: architect, coder, tester; the HITM plan→implement→verify loop with
  an intent gate (websocket `/ws/chat` only)
- `migrate`: same pipeline, migration-focused prompts (websocket only)
- `plan`: architect only; research + closed plan, no pipeline
- `code`: coder only; direct implementation, no automatic testing
- `test`: tester only; read-only runtime verification
- `review`: reviewer only; read-only style, ABI, naming, and correctness review

The headless CLI executes a SINGLE role one-shot and therefore accepts only
`--mode plan|code|test|review` (mapped to architect/coder/tester/reviewer).
`auto` / `migrate` are rejected with a pointer to the websocket pipeline —
the CLI has no human plan-approval gate. Slash aliases `/plan`, `/code`,
`/test`, `/review` are accepted as leading-argument shortcuts.

## 13. External agent swarm orchestrator extension

This feature is intentionally design-only. It is a future replacement or
optional layer above the current single-coder/single-tester graph.

### Responsibilities

The swarm orchestrator analyzes a task queue, decomposes work into bounded
tasks, assigns tasks to multiple coding/review/testing workers, tracks
dependencies and workspace claims, and merges or escalates results. It does
not own ACOM domain rules; workers receive the same context assembler, tools,
skills, budgets, and trust policy as current roles.

### Proposed interfaces

```python
class SwarmOrchestrator(Protocol):
    async def submit(self, request: TaskRequest) -> TaskBatch: ...
    async def plan(self, queue: TaskQueue) -> DispatchPlan: ...
    async def dispatch(self, plan: DispatchPlan) -> AsyncIterator[TaskEvent]: ...
    async def reconcile(self, results: list[TaskResult]) -> SwarmReport: ...
    async def cancel(self, batch_id: str) -> None: ...
```

Core records should include:

- `TaskRequest`: user request, mode, repository/worktree, acceptance criteria
- `TaskSpec`: task ID, role, inputs, dependencies, file/resource claims, budget
- `DispatchPlan`: parallel waves, worker/backend assignment, merge policy
- `TaskResult`: status, changed paths, commits/artifacts, evidence, usage
- `TaskEvent`: queued, started, tool output, blocked, completed, failed
- `SwarmReport`: accepted changes, conflicts, failed tasks, remaining queue

### Dispatch logic

1. Normalize the user request into independent and dependent tasks.
2. Use a DAG rather than unconstrained peer-to-peer handoffs.
3. Assign workers by capability, language, model/backend, budget, and file claims.
4. Run non-conflicting tasks in parallel isolated worktrees.
5. Require every coding task to produce a patch/commit and evidence.
6. Run targeted test/review tasks after each coding wave.
7. Detect file overlap, conflicting contracts, budget exhaustion, and failed evidence.
8. Requeue only bounded, diagnosable failures; escalate ambiguous conflicts to HITL.
9. Reconcile accepted commits through a merge queue or integration worktree.
10. Emit the same event schema consumed by the CLI and UI.

### Safety and quality gates

- no shared mutable worktree between concurrent workers
- per-task and aggregate budgets
- explicit tool allowlists by worker role
- reviewer/tester evidence required before merge
- deterministic conflict ownership and retry limits
- secrets and external command policy inherited from the main harness

The first implementation should be an adapter behind the existing
`AgentBackend`/event interfaces. The current graph remains the default until
swarm scheduling is validated against deterministic integration tests.

## 14. Deployment

Before compose:

1. create `.env`
2. ensure `marketplace_cache` is a directory
3. ensure `marketplace_index.sqlite` is a regular file
4. ensure `eco-cli` and `eco-wizard` are available or configured
5. build/install the frontend dependencies

Run `python scripts/dev_preflight.py` before `docker compose up`; it fails
early when Docker would otherwise create an empty directory at the SQLite
file mount.

The API mount is writable because UI RAG import updates the shared SQLite
index. Production deployments should use an index-update job or a controlled
volume policy rather than exposing arbitrary write access.

This section describes the DEV stack. Customer-facing installs (native wheel
+ uv, or the customer Docker image) and their artifact pipeline are covered
in §18 "Packaging, release pipeline and hosted artifacts".

## 15. Security and trust

- CORS defaults to local UI origins and is configurable with `CORS_ORIGINS`.
- Secrets are environment/secret-store data only. `provider_pin` in model
  profiles is an OpenRouter ROUTING hint (upstream provider slug), not a
  credential.
- CLI subprocesses use argument arrays, `shell=False`, allowlists, timeouts,
  and bounded output.
- Project filesystem tools enforce project-root containment.
- Tester has no write/build tools.
- The role permission layer (`eco_harness/permissions.py`, §5) adds the
  operator-configurable policy on top: denied tool groups never reach the
  model's toolset, and gated execution tools check the command allowlist.
  It is defense-in-depth, not a sandbox boundary.
- The whole API — including `PUT /config/workspace` and the chat WS — is an
  unauthenticated LOCAL dev surface bound to `127.0.0.1` by design; exposing
  it beyond localhost requires a fronting proxy with auth for the ENTIRE API,
  not a single route.
- Retrieved documents, marketplace descriptions, source files, runtime output,
  and build logs are untrusted data.
- WebSocket authentication remains an optional deployment extension and
  should be enabled for non-localhost exposure.

## 16. Deprecated material

Old chat and verification documents are historical references, not production
instructions. The active decisions are consolidated here.
`config/skills/component_author/SKILL.md` (relocated from `agent/skills/c.md`
in PRD_2 Phase 2, converted to the on-demand frontmatter format afterwards) is
now a LIVE dynamic skill of the coder role: its ~60 KB template corpus is
fetched via `read_skill` only when the coder hand-authors or repairs ACOM
component code without a usable eco-wizard — it is never baked into the static
prompt.

Do not use old version-specific prompts, dead LangGraph instructions, or the
old Chroma path when changing the production harness.

## 17. Validation checklist

### Test suite

The suite lives in `eco_harness/agent/internal/tests/` and MUST run through the project
venv so the pinned `pytest-asyncio` / `tree-sitter` versions are used:

```bash
# One-time setup:
python -m venv .venv
.venv/bin/pip install -r eco_harness/agent/requirements.txt   # includes pytest via pytest-asyncio

# Every run:
.venv/bin/python -m pytest eco_harness/agent/internal/tests eco_harness/backend/tests -v
```

(Windows: `.venv\Scripts\python -m pytest eco_harness/agent/internal/tests eco_harness/backend/tests`.)
`make test` is the equivalent one-liner. Live-LLM tests are marked
`@pytest.mark.live` and skipped unless `--live` is passed; the root
`conftest.py` registers that marker and skips them by default.

Coverage map:

- `test_orchestrator.py`, `test_entry.py` — edge routing, hop ceilings,
  `build_pipeline` assembly (`trace_dir` passthrough included).
- `test_eco_agent*.py`, `test_agents.py`, `test_handoff_tools.py`,
  `test_tools_*.py` — EcoAgent loop, role agents, handoff contract,
  file/build/runtime tools, RAG tool offline.
- `test_prd2_regressions.py` — Phase 0/1 locks: external bridge event
  marshalling, prompt precedence (workspace > config > built-in), host-mode
  artifact paths.
- `test_prd2_phase2.py` — Phase 2/3 locks: shared `resolve_binary` order,
  phantom skill-key removal, dead-YAML wiring, external-role prompt parity,
  pipeline-topology constants.

### Baseline gate

```cmd
.venv/bin/python -m pytest eco_harness/agent/internal/tests eco_harness/backend/tests
python -m compileall -q eco_harness scripts agent backend
cd frontend
npm run build
```

For a deployment smoke test:

```cmd
curl http://localhost:8100/health
curl http://localhost:8100/config
docker compose config
```
## 18. Packaging, release pipeline and hosted artifacts

This section is the developer/infra-facing contract for the installable
package (native + Docker). Customer-facing instructions live in the README
("Install" section); everything here is about how the artifacts are produced,
hosted, verified, and consumed.

### 18.1 What ships in the wheel

The wheel (`eco_harness-<ver>-py3-none-any.whl`, built by
`scripts/release/build_wheel.sh`) contains the entire runtime surface — the
installed app must work out of the box with no source checkout:

| In the wheel | Source | Notes |
| --- | --- | --- |
| `eco_harness/` Python packages | `eco_harness/**` | `agent`, `backend`, `interfaces`, `adapters`, `extensions`, `tools`, `roles`, `permissions`, `update`, `doctor` — all under the `eco_harness` namespace |
| `eco_harness/config/**` | repo-root `config/` | mapped via `[tool.setuptools.package-dir]` (`"eco_harness.config" = "config"`): harness/roles/models/modes YAML, prompts, skills, agents rules. Read at runtime through `paths.config_dir()` |
| `eco_harness/web_static/` | `frontend/out/` (Next.js static export) | copied by `build_wheel.sh`; served by FastAPI at `/` (SPA fallback, API routes take priority) |
| `eco_harness/env.example` | root `env.example` | installed-mode reference template |
| `eco_harness/backend/scaffold/*` | dev fallback templates | explicit `HARNESS_SCAFFOLD=1` fallback only |

Deliberately NOT in the wheel: repo-root `agent`/`backend` import shims (dev
checkouts only), test packages (`eco_harness/agent/internal/tests`),
`scripts/`, `.venv`, `output/`,
`traces/`, `marketplace_*`, `eco_framework/`. Runtime deps (fastapi,
uvicorn, websockets, python-multipart, pydantic, PyYAML, dotenv, httpx,
partial-json-parser, tiktoken, sqlite-vec, `tree-sitter>=0.23,<0.24`,
`tree-sitter-c==0.21.4` — the ABI-v14/v15 pin is load-bearing, see
`eco_harness/agent/requirements.txt`) are BASE dependencies of
`pyproject.toml`, not extras; pytest/respx live in the `dev` extra.

The prebuilt RAG index and the native `eco-cli`/`eco-wizard` binaries are
deliberately NOT in the wheel — they are versioned, OS-specific or large
artifacts downloaded from the manifest at install/update time.

### 18.2 Build flow

```text
frontend: npm ci && npm run build  (next.config.mjs: output:"export" → frontend/out/)
   └─ scripts/release/build_wheel.sh
        1. copies frontend/out → eco_harness/web_static   (gitignored)
        2. copies env.example → eco_harness/env.example   (gitignored)
        3. python -m build --wheel --outdir dist .
   └→ dist/eco_harness-<ver>-py3-none-any.whl
```

CI runs the same script (`.github/workflows/release.yml` at the MONOREPO
root — GitHub only loads root-level workflows; all steps run with
`working-directory` pointed at this subproject).

### 18.3 The manifest — single version source of truth

`scripts/release/build_manifest.py` walks a staging dir and emits
`manifest.json`. Every consumer (installers, `eco-harness update`) resolves
everything through it:

```jsonc
{
  "schema_version": 1,
  "updated_at": "…",
  "wheel":   {"version": "1.0.0", "url": "<BASE>/dist/eco_harness-1.0.0-py3-none-any.whl", "sha256": "…", "size": 1905612},
  "binaries": {
    "eco-cli":  {"linux": {"x86_64": {"url": "<BASE>/binaries/eco-cli/linux/x86_64/eco-cli", "sha256": "…"}}, "darwin": {"x86_64": …, "arm64": …}, "windows": {"x86_64": …}},
    "eco-wizard": {…}
  },
  "index": {"url": "<BASE>/index/marketplace_index.tar.gz", "sha256": "…"},
  "image": {"repo": "ghcr.io/<owner>/<name>", "tag": "1.0.0"}
}
```

Staging layout (before `build_manifest.py` runs):

```text
release-staging/
├── dist/eco_harness-<ver>-py3-none-any.whl
├── binaries/<tool>/<os>/<arch>/<artifact>   ← EcoCLI pipeline contract
├── index/marketplace_index.tar.gz           ← prebuilt RAG index + cache
└── install/install.sh, install.ps1          ← hosted for stable curl|sh URLs
```

Hard rule: `build_manifest.py` exits non-zero unless `binaries`, `index` and
`wheel` are all present (`--allow-empty` is for local testing only) — an
empty manifest would ship installs with no eco-cli and no RAG data.

The `binaries/` and `index/` assets are owned by the EcoCLI pipeline
(binaries) and the index build job (tarball of `marketplace_index.sqlite` +
`marketplace_cache/`). They must be staged into `release-staging/` before
the manifest job runs — via the `ECOCLI_STAGING_URL` repo variable (fetched
by the workflow) or by dispatching this workflow from the EcoCLI pipeline
with the artifacts merged in. There is no implicit fallback: missing assets
fail the release.

### 18.4 CI release workflow (monorepo root `.github/workflows/release.yml`)

- `build` — wheel build (frontend export baked in), stages wheel + installer
  scripts, uploads `release-assets`.
- `publish-image` — `docker/setup-qemu-action` (arm64 emulation) +
  buildx multi-arch (`linux/amd64`, `linux/arm64`) of `docker/Dockerfile`
  (wheel staged into `docker/wheel/` inside the build context), pushed to
  ghcr with `type=semver` + `latest` tags; fails fast if no tag resolves or
  the wheel version ≠ git tag.
- `publish-manifest` — validates `RELEASE_BASE_URL`/`RELEASE_S3_BUCKET`,
  stages EcoCLI assets, builds + validates the manifest, `aws s3 sync`s
  manifest, installers, binaries, index, wheel.

Required repo configuration: variables `RELEASE_BASE_URL`,
`RELEASE_S3_BUCKET`, `ECOCLI_STAGING_URL` (set when the EcoCLI pipeline
publishes), `RELEASE_AWS_REGION`; secrets `RELEASE_AWS_ACCESS_KEY_ID`,
`RELEASE_AWS_SECRET_ACCESS_KEY`. ghcr push uses the built-in
`GITHUB_TOKEN` with `packages: write`. The image repo must match what the
installers default to (`ghcr.io/<owner>/<repo>`, lowercased) — the
installers override from `manifest.image.repo` whenever the manifest is
reachable.

### 18.5 Install flow (what the installers actually do)

`scripts/install/install.sh` (POSIX) / `install.ps1` (Windows), `--docker` /
`-Docker` variants:

```text
NATIVE
 1. uv (installed per-OS if missing) → uv python install 3.11
 2. uv venv $ECO_HOME/venv (default ~/.eco-harness)
 3. uv pip install --python $ECO_HOME/venv/bin/python <wheel from manifest>
 4. python -m eco_harness update      → native binaries → $ECO_HOME/bin
                                      → prebuilt index  → $ECO_HOME/data
    (sha256-verified against the manifest; macOS quarantine xattr stripped)
 5. seed $ECO_HOME/.env (chmod 600; keys optional — /setup completes it)
    [--project-dir writes ECO_PROJECT_DIR into the seeded .env]
 6. PATH shims: ~/.local/bin/eco-harness{,-update} (POSIX);
    $ECO_HOME/bin/eco-harness*.cmd + user-PATH (Windows)

DOCKER
 1. resolve image repo/tag from the manifest (fall back to the built-in
    default with a loud warning when the manifest is unreachable)
 2. write $ECO_HOME/docker-compose.yml (absolute host paths baked in),
    seed .env (600), `docker compose up -d --wait`
 3. `docker compose exec -T eco-harness python -m eco_harness update`
    populates the mounted /data with binaries + index
```

Missing API keys never block install or launch — the `/setup` wizard or a
manual `.env` edit completes configuration (see the wizard endpoints in
§10: `GET /api/setup/status`, `POST /api/setup/config`).

### 18.6 Installed-mode path policy (`paths.py` is the single source)

| Helper | Dev checkout | Installed wheel |
| --- | --- | --- |
| `is_dev_checkout()` | True (`pyproject.toml`/`config/` at `_CHECKOUT_ROOT`) — also True in the DEV container, where uvicorn runs with CWD = the mounted Assembly1 checkout | False |
| `repo_root()` | checkout root | `$ECO_HOME` |
| `package_root()` | `<repo>/eco_harness` | `site-packages/eco_harness` (wheel data inside) |
| `config_dir()` | `<repo>/config` | `site-packages/eco_harness/config` (package data) |
| `eco_home()` | `~/.eco-harness` (or `$ECO_HOME`) | same |
| `project_dir()` | checkout root (or `$ECO_PROJECT_DIR`) | `$ECO_PROJECT_DIR`, else `$ECO_HOME` |
| `output_root()` | `<repo>/output` (`HARNESS_OUTPUT_ROOT` first) | `$ECO_HOME/output` |
| `traces_root()` | `<repo>/traces` (`HARNESS_TRACES_DIR` first) | `$ECO_HOME/traces` |
| workspace.yaml | `<repo>/.eco-harness/workspace.yaml` | `$ECO_HOME/workspace.yaml` |

Artifact resolution (`marketplace_index.sqlite`, `marketplace_cache`,
`eco_framework`): env var → `<repo_root>/<artifact>` if present →
`$ECO_HOME/data/<artifact>` if present → `/app/<artifact>` if present →
deterministic fallback + one-time warning. Worktrees always branch the USER
project (`paths.project_dir()`), never the harness install — `git rev-parse`
inside `ECO_HOME` fails loudly with a WorktreeError instead.

### 18.7 Self-update and health (`eco-harness update` / `doctor`)

`update` (`eco_harness/update.py`), manifest-driven, idempotent:

1. fetch manifest (defaults: `$ECO_MANIFEST_URL` → the S3 base URL)
2. wheel: if `manifest.wheel.version != installed`, download → sha256
   verify → `uv pip install --python <venv>` (pip fallback), report
   "restart to apply"
3. binaries: per-OS/arch target `$ECO_HOME/bin/<name>[.exe]` — safe-name
   regex + `bin_dir` containment check, sha256 compare against the existing
   file, chmod 0755, macOS `xattr -d com.apple.quarantine`
4. index: tarball → sha256 → member-validated extraction
   (`_safe_extractall`: rejects absolute/`..`/link members on every 3.11.x)
   into `$ECO_HOME/data/`, `.index_sha256` marker skips no-op refreshes
5. report printed; exit 1 when any step errored (never partial-silent)

Docker installs update via `docker compose pull && up -d` (image carries
the wheel); the in-container `python -m eco_harness update` path is what
the installers use for binaries/index bootstrap.

`doctor` (`eco_harness/doctor.py`) checks and reports (warnings never block
launch): python ≥3.11, binaries resolve+executable (prints
`describe_search_order`), RAG index loads through sqlite-vec (chunk count),
`OPENAI_API_KEY`/`ECO_API_TOKEN` present (warn-only), static UI bundle
present, `project-dir`/`output-root`/`data-dir` writable. Exit 1 only on
FAIL-class findings.

### 18.8 Versioning rules

- `pyproject.toml` `version` is the wheel version and MUST equal the git tag
  (`v<version>`); the workflow asserts this before publishing.
- The manifest is the single source of truth for installers and
  `eco-harness update` — never hardcode version/URLs in the installers when
  a manifest entry exists (fallbacks exist only for offline resilience and
  warn loudly).
- The wheel version-bump is part of the release checklist: tag without a
  bump fails CI.
