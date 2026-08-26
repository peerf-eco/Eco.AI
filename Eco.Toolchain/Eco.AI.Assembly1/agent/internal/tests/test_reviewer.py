"""Tests for the reviewer agent — pipeline (coder→reviewer→tester) vs
standalone (/review) tool wiring.

The reviewer is read-only in BOTH contexts; the difference is only which
stop-tools it is given, which is the deterministic signal it uses to know
whether it is inside the migrate build pipeline or a standalone review.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.internal.agents.reviewer import make_reviewer
from agent.internal.tests.conftest import make_scripted_model_pair, ai_tool


@pytest.fixture
def model():
    m, _stream_fn = make_scripted_model_pair([ai_tool("fail", {"reason": "smoke"}, "c0")])
    return m


def test_reviewer_is_read_only(model, project_dir):
    """Load-bearing: the reviewer must never mutate state, in either mode."""
    for pipeline in (False, True):
        agent = make_reviewer(model=model, project_dir=project_dir, pipeline=pipeline)
        forbidden = {"write_file", "edit_file", "run_build", "run_artifact", "eco_cli"}
        assert forbidden & set(agent.tools.keys()) == set(), (
            f"Reviewer(pipeline={pipeline}) bound to forbidden tools "
            f"{forbidden & set(agent.tools.keys())}."
        )


def test_reviewer_pipeline_mode_has_to_tester_and_to_coder(model, project_dir):
    agent = make_reviewer(model=model, project_dir=project_dir, pipeline=True)
    assert agent.stop_tools == {"to_tester", "to_coder", "fail"}
    # Forward + backward handoffs must exist as tools.
    assert "to_tester" in agent.tools
    assert "to_coder" in agent.tools
    # No `done` in pipeline — the reviewer must forward, not self-terminate.
    assert "done" not in agent.tools


def test_reviewer_standalone_mode_has_done(model, project_dir):
    agent = make_reviewer(model=model, project_dir=project_dir, pipeline=False)
    assert agent.stop_tools == {"done", "fail"}
    assert "done" in agent.tools
    # No pipeline handoffs in standalone mode.
    assert "to_tester" not in agent.tools
    assert "to_coder" not in agent.tools


def test_reviewer_has_read_and_search_tools(model, project_dir):
    agent = make_reviewer(model=model, project_dir=project_dir)
    names = set(agent.tools.keys())
    assert "read_file" in names
