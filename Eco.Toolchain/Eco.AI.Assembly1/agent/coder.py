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


def _compile_windows(c_files, include_dirs, work_path):
    """Compile .c files into .lib on Windows using MSVC."""
    build_dir = work_path / "BuildFiles" / "Windows" / "amd64" / "StaticRelease"
    build_dir.mkdir(parents=True, exist_ok=True)

    inc_flags = " ".join(f'/I "{d}"' for d in include_dirs)
    c_file_list = " ".join(f'"{f}"' for f in c_files)
    obj_dir = work_path / "SourceFiles"

    # Find vcvarsall
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

    # Compile + archive
    compile_cmd = (
        f'cl {inc_flags} /O2 /W3 /DECO_LIB /DECO_WIN64 /DECO_X86_64 '
        f'/DUGUID_UTILITY /DECO_SIZE_T_DEFINED /DECO_WINDOWS '
        f'/D_CRT_SECURE_NO_WARNINGS /c {c_file_list}'
    )
    lib_name = work_path.name.replace(".", "") + ".lib"
    lib_cmd = f'lib /OUT:"{build_dir / lib_name}" "{obj_dir}\\*.obj"'

    full_cmd = (
        f'call "{vcvarsall}" x64 >nul 2>&1 && '
        f'cd /d "{obj_dir}" && {compile_cmd} && {lib_cmd}'
    )

    env = os.environ.copy()
    env["MSYS_NO_PATHCONV"] = "1"
    env["MSYS2_ARG_CONV_EXCL"] = "*"

    result = subprocess.run(
        full_cmd, capture_output=True, text=True,
        timeout=60, shell=True, env=env,
    )

    output = f"{result.stdout}\n{result.stderr}".strip()
    if result.returncode == 0:
        return f"OK: Library built: {build_dir / lib_name}\n{output[-500:]}"
    return f"ERROR: Compile failed (exit {result.returncode}):\n{output[:2000]}"


def _compile_linux(c_files, include_dirs, work_path):
    """Compile .c files into .a on Linux using gcc."""
    build_dir = work_path / "BuildFiles" / "Linux" / "x86_64" / "StaticRelease"
    build_dir.mkdir(parents=True, exist_ok=True)

    inc_flags = " ".join(f'-I "{d}"' for d in include_dirs)
    c_file_list = " ".join(str(f) for f in c_files)

    lib_name = "lib" + work_path.name.replace(".", "") + ".a"

    compile_cmd = (
        f'gcc {inc_flags} -Wall -O2 -DLINUX -DECO_LINUX -DECO_X86_64 '
        f'-DUGUID_UTILITY -DECO_LIB -c {c_file_list}'
    )
    ar_cmd = f'ar rcs "{build_dir / lib_name}" *.o'

    full_cmd = f'cd "{work_path / "SourceFiles"}" && {compile_cmd} && {ar_cmd}'

    result = subprocess.run(
        full_cmd, capture_output=True, text=True,
        timeout=60, shell=True,
    )

    output = f"{result.stdout}\n{result.stderr}".strip()
    if result.returncode == 0:
        return f"OK: Library built: {build_dir / lib_name}\n{output[-500:]}"
    return f"ERROR: Compile failed (exit {result.returncode}):\n{output[:2000]}"
