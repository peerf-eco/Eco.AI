"""
EcoOS Coder Sub-Agent (V4)

Autonomous component developer. Works in an isolated directory,
loads skill templates, writes EcoOS component files, compiles, and tests.

Created as a sub-agent by the Architect via spawn_coder tool.
"""

import os
import sys
import uuid
import subprocess
import logging
from pathlib import Path

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from .prompts_v4 import CODER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent / "skills"
BASE_DIR = Path(__file__).parent.parent


def create_coder_agent(llm, work_dir: str):
    """Create a Coder sub-agent that works in an isolated directory.

    Args:
        llm: LLM instance to use for reasoning
        work_dir: Absolute path to the component working directory
    """

    work_path = Path(work_dir)

    @tool
    def load_skill(language: str) -> str:
        """Load component development templates/skill for a programming language.

        Args:
            language: "c", "cpp", or "asm"
        """
        skill_file = SKILLS_DIR / f"{language}.md"
        if not skill_file.exists():
            available = [f.stem for f in SKILLS_DIR.glob("*.md")]
            return f"ERROR: No skill file for language '{language}'. Available: {available}"
        content = skill_file.read_text(encoding="utf-8")
        logger.info(f"[CODER] Loaded skill: {language} ({len(content)} chars)")
        return content

    @tool
    def write_file(relative_path: str, content: str) -> str:
        """Write a file in the component working directory.

        Args:
            relative_path: Path relative to work_dir, e.g. "SharedFiles/IEcoMyComponent.h"
            content: File content
        """
        target = work_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info(f"[CODER] Wrote: {target}")
        return f"OK: Written {relative_path} ({len(content)} bytes)"

    @tool
    def read_file(relative_path: str) -> str:
        """Read a file from the working directory or dependencies.

        Args:
            relative_path: Path relative to work_dir
        """
        target = work_path / relative_path
        if not target.exists():
            return f"ERROR: File not found: {relative_path}"
        return target.read_text(encoding="utf-8")

    @tool
    def list_files() -> str:
        """List all files in the component working directory."""
        files = []
        for f in sorted(work_path.rglob("*")):
            if f.is_file():
                rel = f.relative_to(work_path)
                files.append(f"  {rel} ({f.stat().st_size} bytes)")
        if not files:
            return "Working directory is empty."
        return f"Files in {work_path.name}:\n" + "\n".join(files)

    @tool
    def generate_guid() -> str:
        """Generate a random GUID for use as CID or IID.

        Returns a 32-char uppercase hex string (EcoOS UGUID format).
        """
        guid = uuid.uuid4().hex.upper()
        return (
            f"GUID: {guid}\n"
            f"Formatted: {{0x{guid[:8]}, 0x{guid[8:12]}, 0x{guid[12:16]}, "
            f"{{0x{guid[16:18]}, 0x{guid[18:20]}, 0x{guid[20:22]}, "
            f"0x{guid[22:24]}, 0x{guid[24:26]}, 0x{guid[26:28]}, "
            f"0x{guid[28:30]}, 0x{guid[30:32]}}}}}"
        )

    @tool
    def compile_component() -> str:
        """Compile the component sources into a static library (.lib or .a).

        Compiles all .c files in SourceFiles/ and archives into a library
        in BuildFiles/.
        """
        source_dir = work_path / "SourceFiles"
        if not source_dir.exists():
            return "ERROR: SourceFiles/ directory not found"

        c_files = list(source_dir.glob("*.c"))
        if not c_files:
            return "ERROR: No .c files in SourceFiles/"

        is_linux = sys.platform.startswith("linux")
        include_dirs = [
            str(work_path / "SharedFiles"),
            str(work_path / "HeaderFiles"),
        ]
        # Add framework headers from sibling DependenciesFiles
        deps_dir = work_path.parent
        for dep in deps_dir.iterdir():
            if dep.is_dir() and dep != work_path:
                shared = dep / "SharedFiles"
                if shared.exists():
                    include_dirs.append(str(shared))

        try:
            if is_linux:
                return _compile_linux(c_files, include_dirs, work_path)
            else:
                return _compile_windows(c_files, include_dirs, work_path)
        except Exception as e:
            return f"ERROR: Compilation failed: {e}"

    @tool
    def test_component() -> str:
        """Run a basic integration test for the component.

        Checks if the compiled library exists. Full integration testing
        happens during the final project build.
        """
        build_dir = work_path / "BuildFiles"
        libs = list(build_dir.rglob("*.lib")) + list(build_dir.rglob("*.a")) if build_dir.exists() else []
        if not libs:
            return "ERROR: No compiled library found. Run compile_component first."

        lib_sizes = ", ".join(f"{l.name} ({l.stat().st_size} bytes)" for l in libs)
        return f"OK: Component library exists: {lib_sizes}. Full integration test during final build."

    # --- Create the agent ---
    coder_tools = [
        load_skill, write_file, read_file, list_files,
        generate_guid, compile_component, test_component,
    ]

    prompt = CODER_SYSTEM_PROMPT.format(work_dir=work_dir)

    agent = create_react_agent(
        llm,
        tools=coder_tools,
        prompt=prompt,
    )

    return agent


