# `agent/v6/` — V6 and V7 agent layer

This directory houses **two** pipeline implementations side by side.
The folder is still called `v6` for historical reasons (renaming would
churn many imports mid-flight). See `docs/V7_ARCHITECTURE.md` for the
full picture.

## Quick orientation

| Subdir | Belongs to | Status |
|---|---|---|
| `nodes/` | V6 LangGraph StateGraph | Legacy, kept for rollback |
| `agents/` | V7 flat orchestrator | **Current production** |
| `tools/` | Shared by both | See `tools/README.md` |
| `tests/` | Mixed | `test_*node*.py` → V6, `test_*agent*.py` → V7, others → tools |

Frontend default: `NEXT_PUBLIC_PIPELINE_VERSION=v7` (`docker-compose.yml`).
Set to `v6` for legacy rollback.

## V7 entry point (current)

```python
from agent.v6.entry import build_v7_pipeline

orchestrator = build_v7_pipeline(
    model=model,                    # agent.pi_ai.Model
    cli_path=Path("eco.sli-linux/eco-cli"),
    project_dir=Path("./output/v7-abc12345"),
    make_exe=Path("make"),
)
result = orchestrator.run("Build a calculator with pow and sqrt")
```

WebSocket endpoint: `/ws/v7/chat` in `backend/server.py:1020`.

## V6 entry point (legacy)

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

WebSocket endpoint: `/ws/v6/chat` in `backend/server.py:672`.

## Tests

`pytest agent/v6/tests/ -q` — full unit + integration suite (~50 tests,
no network).

Per-tool unit tests live as `test_tool_<name>.py` /
`test_tools_<name>.py`.

V6-node-specific tests: `test_*_node.py`. V7-agent-specific:
`test_agents.py`, `test_eco_agent.py`, `test_handoff_tools.py`.

## Further reading

- `docs/V7_ARCHITECTURE.md` — orchestrator, topology, endpoint mapping
- `tools/README.md` — every tool's purpose + capability gating
- `memory/MEMORY.md` (loaded into Claude context) — engineering
  constraints, build gotchas, design decisions with rationale
