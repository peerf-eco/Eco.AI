"""
EcoOS Agent Tools — V3

Tools for the assembly-from-SDK-components workflow:
- rag_query: Planner tool to search ChromaDB for SDK components
- eco_cli_search: Search EcoOS marketplace for components
- eco_cli_pull: Download component from marketplace
- build_makefile: Build project via cl.exe + Makefile (no MSBuild!)
"""

import os
import re
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Base paths
BASE_DIR = Path(__file__).parent.parent
REPO_ROOT = BASE_DIR.parent.parent  # H:\ai-hse-diploma-agent
SOURCE_DIR = BASE_DIR / "source"
OUTPUT_DIR = BASE_DIR / "output"
ECO_CLI = REPO_ROOT / "eco.sli" / "eco-cli.exe"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: rag_query — Planner searches ChromaDB for SDK components
# ═══════════════════════════════════════════════════════════════════════════

@tool
def rag_query(query: str) -> str:
    """
    Search ChromaDB for EcoOS SDK components matching the query.

    Use this to find which SDK components are available for the user's request.
    Example queries:
    - "math operations pow sqrt sin cos"
    - "string manipulation copy compare"
    - "file I/O read write"
    - "logging"
    - "network socket TCP"

    Returns: component names, interfaces, methods, CIDs found in the SDK.
    """
    logger.info(f"[TOOL rag_query] query={query}")

    from .nodes.retrieve import get_vectorstore

    vectorstore = get_vectorstore()
    if not vectorstore:
        return "ERROR: ChromaDB not initialized. Run 'python scripts/init_rag.py' first."

    try:
        results = vectorstore.similarity_search(query, k=8)
    except Exception as e:
        logger.error(f"[TOOL rag_query] Search failed: {e}")
        return f"ERROR: Search failed: {e}"

    if not results:
        return "No results found. Try different search terms."

    # Format results for the Planner
    output_parts = []
    seen_components = set()

    for doc in results:
        component = doc.metadata.get("component", "unknown")
        file_name = doc.metadata.get("file_name", "unknown")
        content = doc.page_content[:1500]  # Truncate large chunks

        if component not in seen_components:
            seen_components.add(component)
            output_parts.append(
                f"=== Component: {component} | File: {file_name} ===\n{content}"
            )
        else:
            output_parts.append(
                f"--- {file_name} ---\n{content}"
            )

    result_text = "\n\n".join(output_parts)
    logger.info(f"[TOOL rag_query] Found {len(results)} results from {len(seen_components)} components")
    return result_text


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: eco_cli_search — Search marketplace
# ═══════════════════════════════════════════════════════════════════════════

@tool
def eco_cli_search(cid: str) -> str:
    """
    Search EcoOS marketplace for a component by CID (32-char hex UGUID).

    Use when a component is not found in the local SDK and you know its CID.

    Args:
        cid: Component UGUID (32 uppercase hex chars), e.g. "61C988E21B7041378C5BDAFBB68A3FA0"

    Returns: Marketplace component info (name, versions, files, dependencies).
    """
    logger.info(f"[TOOL eco_cli_search] cid={cid}")

    if not ECO_CLI.exists():
        return "ERROR: eco-cli.exe not found"

    env = os.environ.copy()
    token = os.getenv("ECO_API_TOKEN", "")
    if token:
        env["ECO_API_TOKEN"] = token

    try:
        result = subprocess.run(
            [str(ECO_CLI), "find", "-c", cid],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
            env=env,
        )
        output = result.stdout or result.stderr or "No output"
        logger.info(f"[TOOL eco_cli_search] returncode={result.returncode}")
        return output[:3000]
    except subprocess.TimeoutExpired:
        return "ERROR: eco-cli search timed out (30s)"
    except Exception as e:
        return f"ERROR: eco-cli failed: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: eco_cli_pull — Download component from marketplace
# ═══════════════════════════════════════════════════════════════════════════

