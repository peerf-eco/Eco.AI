"""Tests for io.py — read_file / list_dir / write_file with sandbox enforcement."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.internal.tools.io import (
    make_read_tools,
    make_write_tools,
    _PathArgs,
    _WriteArgs,
    _READ_FILE_MAX_BYTES,
)


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


# ── read_file ──────────────────────────────────────────────────────────────
def test_read_file_happy_path(project_dir):
    (project_dir / "x.txt").write_text("hello")
    t = _tool(make_read_tools(project_dir), "read_file")
    r = t.execute(_PathArgs(path=str(project_dir / "x.txt")))
    assert not r.is_error
    assert r.content == "hello"


def test_read_file_rejects_outside_project_dir(project_dir, tmp_path):
    outside = tmp_path / "escape.txt"
    outside.write_text("secret")
    t = _tool(make_read_tools(project_dir), "read_file")
    r = t.execute(_PathArgs(path=str(outside)))
    assert r.is_error
    assert "outside project_dir" in r.content


def test_read_file_rejects_missing(project_dir):
    t = _tool(make_read_tools(project_dir), "read_file")
    r = t.execute(_PathArgs(path=str(project_dir / "nope.txt")))
    assert r.is_error
    assert "does not exist" in r.content


def test_read_file_rejects_directory(project_dir):
    (project_dir / "sub").mkdir()
    t = _tool(make_read_tools(project_dir), "read_file")
    r = t.execute(_PathArgs(path=str(project_dir / "sub")))
    assert r.is_error
    assert "not a regular file" in r.content


def test_read_file_rejects_oversize(project_dir):
    big = project_dir / "big.bin"
    big.write_bytes(b"x" * (_READ_FILE_MAX_BYTES + 1))
    t = _tool(make_read_tools(project_dir), "read_file")
    r = t.execute(_PathArgs(path=str(big)))
    assert r.is_error
    assert "exceeds limit" in r.content


# ── list_dir ───────────────────────────────────────────────────────────────
def test_list_dir_includes_trailing_slash_for_dirs(project_dir):
    (project_dir / "file.c").write_text("")
    (project_dir / "sub").mkdir()
    t = _tool(make_read_tools(project_dir), "list_dir")
    r = t.execute(_PathArgs(path=str(project_dir)))
    assert not r.is_error
    lines = r.content.splitlines()
    assert "file.c" in lines
    assert "sub/" in lines


def test_list_dir_empty(project_dir):
    t = _tool(make_read_tools(project_dir), "list_dir")
    r = t.execute(_PathArgs(path=str(project_dir)))
    assert not r.is_error
    assert r.content == "(empty)"


def test_list_dir_rejects_outside(project_dir, tmp_path):
    t = _tool(make_read_tools(project_dir), "list_dir")
    r = t.execute(_PathArgs(path=str(tmp_path / "elsewhere")))
    assert r.is_error
    assert "outside" in r.content


def test_list_dir_rejects_file(project_dir):
    (project_dir / "x.txt").write_text("")
    t = _tool(make_read_tools(project_dir), "list_dir")
    r = t.execute(_PathArgs(path=str(project_dir / "x.txt")))
    assert r.is_error
    assert "not a directory" in r.content


# ── write_file ─────────────────────────────────────────────────────────────
def test_write_file_creates_with_content(project_dir):
    t = _tool(make_write_tools(project_dir), "write_file")
    target = project_dir / "main.c"
    r = t.execute(_WriteArgs(path=str(target), content="int main(){return 0;}"))
    assert not r.is_error
    assert target.read_text() == "int main(){return 0;}"
    assert r.details["bytes"] == len("int main(){return 0;}")


def test_write_file_creates_parent_dirs(project_dir):
    t = _tool(make_write_tools(project_dir), "write_file")
    nested = project_dir / "src" / "deep" / "x.c"
    r = t.execute(_WriteArgs(path=str(nested), content="ok"))
    assert not r.is_error
    assert nested.read_text() == "ok"


def test_write_file_overwrites(project_dir):
    (project_dir / "x.c").write_text("old")
    t = _tool(make_write_tools(project_dir), "write_file")
    r = t.execute(_WriteArgs(path=str(project_dir / "x.c"), content="new"))
    assert not r.is_error
    assert (project_dir / "x.c").read_text() == "new"


def test_write_file_rejects_outside_project_dir(project_dir, tmp_path):
    t = _tool(make_write_tools(project_dir), "write_file")
    outside = tmp_path / "escape.c"
    r = t.execute(_WriteArgs(path=str(outside), content="x"))
    assert r.is_error
    assert "outside" in r.content
    assert not outside.exists()


# ── tool registry shape — load-bearing for tester capability gating ───────
def test_make_read_tools_returns_read_and_list_only():
    tools = make_read_tools(Path("/anywhere"))
    names = {t.name for t in tools}
    assert names == {"read_file", "list_dir"}
    # write_file MUST NOT appear in read tools — this is the structural
    # guarantee that prevents tester from modifying code/tests.


def test_make_write_tools_returns_write_only():
    tools = make_write_tools(Path("/anywhere"))
    names = {t.name for t in tools}
    assert names == {"write_file"}

