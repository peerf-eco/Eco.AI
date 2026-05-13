from pathlib import Path
import pytest
from agent.v6.tools.planner import (
    make_planner_tools, ReadComponentArgs, ListComponentsArgs, SubmitPlanArgs,
)


@pytest.fixture
def sdk_dir(tmp_path: Path) -> Path:
    """Mock SDK tree mixing all three layouts seen in the real EcoOS source/."""
    # Versioned 2-level: most common case.
    a = tmp_path / "Eco.Math.C89_DK_v.1.0.1.2" / "Eco.Math.C89"
    (a / "SharedFiles").mkdir(parents=True)
    (a / "SharedFiles" / "IEcoMath.h").write_text("/* math header */")

    b = tmp_path / "Eco.StdIO.C89_DK_v.1.0.1.2" / "Eco.StdIO.C89"
    (b / "SharedFiles").mkdir(parents=True)
    (b / "SharedFiles" / "IEcoStdIO.h").write_text("/* stdio header */")

    # Flat: framework infra (matches real Eco.MemoryManager1).
    mm = tmp_path / "Eco.MemoryManager1"
    (mm / "SharedFiles").mkdir(parents=True)
    (mm / "SharedFiles" / "IEcoMemory.h").write_text("/* mem header */")

    # CID-named build artefact (real source/ has these too) — must NOT be listed.
    cid = tmp_path / "0000000000000000000000004D656D31"
    cid.mkdir()
    (cid / "0000000000000000000000004D656D31.dll").write_text("BIN")

    return tmp_path


def test_list_components_returns_packages(sdk_dir):
    tools = make_planner_tools(sdk_root=sdk_dir)
    list_t = next(t for t in tools if t.name == "list_components")
    r = list_t.execute(ListComponentsArgs())
    assert not r.is_error
    assert "Eco.Math.C89" in r.content
    assert "Eco.StdIO.C89" in r.content


def test_list_components_includes_flat_framework(sdk_dir):
    """Eco.MemoryManager1 (flat, no _DK_v.) must be visible to the planner."""
    tools = make_planner_tools(sdk_root=sdk_dir)
    r = next(t for t in tools if t.name == "list_components").execute(ListComponentsArgs())
    assert "Eco.MemoryManager1" in r.content


def test_list_components_excludes_cid_directories(sdk_dir):
    tools = make_planner_tools(sdk_root=sdk_dir)
    r = next(t for t in tools if t.name == "list_components").execute(ListComponentsArgs())
    assert "0000000000000000000000004D656D31" not in r.content


def test_read_component_returns_headers(sdk_dir):
    tools = make_planner_tools(sdk_root=sdk_dir)
    read_t = next(t for t in tools if t.name == "read_component")
    r = read_t.execute(ReadComponentArgs(name="Eco.Math.C89"))
    assert not r.is_error
    assert "math header" in r.content


def test_read_component_versioned_2level_finds_inner_shared(sdk_dir):
    """Headers live in <pkg>_DK_v.X/<pkg>/SharedFiles — not <pkg>_DK_v.X/SharedFiles."""
    tools = make_planner_tools(sdk_root=sdk_dir)
    r = next(t for t in tools if t.name == "read_component").execute(
        ReadComponentArgs(name="Eco.StdIO.C89")
    )
    assert not r.is_error
    assert "stdio header" in r.content


def test_read_component_flat_package(sdk_dir):
    """Flat packages (Eco.MemoryManager1) must also be readable."""
    tools = make_planner_tools(sdk_root=sdk_dir)
    r = next(t for t in tools if t.name == "read_component").execute(
        ReadComponentArgs(name="Eco.MemoryManager1")
    )
    assert not r.is_error
    assert "mem header" in r.content


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


def test_read_component_buildfiles_only_returns_informative_error(tmp_path):
    """A package found by the resolver via BuildFiles/ only (no SharedFiles/)
    must yield an error that explicitly says 'build-only package' so the LLM
    knows to skip header introspection and just declare the dependency."""
    pkg = tmp_path / "Eco.BuildOnly_DK_v.1.0.0.0" / "Eco.BuildOnly"
    (pkg / "BuildFiles" / "Linux" / "x86_64" / "StaticRelease").mkdir(parents=True)
    tools = make_planner_tools(sdk_root=tmp_path)
    r = next(t for t in tools if t.name == "read_component").execute(
        ReadComponentArgs(name="Eco.BuildOnly")
    )
    assert r.is_error
    assert "build-only" in r.content.lower()
