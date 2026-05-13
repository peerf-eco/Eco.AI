"""Tests for resolve_component_root — three layout variants."""
from pathlib import Path
import pytest
from agent.v6.tools.sdk_layout import resolve_component_root, list_component_roots


@pytest.fixture
def sdk(tmp_path: Path) -> Path:
    # Versioned 2-level (real EcoOS SDK packages):
    #   <sdk>/Eco.Math.C89_DK_v.1.0.1.2/Eco.Math.C89/SharedFiles/IEcoMath.h
    v2 = tmp_path / "Eco.Math.C89_DK_v.1.0.1.2" / "Eco.Math.C89"
    (v2 / "SharedFiles").mkdir(parents=True)
    (v2 / "SharedFiles" / "IEcoMath.h").write_text("/* math */")
    (v2 / "BuildFiles" / "Linux" / "x86_64" / "StaticRelease").mkdir(parents=True)

    # Versioned 1-level (legacy / unknown layout, kept for safety):
    #   <sdk>/Eco.Old_DK_v.1.0.0.0/SharedFiles/IEcoOld.h
    v1 = tmp_path / "Eco.Old_DK_v.1.0.0.0"
    (v1 / "SharedFiles").mkdir(parents=True)
    (v1 / "SharedFiles" / "IEcoOld.h").write_text("/* old */")

    # Flat (framework infra — no _DK_v.):
    #   <sdk>/Eco.MemoryManager1/SharedFiles/IEcoMemory.h
    flat = tmp_path / "Eco.MemoryManager1"
    (flat / "SharedFiles").mkdir(parents=True)
    (flat / "SharedFiles" / "IEcoMemory.h").write_text("/* mem */")

    # CID-named (build artifact only — must NOT be returned by listing):
    cid = tmp_path / "0000000000000000000000004D656D31"
    cid.mkdir()
    (cid / "0000000000000000000000004D656D31.dll").write_text("BIN")

    return tmp_path


def test_resolve_versioned_2level(sdk):
    root = resolve_component_root(sdk, "Eco.Math.C89")
    assert root is not None
    assert (root / "SharedFiles" / "IEcoMath.h").exists()
    # Inner root, NOT outer _DK_v. directory.
    assert root.name == "Eco.Math.C89"
    assert root.parent.name == "Eco.Math.C89_DK_v.1.0.1.2"


def test_resolve_versioned_1level(sdk):
    root = resolve_component_root(sdk, "Eco.Old")
    assert root is not None
    assert (root / "SharedFiles" / "IEcoOld.h").exists()
    # Falls back to the outer _DK_v. directory when no nested name-match.
    assert root.name == "Eco.Old_DK_v.1.0.0.0"


def test_resolve_flat(sdk):
    root = resolve_component_root(sdk, "Eco.MemoryManager1")
    assert root is not None
    assert (root / "SharedFiles" / "IEcoMemory.h").exists()
    assert root.name == "Eco.MemoryManager1"


def test_resolve_picks_latest_version(tmp_path):
    base = "Eco.X"
    (tmp_path / f"{base}_DK_v.1.0.0.0" / base / "SharedFiles").mkdir(parents=True)
    (tmp_path / f"{base}_DK_v.1.0.1.2" / base / "SharedFiles").mkdir(parents=True)
    root = resolve_component_root(tmp_path, base)
    assert root.parent.name == f"{base}_DK_v.1.0.1.2"


def test_resolve_with_explicit_version(tmp_path):
    base = "Eco.X"
    (tmp_path / f"{base}_DK_v.1.0.0.0" / base / "SharedFiles").mkdir(parents=True)
    (tmp_path / f"{base}_DK_v.1.0.1.2" / base / "SharedFiles").mkdir(parents=True)
    root = resolve_component_root(tmp_path, base, version="1.0.0.0")
    assert root.parent.name == f"{base}_DK_v.1.0.0.0"


def test_resolve_missing_returns_none(sdk):
    assert resolve_component_root(sdk, "Eco.DoesNotExist") is None


def test_resolve_sdk_root_missing_returns_none(tmp_path):
    assert resolve_component_root(tmp_path / "no-such-dir", "Eco.X") is None


def test_list_includes_flat_framework(sdk):
    names = list_component_roots(sdk)
    assert "Eco.Math.C89" in names
    assert "Eco.Old" in names
    assert "Eco.MemoryManager1" in names


def test_list_excludes_cid_directories(sdk):
    names = list_component_roots(sdk)
    assert "0000000000000000000000004D656D31" not in names


def test_list_returns_sorted(sdk):
    names = list_component_roots(sdk)
    assert names == sorted(names)


def test_resolve_picks_numerically_latest_version_not_lexicographic(tmp_path):
    """Versions are compared as integer tuples, not strings.
    `1.0.10.0` > `1.0.9.0` numerically but the reverse lexicographically.
    A naive sort would silently return the older package."""
    base = "Eco.X"
    (tmp_path / f"{base}_DK_v.1.0.9.0" / base / "SharedFiles").mkdir(parents=True)
    (tmp_path / f"{base}_DK_v.1.0.10.0" / base / "SharedFiles").mkdir(parents=True)
    root = resolve_component_root(tmp_path, base)
    assert root.parent.name == f"{base}_DK_v.1.0.10.0"


def test_list_excludes_versioned_without_payload(tmp_path):
    """A _DK_v. directory that has no SharedFiles/ or BuildFiles/ at either
    level must NOT appear in the listing — the resolver would return None
    for it, and the planner must not select a phantom component."""
    empty = tmp_path / "Eco.Phantom_DK_v.1.0.0.0"
    empty.mkdir()
    # Also a real one to make sure the listing isn't just empty.
    real = tmp_path / "Eco.Real_DK_v.1.0.0.0" / "Eco.Real"
    (real / "SharedFiles").mkdir(parents=True)
    names = list_component_roots(tmp_path)
    assert "Eco.Phantom" not in names
    assert "Eco.Real" in names


def test_resolve_skips_empty_versioned_to_older_with_payload(tmp_path):
    """If the latest versioned dir has no payload, fall back to an older one."""
    base = "Eco.Y"
    # newer but EMPTY
    (tmp_path / f"{base}_DK_v.2.0.0.0").mkdir(parents=True)
    # older WITH payload
    (tmp_path / f"{base}_DK_v.1.0.0.0" / base / "SharedFiles").mkdir(parents=True)
    root = resolve_component_root(tmp_path, base)
    assert root is not None
    assert root.parent.name == f"{base}_DK_v.1.0.0.0"
