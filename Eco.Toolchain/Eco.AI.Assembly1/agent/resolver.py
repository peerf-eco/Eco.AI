"""
Resolver Node — Pure Python, no LLM.

Resolves component names from Planner into actual SDK paths, headers, and libs.
Creates project directory structure with DependenciesFiles, Makefiles, etc.

This is the most critical deterministic node in the V3 pipeline.
"""

import os
import re
import sys
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent.parent
SOURCE_DIR = BASE_DIR / "source"
OUTPUT_DIR = BASE_DIR / "output"

# Framework components that are ALWAYS required
FRAMEWORK_COMPONENTS = [
    "Eco.System1",
    "Eco.InterfaceBus1",
    "Eco.MemoryManager1",
    "Eco.Core1",
    "Eco.FileSystemManagement1",
]

# Known system lib GUIDs (architecture-dependent)
SYSTEM_LIBS = {
    "x86": "00000000000000000000000053595332.lib",    # SYS2
    "amd64": "00000000000000000000000053595333.lib",   # SYS3
}

# Linux system lib GUIDs (same GUIDs, no lib prefix / .a suffix for linking)
LINUX_SYSTEM_LIBS = {
    "x86_64": "00000000000000000000000053595333",  # SYS3
}

# Platform-specific Windows libs
WINDOWS_LIBS = [
    "kernel32.lib", "user32.lib", "gdi32.lib", "winspool.lib",
    "comdlg32.lib", "advapi32.lib", "shell32.lib", "ole32.lib",
    "oleaut32.lib", "uuid.lib", "odbc32.lib", "odbccp32.lib",
]

# Linux system libs (replace Windows libs)
LINUX_LIBS = ["-lc", "-lm", "-lgcc", "-ldl"]


def detect_platform() -> str:
    """Auto-detect build platform from sys.platform."""
    return "Linux" if sys.platform.startswith("linux") else "Windows"


# ═══════════════════════════════════════════════════════════════════════════
# DK PACKAGE SCANNER
# ═══════════════════════════════════════════════════════════════════════════

def find_dk_package(component_name: str, source_dir: Path = SOURCE_DIR) -> Optional[Path]:
    """
    Find the DK package directory for a component.

    Scans source/ for directories matching patterns:
    - Eco.ComponentName_DK_v.X.X.X.X/Eco.ComponentName/
    - Eco.ComponentName/ (for non-DK components like MemoryManager1)

    Returns the inner component directory (with SharedFiles, BuildFiles, etc.)
    """
    # Normalize: "Eco.Math.C89" -> search for "Eco.Math.C89_DK_v.*"
    # Also handle partial names like "Math.C89" -> "Eco.Math.C89"
    if not component_name.startswith("Eco."):
        component_name = f"Eco.{component_name}"

    # Strategy 1: Look for DK pattern
    for item in source_dir.iterdir():
        if not item.is_dir():
            continue
        dir_name = item.name

        # Match Eco.ComponentName_DK_v.X.X.X.X
        if dir_name.startswith(f"{component_name}_DK_v."):
            inner = item / component_name
            if inner.exists():
                logger.info(f"[RESOLVER] Found DK: {item.name} -> {inner}")
                return inner

    # Strategy 2: Direct directory (e.g. Eco.MemoryManager1/)
    direct = source_dir / component_name
    if direct.exists() and (direct / "SharedFiles").exists():
        logger.info(f"[RESOLVER] Found direct: {direct}")
        return direct

    # Strategy 3: Fuzzy match — search by substring
    for item in source_dir.iterdir():
        if not item.is_dir():
            continue
        # e.g. component_name="Eco.String1" should match "Eco.String1_DK_v..."
        # but NOT "Eco.String.C89_DK_v..."
        if item.name.startswith(component_name) and "_DK_v." in item.name:
            inner = item / component_name
            if inner.exists():
                logger.info(f"[RESOLVER] Found fuzzy DK: {item.name}")
                return inner

    logger.warning(f"[RESOLVER] Component not found locally: {component_name}")
    return None


