"""ECO_FRAMEWORK integration tests (standard ACOM environment variables).

Locks in:

1. ``paths.framework_root()`` resolution: ECO_FRAMEWORK env →
   ``<repo>/eco_framework`` → deterministic repo fallback.
2. Nested development-kit discovery: the curated Eco.Core1 stitch finds
   ``<root>/Eco.Core1_DK_v.<ver>/Eco.Core1/SharedFiles``, not just the flat
   ``<root>/Eco.Core1/SharedFiles`` layout.
3. Token reduction: the stitch includes only C headers (.h), never the C++
   wrappers (.hpp).
4. ``eco_cli pull`` routes into $ECO_FRAMEWORK via eco-cli's -d flag when set.
5. RAG ingest normalizes versioned-DK directory names to marketplace
   component names.
"""
from __future__ import annotations

import contextlib
import os
from pathlib import Path

import pytest

from eco_harness.agent.context.assembler import (
    _core1_candidates,
    _core1_sharedfiles,
    stitch_source_files,
)
from eco_harness.agent.internal.tools import paths as tool_paths
from eco_harness.agent.internal.tools.eco_cli import _apply_framework_dev_target
from eco_harness.agent.rag.ingest import _iter_source_files


@pytest.fixture(autouse=True)
def _reset_warnings(monkeypatch):
    monkeypatch.setattr(tool_paths, "_warned", set())


# ── 1. framework_root resolution ─────────────────────────────────────────────


def test_framework_root_env_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("ECO_FRAMEWORK", str(tmp_path / "custom-fw"))
    assert tool_paths.framework_root(repo=tmp_path) == Path(tmp_path / "custom-fw")


def test_framework_root_repo_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("ECO_FRAMEWORK", raising=False)
    (tmp_path / "eco_framework").mkdir()
    assert tool_paths.framework_root(repo=tmp_path) == (tmp_path / "eco_framework").resolve()


def test_framework_root_deterministic_when_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("ECO_FRAMEWORK", raising=False)
    expected = (tmp_path / "eco_framework").resolve()
    assert tool_paths.framework_root(repo=tmp_path) == expected


# ── 2. Nested DK discovery ───────────────────────────────────────────────────


def test_core1_candidates_flat_layout(tmp_path):
    shared = tmp_path / "Eco.Core1" / "SharedFiles"
    shared.mkdir(parents=True)
    assert _core1_candidates(tmp_path) == [shared.resolve()]


def test_core1_candidates_versioned_dk_layout(tmp_path):
    """The marketplace/`pull -d` layout: <Component>_DK_v.<ver>/<Component>."""
    shared = tmp_path / "Eco.Core1_DK_v.1.0.1.2" / "Eco.Core1" / "SharedFiles"
    shared.mkdir(parents=True)
    assert _core1_candidates(tmp_path) == [shared.resolve()]


def test_core1_candidates_prefers_highest_version(tmp_path):
    for version in ("1.0.0.1", "1.0.1.2", "2.0.0.0"):
        (tmp_path / f"Eco.Core1_DK_v.{version}" / "Eco.Core1" / "SharedFiles").mkdir(
            parents=True,
        )
    resolved = _core1_candidates(tmp_path)
    assert len(resolved) == 3
    assert "_DK_v.2.0.0.0" in str(resolved[0])


def test_core1_sharedfiles_prefers_eco_framework_env(tmp_path, monkeypatch):
    fw = tmp_path / "fw"
    fw_shared = fw / "Eco.Core1_DK_v.9.9.9.9" / "Eco.Core1" / "SharedFiles"
    fw_shared.mkdir(parents=True)
    repo_shared = tmp_path / "repo" / "eco_framework" / "Eco.Core1" / "SharedFiles"
    repo_shared.mkdir(parents=True)
    monkeypatch.setenv("ECO_FRAMEWORK", str(fw))
    found = _core1_sharedfiles([tmp_path / "repo" / "eco_framework"])
    assert found == fw_shared.resolve()


# ── 3. C-only stitch (.h without .hpp) ───────────────────────────────────────


