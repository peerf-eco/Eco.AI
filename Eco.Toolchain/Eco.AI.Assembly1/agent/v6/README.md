# V6 — Five-Node Pipeline

Spec: `docs/superpowers/specs/2026-05-13-v6-pipeline-design.md`
Plan: `docs/superpowers/plans/2026-05-13-v6-agent-layer.md`

## Entry point

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

## Tests

`pytest agent/v6/tests/` — unit + integration, ~50 tests, no network.
`pytest agent/v6/tests/test_live_e2e.py --live -s` — real LLM, real build.