def extract_cid_from_header(id_header_path: Path) -> Optional[str]:
    """
    Extract CID hex string from an IdEco*.h file.

    Parses lines like:
        extern IEcoComponentFactory* GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0;
    or CID comment like:
        /* EcoMathC89 CID = {61C988E2-1B70-4137-8C5B-DAFBB68A3FA0} */
    """
    try:
        content = id_header_path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return None

    # Try to extract from factory function name (most reliable)
    match = re.search(r'GetIEcoComponentFactoryPtr_([0-9A-Fa-f]{32})', content)
    if match:
        return match.group(1).upper()

    # Try CID comment
    match = re.search(r'CID\s*=\s*\{([0-9A-Fa-f-]+)\}', content)
    if match:
        return match.group(1).replace("-", "").upper()

    return None


def extract_iid_from_header(interface_header_path: Path) -> Optional[str]:
    """
    Extract IID hex string from an IEco*.h file.

    Parses IID definition like:
        static const UGUID IID_IEcoMathC89 = {0x01, 0x10, {0xEE, 0x82, ...}};
    """
    try:
        content = interface_header_path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return None

    # Match IID comment like: /* IEcoMathC89 IID = {EE823C32-2B86-470C-B4C9-D3760C0AF470} */
    match = re.search(r'IID\s*=\s*\{([0-9A-Fa-f-]+)\}', content)
    if match:
        return match.group(1).replace("-", "").upper()

    return None


def extract_interface_name(interface_header_path: Path) -> Optional[str]:
    """Extract interface name from IEco*.h, e.g. 'IEcoMathC89'."""
    name = interface_header_path.stem  # e.g. "IEcoMathC89"
    if name.startswith("IEco"):
        return name
    return None


def find_lib_file(component_dir: Path, arch: str = "amd64", platform: str = "Windows") -> Optional[Path]:
    """Find library file for the target platform."""
    if platform == "Linux":
        lib_dir = component_dir / "BuildFiles" / "Linux" / "x86_64" / "StaticRelease"
        if not lib_dir.exists():
            return None
        libs = list(lib_dir.glob("lib*.a"))
    else:
        lib_dir = component_dir / "BuildFiles" / "Windows" / arch / "StaticRelease"
        if not lib_dir.exists():
            return None
        libs = list(lib_dir.glob("*.lib"))

    if libs:
        return libs[0]
    return None


def resolve_single_component(
    component_name: str,
    source_dir: Path = SOURCE_DIR,
    arch: str = "amd64",
    is_framework: bool = False,
    platform: str = "Windows",
) -> Optional[Dict[str, Any]]:
    """
    Resolve a single component to its full metadata.

    Returns dict matching ResolvedComponent fields.
    """
    comp_dir = find_dk_package(component_name, source_dir)
    if comp_dir is None:
        return None

    shared_dir = comp_dir / "SharedFiles"
    if not shared_dir.exists():
        logger.warning(f"[RESOLVER] No SharedFiles for {component_name}")
        return None

    # Find headers
    headers = list(shared_dir.glob("*.h"))
    header_paths = [str(h) for h in headers]

    # Read header contents
    header_contents = {}
    for h in headers:
        try:
            header_contents[h.name] = h.read_text(encoding="utf-8-sig", errors="replace")
        except Exception:
            pass

    # Find IdEco*.h for CID
    id_headers = [h for h in headers if h.name.startswith("Id")]
    cid = ""
    factory_func = ""
    if id_headers:
        cid = extract_cid_from_header(id_headers[0]) or ""
        if cid:
            factory_func = f"GetIEcoComponentFactoryPtr_{cid}"

    # Find IEco*.h for IID (skip extensions like MemExt, FileExt)
    interface_headers = [
        h for h in headers
        if h.name.startswith("IEco")
        and not h.name.startswith("Id")
        and "Ext" not in h.name
        and h.name.endswith(".h")
    ]
    iid = ""
    interface_name = ""
    if interface_headers:
        iid = extract_iid_from_header(interface_headers[0]) or ""
        interface_name = extract_interface_name(interface_headers[0]) or ""

    # Find library file (platform-aware)
    lib_path_obj = find_lib_file(comp_dir, arch, platform)
    lib_path = str(lib_path_obj) if lib_path_obj else ""
    lib_filename = lib_path_obj.name if lib_path_obj else ""

    return {
        "name": component_name,
        "cid": cid,
        "iid": iid,
        "interface_name": interface_name,
        "factory_func": factory_func,
        "lib_path": lib_path,
        "lib_filename": lib_filename,
        "headers": header_paths,
        "header_contents": header_contents,
        "shared_dir": str(shared_dir),
        "dk_dir": str(comp_dir),
        "is_framework": is_framework,
    }


