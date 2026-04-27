import os
import tempfile
from pathlib import Path

from agent.planner import build_planner_tools


def test_read_component_returns_header_content(tmp_path, monkeypatch):
    # Mock SOURCE_DIR with a fake DK structure
    dk = tmp_path / "Eco.Math.C89_DK_v.1.0.1.2"
    shared = dk / "SharedFiles"
    shared.mkdir(parents=True)
    (shared / "IEcoMathC89.h").write_text("// math interface\nint Add(int a, int b);\n")
    (shared / "IdEcoMathC89.h").write_text("// component id\n#define CID_ECO_MATH_C89 0x...\n")

    monkeypatch.setattr("agent.planner.SOURCE_DIR", tmp_path)

    tools = build_planner_tools(llm=None)
    read_component = next(t for t in tools if t.name == "read_component")
    result = read_component.invoke({"name": "Eco.Math.C89"})

    assert "math interface" in result
    assert "Add(int a, int b)" in result
    assert "CID_ECO_MATH_C89" in result


def test_read_component_returns_error_for_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.planner.SOURCE_DIR", tmp_path)
    tools = build_planner_tools(llm=None)
    read_component = next(t for t in tools if t.name == "read_component")
    result = read_component.invoke({"name": "Eco.Nope"})
    assert "ERROR" in result or "not found" in result.lower()
