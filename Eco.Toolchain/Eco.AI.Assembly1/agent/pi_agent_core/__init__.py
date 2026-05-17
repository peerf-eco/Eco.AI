"""pi_agent_core - Python port of @mariozechner/pi-mono/packages/agent.

This package wraps the Phase 1 pi_ai layer with:
- Agent class (stateful conversation handler, message queues, event subscribers)
- run_agent_loop (low-level turn loop with hooks)
- AgentTool (pydantic-schema tool definition with async execute callback)
- AgentEvent (discriminated union of lifecycle events)

See docs/superpowers/specs/2026-05-18-pi-port-design.md for design.
"""
