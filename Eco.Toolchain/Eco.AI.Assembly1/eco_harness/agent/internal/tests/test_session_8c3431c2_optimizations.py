"""Regression tests for the session 8c3431c2 optimization batch.

Covers: eco_wizard result-contract scan (entry file + build subdir + stray
flag-dir detection) and the code_search 0-match hint.
"""
from pathlib import Path

from eco_harness.agent.internal.tools.eco_wizard import _scan_generated_tree
from eco_harness.agent.internal.tools.code_search import _zero_match_hint


def _mk(path: Path, rel: str, content: str = "") -> None:
    p = path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_scan_reports_entry_file_and_build_subdir(tmp_path: Path):
    """The wizard names the entry file SourceFiles/<Name>.c (with EcoMain
    inside), NOT EcoMain.c — the scan must surface that exact file."""
    _mk(tmp_path, "SourceFiles/Eco.TrigTable.c", "int16_t EcoMain(IEcoUnknown* pIUnk) {}")
    _mk(tmp_path, "AssemblyFiles/Linux/gcc_v132/Makefile", "all:\n")
    _mk(tmp_path, "AssemblyFiles/Windows/MSVC_v140/MakefileExe", "# win")
    scan = _scan_generated_tree(tmp_path, tmp_path)
    assert scan["rel_root"] == "."
    assert scan["entry_file"] == "SourceFiles/Eco.TrigTable.c"
    # Makefile preferred over MakefileExe; Linux tree over the deepest dir.
    assert scan["build_subdir"] == "AssemblyFiles/Linux/gcc_v132"
    assert scan["stray_flagged_dirs"] == []


def test_scan_excludes_stray_flag_dirs_from_build_path(tmp_path: Path):
    """Known wizard bug: CLI flags leak as literal `--app/...` directories.
    Everything under them is flagged and excluded from the build-path
    answers, but still reported so the coder knows the artifact exists."""
    _mk(tmp_path, "--app/Eco.Toolchain/Eco.TrigTable/SourceFiles/Eco.TrigTable.c", "EcoMain")
    _mk(tmp_path, "--app/Eco.Toolchain/Eco.TrigTable/AssemblyFiles/Linux/gcc_v132/MakefileExe", "#")
    scan = _scan_generated_tree(tmp_path, tmp_path)
    assert scan["entry_file"] is None
    assert scan["build_subdir"] is None
    assert scan["files"] == []
    assert scan["stray_flagged_dirs"] == ["--app"]


def test_zero_match_hint_only_for_marketplace_root(tmp_path: Path):
    project = tmp_path / "proj"
    marketplace = tmp_path / "marketplace_cache"
    project.mkdir()
    marketplace.mkdir()
    # Marketplace-root miss → hint pointing at project_dir.
    hint = _zero_match_hint(marketplace, [project, marketplace])
    assert "path='.'" in hint
    assert str(project.resolve()) in hint
    # Project-root miss → no hint (there is nothing to retry).
    assert _zero_match_hint(project, [project, marketplace]) == ""