# ═══════════════════════════════════════════════════════════════════════════
# PROJECT STRUCTURE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def create_project_structure(
    project_name: str,
    resolved: List[Dict],
    framework: List[Dict],
    arch: str = "amd64",
    platform: str = "Windows",
) -> Path:
    """
    Create the project directory structure with DependenciesFiles.

    Structure (Windows):
        output/<ProjectName>/
        ├── SourceFiles/, HeaderFiles/, SharedFiles/
        ├── DependenciesFiles/<Component>/SharedFiles + BuildFiles
        ├── MSVC_v140/Makefile, MakefileExe
        └── BuildFiles/

    Structure (Linux):
        output/<ProjectName>/
        ├── SourceFiles/, HeaderFiles/, SharedFiles/
        ├── DependenciesFiles/<Component>/SharedFiles + BuildFiles
        ├── gcc_linux/MakefileExe
        └── BuildFiles/
    """
    project_dir = OUTPUT_DIR / project_name
    logger.info(f"[RESOLVER] Creating project: {project_dir} (platform={platform})")

    # Create directories
    (project_dir / "SourceFiles").mkdir(parents=True, exist_ok=True)
    (project_dir / "HeaderFiles").mkdir(parents=True, exist_ok=True)
    (project_dir / "SharedFiles").mkdir(parents=True, exist_ok=True)
    (project_dir / "BuildFiles").mkdir(parents=True, exist_ok=True)

    # Platform-specific build directory
    if platform == "Linux":
        (project_dir / "gcc_linux").mkdir(parents=True, exist_ok=True)
    else:
        (project_dir / "MSVC_v140").mkdir(parents=True, exist_ok=True)

    deps_dir = project_dir / "DependenciesFiles"
    deps_dir.mkdir(parents=True, exist_ok=True)

    # Copy dependency files from each resolved component
    all_components = framework + resolved
    for comp in all_components:
        comp_name = comp["name"]
        dep_dir = deps_dir / comp_name

        if dep_dir.exists():
            shutil.rmtree(dep_dir)

        dk_dir = Path(comp["dk_dir"])

        # Copy SharedFiles
        src_shared = dk_dir / "SharedFiles"
        if src_shared.exists():
            shutil.copytree(src_shared, dep_dir / "SharedFiles")
            logger.info(f"[RESOLVER] Copied SharedFiles: {comp_name}")

        # Copy BuildFiles (platform-specific)
        if platform == "Linux":
            src_build = dk_dir / "BuildFiles" / "Linux" / "x86_64" / "StaticRelease"
            if src_build.exists():
                dst_build = dep_dir / "BuildFiles" / "Linux" / "x86_64" / "StaticRelease"
                shutil.copytree(src_build, dst_build)
                logger.info(f"[RESOLVER] Copied Linux BuildFiles: {comp_name}")
        else:
            src_build = dk_dir / "BuildFiles" / "Windows" / arch / "StaticRelease"
            if src_build.exists():
                dst_build = dep_dir / "BuildFiles" / "Windows" / arch / "StaticRelease"
                shutil.copytree(src_build, dst_build)
                logger.info(f"[RESOLVER] Copied BuildFiles: {comp_name}")

    return project_dir


# ═══════════════════════════════════════════════════════════════════════════
# MAKEFILE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def _make_slash_path(rel_path: str) -> str:
    """Convert path to use $(SLASH) macro."""
    return rel_path.replace("/", "$(SLASH)")


# Relative path prefix from MSVC_v140/ to project root (1 level up)
_UP = "..$(SLASH)"