_SHELL_METACHARS = (";", "|", "&", "$", "`", "\n", "\r", ">", "<")


def _reject_unsafe(*values: str) -> str | None:
    """Refuse paths/names containing shell metacharacters.

    LLM-controlled values (component names, work_dir) flow into compile commands.
    Without this guard a crafted name like 'foo;rm -rf /' would inject.
    """
    for v in values:
        s = str(v)
        for meta in _SHELL_METACHARS:
            if meta in s:
                return f"ERROR: Unsafe shell metacharacter {meta!r} in argument: {s!r}"
    return None


def _compile_windows(c_files, include_dirs, work_path):
    """Compile .c files into .lib on Windows using MSVC."""
    build_dir = work_path / "BuildFiles" / "Windows" / "amd64" / "StaticRelease"
    build_dir.mkdir(parents=True, exist_ok=True)

    obj_dir = work_path / "SourceFiles"
    lib_name = work_path.name.replace(".", "") + ".lib"
    lib_path = build_dir / lib_name

    unsafe = _reject_unsafe(work_path, build_dir, obj_dir, lib_name, *include_dirs, *c_files)
    if unsafe:
        return unsafe

    vcvarsall = None
    for year in ["2022", "2019"]:
        for ed in ["Community", "Professional", "Enterprise", "BuildTools"]:
            p = Path(f"C:/Program Files/Microsoft Visual Studio/{year}/{ed}/VC/Auxiliary/Build/vcvarsall.bat")
            if p.exists():
                vcvarsall = str(p)
                break
        if vcvarsall:
            break

    if not vcvarsall:
        return "ERROR: vcvarsall.bat not found"

    inc_flags = " ".join(f'/I "{d}"' for d in include_dirs)
    c_file_list = " ".join(f'"{f}"' for f in c_files)

    bat_content = (
        "@echo off\r\n"
        f'call "{vcvarsall}" x64 >nul 2>&1\r\n'
        f'cd /d "{obj_dir}"\r\n'
        f'cl {inc_flags} /O2 /W3 /DECO_LIB /DECO_WIN64 /DECO_X86_64 '
        f'/DUGUID_UTILITY /DECO_SIZE_T_DEFINED /DECO_WINDOWS '
        f'/D_CRT_SECURE_NO_WARNINGS /c {c_file_list}\r\n'
        f'if errorlevel 1 exit /b 1\r\n'
        f'lib /OUT:"{lib_path}" "{obj_dir}\\*.obj"\r\n'
    )
    bat_path = work_path / "_compile.bat"
    bat_path.write_text(bat_content, encoding="utf-8")

    env = os.environ.copy()
    env["MSYS_NO_PATHCONV"] = "1"
    env["MSYS2_ARG_CONV_EXCL"] = "*"

    result = subprocess.run(
        ["cmd.exe", "/c", str(bat_path)],
        capture_output=True, text=True,
        timeout=60, shell=False, env=env,
    )

    output = f"{result.stdout}\n{result.stderr}".strip()
    if result.returncode == 0:
        return f"OK: Library built: {lib_path}\n{output[-500:]}"
    return f"ERROR: Compile failed (exit {result.returncode}):\n{output[:2000]}"


