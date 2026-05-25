# V6/V7 Agent Tools

The toolbox available to architect / coder / tester agents. Each module
exports a `make_*` factory that returns one or more `EcoTool` instances
ready to be passed to an `EcoAgent`.

## Tools by category

### Code exploration (claude-code-style, primary)

These are the universal file-system primitives every agent uses to
discover code, locate symbols, and read files. Same mental model as
Claude Code / Codex / pi-harness.

| Tool | Module | Purpose |
|---|---|---|
| `grep` | `code_search.py` | POSIX extended-regex content search (`grep -rnE`). Searches `marketplace_cache/` by default; can target `project_dir`. Returns `file:line:match` lines. |
| `glob` | `code_search.py` | File-pattern enumeration with `**` recursive descent. Returns paths sorted by mtime. |
| `read` | `code_search.py` | UTF-8 file read with `offset`/`limit`. Reads from `project_dir` OR `marketplace_cache` (whitelisted roots). |

Sandbox rule: relative paths anchor at `project_dir`. A relative path
whose first segment matches a basename of any allowed root (e.g.
`marketplace_cache/...`) anchors there instead.

### Marketplace discovery (domain helpers)

| Tool | Module | Purpose |
|---|---|---|
| `search_marketplace` | `rag.py` | Semantic RAG search over ~1200 chunks of all 30 published EcoOS components. Use when a literal regex misses (conceptual queries). |
| `read_component_profile` | `profile_cache.py` | Look up `{cid, version, devkit_file_id}` for a component name. Reads `marketplace_cache/_profiles/<Name>.json`. Faster than `eco_cli find -c`. |

### Marketplace fetch

| Tool | Module | Purpose |
|---|---|---|
| `eco_cli` | `eco_cli.py` | Passthrough to the Eco marketplace CLI (`find`, `pull`, `version`, `help`). Whitelisted subcommands; output is raw stdout/stderr + rc. |

### Build / runtime / file I/O (sandboxed to `project_dir`)

| Tool | Module | Purpose |
|---|---|---|
| `read_file` | `io.py` | Legacy `project_dir`-sandboxed file read (prefer `read`). |
| `list_dir` | `io.py` | Legacy directory listing (prefer `glob`). |
| `write_file` | `io.py` | Create/overwrite a file under `project_dir`. Coder only. |
| `run_build` | `build.py` | Invoke GNU make in `project_dir/<subdir>`. Returns rc + truncated build log. Coder only. |
| `run_artifact` | `runtime.py` | Execute the built binary with stdin piped from a test case. Returns stdout + rc. Tester only. |

### Agent-to-agent handoff (stop tools)

Stop tools terminate the calling agent's run and signal the orchestrator
which edge to follow next.

| Tool | Module | Purpose |
|---|---|---|
| `to_coder(message)` | `handoff.py` | Architect → Coder edge. |
| `to_tester(message)` | `handoff.py` | Coder → Tester edge. |
| `to_architect(message)` | `handoff.py` | Coder → Architect edge (plan escalation). |
| `fail(reason)` | `handoff.py` | Any agent → terminal failure. |

## Capability gating (who gets what)

The agent factories pick a subset matching the agent's role:

```
architect:  grep, glob, read, search_marketplace, read_component_profile,
            eco_cli, read_file, list_dir, to_coder, fail
coder:      grep, glob, read, search_marketplace,
            read_file, list_dir, write_file, run_build,
            to_tester, to_architect, fail
tester:     grep, glob, read, search_marketplace,
            read_file, list_dir, run_artifact,
            to_coder, done, fail
```

Note the asymmetry: only coder has `write_file` + `run_build`; only
tester has `run_artifact`. This prevents the tester from "fixing" tests
to pass, and prevents the architect from pre-writing code the coder is
supposed to author.

## Common ground

Every tool returns a `ToolResult(content, details, is_error)`:

- `content` — markdown / plain text shown to the model in the next turn.
- `details` — structured dict for downstream consumers (UI, traces).
- `is_error` — `True` flips the result into the "error" branch the agent
  loop uses to retry / escalate.

`is_error=True` with a helpful `content` is **preferred** over raising
an exception: the model sees the error message and can self-correct on
the next iteration.

## Tests

Per-tool unit tests live in `agent/v6/tests/test_tool*.py` and
`test_tools_*.py`. Run all of them: `pytest agent/v6/tests/ -q`.

## Adding a new tool

1. Define a Pydantic `BaseModel` for args.
2. Write an `_execute(args, ...) -> ToolResult` function.
3. Wrap in a `make_<name>_tool(...)` factory returning an `EcoTool`.
4. Add to the relevant agent's `tools` list in `agent/v6/agents/`.
5. Mention it in the agent's system prompt (one paragraph + one
   concrete invocation example — see `feedback_prompts_positive_procedure`
   in memory for why examples are required, not bans).
6. Add a unit test in `agent/v6/tests/`.
