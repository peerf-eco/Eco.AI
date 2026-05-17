"""Agent-loop smoke tests using the faux provider from pi_ai.

These exercise run_agent_loop end-to-end without a real LLM.
"""
from __future__ import annotations

import asyncio
import time

import pytest
from pydantic import BaseModel

from agent.pi_ai import Model, ModelCost
from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.providers.faux import make_faux_provider
from agent.pi_agent_core import (
    AgentContext, AgentEvent, AgentLoopConfig, AgentTool, AgentToolResult,
    BeforeToolCallResult, default_convert_to_llm, run_agent_loop,
)
from agent.pi_ai.types import TextContent


class _SearchArgs(BaseModel):
    q: str


async def _search_exec(call_id, params: _SearchArgs, signal, on_update):
    if on_update:
        on_update(AgentToolResult(content=[TextContent(text="searching...")], details=None))
    return AgentToolResult(
        content=[TextContent(text=f"results for {params.q}")],
        details={"q": params.q},
    )


def _search_tool() -> AgentTool:
    return AgentTool(
        name="search", description="search the web", label="Search",
        parameters=_SearchArgs, execute=_search_exec,
    )


def _model(api: str) -> Model:
    return Model(id="m", name="m", api=api, provider="faux", baseUrl="", cost=ModelCost())


def _user_message(text: str) -> dict:
    return {"role": "user", "content": text, "timestamp": int(time.time() * 1000)}


def _config(model: Model) -> AgentLoopConfig:
    return AgentLoopConfig(model=model, convertToLlm=default_convert_to_llm)


@pytest.mark.asyncio
async def test_run_agent_loop_text_only_no_tools():
    register_provider("faux-loop-text", make_faux_provider(text="hi"))
    events: list[AgentEvent] = []

    async def emit(ev):
        events.append(ev)

    new_messages = await run_agent_loop(
        prompts=[_user_message("hello")],
        context=AgentContext(systemPrompt="sys"),
        config=_config(_model("faux-loop-text")),
        emit=emit,
    )
    types = [e.type for e in events]
    assert types[0] == "agent_start"
    assert types[-1] == "agent_end"
    assert "message_start" in types and "message_end" in types
    assistants = [m for m in new_messages if getattr(m, "role", None) == "assistant"]
    assert len(assistants) == 1
    assert assistants[0].content[0].text == "hi"


@pytest.mark.asyncio
async def test_run_agent_loop_single_tool_call():
    """Faux emits one tool_call -> we execute -> next turn emits text."""
    call_count = {"n": 0}

    async def stateful_stream(model, ctx, opts=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            inner = make_faux_provider(
                text="",
                tool_calls=[{"name": "search", "arguments": {"q": "python"}}],
            )
        else:
            inner = make_faux_provider(text="done")
        async for ev in inner(model, ctx, opts):
            yield ev

    register_provider("faux-loop-tool", stateful_stream)
    events: list[AgentEvent] = []

    async def emit(ev):
        events.append(ev)

    new_messages = await run_agent_loop(
        prompts=[_user_message("search python")],
        context=AgentContext(systemPrompt="sys", tools=[_search_tool()]),
        config=_config(_model("faux-loop-tool")),
        emit=emit,
    )
    types = [e.type for e in events]
    assert "tool_execution_start" in types
    assert "tool_execution_end" in types
    assert "tool_execution_update" in types
    assistants = [m for m in new_messages if getattr(m, "role", None) == "assistant"]
    tool_results = [m for m in new_messages if getattr(m, "role", None) == "toolResult"]
    assert len(assistants) == 2
    assert len(tool_results) == 1
    assert "results for python" in tool_results[0].content[0].text


@pytest.mark.asyncio
async def test_run_agent_loop_unknown_tool_immediate_error():
    """LLM calls a tool that isn't registered -> immediate error tool result."""
    call_count = {"n": 0}

    async def stateful_stream(model, ctx, opts=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            inner = make_faux_provider(
                text="",
                tool_calls=[{"name": "does_not_exist", "arguments": {}}],
            )
        else:
            inner = make_faux_provider(text="oh well")
        async for ev in inner(model, ctx, opts):
            yield ev

    register_provider("faux-loop-unknown", stateful_stream)
    events = []

    async def emit(ev):
        events.append(ev)

    new_messages = await run_agent_loop(
        prompts=[_user_message("call missing")],
        context=AgentContext(systemPrompt="sys", tools=[]),
        config=_config(_model("faux-loop-unknown")),
        emit=emit,
    )
    tool_results = [m for m in new_messages if getattr(m, "role", None) == "toolResult"]
    assert len(tool_results) == 1
    assert tool_results[0].isError is True
    assert "not found" in tool_results[0].content[0].text


@pytest.mark.asyncio
async def test_run_agent_loop_before_tool_call_blocks():
    """beforeToolCall returning block=True -> tool not executed, error result."""
    tool_executed = {"yes": False}

    async def watching_exec(call_id, params, signal, on_update):
        tool_executed["yes"] = True
        return AgentToolResult(content=[TextContent(text="ok")], details=None)

    tool = AgentTool(
        name="search", description="d", label="L",
        parameters=_SearchArgs, execute=watching_exec,
    )

    async def block_hook(ctx, signal):
        return BeforeToolCallResult(block=True, reason="nope")

    call_count = {"n": 0}

    async def stateful_stream(model, ctx, opts=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            inner = make_faux_provider(
                text="",
                tool_calls=[{"name": "search", "arguments": {"q": "x"}}],
            )
        else:
            inner = make_faux_provider(text="ok")
        async for ev in inner(model, ctx, opts):
            yield ev
    register_provider("faux-loop-block", stateful_stream)

    config = AgentLoopConfig(
        model=_model("faux-loop-block"),
        convertToLlm=default_convert_to_llm,
        beforeToolCall=block_hook,
    )
    events = []

    async def emit(ev):
        events.append(ev)

    new_messages = await run_agent_loop(
        prompts=[_user_message("go")],
        context=AgentContext(tools=[tool]),
        config=config,
        emit=emit,
    )
    tool_results = [m for m in new_messages if getattr(m, "role", None) == "toolResult"]
    assert len(tool_results) == 1
    assert tool_results[0].isError is True
    assert "nope" in tool_results[0].content[0].text
    assert tool_executed["yes"] is False  # critical: tool NEVER ran
