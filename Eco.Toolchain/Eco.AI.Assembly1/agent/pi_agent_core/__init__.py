"""pi_agent_core - Python port of @mariozechner/pi-mono/packages/agent.

Public API:
    from agent.pi_agent_core import (
        # Class facades
        Agent, AgentOptions,
        # Low-level
        run_agent_loop, run_agent_loop_continue, AgentEventSink,
        # Types
        AgentMessage, AgentContext, AgentTool, AgentToolResult, AgentState,
        AgentEvent, AgentLoopConfig, ToolExecutionMode,
        # Hook contexts/results
        BeforeToolCallContext, BeforeToolCallResult,
        AfterToolCallContext, AfterToolCallResult,
        # Defaults
        default_convert_to_llm,
        # Sub-types of AgentEvent (for isinstance checks)
        AgentStartEvent, AgentEndEvent,
        TurnStartEvent, TurnEndEvent,
        MessageStartEvent, MessageUpdateEvent, MessageEndEvent,
        ToolExecutionStartEvent, ToolExecutionUpdateEvent, ToolExecutionEndEvent,
    )

See docs/superpowers/specs/2026-05-18-pi-port-design.md for design.
"""

from agent.pi_agent_core.agent import (
    Agent, AgentOptions, default_convert_to_llm,
)
from agent.pi_agent_core.agent_loop import (
    AgentEventSink, run_agent_loop, run_agent_loop_continue,
)
from agent.pi_agent_core.types import (
    AfterToolCallContext, AfterToolCallResult,
    AgentContext, AgentEndEvent, AgentEvent, AgentLoopConfig, AgentMessage,
    AgentStartEvent, AgentState, AgentTool, AgentToolResult,
    BeforeToolCallContext, BeforeToolCallResult,
    MessageEndEvent, MessageStartEvent, MessageUpdateEvent,
    ToolExecutionEndEvent, ToolExecutionMode, ToolExecutionStartEvent,
    ToolExecutionUpdateEvent, TurnEndEvent, TurnStartEvent,
)

__all__ = [
    "Agent", "AgentOptions", "default_convert_to_llm",
    "run_agent_loop", "run_agent_loop_continue", "AgentEventSink",
    "AgentMessage", "AgentContext", "AgentTool", "AgentToolResult", "AgentState",
    "AgentEvent", "AgentLoopConfig", "ToolExecutionMode",
    "BeforeToolCallContext", "BeforeToolCallResult",
    "AfterToolCallContext", "AfterToolCallResult",
    "AgentStartEvent", "AgentEndEvent",
    "TurnStartEvent", "TurnEndEvent",
    "MessageStartEvent", "MessageUpdateEvent", "MessageEndEvent",
    "ToolExecutionStartEvent", "ToolExecutionUpdateEvent", "ToolExecutionEndEvent",
]
