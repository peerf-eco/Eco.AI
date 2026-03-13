"""
EcoOS Component Agent - State Definition

V1: Old state for code generation from scratch (deprecated).
V3: New state for assembly from SDK components.
"""

from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


# ═══════════════════════════════════════════════════════════════════════════
# V1 STATE (deprecated, kept for backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════

class ComponentSpec(BaseModel):
    cid: str = Field(description="Component ID")
    name: str = Field(description="Component name")
    factory_export: str = Field(default="GetIEcoComponentFactoryPtr")
    factory_signature: str = Field(description="Factory signature")
    iid: str = Field(description="Interface ID")
    interface_name: str = Field(description="Interface name")
    methods: Dict[str, str] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    header_path: str = Field(description="Interface header path")
    id_header_path: str = Field(description="Id header path")


class GeneratedFile(BaseModel):
    path: str = Field(description="File path")
    content: str = Field(description="File content")
    file_type: str = Field(description="Type: 'source', 'header', 'build'")


class ValidationError(BaseModel):
    file: str = Field(description="File with error")
    line: Optional[int] = Field(default=None)
    message: str = Field(description="Error description")
    severity: str = Field(default="error")


class AgentState(TypedDict):
    """V1 state (deprecated)."""
    messages: Annotated[list, add_messages]
    user_intent: str
    required_features: List[str]
    target_platform: str
    app_type: str
    selected_components: List[dict]
    retrieved_headers: Dict[str, str]
    retrieved_examples: Dict[str, str]
    code_patterns: Dict[str, str]
    generated_files: List[dict]
    validation_errors: List[dict]
    is_valid: bool
    iteration_count: int
    max_iterations: int


# ═══════════════════════════════════════════════════════════════════════════
# V3 STATE — Assembly from SDK Components
# ═══════════════════════════════════════════════════════════════════════════

class ResolvedComponent(BaseModel):
    """A resolved SDK component with all paths."""
    name: str = Field(description="Component name, e.g. 'Eco.Math.C89'")
    cid: str = Field(description="Component ID hex string, e.g. '61C988E21B7041378C5BDAFBB68A3FA0'")
    iid: str = Field(default="", description="Interface ID hex string")
    interface_name: str = Field(default="", description="Interface name, e.g. 'IEcoMathC89'")
    factory_func: str = Field(default="", description="Static factory function name, e.g. 'GetIEcoComponentFactoryPtr_61C988E...'")
    lib_path: str = Field(default="", description="Full path to .lib file")
    lib_filename: str = Field(default="", description=".lib filename, e.g. '61C988E21B7041378C5BDAFBB68A3FA0.lib'")
    headers: List[str] = Field(default_factory=list, description="List of header file paths")
    header_contents: Dict[str, str] = Field(default_factory=dict, description="Header filename -> content")
    shared_dir: str = Field(default="", description="Path to SharedFiles directory")
    dk_dir: str = Field(default="", description="Path to DK root directory")
    is_framework: bool = Field(default=False, description="True if this is a framework component")


class PlannerResponse(BaseModel):
    """Structured output from Planner node."""
    components: List[Dict[str, str]] = Field(
        description="List of {name, reason} dicts"
    )
    app_description: str = Field(
        description="Brief description of what the app does"
    )
    project_name: str = Field(
        default="EcoApp",
        description="Project name for output directory"
    )


class AgentStateV3(TypedDict):
    """
    State for the V3 assembly-from-SDK-components workflow.

    Flow: planner → resolver → writer → build → (retry | end)
    """

    # ═══════════════════════════════════════════════════════════════
    # USER INPUT
    # ═══════════════════════════════════════════════════════════════
    user_request: str

    # ═══════════════════════════════════════════════════════════════
    # PLANNER OUTPUT (ReAct LLM + rag_query tool)
    # ═══════════════════════════════════════════════════════════════
    component_plan: dict           # PlannerResponse as dict: {components, app_description, project_name}
    planner_messages: Annotated[list, add_messages]

    # ═══════════════════════════════════════════════════════════════
    # RESOLVER OUTPUT (pure Python, no LLM)
    # ═══════════════════════════════════════════════════════════════
    resolved_components: list      # List[ResolvedComponent.model_dump()]
    framework_components: list     # Always: System1, InterfaceBus1, MemoryManager1, Core1, FSM1
    include_dirs: list             # [str] — all /I paths for compiler
    lib_dirs: list                 # [str] — all /LIBPATH: for linker
    lib_files: list                # [str] — all .lib filenames
    makefile_content: str          # Generated Makefile text
    makefile_exe_content: str      # Generated MakefileExe text
    project_dir: str               # output/<ProjectName>/
    missing_components: list       # Components not found locally
    build_platform: str            # "Windows" or "Linux" (auto-detected)

    # ═══════════════════════════════════════════════════════════════
    # WRITER OUTPUT (LLM generates only EcoMain.c)
    # ═══════════════════════════════════════════════════════════════
    ecomain_content: str           # The generated EcoMain.c source
    writer_messages: Annotated[list, add_messages]

    # ═══════════════════════════════════════════════════════════════
    # BUILD OUTPUT (pure Python, runs make)
    # ═══════════════════════════════════════════════════════════════
    build_result: str              # Full compiler/linker output
    is_success: bool               # True if build succeeded
    error_message: str             # Human-readable error summary
    error_type: str                # "compile"|"link"|"missing_component"|"none"

    # ═══════════════════════════════════════════════════════════════
    # TESTER OUTPUT (LLM generates tests, Python executes)
    # ═══════════════════════════════════════════════════════════════
    test_cases: str                # JSON string with test cases from LLM
    test_results: str              # JSON string with test execution results
    tests_passed: bool             # True if all tests passed

    # ═══════════════════════════════════════════════════════════════
    # CONTROL
    # ═══════════════════════════════════════════════════════════════
    iteration: int
    max_iterations: int

