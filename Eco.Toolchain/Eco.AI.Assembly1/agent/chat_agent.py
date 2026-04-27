"""
EcoOS Chat Agent (V4)

Conversational wrapper that delegates assembly to the V4 Architect agent.
Uses LangGraph create_react_agent with an assemble_ecoos_app tool
that invokes the Architect (ReAct) → Coder (sub-agents) pipeline.

V3 graph is still available via create_chat_agent_v3() for backward compat.
"""

import os
import json
import uuid
import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from .architect import create_architect_agent
from .state_helpers import make_initial_v3_state

logger = logging.getLogger(__name__)

# Stores interrupted Architect sessions for resume
# Key: architect_thread_id, Value: {"config": ..., "architect": ...}
_interrupted_sessions: dict[str, dict] = {}


@dataclass
class ChatContext:
    """Runtime context passed to chat agent (via stream/astream kwargs)."""
    llm: Any = None
    max_iterations: int = 5


CHAT_SYSTEM_PROMPT = """\
You are an EcoOS Assembly Agent — an AI assistant that helps users build \
applications from pre-built EcoOS SDK components.

You can:
1. **Chat** — answer questions about EcoOS, its component model, SDK, and architecture.
2. **Assemble** — when the user asks to create/build/assemble an application, \
call the `assemble_ecoos_app` tool with their request.

EcoOS uses a component-based architecture where applications are assembled from \
pre-built DevKit (DK) packages. Each DK contains headers (IEco*.h), static \
libraries (.lib), and ID headers with factory functions.

Always respond in the same language as the user's message.
When assembly is complete, summarize the result (success/failure, components used, \
test status) in a clear, friendly way.
"""


def create_chat_agent(llm):
    """
    Create a V4 chat agent that delegates assembly to the Architect.

    Returns a compiled LangGraph graph supporting:
        stream_mode=["messages", "custom"]
    """
    architect = create_architect_agent(llm)

    @tool
    def assemble_ecoos_app(user_request: str) -> str:
        """Delegate application assembly to the V4 Architect agent.

        The Architect will:
        1. Search for available components (SDK + marketplace)
        2. Present a PRD (component plan) for user review
        3. Spawn Coder sub-agents for custom components
        4. Generate EcoMain.c and build the project

        If the Architect needs user approval (PRD review), this tool returns
        the PRD data. Call resume_assembly after the user approves.

        Args:
            user_request: The user's description of what application to build.
        """
        from langgraph.config import get_stream_writer

        stream_writer = get_stream_writer()
        stream_writer({"type": "status", "content": "Starting Architect..."})

        logger.info(f"[CHAT] Delegating to Architect: {user_request}")

        arch_thread_id = str(uuid.uuid4())
        config = {
            "configurable": {"thread_id": arch_thread_id},
            "recursion_limit": 150,
        }

        try:
            result = architect.invoke(
                {"messages": [("user", user_request)]},
                config,
            )

            messages = result.get("messages", [])
            final_msg = messages[-1].content if messages else "No response from Architect"

            logger.info("[CHAT] Architect finished")
            return final_msg

        except GraphInterrupt as e:
            # Architect called interrupt() for PRD review
            interrupt_value = e.interrupts[0].value if e.interrupts else {}
            prd = interrupt_value.get("prd", interrupt_value)

            logger.info(f"[CHAT] Architect interrupted for PRD review: {prd.get('project_name', '?')}")

            # Save session for resume
            _interrupted_sessions[arch_thread_id] = {
                "config": config,
                "architect": architect,
            }

            # Send PRD to frontend
            stream_writer({
                "type": "prd_review",
                "data": prd,
                "thread_id": arch_thread_id,
            })

            return json.dumps({
                "status": "awaiting_prd_review",
                "architect_thread_id": arch_thread_id,
                "prd": prd,
                "message": "PRD sent to user for review. Wait for resume_assembly call.",
            }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"[CHAT] Architect error: {e}", exc_info=True)
            stream_writer({
                "type": "progress",
                "stage": "build",
                "status": f"Error: {e}",
            })
            return json.dumps({"error": str(e), "is_success": False})

    @tool
    def resume_assembly(architect_thread_id: str, approved: bool, modified_prd_json: str = "") -> str:
        """Resume the Architect after user reviewed the PRD.

        Call this when the user has approved or rejected the component plan.

        Args:
            architect_thread_id: Thread ID from the interrupted session.
            approved: True if user approved, False if rejected.
            modified_prd_json: Optional modified PRD as JSON (if user edited it).
        """
        from langgraph.config import get_stream_writer

        stream_writer = get_stream_writer()

        session = _interrupted_sessions.pop(architect_thread_id, None)
        if not session:
            return "ERROR: No interrupted session found. The session may have expired."

        config = session["config"]
        arch = session["architect"]

        if approved:
            if modified_prd_json:
                try:
                    modified_prd = json.loads(modified_prd_json)
                    resume_value = {"approved": True, "prd": modified_prd}
                except json.JSONDecodeError:
                    resume_value = {"approved": True}
            else:
                resume_value = {"approved": True}
        else:
            resume_value = {"approved": False, "reason": "User rejected the plan"}

        logger.info(f"[CHAT] Resuming Architect: approved={approved}")
        stream_writer({"type": "status", "content": "Resuming assembly..."})

        try:
            result = arch.invoke(
                Command(resume=resume_value),
                config,
            )

            messages = result.get("messages", [])
            final_msg = messages[-1].content if messages else "No response from Architect"

            logger.info("[CHAT] Architect finished after resume")
            return final_msg

        except GraphInterrupt as e:
            # Another interrupt (shouldn't normally happen)
            interrupt_value = e.interrupts[0].value if e.interrupts else {}
            logger.warning(f"[CHAT] Architect interrupted again: {interrupt_value}")
            return json.dumps({"error": "Unexpected second interrupt", "data": str(interrupt_value)})

        except Exception as e:
            logger.error(f"[CHAT] Architect resume error: {e}", exc_info=True)
            return json.dumps({"error": str(e), "is_success": False})

    memory = MemorySaver()

    agent = create_react_agent(
        llm,
        tools=[assemble_ecoos_app, resume_assembly],
        prompt=CHAT_SYSTEM_PROMPT,
        checkpointer=memory,
    )

    return agent


