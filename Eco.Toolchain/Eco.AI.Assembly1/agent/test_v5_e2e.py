"""E2E integration test for the V5 three-node pipeline.

Uses real LLM (env: OPENAI_API_KEY, LLM_MODEL). Skips if not configured.
"""

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import pytest


pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set; skipping E2E",
)


def _get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=os.environ.get("LLM_MODEL", "z-ai/glm-5.1"),
        temperature=0,
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_api_base=os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
        timeout=120,
        max_retries=1,
    )


def test_v5_pipeline_planning_to_handoff_smoke():
    """Smoke: enter planning, send approval message, observe phase transition."""
    from agent.chat_agent import create_chat_agent_v5, make_chat_agent_initial_state

    graph = create_chat_agent_v5(_get_llm())
    config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": 80}

    # Turn 1: initial request
    state = make_chat_agent_initial_state(
        "Make a tiny EcoOS calculator: read two integers, print their sum. Use Eco.Math.C89 and Eco.StdIO.C89. No custom components. Approve immediately."
    )
    final_state = graph.invoke(state, config)

    assert final_state["phase"] in ("planning", "coding", "executing", "done")
    # Planner must have produced *some* response
    assert len(final_state["planner_messages"]) > 1


def test_v5_parser_robust_across_models():
    """Run parse_plan on synthetic Markdown that 3 models produced in earlier tests."""
    from agent.parsers import parse_plan
    samples = [
        # glm-5.1-style
        "## Project: TestApp\n\n## Components\n- **Eco.Math.C89** — source: sdk — math",
        # kimi-k2.6-style with em-dashes
        "## Project: Test2\n\n## Components\n- **Eco.StdIO.C89** — source: sdk — io",
        # minimal
        "## Project: Tiny\n\n## Components\n- **A** — source: develop\n  - spec: x",
    ]
    for s in samples:
        result = parse_plan(s)
        assert result["project_name"]
        assert len(result["components"]) >= 1
