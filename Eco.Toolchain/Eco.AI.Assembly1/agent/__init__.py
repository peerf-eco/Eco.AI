"""
EcoOS Component Agent

AI-агент на LangGraph для генерации компонентов EcoOS из "кирпичиков".

Версия 2 (v2):
    from agent import run_agent
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(model="...", temperature=0)
    result = run_agent(llm, "Создай калькулятор с операцией сложения")
    
    if result["is_success"]:
        print(f"EXE: {result['build_result']}")
    else:
        print(f"Error: {result['error_message']}")

Автотест:
    python -m agent.test_agent
"""

# V1 (старая версия)
from .graph import create_agent_graph, create_simple_graph
from .state import AgentState, ComponentSpec, GeneratedFile, ValidationError

# V2 (новая версия)
from .graph_v2 import create_agent_graph_v2, run_agent, AgentStateV2
from .tools import list_files, read_file, write_file, build, PLANNER_TOOLS, BUILDER_TOOLS

__all__ = [
    # V1
    "create_agent_graph",
    "create_simple_graph",
    "AgentState",
    "ComponentSpec",
    "GeneratedFile",
    "ValidationError",
    # V2
    "create_agent_graph_v2",
    "run_agent",
    "AgentStateV2",
    "list_files",
    "read_file",
    "write_file",
    "build",
    "PLANNER_TOOLS",
    "BUILDER_TOOLS",
]

__version__ = "0.2.0"