def generate_makefile(
    resolved: List[Dict],
    framework: List[Dict],
    project_name: str,
) -> str:
    """
    Generate Makefile for building the component .lib.

    Based on MSVC_v140/Makefile template.
    Builds SourceFiles/*.c into a static lib.
    """
    all_components = framework + resolved

    # INC paths — DependenciesFiles/<Component>/SharedFiles
    # Paths are relative to MSVC_v140/ dir (1 level below project root)
    inc_lines = []
    inc_lines.append(f'/I {_UP}HeaderFiles')
    inc_lines.append(f'/I {_UP}SharedFiles')
    for comp in all_components:
        name = comp["name"]
        inc_lines.append(
            f'/I "{_UP}DependenciesFiles$(SLASH){name}$(SLASH)SharedFiles"'
        )

    inc_str = " \\\n".join(inc_lines)

    # Source files
    src_str = f"{_UP}SourceFiles$(SLASH)EcoMain.c"

    # Determine a CID-based output name for the lib
    # Use first resolved (non-framework) component CID, or project-based hash
    out_target_lib = "EcoApp.lib"
    if resolved:
        first_cid = resolved[0].get("cid", "")
        if first_cid:
            out_target_lib = f"{first_cid}.lib"

    return f"""# Auto-generated Makefile for {project_name}
# Build static library from project sources

# Platform detection
PLATFORM = Windows

ifeq ($(OS), Windows_NT)
\tRM = -rm -f
\tSLASH = /
\tSWALLOW_OUTPUT = >nul 2>nul
\tFRAMEWORK := $(subst \\,/,$(ECO_FRAMEWORK))
else
\tRM = -rm -f
\tSLASH = /
\tSWALLOW_OUTPUT =
endif

# Target configuration
ifeq ($(TARGET), 1)
\tOUT_TARGET = {out_target_lib}
\tBASE_TARGET = Static
\tCCFLAGS_TARGET = /Gz /TC /W4 /D_CRT_SECURE_NO_WARNINGS
\tCCFLAGS_TARGET += /D__STDC_VERSION__=199901L /DUGUID_UTILITY /DECO_WINDOWS /DECO_LIB /DECO_SIZE_T_DEFINED
\tLDFLAGS_TARGET = /NOLOGO /SUBSYSTEM:CONSOLE /INCREMENTAL:NO
else
\tOUT_TARGET = {out_target_lib.replace('.lib', '.dll')}
\tBASE_TARGET = Dynamic
\tCCFLAGS_TARGET = /Gz /TC /W4 /D_CRT_SECURE_NO_WARNINGS
\tCCFLAGS_TARGET += /D__STDC_VERSION__=199901L /DUGUID_UTILITY /DECO_WINDOWS /DECO_DLL
\tLDFLAGS_TARGET = /NOLOGO /SUBSYSTEM:CONSOLE /INCREMENTAL:NO
endif

# Debug configuration
ifeq ($(DEBUG), 1)
\tCONFIG_TARGET = $(BASE_TARGET)Debug
\tCCFLAGS_TARGET += /D_DEBUG /Zi /Fd$(subst /,$(SLASH),$(OUT_DIR)/$(OUT_TARGET:.lib=.pdb))
\tifeq ($(TARGET), 1)
\t\tCCFLAGS_TARGET += /MTd
\tendif
else
\tCONFIG_TARGET = $(BASE_TARGET)Release
\tCCFLAGS_TARGET += /DNDEBUG /Z7
\tifeq ($(TARGET), 1)
\t\tCCFLAGS_TARGET += /MT
\tendif
\tLDFLAGS_TARGET += /DEBUG:NONE
endif

# Architecture
ifeq ($(ARCH), x86)
\tCCFLAGS_TARGET += /DECO_X86_32
\tLDFLAGS_TARGET += /MACHINE:X86
\tARCH_TARGET = x86
else ifeq ($(ARCH), x64)
\tCCFLAGS_TARGET += /DECO_X86_64
\tLDFLAGS_TARGET += /MACHINE:X64
\tARCH_TARGET = amd64
endif

# Include directories
INC = {inc_str}

# Source files
SRC = {src_str}

# Libraries
LIBS = "kernel32.lib" "user32.lib" "gdi32.lib" "winspool.lib" "comdlg32.lib" "advapi32.lib" "shell32.lib" "ole32.lib" "oleaut32.lib" "uuid.lib" "odbc32.lib" "odbccp32.lib"

# Object files
OBJ = $(SRC:.c=.o)

OUT = $(OUT_TARGET)
OUT_DIR = {_UP}BuildFiles$(SLASH)$(PLATFORM)$(SLASH)$(ARCH_TARGET)$(SLASH)$(CONFIG_TARGET)

CCFLAGS = $(CCFLAGS_TARGET)
LDFLAGS = $(LDFLAGS_TARGET)

CC = cl
LD = link
AR = lib

ifeq ($(TARGET), 1)
\tCMD_TARGET=$(AR) /OUT:$(OUT_DIR)$(SLASH)$(OUT) $(OBJ) $(LDFLAGS)
else
\tCMD_TARGET=$(LD) /DLL $(LIBS) /OUT:$(OUT_DIR)$(SLASH)$(OUT) $(OBJ) $(LDFLAGS)
endif

.SUFFIXES: .c

all: $(OUT)

.c.o:
\tmkdir -p "$(subst /,\\,$(OUT_DIR))"
\t$(CC) $(INC) $(CCFLAGS) /c $< /Fo$@

$(OUT): $(OBJ)
\t$(CMD_TARGET)
\t$(RM) $(OBJ)

clean:
\t$(RM) $(OBJ) $(OUT_DIR)$(SLASH)$(OUT) $(OUT_DIR)$(SLASH)*.pdb
"""


