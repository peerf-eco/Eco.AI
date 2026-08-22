import os
import pytest
from pathlib import Path
from agent.internal.tools.common import (
    is_valid_cid, is_valid_version, ensure_inside, resolve_inside,
)


@pytest.mark.parametrize("cid,ok", [
    ("0123456789ABCDEF0123456789ABCDEF", True),
    ("0123456789abcdef0123456789abcdef", False),    # lowercase not allowed
    ("0123456789ABCDEF0123456789ABCDE",  False),    # 31 chars
    ("0123456789ABCDEF0123456789ABCDEFA", False),   # 33 chars
    ("0123456789ABCDEF0123456789ABCDEG", False),    # G is not hex
    ("",                                  False),
])
def test_is_valid_cid(cid, ok):
    assert is_valid_cid(cid) is ok


@pytest.mark.parametrize("v,ok", [
    ("1.0.1.2",  True),
    ("0.0.0.0",  True),
    ("10.20.30.40", True),
    ("1.0.1",    False),
    ("1.0.1.2.3", False),
    ("a.b.c.d",  False),
    ("",         False),
])
def test_is_valid_version(v, ok):
    assert is_valid_version(v) is ok


def test_ensure_inside_accepts_child(tmp_path):
    parent = tmp_path / "proj"
    parent.mkdir()
    child = parent / "src" / "main.c"
    assert ensure_inside(parent, child) is True


def test_ensure_inside_rejects_traversal(tmp_path):
    parent = tmp_path / "proj"
    parent.mkdir()
    outside = tmp_path / "other.c"
    assert ensure_inside(parent, outside) is False


def test_ensure_inside_rejects_dotdot_escape(tmp_path):
    parent = tmp_path / "proj"
    parent.mkdir()
    sneaky = parent / "src" / ".." / ".." / "other.c"
    assert ensure_inside(parent, sneaky) is False


# ── resolve_inside — covers the dual-resolve UX fix ─────────────────────────
def test_resolve_inside_passes_absolute_through(tmp_path):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    abs_path = project_dir / "main.c"
    # Absolute paths are returned unchanged; ensure_inside is the gate.
    assert resolve_inside(project_dir, str(abs_path)) == abs_path


def test_resolve_inside_anchors_relative_at_project_dir(tmp_path, monkeypatch):
    """Bare 'Eco.Math.C89' should resolve to project_dir/Eco.Math.C89 even when
    CWD is somewhere unrelated. This is the new UX the prompts teach."""
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    # Move CWD somewhere project_dir is NOT under
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    result = resolve_inside(project_dir, "Eco.Math.C89")
    assert result == project_dir / "Eco.Math.C89"


def test_resolve_inside_backwards_compat_cwd_relative(tmp_path, monkeypatch):
    """If the caller passes a CWD-relative path that already lands inside
    project_dir (legacy 'output/chat-XXX/Eco.Math.C89' style), keep it as-is."""
    cwd_root = tmp_path
    project_dir = cwd_root / "output" / "chat-XXX"
    project_dir.mkdir(parents=True)
    monkeypatch.chdir(cwd_root)
    # "output/chat-XXX/Eco.Math.C89" is CWD-relative AND inside project_dir
    result = resolve_inside(project_dir, "output/chat-XXX/Eco.Math.C89")
    # Should NOT be double-prefixed to project_dir/output/chat-XXX/...
    assert result == cwd_root / "output/chat-XXX/Eco.Math.C89"


def test_resolve_inside_dot_resolves_to_project_dir(tmp_path, monkeypatch):
    """'.' from a CWD that is not project_dir should anchor at project_dir,
    not return the unrelated CWD itself (which would then fail ensure_inside)."""
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    result = resolve_inside(project_dir, ".")
    # project_dir / "." resolves to project_dir; ensure_inside then passes.
    assert ensure_inside(project_dir, result) is True

