from pathlib import Path
import pytest
from agent.v6.tools.planner import (
    make_planner_tools, ReadComponentArgs, ListComponentsArgs, SubmitPlanArgs,
)


@pytest.fixture
def sdk_dir(tmp_path: Path) -> Path:
    """Mock SDK tree with two packages."""
    a = tmp_path / "Eco.Math.C89_DK_v.1.0.1.2"
    a.mkdir()
    (a / "SharedFiles").mkdir()
    (a / "SharedFiles" / "IEcoMath.h").write_text("/* math header */")
    b = tmp_path / "Eco.StdIO.C89_DK_v.1.0.1.2"
    b.mkdir()
    (b / "SharedFiles").mkdir()
    (b / "SharedFiles" / "IEcoStdIO.h").write_text("/* stdio header */")
    return tmp_path


def test_list_components_returns_packages(sdk_dir):
    tools = make_planner_tools(sdk_root=sdk_dir)
    list_t = next(t for t in tools if t.name == "list_components")
    r = list_t.execute(ListComponentsArgs())
    assert not r.is_error
    assert "Eco.Math.C89" in r.content
    assert "Eco.StdIO.C89" in r.content


def test_read_component_returns_headers(sdk_dir):
    tools = make_planner_tools(sdk_root=sdk_dir)
    read_t = next(t for t in tools if t.name == "read_component")
    r = read_t.execute(ReadComponentArgs(name="Eco.Math.C89"))
    assert not r.is_error
    assert "math header" in r.content


def test_read_component_not_found(sdk_dir):
    tools = make_planner_tools(sdk_root=sdk_dir)
    read_t = next(t for t in tools if t.name == "read_component")
    r = read_t.execute(ReadComponentArgs(name="Eco.Nonexistent"))
    assert r.is_error
    assert "not found" in r.content.lower()


def test_submit_plan_is_stop_tool_schema():
    args = SubmitPlanArgs(
        project_name="Calculator",
        plan_md="# Plan\n## Acceptance criteria\n- prints sum",
        components=[{"cid": "ABCD" * 8, "version": "1.0.1.2",
                     "name": "Eco.Math.C89", "reason": "math"}],
        acceptance_criteria=["stdout contains the sum"],
    )
    assert args.project_name == "Calculator"
    assert args.components[0]["cid"] == "ABCD" * 8