def generate_makefile_exe(
    resolved: List[Dict],
    framework: List[Dict],
    project_name: str,
    arch: str = "amd64",
) -> str:
    """
    Generate MakefileExe for building the final executable.

    Based on MSVC_v140/MakefileExe template.
    Links EcoMain.c with all component .lib files.
    """
    all_components = framework + resolved

    # INC paths — relative to MSVC_v140/ dir (1 level below project root)
    inc_lines = []
    inc_lines.append(f'/I {_UP}HeaderFiles')
    inc_lines.append(f'/I {_UP}SharedFiles')
    for comp in all_components:
        name = comp["name"]
        inc_lines.append(
            f'/I "{_UP}DependenciesFiles$(SLASH){name}$(SLASH)SharedFiles"'
        )
    inc_str = " \\\n".join(inc_lines)

    # LIB_DIR paths
    lib_dir_lines = []
    lib_dir_lines.append(
        f'/LIBPATH:"{_UP}BuildFiles$(SLASH)$(PLATFORM)$(SLASH)$(ARCH_TARGET)$(SLASH)$(CONFIG_TARGET)"'
    )
    for comp in all_components:
        name = comp["name"]
        if comp.get("lib_filename"):
            lib_dir_lines.append(
                f'/LIBPATH:"{_UP}DependenciesFiles$(SLASH){name}$(SLASH)BuildFiles$(SLASH)$(PLATFORM)$(SLASH)$(ARCH_TARGET)$(SLASH)StaticRelease"'
            )
    lib_dir_str = " \\\n".join(lib_dir_lines)

    # Component LIBS (deduplicated)
    seen_libs = set()
    component_libs = []
    for comp in all_components:
        lib = comp.get("lib_filename", "")
        if lib and lib not in seen_libs:
            seen_libs.add(lib)
            component_libs.append(f'"{lib}"')

    # System architecture lib (may already be included via System1)
    sys_lib = SYSTEM_LIBS.get(arch, SYSTEM_LIBS["amd64"])
    if sys_lib not in seen_libs:
        component_libs.append(f'"{sys_lib}"')

    component_libs_str = " ".join(component_libs)

    # Source files
    src_str = f"{_UP}SourceFiles$(SLASH)EcoMain.c"

    return f"""# Auto-generated MakefileExe for {project_name}
# Build executable from EcoMain.c + SDK component libs

# Platform detection
PLATFORM = Windows

ifeq ($(OS), Windows_NT)
\tRM = -rm -f
\tSLASH = /
\tSWALLOW_OUTPUT = >nul 2>nul
else
\tRM = -rm -f
\tSLASH = /
\tSWALLOW_OUTPUT =
endif

# Target configuration
ifeq ($(TARGET), 1)
\tOUT_TARGET = {project_name}
\tBASE_TARGET = Static
\tCCFLAGS_TARGET = /Gz /TC /W4 /D_CRT_SECURE_NO_WARNINGS
\tCCFLAGS_TARGET += /D__STDC_VERSION__=199901L /DUGUID_UTILITY /DECO_WINDOWS /DECO_LIB /DECO_SIZE_T_DEFINED
\tLDFLAGS_TARGET = /NOLOGO /SUBSYSTEM:CONSOLE /INCREMENTAL:NO
else
\tOUT_TARGET = {project_name}
\tBASE_TARGET = Dynamic
\tCCFLAGS_TARGET = /Gz /TC /W4 /D_CRT_SECURE_NO_WARNINGS
\tCCFLAGS_TARGET += /D__STDC_VERSION__=199901L /DUGUID_UTILITY /DECO_WINDOWS /DECO_DLL
\tLDFLAGS_TARGET = /NOLOGO /SUBSYSTEM:CONSOLE /INCREMENTAL:NO
endif

# Debug configuration
ifeq ($(DEBUG), 1)
\tCONFIG_TARGET = $(BASE_TARGET)Debug
\tCCFLAGS_TARGET += /Zi /Fd$(OUT_DIR)$(SLASH)$(OUT_TARGET:.exe=.pdb)
\tifeq ($(TARGET), 1)
\t\tCCFLAGS_TARGET += /MTd
\tendif
\tLDFLAGS_TARGET += /DEBUG /PDB:$(OUT_DIR)$(SLASH)$(OUT_TARGET:.exe=.pdb)
else
\tCONFIG_TARGET = $(BASE_TARGET)Release
\tCCFLAGS_TARGET += /Z7
\tifeq ($(TARGET), 1)
\t\tCCFLAGS_TARGET += /MT
\tendif
\tLDFLAGS_TARGET += /DEBUG:NONE
endif

# Architecture
ifeq ($(ARCH), x86)
\tCCFLAGS_TARGET += /DECO_X86_32
\tLDFLAGS_TARGET += /MACHINE:X86
\tARCH_TARGET = x86
else ifeq ($(ARCH), x86_64)
\tCCFLAGS_TARGET += /DECO_X86_64
\tLDFLAGS_TARGET += /MACHINE:X64
\tARCH_TARGET = amd64
endif

# Include directories
INC = {inc_str}

# Library directories
LIB_DIR = {lib_dir_str}

# Source files
SRC = {src_str}

# Libraries
LIBS = "kernel32.lib" "user32.lib" "gdi32.lib" "winspool.lib" "comdlg32.lib" "advapi32.lib" "shell32.lib" "ole32.lib" "oleaut32.lib" "uuid.lib" "odbc32.lib" "odbccp32.lib" "legacy_stdio_definitions.lib"
LIBS += {component_libs_str}

# Object files
OBJ = $(SRC:.c=.o)

OUT = $(OUT_TARGET)
OUT_DIR = {_UP}BuildFiles$(SLASH)$(PLATFORM)$(SLASH)$(ARCH_TARGET)$(SLASH)$(CONFIG_TARGET)

CCFLAGS = $(CCFLAGS_TARGET)
LDFLAGS = $(LDFLAGS_TARGET)

CC = cl
LD = cl
AR = lib

.SUFFIXES: .c

all: $(OUT)

.c.o:
\tmkdir -p "$(subst /,\\,$(OUT_DIR))"
\t$(CC) $(INC) $(CCFLAGS) /c $< /Fo$@

$(OUT): $(OBJ)
\t$(LD) $(OBJ) /link $(LIB_DIR) $(LIBS) $(LDFLAGS_TARGET) /OUT:$(OUT_DIR)/$(OUT).exe

clean:
\t$(RM) $(OBJ) $(OUT_DIR)$(SLASH)$(OUT) $(OUT_DIR)$(SLASH)*.pdb $(OUT_DIR)$(SLASH)*.ilk
"""