def _compile_linux(c_files, include_dirs, work_path):
    """Compile .c files into .a on Linux using gcc."""
    build_dir = work_path / "BuildFiles" / "Linux" / "x86_64" / "StaticRelease"
    build_dir.mkdir(parents=True, exist_ok=True)

    src_dir = work_path / "SourceFiles"
    lib_name = "lib" + work_path.name.replace(".", "") + ".a"
    lib_path = build_dir / lib_name

    unsafe = _reject_unsafe(work_path, build_dir, src_dir, lib_name, *include_dirs, *c_files)
    if unsafe:
        return unsafe

    gcc_argv = ["gcc"]
    for d in include_dirs:
        gcc_argv += ["-I", str(d)]
    gcc_argv += [
        "-Wall", "-O2",
        "-DLINUX", "-DECO_LINUX", "-DECO_X86_64",
        "-DUGUID_UTILITY", "-DECO_LIB",
        "-c",
    ]
    gcc_argv += [str(f) for f in c_files]

    compile_result = subprocess.run(
        gcc_argv, capture_output=True, text=True,
        timeout=60, shell=False, cwd=str(src_dir),
    )
    if compile_result.returncode != 0:
        out = f"{compile_result.stdout}\n{compile_result.stderr}".strip()
        return f"ERROR: gcc failed (exit {compile_result.returncode}):\n{out[:2000]}"

    obj_files = sorted(p.name for p in src_dir.glob("*.o"))
    if not obj_files:
        return "ERROR: gcc produced no .o files"

    ar_argv = ["ar", "rcs", str(lib_path)] + obj_files
    ar_result = subprocess.run(
        ar_argv, capture_output=True, text=True,
        timeout=60, shell=False, cwd=str(src_dir),
    )
    out = f"{ar_result.stdout}\n{ar_result.stderr}".strip()
    if ar_result.returncode == 0:
        return f"OK: Library built: {lib_path}\n{out[-500:]}"
    return f"ERROR: ar failed (exit {ar_result.returncode}):\n{out[:2000]}"


def build_coder_tools_v5(work_dir: str):
    """V5 Coder toolset: existing file ops + download_component + done handoff."""
    from langgraph.types import Command
    from .tools import download_component

    work_path = Path(work_dir)

    @tool
    def write_file(relative_path: str, content: str) -> str:
        """Write a file relative to the project working directory."""
        target = work_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: Written {relative_path} ({len(content)} bytes)"

    @tool
    def read_file(relative_path: str) -> str:
        """Read a file relative to the project working directory."""
        target = work_path / relative_path
        if not target.exists():
            return f"ERROR: File not found: {relative_path}"
        return target.read_text(encoding="utf-8")

    @tool
    def list_files() -> str:
        """List all files under the project working directory."""
        if not work_path.exists():
            return "(empty)"
        return "\n".join(sorted(str(p.relative_to(work_path)) for p in work_path.rglob("*") if p.is_file()))

    @tool
    def load_skill(language: str) -> str:
        """Load component-development templates for a language ('c', 'cpp', 'asm')."""
        skill_file = SKILLS_DIR / f"{language}.md"
        if not skill_file.exists():
            available = [f.stem for f in SKILLS_DIR.glob("*.md")]
            return f"ERROR: No skill for '{language}'. Available: {available}"
        return skill_file.read_text(encoding="utf-8")

    @tool
    def done(summary_md: str) -> Command:
        """HANDOFF: all files written. Pass a Markdown summary of what was done."""
        return Command(update={"coder_summary_md": summary_md, "phase": "executing"})

    return [write_file, read_file, list_files, load_skill, download_component, done]


CODER_SYSTEM_PROMPT_V5 = """\
You are the EcoOS Coder. You receive an approved PRD and must produce all the
files for the project: download SDK components listed under source: sdk or
marketplace, write custom components from scratch (source: develop), and write
the EcoMain.c that wires them together.

Tools:
- write_file(path, content)
- read_file(path)
- list_files()
- load_skill(language)        — load C/C++ component templates BEFORE writing custom components.
- download_component(name)    — pull from marketplace into DependenciesFiles/.
- done(summary_md)            — HANDOFF when all files are in place. List what
                                 you wrote/modified.

If feedback is provided (retry loop), focus your edits on the listed files and
errors. Do not redo work that succeeded.

Always reply in the user's language for any human-facing summary.
"""


def create_coder_node_v5(llm):
    """V5 Coder node — receives plan_md (and feedback_md on retries) via system prompt."""
    from langgraph.prebuilt import create_react_agent

    def coder_node(state):
        work_dir = state.get("project_dir") or "output/_v5_default"
        Path(work_dir).mkdir(parents=True, exist_ok=True)

        tools = build_coder_tools_v5(work_dir)
        ctx_lines = [CODER_SYSTEM_PROMPT_V5, "", "## Approved Plan", state["plan_md"]]
        if state.get("feedback_md"):
            ctx_lines += ["", "## Previous build/test feedback (you must address these)", state["feedback_md"]]
        prompt = "\n".join(ctx_lines)

        react = create_react_agent(llm, tools=tools, prompt=prompt)
        seed = state["coder_messages"] or [{"role": "user", "content": "Implement the plan above."}]
        result = react.invoke({"messages": seed})
        new_msgs = result["messages"][len(seed):]
        return {"coder_messages": new_msgs}

    return coder_node
