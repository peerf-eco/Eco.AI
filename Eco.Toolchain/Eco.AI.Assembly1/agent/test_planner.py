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


def test_read_component_finds_plain_directory_without_dk_suffix(tmp_path, monkeypatch):
    """Eco.MemoryManager1 lives as a plain dir (no _DK_v.* suffix). Must still resolve."""
    plain = tmp_path / "Eco.MemoryManager1" / "SharedFiles"
    plain.mkdir(parents=True)
    (plain / "IEcoMemoryManager1.h").write_text("// memory mgmt\nvoid* Allocate(size_t);\n")
    monkeypatch.setattr("agent.planner.SOURCE_DIR", tmp_path)

    tool = next(t for t in build_planner_tools(None) if t.name == "read_component")
    result = tool.invoke({"name": "Eco.MemoryManager1"})
    assert "memory mgmt" in result
    assert "Allocate" in result


def test_read_component_picks_latest_version_when_multiple_dks(tmp_path, monkeypatch):
    """If both v1.0 and v2.0 of a component exist, read_component picks the higher version."""
    older = tmp_path / "Eco.X_DK_v.1.0.0.0" / "SharedFiles"
    newer = tmp_path / "Eco.X_DK_v.2.0.0.0" / "SharedFiles"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "IEcoX.h").write_text("// OLD VERSION\n")
    (newer / "IEcoX.h").write_text("// NEW VERSION\n")
    monkeypatch.setattr("agent.planner.SOURCE_DIR", tmp_path)

    tool = next(t for t in build_planner_tools(None) if t.name == "read_component")
    result = tool.invoke({"name": "Eco.X"})
    assert "NEW VERSION" in result
    assert "OLD VERSION" not in result


def test_read_component_errors_when_shared_missing(tmp_path, monkeypatch):
    """DK directory exists but SharedFiles/ is absent."""
    (tmp_path / "Eco.Broken_DK_v.1.0").mkdir(parents=True)
    monkeypatch.setattr("agent.planner.SOURCE_DIR", tmp_path)

    tool = next(t for t in build_planner_tools(None) if t.name == "read_component")
    result = tool.invoke({"name": "Eco.Broken"})
    assert "SharedFiles missing" in result


def test_read_component_errors_when_no_headers(tmp_path, monkeypatch):
    """SharedFiles/ exists but contains no IEco*.h or IdEco*.h files."""
    (tmp_path / "Eco.Empty_DK_v.1.0" / "SharedFiles").mkdir(parents=True)
    monkeypatch.setattr("agent.planner.SOURCE_DIR", tmp_path)

    tool = next(t for t in build_planner_tools(None) if t.name == "read_component")
    result = tool.invoke({"name": "Eco.Empty"})
    assert "No headers" in result