def generate_makefile_exe_linux(
    resolved: List[Dict],
    framework: List[Dict],
    project_name: str,
) -> str:
    """
    Generate MakefileExe for building on Linux with gcc.

    Based on source/Lessons/Lesson04 Makefile pattern.
    Paths are relative to gcc_linux/ (1 level below project root).
    """
    all_components = framework + resolved

    # INC paths — -I relative to gcc_linux/ dir
    inc_lines = []
    inc_lines.append("-I ../HeaderFiles")
    inc_lines.append("-I ../SharedFiles")
    for comp in all_components:
        name = comp["name"]
        inc_lines.append(f'-I "../DependenciesFiles/{name}/SharedFiles"')
    inc_str = " \\\n".join(inc_lines)

    # LIB_DIR paths — -L for each component with a lib
    lib_dir_lines = []
    for comp in all_components:
        name = comp["name"]
        if comp.get("lib_filename"):
            lib_dir_lines.append(
                f'-L"../DependenciesFiles/{name}/BuildFiles/Linux/x86_64/StaticRelease"'
            )
    lib_dir_str = " \\\n".join(lib_dir_lines) if lib_dir_lines else ""

    # Component libs: extract GUID from lib<GUID>.a -> -l<GUID>
    seen_libs = set()
    component_link_flags = []
    for comp in all_components:
        lib_name = comp.get("lib_filename", "")
        if not lib_name:
            continue
        # lib<GUID>.a -> <GUID>
        guid = lib_name
        if guid.startswith("lib"):
            guid = guid[3:]
        if guid.endswith(".a"):
            guid = guid[:-2]
        if guid and guid not in seen_libs:
            seen_libs.add(guid)
            component_link_flags.append(f"-l{guid}")

    # System lib (SYS3 for x86_64)
    sys_guid = LINUX_SYSTEM_LIBS.get("x86_64", "")
    if sys_guid and sys_guid not in seen_libs:
        component_link_flags.append(f"-l{sys_guid}")

    # Combine: SDK component libs FIRST, then system libs (GCC link order matters!)
    all_link_libs = " ".join(component_link_flags + LINUX_LIBS)

    return f"""# Auto-generated MakefileExe for {project_name} (Linux/gcc)
# Build executable from EcoMain.c + SDK component libs

# Source files
SRC = ../SourceFiles/EcoMain.c

# Include directories
INCLUDES = {inc_str}

# Library directories
LIB_DIR = {lib_dir_str}

OBJ = $(SRC:.c=.o)

OUT = {project_name}
OUT_DIR = ../BuildFiles/Linux/x86_64/StaticRelease

# Compiler flags
CCFLAGS = -Wall -O3 -g -DLINUX -DECO_LINUX -DECO_X86_64 -DUGUID_UTILITY -DECO_LIB -D__STDC_VERSION__=199901L

# Compiler
CC = gcc

# Library link flags
LIBS = $(LIB_DIR) {all_link_libs}

# Linker flags
LDFLAGS = -g $(LIBS)

.SUFFIXES: .c

.c.o:
\t$(CC) $(INCLUDES) $(CCFLAGS) -c $< -o $@

$(OUT): $(OBJ)
\tmkdir -p $(OUT_DIR)
\t$(CC) $(LDFLAGS) -o $(OUT_DIR)/$(OUT) $(OBJ) $(LDFLAGS)
\trm -f $(OBJ)

clean:
\trm -f $(OBJ) $(OUT_DIR)/$(OUT)
"""