@tool
def eco_cli_pull(cid: str, version: str = "latest") -> str:
    """
    Download a component from EcoOS marketplace.

    Args:
        cid: Component ID (GUID)
        version: Version to download (default: "latest")

    Returns: Download result or error message.
    """
    logger.info(f"[TOOL eco_cli_pull] cid={cid}, version={version}")

    if not ECO_CLI.exists():
        return "ERROR: eco-cli.exe not found"

    env = os.environ.copy()
    token = os.getenv("ECO_API_TOKEN", "")
    if token:
        env["ECO_API_TOKEN"] = token

    try:
        cmd = [str(ECO_CLI), "pull", "-c", cid, "-v", version, "-d"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
            env=env,
        )
        output = result.stdout or result.stderr or "No output"
        logger.info(f"[TOOL eco_cli_pull] returncode={result.returncode}")
        return output[:3000]
    except subprocess.TimeoutExpired:
        return "ERROR: eco-cli pull timed out (120s)"
    except Exception as e:
        return f"ERROR: eco-cli pull failed: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: build_makefile — Build via cl.exe + Makefile
# ═══════════════════════════════════════════════════════════════════════════

def _find_vcvarsall() -> Optional[str]:
    """Find vcvarsall.bat via MSVS_BT_ROOT or standard VS paths."""
    # Try MSVS_BT_ROOT env var first
    msvs_root = os.environ.get("MSVS_BT_ROOT")
    if msvs_root:
        vcvars = Path(msvs_root) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
        if vcvars.exists():
            return str(vcvars)

    # Standard Visual Studio paths
    for year in ["2022", "2019"]:
        for edition in ["Community", "Professional", "Enterprise", "BuildTools"]:
            vcvars = Path(f"C:/Program Files/Microsoft Visual Studio/{year}/{edition}/VC/Auxiliary/Build/vcvarsall.bat")
            if vcvars.exists():
                return str(vcvars)
            # x86 path
            vcvars = Path(f"C:/Program Files (x86)/Microsoft Visual Studio/{year}/{edition}/VC/Auxiliary/Build/vcvarsall.bat")
            if vcvars.exists():
                return str(vcvars)

    return None


