"""Agent class smoke tests."""
from __future__ import annotations

import asyncio
import time

import pytest
from pydantic import BaseModel

from agent.pi_ai import Model, ModelCost
from agent.pi_ai.api_registry import register_provider
from agent.pi_ai.providers.faux import make_faux_provider
from agent.pi_agent_core import Agent, AgentOptions, AgentTool, AgentToolResult
from agent.pi_ai.types import TextContent


def _model(api: str) -> Model:
    return Model(id="m", name="m", api=api, provider="faux", baseUrl="", cost=ModelCost())


def _user_message(text: str) -> dict:
    return {"role": "user", "content": text, "timestamp": int(time.time() * 1000)}


class _NoArgs(BaseModel):
    pass


async def _ok_exec(call_id, params, signal, on_update):
    return AgentToolResult(content=[TextContent(text="done")], details=None)


@pytest.mark.asyncio
async def test_agent_prompt_text_only():
    register_provider("faux-agent-text", make_faux_provider(text="hello"))
    a = Agent(AgentOptions(initial_state={
        "systemPrompt": "sys",
        "model": _model("faux-agent-text"),
    }))
    events = []

    async def listener(ev, sig):
        events.append(ev)

    a.subscribe(listener)
    await a.prompt("hi")
    types = [e.type for e in events]
    assert "agent_start" in types
    assert "agent_end" in types
    assert any(getattr(m, "role", None) == "assistant" for m in a.state.messages)


@pytest.mark.asyncio
async def test_agent_subscribe_unsubscribe():
    register_provider("faux-agent-sub", make_faux_provider(text="hi"))
    a = Agent(AgentOptions(initial_state={
        "model": _model("faux-agent-sub"),
    }))
    seen = []

    async def listener(ev, sig):
        seen.append(ev.type)

    unsubscribe = a.subscribe(listener)
    await a.prompt("first")
    first_count = len(seen)
    unsubscribe()
    await a.prompt("second")
    assert len(seen) == first_count  # no new events after unsubscribe


@pytest.mark.asyncio
async def test_agent_rejects_concurrent_prompt():
    register_provider("faux-agent-conc", make_faux_provider(text="hi"))
    a = Agent(AgentOptions(initial_state={"model": _model("faux-agent-conc")}))

    async def slow_listener(ev, sig):
        if ev.type == "agent_start":
            await asyncio.sleep(0.05)

    a.subscribe(slow_listener)
    task = asyncio.create_task(a.prompt("first"))
    await asyncio.sleep(0.01)
    with pytest.raises(RuntimeError, match="already processing"):
        await a.prompt("second")
    await task


@pytest.mark.asyncio
async def test_agent_steer_and_followup_queues():
    a = Agent(AgentOptions())
    assert a.has_queued_messages() is False
    a.steer(_user_message("steer1"))
    assert a.has_queued_messages() is True
    a.clear_steering_queue()
    assert a.has_queued_messages() is False
    a.follow_up(_user_message("fu1"))
    a.follow_up(_user_message("fu2"))
    assert a.has_queued_messages() is True
    a.clear_all_queues()
    assert a.has_queued_messages() is False


@pytest.mark.asyncio
async def test_agent_reset_clears_state():
    register_provider("faux-agent-reset", make_faux_provider(text="hi"))
    a = Agent(AgentOptions(initial_state={"model": _model("faux-agent-reset")}))
    await a.prompt("hello")
    assert len(a.state.messages) >= 2  # user + assistant
    a.reset()
    assert a.state.messages == []
    assert a.state.isStreaming is False
    assert a.state.pendingToolCalls == set()


@pytest.mark.asyncio
async def test_agent_set_tools_copy_on_assign():
    a = Agent()
    tools_list = [
        AgentTool(name="t", description="d", label="L",
                  parameters=_NoArgs, execute=_ok_exec),
    ]
    a.set_tools(tools_list)
    tools_list.clear()
    assert len(a.state.tools) == 1  # internal copy unchanged