# ═══════════════════════════════════════════════════════════════════════════
# RESOLVER NODE
# ═══════════════════════════════════════════════════════════════════════════

def resolver_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolver node — resolves component plan into actual SDK paths and project structure.

    Input (from state):
        - component_plan: {components: [{name, reason}], app_description, project_name}

    Output:
        - resolved_components, framework_components
        - include_dirs, lib_dirs, lib_files
        - makefile_content, makefile_exe_content
        - project_dir
        - missing_components
        - build_platform
    """
    logger.info("[RESOLVER] Starting component resolution...")

    component_plan = state.get("component_plan", {})
    planned_components = component_plan.get("components", [])
    project_name = component_plan.get("project_name", "EcoApp")
    arch = "amd64"  # Default to x64
    platform = detect_platform()

    logger.info(f"[RESOLVER] Project: {project_name}")
    logger.info(f"[RESOLVER] Platform: {platform}")
    logger.info(f"[RESOLVER] Planned components: {len(planned_components)}")

    # 1. Resolve framework components (always required)
    framework_resolved = []
    for fw_name in FRAMEWORK_COMPONENTS:
        result = resolve_single_component(fw_name, SOURCE_DIR, arch, is_framework=True, platform=platform)
        if result:
            framework_resolved.append(result)
            logger.info(f"[RESOLVER] Framework OK: {fw_name} (CID: {result['cid'][:8]}...)")
        else:
            logger.warning(f"[RESOLVER] Framework component not found: {fw_name}")

    # 2. Resolve user-requested components
    resolved = []
    missing = []
    for comp_info in planned_components:
        comp_name = comp_info.get("name", "")
        if not comp_name:
            continue

        # Skip if it's already a framework component
        if comp_name in FRAMEWORK_COMPONENTS:
            continue

        result = resolve_single_component(comp_name, SOURCE_DIR, arch, platform=platform)
        if result:
            resolved.append(result)
            logger.info(f"[RESOLVER] Component OK: {comp_name} (CID: {result['cid'][:8]}...)")
        else:
            missing.append(comp_name)
            logger.warning(f"[RESOLVER] MISSING: {comp_name}")

    # 3. Create project structure with DependenciesFiles
    project_dir = create_project_structure(project_name, resolved, framework_resolved, arch, platform)

    # 4. Generate Makefiles (platform-specific)
    if platform == "Linux":
        makefile_content = ""  # Not needed for Linux EXE builds
        makefile_exe_content = generate_makefile_exe_linux(resolved, framework_resolved, project_name)

        makefile_exe_path = project_dir / "gcc_linux" / "MakefileExe"
        makefile_exe_path.write_text(makefile_exe_content, encoding="utf-8")
        logger.info(f"[RESOLVER] Written Linux MakefileExe: {makefile_exe_path}")
    else:
        makefile_content = generate_makefile(resolved, framework_resolved, project_name)
        makefile_exe_content = generate_makefile_exe(resolved, framework_resolved, project_name, arch)

        makefile_path = project_dir / "MSVC_v140" / "Makefile"
        makefile_path.write_text(makefile_content, encoding="utf-8")

        makefile_exe_path = project_dir / "MSVC_v140" / "MakefileExe"
        makefile_exe_path.write_text(makefile_exe_content, encoding="utf-8")

        logger.info(f"[RESOLVER] Written Makefile: {makefile_path}")
        logger.info(f"[RESOLVER] Written MakefileExe: {makefile_exe_path}")

    # 5. Compute include/lib paths for reference
    all_components = framework_resolved + resolved
    include_dirs = []
    lib_dirs = []
    lib_files = []

    for comp in all_components:
        if comp.get("shared_dir"):
            include_dirs.append(comp["shared_dir"])
        if comp.get("lib_path"):
            lib_dirs.append(str(Path(comp["lib_path"]).parent))
            lib_files.append(comp["lib_filename"])

    logger.info(f"[RESOLVER] Resolved: {len(resolved)} components, {len(framework_resolved)} framework")
    logger.info(f"[RESOLVER] Missing: {len(missing)} components: {missing}")
    logger.info(f"[RESOLVER] Project dir: {project_dir}")

    return {
        "resolved_components": resolved,
        "framework_components": framework_resolved,
        "include_dirs": include_dirs,
        "lib_dirs": lib_dirs,
        "lib_files": lib_files,
        "makefile_content": makefile_content,
        "makefile_exe_content": makefile_exe_content,
        "project_dir": str(project_dir),
        "missing_components": missing,
        "build_platform": platform,
    }
