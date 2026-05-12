from pathlib import Path
from agent.v6.tools.coder import (
    make_coder_tools, WriteFileArgs, EditFileArgs, ReadFileArgs, GlobArgs, GrepArgs,
)


def _tool(tools, name):
    return next(t for t in tools if t.name == name)


def test_write_file_creates_file(project_dir):
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "write_file").execute(WriteFileArgs(path=str(project_dir / "EcoMain.c"),
                                                          content="int main(){}"))
    assert not r.is_error
    assert (project_dir / "EcoMain.c").read_text() == "int main(){}"


def test_write_file_rejects_outside(project_dir, tmp_path):
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "write_file").execute(WriteFileArgs(path=str(tmp_path / "evil.c"),
                                                          content="x"))
    assert r.is_error


def test_edit_file_replaces_substring(project_dir):
    f = project_dir / "x.c"
    f.write_text("hello world")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "edit_file").execute(EditFileArgs(path=str(f),
                                                        old="world", new="EcoOS"))
    assert not r.is_error
    assert f.read_text() == "hello EcoOS"


def test_edit_file_old_not_found(project_dir):
    f = project_dir / "x.c"
    f.write_text("hello")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "edit_file").execute(EditFileArgs(path=str(f),
                                                        old="missing", new="x"))
    assert r.is_error
    assert "not found" in r.content.lower()


def test_read_file_can_read_downloaded_paths(project_dir, tmp_path):
    sdk = tmp_path / "sdk_component"
    sdk.mkdir()
    (sdk / "header.h").write_text("/* sdk */")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[sdk])
    r = _tool(tools, "read_file").execute(ReadFileArgs(path=str(sdk / "header.h")))
    assert not r.is_error
    assert "sdk" in r.content


def test_glob_under_project_dir(project_dir):
    (project_dir / "a.c").write_text("")
    (project_dir / "b.c").write_text("")
    (project_dir / "x.h").write_text("")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "glob").execute(GlobArgs(pattern="*.c"))
    assert not r.is_error
    assert "a.c" in r.content and "b.c" in r.content


def test_grep_finds_match(project_dir):
    (project_dir / "f.c").write_text("int main() { return 0; }")
    tools = make_coder_tools(project_dir=project_dir, downloaded_paths=[])
    r = _tool(tools, "grep").execute(GrepArgs(pattern="main", path=str(project_dir)))
    assert not r.is_error
    assert "f.c" in r.content
