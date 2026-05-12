import pytest
from pathlib import Path
from agent.v6.tools.common import (
    is_valid_cid, is_valid_version, ensure_inside,
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