def _find_make() -> str:
    """Find make executable."""
    if sys.platform.startswith("linux"):
        return "make"  # Always available via build-essential in Docker

    # Windows: try GNU make first (from Git for Windows, MSYS2, etc.)
    for make_name in ["make", "mingw32-make"]:
        try:
            result = subprocess.run(
                ["where", make_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return make_name
        except Exception:
            pass
    return "make"  # Default, hope it's in PATH


@tool
def build_makefile(project_dir: str) -> str:
    """
    Build EcoOS project using Makefile.

    On Windows: vcvarsall.bat x64 + make -f MakefileExe (cl.exe)
    On Linux:   make -f MakefileExe (gcc)

    Args:
        project_dir: Path to project directory (e.g. "output/EcoCalculator")

    Returns: "OK: Build succeeded: <exe_path>" or "ERROR: <compiler_output>"
    """
    logger.info(f"[TOOL build_makefile] project_dir={project_dir}")

    project_path = Path(project_dir)
    if not project_path.is_absolute():
        project_path = BASE_DIR / project_dir

    is_linux = sys.platform.startswith("linux")
    make_cmd = _find_make()

    if is_linux:
        return _build_linux(project_path, make_cmd)
    else:
        return _build_windows(project_path, make_cmd)


def _build_linux(project_path: Path, make_cmd: str) -> str:
    """Build on Linux using gcc via MakefileExe."""
    makefile_dir = project_path / "gcc_linux"

    if not makefile_dir.exists():
        return f"ERROR: gcc_linux directory not found in {project_path}"

    makefile_exe = makefile_dir / "MakefileExe"
    if not makefile_exe.exists():
        return f"ERROR: MakefileExe not found in {makefile_dir}"

    cmd = f"{make_cmd} -f MakefileExe"
    logger.info(f"[TOOL build_makefile] Linux build: {cmd} in {makefile_dir}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(makefile_dir),
            shell=True,
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        combined = f"{stdout}\n{stderr}".strip()

        if result.returncode == 0:
            # Find the built binary (no .exe extension on Linux)
            build_dir = project_path / "BuildFiles" / "Linux" / "x86_64" / "StaticRelease"
            if build_dir.exists():
                binaries = [f for f in build_dir.iterdir() if f.is_file() and not f.suffix]
                if binaries:
                    exe_path = binaries[0]
                    logger.info(f"[TOOL build_makefile] SUCCESS: {exe_path}")
                    return f"OK: Build succeeded: {exe_path}"
            return f"OK: Build succeeded (check BuildFiles/ for output).\n{combined[-500:]}"
        else:
            logger.error(f"[TOOL build_makefile] FAILED:\n{combined[:2000]}")
            return f"ERROR: Build failed (exit code {result.returncode}):\n{combined[:3000]}"

    except subprocess.TimeoutExpired:
        return "ERROR: Build timed out (120s)"
    except Exception as e:
        return f"ERROR: Build failed: {e}"


def _build_windows(project_path: Path, make_cmd: str) -> str:
    """Build on Windows using cl.exe via vcvarsall + MakefileExe."""
    makefile_dir = project_path / "MSVC_v140"

    if not makefile_dir.exists():
        return f"ERROR: MSVC_v140 directory not found in {project_path}"

    makefile_exe = makefile_dir / "MakefileExe"
    if not makefile_exe.exists():
        return f"ERROR: MakefileExe not found in {makefile_dir}"

    # Find vcvarsall.bat
    vcvarsall = _find_vcvarsall()
    if not vcvarsall:
        return "ERROR: vcvarsall.bat not found. Install Visual Studio Build Tools."

    # Build command: vcvarsall.bat + make
    # CRITICAL: Set MSYS_NO_PATHCONV to prevent Git Bash's sh.exe from
    # mangling /I, /D, /Fo and other cl.exe flags that start with /
    cmd = (
        f'set MSYS_NO_PATHCONV=1 && '
        f'set MSYS2_ARG_CONV_EXCL=* && '
        f'call "{vcvarsall}" x64 && '
        f'cd /d "{makefile_dir}" && '
        f'{make_cmd} -f MakefileExe TARGET=1 ARCH=x86_64 DEBUG=0'
    )

    logger.info(f"[TOOL build_makefile] Running: {cmd}")

    try:
        env = os.environ.copy()
        env["MSYS_NO_PATHCONV"] = "1"
        env["MSYS2_ARG_CONV_EXCL"] = "*"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(makefile_dir),
            env=env,
            shell=True,
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""
        combined = f"{stdout}\n{stderr}".strip()

        if result.returncode == 0:
            build_dir = project_path / "BuildFiles" / "Windows" / "amd64" / "StaticRelease"
            exe_files = list(build_dir.glob("*.exe")) if build_dir.exists() else []
            if exe_files:
                exe_path = exe_files[0]
                logger.info(f"[TOOL build_makefile] SUCCESS: {exe_path}")
                return f"OK: Build succeeded: {exe_path}"
            else:
                return f"OK: Build succeeded (check BuildFiles/ for output).\n{combined[-500:]}"
        else:
            logger.error(f"[TOOL build_makefile] FAILED:\n{combined[:2000]}")
            return f"ERROR: Build failed (exit code {result.returncode}):\n{combined[:3000]}"

    except subprocess.TimeoutExpired:
        return "ERROR: Build timed out (120s)"
    except Exception as e:
        return f"ERROR: Build failed: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# BUILD NODE (non-tool version for graph node use)
# ═══════════════════════════════════════════════════════════════════════════

def classify_build_error(output: str) -> str:
    """
    Classify build error type for routing.

    Returns: "compile", "link", "missing_component", or "none"
    """
    if not output:
        return "none"

    output_lower = output.lower()

    # Environment error — no compiler available
    if any(x in output_lower for x in ["vcvarsall", "install visual studio"]):
        return "compile"

    # Missing component — unresolved external symbol for factory function (MSVC or gcc)
    if "getiecocomponentfactoryptr_" in output_lower and (
        "unresolved" in output_lower or "lnk2019" in output_lower or "undefined reference" in output_lower
    ):
        return "missing_component"

    # MSVC link errors
    if any(x in output_lower for x in ["lnk2019", "lnk2001", "lnk1120", "lnk1104", "unresolved external"]):
        return "link"

    # GCC link errors
    if "undefined reference" in output_lower:
        return "link"
    if "cannot find -l" in output_lower:
        return "link"

    # MSVC compile errors
    if any(x in output_lower for x in ["error c", "fatal error", "syntax error", "undeclared identifier"]):
        return "compile"

    # GCC compile errors
    if re.search(r"error:", output_lower) and not "undefined reference" in output_lower:
        return "compile"
    if "fatal error:" in output_lower:
        return "compile"

    return "none"


def build_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build node — runs make on the generated project.

    Pure Python, no LLM. Classifies errors for routing.
    """
    print("[BUILD] Starting build...")

    project_dir = state.get("project_dir", "")
    iteration = state.get("iteration", 0)

    if not project_dir:
        return {
            "build_result": "ERROR: No project_dir in state",
            "is_success": False,
            "error_message": "No project directory specified",
            "error_type": "compile",
            "iteration": iteration + 1,
        }

    # Write EcoMain.c to project
    ecomain_content = state.get("ecomain_content", "")
    if ecomain_content:
        ecomain_path = Path(project_dir) / "SourceFiles" / "EcoMain.c"
        ecomain_path.parent.mkdir(parents=True, exist_ok=True)
        ecomain_path.write_text(ecomain_content, encoding="utf-8")
        print(f"[BUILD] Written EcoMain.c: {ecomain_path}")

    # Run build
    result = build_makefile.invoke({"project_dir": project_dir})

    is_success = result.startswith("OK:")
    error_type = "none" if is_success else classify_build_error(result)
    error_message = "" if is_success else result

    print(f"[BUILD] Result: {'SUCCESS' if is_success else 'FAILED'}")
    print(f"[BUILD] Error type: {error_type}")

    return {
        "build_result": result,
        "is_success": is_success,
        "error_message": error_message,
        "error_type": error_type,
        "iteration": iteration + 1,
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEST EXECUTOR — runs EXE with stdin and checks stdout
# ═══════════════════════════════════════════════════════════════════════════

import json

def run_tests(exe_path: str, test_cases_json: str) -> Dict[str, Any]:
    """
    Execute test cases against a built EXE.

    Args:
        exe_path: Path to the built .exe file
        test_cases_json: JSON string with {strategy, tests} structure

    Returns:
        Dict with {passed: bool, total: int, failed: int, results: [...]}
    """
    logger.info(f"[TEST RUNNER] exe_path={exe_path}")

    exe = Path(exe_path)
    if not exe.exists():
        return {
            "passed": False,
            "total": 0,
            "failed": 0,
            "results": [],
            "error": f"EXE not found: {exe_path}",
        }

    try:
        test_cases = json.loads(test_cases_json)
    except json.JSONDecodeError as e:
        return {
            "passed": False,
            "total": 0,
            "failed": 0,
            "results": [],
            "error": f"Invalid test JSON: {e}",
        }

    tests = test_cases.get("tests", [])
    strategy = test_cases.get("strategy", "stdin_stdout")

    if not tests:
        return {
            "passed": True,
            "total": 0,
            "failed": 0,
            "results": [],
            "error": "No tests defined",
        }

    results = []
    failed_count = 0

    for i, test in enumerate(tests):
        name = test.get("name", f"test_{i}")
        stdin_data = test.get("stdin", "")
        expect_contains = test.get("expect_contains", [])

        logger.info(f"[TEST RUNNER] Running test {i+1}/{len(tests)}: {name}")

        try:
            proc = subprocess.run(
                [str(exe)],
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(exe.parent),
            )

            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            combined_output = f"{stdout}\n{stderr}".strip()

            # Check expect_contains (case-insensitive)
            missing = []
            for expected in expect_contains:
                if expected.lower() not in combined_output.lower():
                    missing.append(expected)

            test_passed = len(missing) == 0

            if not test_passed:
                failed_count += 1

            test_result = {
                "name": name,
                "passed": test_passed,
                "stdin": stdin_data[:200],
                "stdout": combined_output[:1000],
                "exit_code": proc.returncode,
                "expected": expect_contains,
                "missing": missing,
            }

            results.append(test_result)
            logger.info(f"[TEST RUNNER]   {'PASS' if test_passed else 'FAIL'}: {name}")
            if missing:
                logger.info(f"[TEST RUNNER]   Missing: {missing}")

        except subprocess.TimeoutExpired:
            failed_count += 1
            results.append({
                "name": name,
                "passed": False,
                "stdin": stdin_data[:200],
                "stdout": "",
                "exit_code": -1,
                "expected": expect_contains,
                "missing": expect_contains,
                "error": "Timeout (10s)",
            })
            logger.warning(f"[TEST RUNNER]   TIMEOUT: {name}")

        except Exception as e:
            failed_count += 1
            results.append({
                "name": name,
                "passed": False,
                "stdin": stdin_data[:200],
                "stdout": "",
                "exit_code": -1,
                "expected": expect_contains,
                "missing": expect_contains,
                "error": str(e),
            })
            logger.error(f"[TEST RUNNER]   ERROR: {name}: {e}")

    all_passed = failed_count == 0

    logger.info(f"[TEST RUNNER] Done: {len(tests) - failed_count}/{len(tests)} passed")

    return {
        "passed": all_passed,
        "total": len(tests),
        "failed": failed_count,
        "results": results,
    }


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: list_all_components — Scan local source/ directory
# ═══════════════════════════════════════════════════════════════════════════

@tool
def list_all_components() -> str:
    """List all SDK components available locally in the source/ directory.

    Returns component names and whether they have Windows/Linux libraries.
    Use this to understand what's already available before searching RAG.
    """
    components = []
    if not SOURCE_DIR.exists():
        return "ERROR: source/ directory not found"

    for dk_dir in sorted(SOURCE_DIR.iterdir()):
        if not dk_dir.is_dir():
            continue
        name = dk_dir.name
        # Extract component name from DK pattern: Eco.Name_DK_v.X.X.X.X
        if "_DK_" in name:
            comp_name = name.split("_DK_")[0]
        elif name.startswith("Eco."):
            comp_name = name
        else:
            continue

        # Check for libraries
        has_win = any((dk_dir).rglob("*.lib"))
        has_linux = any((dk_dir).rglob("*.a"))
        platform = []
        if has_win: platform.append("Windows")
        if has_linux: platform.append("Linux")

        components.append(f"  {comp_name} [{', '.join(platform) or 'headers-only'}]")

    if not components:
        return "No components found in source/"

    return f"Available SDK components ({len(components)}):\n" + "\n".join(components)


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: download_component — Download by name from marketplace
# ═══════════════════════════════════════════════════════════════════════════

@tool
def download_component(component_name: str) -> str:
    """Download an EcoOS component from the marketplace by name.

    First searches the marketplace for the component, then downloads it.
    Use this when a component is not available locally but may exist
    in the EcoOS marketplace.

    Args:
        component_name: Component name, e.g. "Eco.Socket.P02"
    """
    logger.info(f"[TOOL download_component] name={component_name}")

    if not ECO_CLI.exists():
        return f"ERROR: eco-cli not found at {ECO_CLI}"

    env = os.environ.copy()
    token = os.getenv("ECO_API_TOKEN", "")
    if token:
        env["ECO_API_TOKEN"] = token

    # Step 1: Search by name to find CID
    try:
        search_result = subprocess.run(
            [str(ECO_CLI), "find", "-n", component_name],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT), env=env,
        )
        search_output = search_result.stdout or search_result.stderr or ""

        if search_result.returncode != 0 or "not found" in search_output.lower():
            return f"NOT_FOUND: Component '{component_name}' not found in marketplace"

        # Step 2: Pull the component
        pull_result = subprocess.run(
            [str(ECO_CLI), "pull", "-n", component_name, "-d"],
            capture_output=True, text=True, timeout=120,
            cwd=str(REPO_ROOT), env=env,
        )
        pull_output = pull_result.stdout or pull_result.stderr or ""

        if pull_result.returncode == 0:
            return f"OK: Downloaded {component_name}\n{pull_output[:500]}"
        else:
            return f"ERROR: Failed to download {component_name}\n{pull_output[:500]}"

    except subprocess.TimeoutExpired:
        return f"ERROR: Timeout downloading {component_name}"
    except Exception as e:
        return f"ERROR: {e}"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL COLLECTIONS
# ═══════════════════════════════════════════════════════════════════════════

# Tools for Planner (ReAct agent with RAG search)
PLANNER_TOOLS = [rag_query]

# Tools for Architect (V4)
ARCHITECT_TOOLS = [list_all_components, rag_query, download_component]

# Tools for future use (marketplace integration)
MARKETPLACE_TOOLS = [eco_cli_search, eco_cli_pull]

# Build tool (for QA / manual use)
BUILD_TOOLS = [build_makefile]
