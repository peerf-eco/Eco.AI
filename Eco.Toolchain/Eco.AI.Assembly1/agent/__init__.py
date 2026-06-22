"""EcoOS Component Agent (V7).

Production pipeline: a custom ``Orchestrator`` (agent/v6/orchestrator.py) drives
three pi_ai ``EcoAgent`` loops — architect / coder / tester (agent/v6/agents/*).
Served at ``/ws/v7/chat`` (backend/server.py). LLM layer = agent/pi_ai/*;
RAG = agent/rag/* (sqlite-vec) exposed via agent/v6/tools/rag.py.

No LangGraph / LangChain. Earlier generations V1–V6 were removed 2026-06-22
(see git history for rollback).
"""

__version__ = "0.7.0"
