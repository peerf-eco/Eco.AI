# `agent/v6/` — V7 agent layer

The folder is still called `v6` for historical reasons (renaming would churn
many imports). Since the **2026-06-22 retirement** it contains **only V7** —
the V6 LangGraph rollback (`graph.py`, `state.py`, `trace.py`,
`stream_events.py`, `nodes/`) and its node-tools were removed. For rollback,
use git history. See `docs/V7_ARCHITECTURE.md` for the full picture.

## Layout

| Subdir | Purpose |
|---|---|
| `agents/` | V7 agents: `architect`, `coder`, `tester` (pi_ai `EcoAgent` loops) + `_taxonomy` |
| `tools/` | Tools the agents call — see `tools/README.md` |
| `tests/` | V7 unit + integration suite (no network) |
| `orchestrator.py` | Custom orchestrator driving the three agents (no LangGraph) |
| `eco_agent.py` | `EcoTool` / `EcoAgent` — claude-code-style loop on pi_ai |
| `entry.py` | `build_v7_pipeline(...)` — programmatic V7 entry |
| `call_trace.py` | Per-call LLM trace persistence (`traces/v7-<id>/`) |

Frontend is pinned to V7: `NEXT_PUBLIC_PIPELINE_VERSION=v7` (`docker-compose.yml`).

## V7 entry point

```python
from agent.v6.entry import build_v7_pipeline

orchestrator = build_v7_pipeline(
    model=model,                    # agent.pi_ai.Model (see agent/main.py get_model)
    cli_path=Path("eco.sli-linux/eco-cli"),
    project_dir=Path("./output/v7-abc12345"),
    make_exe=Path("make"),
)
result = orchestrator.run("Build a calculator with pow and sqrt")
```

WebSocket endpoint: `/ws/v7/chat` in `backend/server.py` (the only pipeline
endpoint after the V1–V6 retirement).

## Tests

`pytest agent/v6/tests/ -q` — V7 unit + integration suite (no network):
`test_agents.py`, `test_eco_agent.py`, `test_orchestrator.py`,
`test_entry.py`, `test_handoff_tools.py`, `test_tool_rag.py`, and the
`test_tools_*.py` for the kept tools.

## Further reading

- `docs/V7_ARCHITECTURE.md` — orchestrator, topology, endpoint mapping
- `docs/RAG_SETUP.md` — building/connecting the sqlite-vec marketplace index
- `tools/README.md` — every tool's purpose + capability gating
- `memory/MEMORY.md` — engineering constraints, build gotchas, design rationale