def test_stitch_core1_excludes_hpp(tmp_path):
    shared = tmp_path / "Eco.Core1_DK_v.1.0.1.2" / "Eco.Core1" / "SharedFiles"
    shared.mkdir(parents=True)
    (shared / "IEcoBase1.h").write_text("/* C HEADER */", encoding="utf-8")
    (shared / "IEcoBase1.hpp").write_text("// CPP WRAPPER", encoding="utf-8")
    stitched = stitch_source_files([shared], extensions=frozenset({".h"}))
    assert "C HEADER" in stitched
    assert "CPP WRAPPER" not in stitched


def test_build_static_prompt_uses_c_only_stitch(tmp_path, monkeypatch):
    from eco_harness.agent.context.assembler import build_static_system_prompt

    # Isolate from the host's real ECO_FRAMEWORK (if set) so the tmp layout
    # is what gets stitched.
    monkeypatch.delenv("ECO_FRAMEWORK", raising=False)
    monkeypatch.setattr(tool_paths, "_CHECKOUT_ROOT", tmp_path)

    shared = tmp_path / "src_roots" / "Eco.Core1_DK_v.1.0.1.2" / "Eco.Core1" / "SharedFiles"
    shared.mkdir(parents=True)
    (shared / "macros.h").write_text("#define ECO_OK 0", encoding="utf-8")
    (shared / "macros.hpp").write_text("// cpp noise", encoding="utf-8")
    prompt = build_static_system_prompt(
        "ROLE",
        source_roots=[tmp_path / "src_roots"],
        domain_knowledge="D",
        tool_contract="T",
        header_path=tmp_path / "no-header.md",
    )
    assert "#define ECO_OK 0" in prompt
    assert "cpp noise" not in prompt
    assert "_DK_v.1.0.1.2" in prompt


# ── 4. eco_cli pull → $ECO_FRAMEWORK via -d ──────────────────────────────────


def test_pull_gets_dev_flag_when_framework_set(monkeypatch):
    monkeypatch.setenv("ECO_FRAMEWORK", "/opt/acom-framework")
    args, note = _apply_framework_dev_target(["pull", "-c", "CID", "-v", "1", "-fid=F"])
    assert args[-2:] == ["-d", "/opt/acom-framework"]
    assert "ECO_FRAMEWORK" in note


def test_pull_respects_explicit_dev_flag(monkeypatch):
    monkeypatch.setenv("ECO_FRAMEWORK", "/opt/acom-framework")
    original = ["pull", "-c", "CID", "-d", "/custom"]
    args, note = _apply_framework_dev_target(list(original))
    assert args == original
    assert note == ""


def test_find_untouched_by_dev_flag(monkeypatch):
    monkeypatch.setenv("ECO_FRAMEWORK", "/opt/acom-framework")
    args, note = _apply_framework_dev_target(["find", "-p"])
    assert args == ["find", "-p"]
    assert note == ""


def test_pull_without_framework_env(monkeypatch):
    monkeypatch.delenv("ECO_FRAMEWORK", raising=False)
    original = ["pull", "-c", "CID"]
    args, note = _apply_framework_dev_target(list(original))
    assert args == original
    assert note == ""


# ── 5. RAG ingest understands the DK layout ──────────────────────────────────


def test_ingest_walk_normalizes_dk_component_names(tmp_path):
    dk = tmp_path / "Eco.Core1_DK_v.1.0.1.2" / "Eco.Core1" / "SharedFiles"
    dk.mkdir(parents=True)
    header = dk / "IEcoBase1.h"
    header.write_text("int16_t f(void);", encoding="utf-8")
    # Non-DK dir keeps its plain name.
    plain = tmp_path / "Eco.Math.C89" / "SharedFiles"
    plain.mkdir(parents=True)
    (plain / "IEcoMathC89.h").write_text("int16_t m(void);", encoding="utf-8")

    pairs = {
        component: (path, rel_base)
        for component, path, rel_base in _iter_source_files(tmp_path)
    }
    core1_header, core1_base = pairs["Eco.Core1"]
    assert core1_header == header
    # Relative paths must be anchored inside <DK>/<Component>/, not the DK dir.
    assert core1_header.relative_to(core1_base).as_posix() == "SharedFiles/IEcoBase1.h"
    assert "Eco.Math.C89" in pairs
