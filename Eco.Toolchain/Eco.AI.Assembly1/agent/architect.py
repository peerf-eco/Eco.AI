"""
EcoOS Architect Agent (V4)

Central orchestrator that replaces the rigid V3 graph.
Architect is a ReAct agent that decides the workflow:
  discover → download → plan (PRD) → user review → spawn coders → assemble → build

Uses interrupt() for PRD review and spawn_coder for Coder sub-agents.
"""

import os
import json
import logging
from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from langgraph.config import get_stream_writer

from .tools import (
    list_all_components, rag_query, download_component,
    build_node, build_makefile, run_tests, SOURCE_DIR, OUTPUT_DIR,
)
from .coder import create_coder_agent
from .resolver import resolver_node
from .state_helpers import make_initial_v3_state
from .prompts_v4 import ARCHITECT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def create_architect_agent(llm):
    """Create the V4 Architect agent — orchestrates the full build pipeline.

    Args:
        llm: LLM instance to use for reasoning

    Returns:
        Compiled LangGraph ReAct agent with checkpointer.
    """

    coder_llm = llm  # same LLM for now, can be different later

    # --- Architect-specific tools (closures over llm) ---

    @tool
    def present_prd(prd_json: str) -> str:
        """Present the PRD to the user for review and approval.

        Call this after you've analyzed the task and created a plan.
        The user will review and may modify the plan.

        Args:
            prd_json: JSON string with the PRD structure containing:
                - project_name: str
                - description: str
                - components: list of {name, source, reason, spec?}
                  where source is "sdk", "marketplace", or "develop"
        """
        writer = get_stream_writer()
        try:
            prd = json.loads(prd_json)
        except json.JSONDecodeError:
            return "ERROR: Invalid JSON in PRD"

        # Send PRD to frontend via custom stream event
        writer({"type": "prd", "data": prd})

        # Pause for user review
        decision = interrupt({
            "type": "prd_review",
            "prd": prd,
            "message": "Please review the component plan. Approve or modify.",
        })

        # decision is what user sends back via Command(resume=...)
        if isinstance(decision, dict):
            if decision.get("approved"):
                approved_prd = decision.get("prd", prd)
                return f"PRD approved by user:\n{json.dumps(approved_prd, ensure_ascii=False)}"
            else:
                return f"PRD rejected by user. Reason: {decision.get('reason', 'unknown')}"
        elif decision is True:
            return f"PRD approved by user:\n{json.dumps(prd, ensure_ascii=False)}"
        else:
            return "PRD rejected by user."

    @tool
    def spawn_coder(component_name: str, spec: str, project_name: str) -> str:
        """Spawn a Coder sub-agent to develop a new EcoOS component.

        The coder works in an isolated directory and creates all files
        needed for a complete EcoOS component (.h, .c, factory, makefile).
        Blocks until the coder finishes.

        Args:
            component_name: e.g. "Eco.HttpParser1"
            spec: Specification — interface methods, dependencies, description
            project_name: Project name for output directory
        """
        writer = get_stream_writer()
        writer({
            "type": "component_progress",
            "component": component_name,
            "stage": "starting",
        })

        # Isolated working directory for this coder
        work_dir = str(
            OUTPUT_DIR / project_name / "DependenciesFiles" / component_name
        )
        os.makedirs(work_dir, exist_ok=True)

        logger.info(f"[ARCHITECT] Spawning coder for {component_name} in {work_dir}")

        coder = create_coder_agent(coder_llm, work_dir)

        prompt = (
            f"Create the EcoOS component: {component_name}\n\n"
            f"Specification:\n{spec}\n\n"
            f"Working directory: {work_dir}\n"
            f"All files must be created inside this directory."
        )

        try:
            result = coder.invoke(
                {"messages": [("user", prompt)]},
                {"recursion_limit": 40},
            )

            # Extract final response
            messages = result.get("messages", [])
            final_msg = messages[-1].content if messages else "No response"

            writer({
                "type": "component_progress",
                "component": component_name,
                "stage": "done",
            })

            logger.info(f"[ARCHITECT] Coder done: {component_name}")
            return f"Coder result for {component_name}:\n{final_msg[:2000]}"

        except Exception as e:
            logger.error(f"[ARCHITECT] Coder failed: {component_name}: {e}")
            writer({
                "type": "component_progress",
                "component": component_name,
                "stage": "error",
            })
            return f"ERROR: Coder failed for {component_name}: {e}"

    @tool
    def write_ecomain(
        project_name: str,
        app_description: str,
        components_json: str,
    ) -> str:
        """Generate EcoMain.c that assembles all components into an application.

        Call this AFTER all components are ready (downloaded + developed).
        Uses the V3 resolver + writer pipeline internally.

        Args:
            project_name: e.g. "EcoNginx"
            app_description: What the app does
            components_json: JSON list of component names to use
        """
        writer = get_stream_writer()
        writer({"type": "progress", "stage": "writer", "status": "Generating EcoMain.c..."})

        try:
            components = json.loads(components_json)
        except json.JSONDecodeError:
            return "ERROR: Invalid components JSON"

        # Run resolver to set up project structure
        state = make_initial_v3_state(app_description)
        state["component_plan"] = {
            "components": [{"name": c} for c in components],
            "app_description": app_description,
            "project_name": project_name,
        }

        resolver_result = resolver_node(state)
        state.update(resolver_result)

        writer({"type": "progress", "stage": "resolver", "status": "Resolved components"})

        if state.get("missing_components"):
            missing = state["missing_components"]
            logger.warning(f"[ARCHITECT] Missing components after resolve: {missing}")

        # Generate EcoMain.c using Writer LLM
        from .graph_v2 import create_writer_node_v3, verifier_node
        writer_fn = create_writer_node_v3(llm)
        writer_result = writer_fn(state)
        state.update(writer_result)

        writer({"type": "progress", "stage": "writer", "status": "EcoMain.c generated"})

        # Run verifier
        verifier_result = verifier_node(state)
        state.update(verifier_result)

        if state.get("verification_errors"):
            return f"VERIFICATION_ERRORS:\n{state['verification_errors']}"

        project_dir = state.get("project_dir", "")
        return f"OK: EcoMain.c generated for {project_name}. Project dir: {project_dir}"

    @tool
    def build_project(project_dir: str) -> str:
        """Build the complete project (compile + link into executable).

        Args:
            project_dir: Path to project directory, e.g. "output/EcoNginx"
        """
        writer = get_stream_writer()
        writer({"type": "progress", "stage": "build", "status": "Building..."})

        result = build_makefile.invoke({"project_dir": project_dir})

        is_success = result.startswith("OK:")
        writer({
            "type": "progress",
            "stage": "build",
            "status": "Build succeeded" if is_success else "Build failed",
        })

        return result

    # --- Create Architect agent ---

    architect_tools = [
        list_all_components,
        rag_query,
        download_component,
        present_prd,
        spawn_coder,
        write_ecomain,
        build_project,
    ]

    memory = MemorySaver()

    agent = create_react_agent(
        llm,
        tools=architect_tools,
        prompt=ARCHITECT_SYSTEM_PROMPT,
        checkpointer=memory,
    )

    return agent
