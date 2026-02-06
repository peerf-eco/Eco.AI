"""
EcoOS Agent Tools

Тулы для Planner и Builder агентов:
- list_files: навигация по файловой системе
- read_file: чтение содержимого файлов
- write_file: запись файлов (только для Builder)
- build: компиляция проекта (только для QA)
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Базовые пути
BASE_DIR = Path(__file__).parent.parent
SOURCE_DIR = BASE_DIR / "source"
LESSONS_DIR = SOURCE_DIR / "Lessons"
OUTPUT_DIR = BASE_DIR / "output"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: list_files
# ═══════════════════════════════════════════════════════════════════════════

@tool
def list_files(path: str) -> str:
    """
    Список файлов и папок в директории.
    
    Args:
        path: Путь относительно source/ (например "Lessons/Lesson02")
              Или "." для корня source/
    
    Returns:
        Список файлов и папок, по одному на строку.
        Папки помечены [DIR], файлы - [FILE].
    
    Example:
        list_files("Lessons/Lesson02/Eco.CalculatorA")
        → [DIR] SharedFiles
          [DIR] HeaderFiles
          [DIR] SourceFiles
          [DIR] AssemblyFiles
    """
    logger.info(f"[TOOL list_files] path={path}")
    
    # Нормализуем путь
    if path == "." or path == "":
        target_path = SOURCE_DIR
    else:
        target_path = SOURCE_DIR / path
    
    # Проверяем существование
    if not target_path.exists():
        error_msg = f"Директория не найдена: {path}"
        logger.warning(f"[TOOL list_files] {error_msg}")
        return f"ERROR: {error_msg}"
    
    if not target_path.is_dir():
        error_msg = f"Это не директория: {path}"
        logger.warning(f"[TOOL list_files] {error_msg}")
        return f"ERROR: {error_msg}"
    
    # Собираем список
    items = []
    try:
        for item in sorted(target_path.iterdir()):
            if item.name.startswith('.'):
                continue  # Пропускаем скрытые файлы
            
            if item.is_dir():
                items.append(f"[DIR] {item.name}")
            else:
                items.append(f"[FILE] {item.name}")
        
        result = "\n".join(items) if items else "(пустая директория)"
        logger.info(f"[TOOL list_files] Found {len(items)} items")
        return result
        
    except PermissionError as e:
        error_msg = f"Нет доступа к директории: {path}"
        logger.error(f"[TOOL list_files] {error_msg}: {e}")
        return f"ERROR: {error_msg}"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: read_file
# ═══════════════════════════════════════════════════════════════════════════

@tool
def read_file(path: str) -> str:
    """
    Прочитать содержимое файла.
    
    Args:
        path: Путь к файлу относительно source/ или output/
              Примеры:
              - "Lessons/Lesson02/Eco.CalculatorA/SharedFiles/IEcoCalculatorX.h" (source)
              - "Eco.Calculator/HeaderFiles/CEcoCalculator.h" (output)
    
    Returns:
        Содержимое файла или сообщение об ошибке.
    
    Example:
        read_file("Lessons/Lesson02/Eco.CalculatorA/SharedFiles/IEcoCalculatorX.h")
        → /* IEcoCalculatorX.h */ ...
    """
    logger.info(f"[TOOL read_file] path={path}")
    
    # Сначала ищем в source/
    target_path = SOURCE_DIR / path
    
    # Если не нашли в source/, ищем в output/
    if not target_path.exists():
        output_path = OUTPUT_DIR / path
        if output_path.exists():
            logger.info(f"[TOOL read_file] Found in output/: {path}")
            target_path = output_path
    
    # Проверяем существование
    if not target_path.exists():
        error_msg = f"Файл не найден: {path} (искали в source/ и output/)"
        logger.warning(f"[TOOL read_file] {error_msg}")
        return f"ERROR: {error_msg}"
    
    if not target_path.is_file():
        error_msg = f"Это не файл: {path}"
        logger.warning(f"[TOOL read_file] {error_msg}")
        return f"ERROR: {error_msg}"
    
    # Читаем файл
    try:
        # Пробуем разные кодировки
        for encoding in ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']:
            try:
                content = target_path.read_text(encoding=encoding)
                logger.info(f"[TOOL read_file] Read {len(content)} chars with {encoding}")
                return content
            except UnicodeDecodeError:
                continue
        
        # Если ничего не подошло, читаем как бинарный и декодируем с ошибками
        content = target_path.read_bytes().decode('utf-8', errors='replace')
        logger.info(f"[TOOL read_file] Read {len(content)} chars with fallback")
        return content
        
    except PermissionError as e:
        error_msg = f"Нет доступа к файлу: {path}"
        logger.error(f"[TOOL read_file] {error_msg}: {e}")
        return f"ERROR: {error_msg}"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: write_file
# ═══════════════════════════════════════════════════════════════════════════

@tool
def write_file(path: str, content: str) -> str:
    """
    Записать содержимое в файл.
    
    Файлы создаются в директории output/ (не в source/).
    Директории создаются автоматически.
    
    Args:
        path: Путь к файлу относительно output/
              (например "Eco.Calculator/SharedFiles/IEcoCalculatorX.h")
        content: Содержимое файла
    
    Returns:
        "OK: Файл записан: {path}" или сообщение об ошибке.
    
    Example:
        write_file("Eco.Calculator/SharedFiles/IEcoCalculatorX.h", "/* content */")
        → OK: Файл записан: Eco.Calculator/SharedFiles/IEcoCalculatorX.h
    """
    logger.info(f"[TOOL write_file] path={path}, content_len={len(content)}")
    
    target_path = OUTPUT_DIR / path
    
    # Создаём директории
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        error_msg = f"Не удалось создать директорию для: {path}"
        logger.error(f"[TOOL write_file] {error_msg}: {e}")
        return f"ERROR: {error_msg}"
    
    # Записываем файл
    try:
        target_path.write_text(content, encoding='utf-8')
        logger.info(f"[TOOL write_file] Written {len(content)} chars to {target_path}")
        return f"OK: Файл записан: {path}"
        
    except PermissionError as e:
        error_msg = f"Нет доступа для записи: {path}"
        logger.error(f"[TOOL write_file] {error_msg}: {e}")
        return f"ERROR: {error_msg}"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: build
# ═══════════════════════════════════════════════════════════════════════════

def _find_msbuild() -> Optional[str]:
    """Найти MSBuild.exe на системе."""
    # Стандартные пути VS 2022/2019
    possible_paths = [
        r"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
        r"C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
        r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
        r"C:\Program Files\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
        r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            logger.info(f"[BUILD] Found MSBuild: {path}")
            return path
    
    # Попробуем через vswhere
    vswhere = r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
    if Path(vswhere).exists():
        try:
            result = subprocess.run(
                [vswhere, "-latest", "-requires", "Microsoft.Component.MSBuild", 
                 "-find", "MSBuild\\**\\Bin\\MSBuild.exe"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                msbuild = result.stdout.strip().split('\n')[0]
                logger.info(f"[BUILD] Found MSBuild via vswhere: {msbuild}")
                return msbuild
        except Exception as e:
            logger.warning(f"[BUILD] vswhere failed: {e}")
    
    return None


def _generate_vcxproj(project_path: Path, project_name: str, source_files: List[Path]) -> Path:
    """Генерирует .vcxproj файл для EXE приложения."""
    
    # Генерируем GUID для проекта
    import hashlib
    guid_hash = hashlib.md5(project_name.encode()).hexdigest().upper()
    project_guid = f"{guid_hash[:8]}-{guid_hash[8:12]}-{guid_hash[12:16]}-{guid_hash[16:20]}-{guid_hash[20:32]}"
    
    # Target name = имя проекта без Eco.
    target_name = project_name.replace("Eco.", "")
    
    # Source files для vcxproj
    source_items = "\n    ".join([f'<ClCompile Include="..\\..\\..\\SourceFiles\\{sf.name}" />' for sf in source_files])
    
    # Header files
    header_path = project_path / "HeaderFiles"
    header_files = list(header_path.glob("*.h")) if header_path.exists() else []
    header_items = "\n    ".join([f'<ClInclude Include="..\\..\\..\\HeaderFiles\\{hf.name}" />' for hf in header_files])
    
    # Shared files  
    shared_path = project_path / "SharedFiles"
    shared_files = list(shared_path.glob("*.h")) if shared_path.exists() else []
    shared_items = "\n    ".join([f'<ClInclude Include="..\\..\\..\\SharedFiles\\{sf.name}" />' for sf in shared_files])
    
    # EXE Application vcxproj
    vcxproj_content = f'''<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" ToolsVersion="17.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Release|x64">
      <Configuration>Release</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
  </ItemGroup>
  <PropertyGroup Label="Globals">
    <ProjectGuid>{{{project_guid}}}</ProjectGuid>
    <Keyword>Win32Proj</Keyword>
    <RootNamespace>{project_name.replace('.', '')}</RootNamespace>
    <WindowsTargetPlatformVersion>10.0</WindowsTargetPlatformVersion>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.Default.props" />
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'" Label="Configuration">
    <ConfigurationType>Application</ConfigurationType>
    <UseDebugLibraries>false</UseDebugLibraries>
    <PlatformToolset>v143</PlatformToolset>
    <WholeProgramOptimization>true</WholeProgramOptimization>
    <CharacterSet>Unicode</CharacterSet>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.props" />
  <ImportGroup Label="ExtensionSettings">
  </ImportGroup>
  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Release|x64'">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <PropertyGroup Label="UserMacros" />
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'">
    <OutDir>$(SolutionDir)..\\BuildFiles\\Windows\\x64\\$(Configuration)\\</OutDir>
    <IntDir>$(Configuration)\\</IntDir>
    <TargetName>{target_name}</TargetName>
  </PropertyGroup>
  <ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'">
    <ClCompile>
      <WarningLevel>Level3</WarningLevel>
      <PrecompiledHeader></PrecompiledHeader>
      <Optimization>MaxSpeed</Optimization>
      <FunctionLevelLinking>true</FunctionLevelLinking>
      <IntrinsicFunctions>true</IntrinsicFunctions>
      <AdditionalIncludeDirectories>..\\..\\..\\HeaderFiles;..\\..\\..\\SharedFiles;$(ECO_FRAMEWORK)\\Eco.Core1_DK_v.1.0.1.2\\Eco.Core1\\SharedFiles;$(ECO_FRAMEWORK)\\Eco.MemoryManager1\\SharedFiles;$(ECO_FRAMEWORK)\\Eco.InterfaceBus1_DK_v.1.0.1.2\\Eco.InterfaceBus1\\SharedFiles;$(ECO_FRAMEWORK)\\Eco.System1_DK_v.1.0.1.2\\Eco.System1\\SharedFiles;%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>
      <RuntimeLibrary>MultiThreaded</RuntimeLibrary>
      <CompileAs>CompileAsC</CompileAs>
      <PreprocessorDefinitions>ECO_WINDOWS;ECO_X86_64;_WINDOWS;ECO_LIB;UGUID_UTILITY;%(PreprocessorDefinitions)</PreprocessorDefinitions>
      <CallingConvention>StdCall</CallingConvention>
    </ClCompile>
    <Link>
      <SubSystem>Console</SubSystem>
      <EnableCOMDATFolding>true</EnableCOMDATFolding>
      <OptimizeReferences>true</OptimizeReferences>
      <GenerateDebugInformation>true</GenerateDebugInformation>
      <OutputFile>$(OutDir)$(TargetName).exe</OutputFile>
      <AdditionalLibraryDirectories>$(ECO_FRAMEWORK)\\Eco.System1_DK_v.1.0.1.2\\Eco.System1\\BuildFiles\\Windows\\amd64\\DynamicRelease;%(AdditionalLibraryDirectories)</AdditionalLibraryDirectories>
      <AdditionalDependencies>00000000000000000000000053595333.lib;%(AdditionalDependencies)</AdditionalDependencies>
    </Link>
  </ItemDefinitionGroup>
  <ItemGroup>
    {source_items}
  </ItemGroup>
  <ItemGroup>
    {header_items}
    {shared_items}
  </ItemGroup>
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.targets" />
  <ImportGroup Label="ExtensionTargets">
  </ImportGroup>
</Project>'''
    
    # Создаём директорию для VS проекта
    vs_dir = project_path / "AssemblyFiles" / "Windows" / "VisualStudio"
    vs_dir.mkdir(parents=True, exist_ok=True)
    
    vcxproj_path = vs_dir / f"{project_name}.vcxproj"
    vcxproj_path.write_text(vcxproj_content, encoding='utf-8')
    
    logger.info(f"[BUILD] Generated vcxproj for EXE: {vcxproj_path}")
    return vcxproj_path


@tool
def build(project_name: str) -> str:
    """
    Скомпилировать проект через MSBuild в EXE.
    
    Генерирует .vcxproj и собирает EXE приложение.
    
    Args:
        project_name: Имя проекта в output/ (например "Eco.Calculator")
    
    Returns:
        "OK: Сборка успешна: {exe_path}" или "ERROR: {compiler_output}"
    """
    logger.info(f"[TOOL build] project_name={project_name}")
    
    project_path = OUTPUT_DIR / project_name
    
    # Проверяем существование проекта
    if not project_path.exists():
        error_msg = f"Проект не найден: {project_name}"
        logger.warning(f"[TOOL build] {error_msg}")
        return f"ERROR: {error_msg}"
    
    # Находим MSBuild
    msbuild = _find_msbuild()
    if not msbuild:
        error_msg = "MSBuild не найден. Установите Visual Studio."
        logger.error(f"[TOOL build] {error_msg}")
        return f"ERROR: {error_msg}"
    
    # Собираем список .c файлов
    source_files = list((project_path / "SourceFiles").glob("*.c")) if (project_path / "SourceFiles").exists() else []
    
    if not source_files:
        error_msg = f"Нет исходных файлов в {project_name}/SourceFiles/"
        logger.warning(f"[TOOL build] {error_msg}")
        return f"ERROR: {error_msg}"
    
    logger.info(f"[TOOL build] Found {len(source_files)} source files:")
    for sf in source_files:
        logger.info(f"[TOOL build]   - {sf.name}")
    
    # Генерируем .vcxproj для EXE
    vcxproj_path = _generate_vcxproj(project_path, project_name, source_files)
    
    # Устанавливаем ECO_FRAMEWORK env variable
    eco_framework = str(SOURCE_DIR)
    logger.info(f"[TOOL build] ECO_FRAMEWORK={eco_framework}")
    
    # Формируем команду MSBuild для EXE (Configuration=Release)
    cmd = [
        msbuild,
        str(vcxproj_path),
        "/p:Configuration=Release",
        "/p:Platform=x64",
        "/t:Build",
        "/v:minimal"
    ]
    
    logger.info(f"[TOOL build] Running MSBuild for EXE...")
    
    try:
        # Копируем env и добавляем ECO_FRAMEWORK
        env = os.environ.copy()
        env["ECO_FRAMEWORK"] = eco_framework
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(vcxproj_path.parent),
            env=env
        )
        
        if result.returncode == 0:
            # Ищем созданный EXE
            build_dir = project_path / "BuildFiles" / "Windows" / "x64" / "Release"
            exe_files = list(build_dir.glob("*.exe")) if build_dir.exists() else []
            
            if exe_files:
                exe_path = exe_files[0]
                logger.info(f"[TOOL build] SUCCESS: {exe_path}")
                return f"OK: Сборка успешна: {exe_path}"
            else:
                # Попробуем найти в AssemblyFiles
                alt_build_dir = project_path / "AssemblyFiles" / "Windows" / "BuildFiles" / "Windows" / "x64" / "Release"
                exe_files = list(alt_build_dir.glob("*.exe")) if alt_build_dir.exists() else []
                if exe_files:
                    exe_path = exe_files[0]
                    logger.info(f"[TOOL build] SUCCESS: {exe_path}")
                    return f"OK: Сборка успешна: {exe_path}"
                logger.info(f"[TOOL build] SUCCESS but EXE not found in expected location")
                return f"OK: Сборка успешна (проверьте BuildFiles/)"
        else:
            error_output = result.stderr or result.stdout or "Unknown error"
            logger.error(f"[TOOL build] FAILED: {error_output[:1000]}")
            return f"ERROR: Ошибка компиляции:\n{error_output[:2000]}"
            
    except subprocess.TimeoutExpired:
        error_msg = "Таймаут компиляции (120 сек)"
        logger.error(f"[TOOL build] {error_msg}")
        return f"ERROR: {error_msg}"
        
    except Exception as e:
        error_msg = f"Ошибка запуска MSBuild: {e}"
        logger.error(f"[TOOL build] {error_msg}")
        return f"ERROR: {error_msg}"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL COLLECTIONS
# ═══════════════════════════════════════════════════════════════════════════

# Тулы для Planner (только чтение)
PLANNER_TOOLS = [list_files, read_file]

# Тулы для Builder (чтение + запись + сборка)
# Builder сам вызывает build, анализирует ошибки и исправляет код
BUILDER_TOOLS = [list_files, read_file, write_file, build]

# Тулы для QA (legacy, может быть убрано)
QA_TOOLS = [build]


def get_tools_description(tools: List) -> str:
    """Получить описание тулов для промпта."""
    descriptions = []
    for tool in tools:
        descriptions.append(f"- {tool.name}: {tool.description.split(chr(10))[0]}")
    return "\n".join(descriptions)
