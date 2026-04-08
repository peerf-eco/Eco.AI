"""
EcoOS Component Agent

AI-агент на LangGraph для сборки приложений EcoOS из SDK-компонентов.

V4 (current):
    from agent.chat_agent import create_chat_agent
    agent = create_chat_agent(llm)  # delegates to Architect → Coders

V3 (legacy):
    from agent.chat_agent import create_chat_agent_v3
    agent = create_chat_agent_v3(llm)  # rigid planner→resolver→writer→build→tester

Автотест:
    python -m agent.test_agent
"""

# V1 (legacy)
from .graph import create_agent_graph, create_simple_graph
from .state import AgentState, ComponentSpec, GeneratedFile, ValidationError

# V3 (legacy) — assembly from SDK components
from .graph_v2 import create_agent_graph_v3, run_agent_v3
from .chat_agent import create_chat_agent, create_chat_agent_v3, ChatContext
from .state_helpers import make_initial_v3_state
from .tools import (
    rag_query,
    eco_cli_search,
    eco_cli_pull,
    build_makefile,
    build_node,
    run_tests,
    list_all_components,
    download_component,
    PLANNER_TOOLS,
    ARCHITECT_TOOLS,
    BUILD_TOOLS,
)
from .state import AgentStateV3

# V4 (current) — Architect + Coder sub-agents
from .architect import create_architect_agent
from .coder import create_coder_agent

__all__ = [
    # V1 (legacy)
    "create_agent_graph",
    "create_simple_graph",
    "AgentState",
    "ComponentSpec",
    "GeneratedFile",
    "ValidationError",
    # V3 (legacy)
    "create_agent_graph_v3",
    "run_agent_v3",
    "create_chat_agent_v3",
    "make_initial_v3_state",
    "AgentStateV3",
    "rag_query",
    "eco_cli_search",
    "eco_cli_pull",
    "build_makefile",
    "build_node",
    "run_tests",
    "PLANNER_TOOLS",
    "BUILD_TOOLS",
    # V4 (current)
    "create_chat_agent",
    "ChatContext",
    "create_architect_agent",
    "create_coder_agent",
    "list_all_components",
    "download_component",
    "ARCHITECT_TOOLS",
]

__version__ = "0.4.0"