def create_chat_agent_v3(llm):
    """
    Create the legacy V3 chat agent (for backward compatibility).

    Uses the rigid V3 graph: planner → resolver → writer → build → tester.
    """
    from .graph_v2 import create_agent_graph_v3

    v3_graph = create_agent_graph_v3(llm)
    max_iterations = min(int(os.getenv("AGENT_MAX_ITERATIONS", "5")), 5)

    @tool
    def assemble_ecoos_app_v3(user_request: str) -> str:
        """Run the EcoOS V3 assembly pipeline to build an app from SDK components.

        Args:
            user_request: The user's description of what application to build.
        """
        from langgraph.config import get_stream_writer

        stream_writer = get_stream_writer()

        initial_state = make_initial_v3_state(user_request, max_iterations)
        thread_id = str(uuid.uuid4())
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 100,
        }

        logger.info(f"[CHAT V3] Starting V3 assembly: {user_request}")

        final_state = initial_state.copy()

        try:
            for event in v3_graph.stream(
                initial_state, config, stream_mode="updates"
            ):
                for node_name, node_output in event.items():
                    stream_writer({
                        "type": "progress",
                        "stage": node_name,
                        "status": f"Executing {node_name}...",
                    })
                    if isinstance(node_output, dict):
                        final_state.update(node_output)

        except Exception as e:
            logger.error(f"[CHAT V3] Assembly error: {e}", exc_info=True)
            stream_writer({
                "type": "progress",
                "stage": "build",
                "status": f"Error: {e}",
            })
            return json.dumps({"error": str(e), "is_success": False})

        resolved = []
        for comp in final_state.get("resolved_components", []):
            if isinstance(comp, dict):
                resolved.append({
                    "name": comp.get("name", ""),
                    "cid": comp.get("cid", ""),
                })

        result_data = {
            "is_success": final_state.get("is_success", False),
            "tests_passed": final_state.get("tests_passed", False),
            "project_dir": final_state.get("project_dir", ""),
            "build_result": final_state.get("build_result", ""),
            "test_results": final_state.get("test_results", ""),
            "iterations": final_state.get("iteration", 0),
            "resolved_components": resolved,
            "missing_components": final_state.get("missing_components", []),
        }

        stream_writer({"type": "result", "data": result_data})

        logger.info(
            f"[CHAT V3] Assembly done: success={result_data['is_success']}, "
            f"iterations={result_data['iterations']}"
        )

        return json.dumps(result_data, ensure_ascii=False)

    memory = MemorySaver()

    agent = create_react_agent(
        llm,
        tools=[assemble_ecoos_app_v3],
        prompt=CHAT_SYSTEM_PROMPT,
        checkpointer=memory,
    )

    return agent


def create_chat_agent_v5(llm):
    """V5: returns the three-node graph directly. Caller manages thread_id and state."""
    from .three_node_graph import create_v5_graph
    return create_v5_graph(llm)


def make_chat_agent_initial_state(user_request: str, max_iterations: int = 5):
    from .state_v5 import make_initial_state
    return make_initial_state(user_request, max_iterations)
