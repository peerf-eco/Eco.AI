"""Live E2E — real OpenRouter LLM, real subprocess.

Run manually with: pytest agent/v6/tests/test_live_e2e.py -v --live -s
NOT in CI. Requires:
  - OPENAI_API_KEY (OpenRouter token) in .env
  - eco-cli.exe present at H:/ai-hse-diploma-agent/eco.sli/eco-cli.exe
  - MSVC vcvarsall.bat at the known path
  - make.exe at C:/Users/gaevy/gcc/bin/make.exe
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import pytest
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver


@pytest.mark.live
@pytest.mark.timeout(600)
def test_calculator_app():
    from agent.main import get_llm
    from agent.v6.graph import create_v6_graph
    from agent.v6.state import make_initial_v6_state

    project_root = Path(__file__).resolve().parents[5]   # repo root: H:/ai-hse-diploma-agent
    sdk_root  = project_root / "source"
    cli_path  = project_root / "eco.sli" / "eco-cli.exe"
    vcvarsall = Path(r"C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/vcvarsall.bat")
    make_exe  = Path(r"C:/Users/gaevy/gcc/bin/make.exe")
    out_dir   = project_root / "output" / "v6_live_calc"
    out_dir.mkdir(parents=True, exist_ok=True)

    llm = get_llm()
    graph = create_v6_graph(llm, sdk_root=sdk_root, cli_path=cli_path,
                            vcvarsall=vcvarsall, make_exe=make_exe,
                            checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "live-calc-1"}, "recursion_limit": 100}
    initial = make_initial_v6_state("калькулятор: сложение двух чисел")
    initial["project_dir"] = str(out_dir)

    # 1. planner runs until interrupt
    for ev in graph.stream(initial, config):
        if "__interrupt__" in ev:
            break
    state = graph.get_state(config).values
    assert state["phase"] == "awaiting_approval"
    assert state["plan_md"], "planner produced no plan_md"
    assert state["components"], "planner produced no components"
    print(f"\n[plan]\n{state['plan_md']}\n")

    # 2. approve
    for _ in graph.stream(Command(resume={"approved": True}), config):
        pass
    final = graph.get_state(config).values
    print(f"\n[status] {final['last_status']}, phase={final['phase']}")
    print(f"[artifact] {final.get('build_artifact', '(none)')}")
    assert final["last_status"] == "success", f"pipeline failed: {final}"
    assert Path(final["build_artifact"]).exists()
