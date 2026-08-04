"""internal test fixtures and pi_ai-based scripted stream helpers.

Replaces the previous langchain ScriptedChatModel/FakeChatModel with a
ScriptedStreamFn that plays back pre-built pi_ai event sequences — exactly
the contract EcoAgent now consumes from pi_ai.stream_simple.

Existing test helpers ai_text / ai_tool keep their names and signatures, but
they now return the pi_ai-flavored equivalents (one scripted "turn" each).
make_scripted_model_pair() returns (model, stream_fn) so tests can plug both
into EcoAgent.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import pytest

from agent.pi_ai import Model, ModelCost
from agent.pi_ai.types import (
    AssistantMessage, Context, DoneEvent, SimpleStreamOptions, StartEvent,
    TextContent, TextDeltaEvent, TextEndEvent, TextStartEvent, ToolCall,
    ToolCallEndEvent, ToolCallStartEvent,
)


def _now_ms() -> int:
    return int(time.time() * 1000)


# ── Scripted "turn" descriptors ──────────────────────────────────────────────
# A scripted turn is a small dict describing one assistant response.
# ScriptedStreamFn replays them sequentially across LLM calls.

def ai_text(text: str) -> dict:
    """One turn that emits plain text and stops (no tool calls)."""
    return {"kind": "text", "text": text}


def ai_tool(name: str, args: dict, call_id: str = "call_1", text: str = "") -> dict:
    """One turn that emits an optional text prefix + a single tool_call,
    then stops with toolUse."""
    return {"kind": "tool", "text": text, "name": name, "args": args, "id": call_id}


def ai_text_and_tool(text: str, name: str, args: dict, call_id: str = "call_1") -> dict:
    """One turn that emits text AND a tool call (rare but useful for coverage)."""
    return {"kind": "tool", "text": text, "name": name, "args": args, "id": call_id}


# ── ScriptedStreamFn — pi_ai StreamFunction replaying a scripted sequence ───

class ScriptedStreamFn:
    """A scripted pi_ai StreamFunction. Each call drains one entry from the
    script and emits the corresponding event sequence.

    Compatible with pi_ai.types.StreamFunction protocol (callable returning
    AsyncIterator[AssistantMessageEvent]). Designed to be passed to
    EcoAgent(..., stream_fn=ScriptedStreamFn(script=[...]))."""

    def __init__(self, script: list[dict]):
        self._script = list(script)
        self._cursor = 0

    def __call__(
        self,
        model: Model,
        context: Context,
        options: Optional[SimpleStreamOptions] = None,
    ) -> AsyncIterator:
        if self._cursor >= len(self._script):
            raise AssertionError(
                f"ScriptedStreamFn exhausted: {self._cursor} calls, "
                f"only {len(self._script)} scripted turns"
            )
        turn = self._script[self._cursor]
        self._cursor += 1
        return self._emit_turn(model, turn)

    async def _emit_turn(self, model: Model, turn: dict) -> AsyncIterator:
        partial = AssistantMessage(
            api=model.api, provider=model.provider, model=model.id,
            timestamp=_now_ms(),
        )
        yield StartEvent(partial=partial.model_copy(deep=True))

        idx = -1
        text = turn.get("text") or ""
        if text:
            idx += 1
            yield TextStartEvent(contentIndex=idx, partial=partial.model_copy(deep=True))
            yield TextDeltaEvent(contentIndex=idx, delta=text, partial=partial.model_copy(deep=True))
            partial.content.append(TextContent(text=text))
            yield TextEndEvent(contentIndex=idx, content=text, partial=partial.model_copy(deep=True))

        if turn["kind"] == "tool":
            idx += 1
            yield ToolCallStartEvent(contentIndex=idx, partial=partial.model_copy(deep=True))
            tc = ToolCall(id=turn["id"], name=turn["name"], arguments=dict(turn["args"]))
            partial.content.append(tc)
            yield ToolCallEndEvent(
                contentIndex=idx, toolCall=tc,
                partial=partial.model_copy(deep=True),
            )
            partial.stopReason = "toolUse"
            yield DoneEvent(reason="toolUse", message=partial.model_copy(deep=True))
        else:
            partial.stopReason = "stop"
            yield DoneEvent(reason="stop", message=partial.model_copy(deep=True))


# ── Convenience: build a (model, stream_fn) pair for tests ──────────────────

def make_scripted_model_pair(script: list[dict]) -> tuple[Model, ScriptedStreamFn]:
    """Return (model, stream_fn) wired together so tests can pass them to
    EcoAgent(model=..., stream_fn=...) without further plumbing."""
    model = Model(
        id="scripted", name="scripted",
        api="faux-scripted", provider="scripted",
        baseUrl="", cost=ModelCost(),
    )
    return model, ScriptedStreamFn(script=script)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Empty project dir under tmp_path."""
    d = tmp_path / "Project1"
    d.mkdir()
    return d


@pytest.fixture(autouse=True)
def _isolate_internal_traces(tmp_path_factory, monkeypatch):
    """Redirect write_trace output to a throwaway dir for every internal test.

    Graph-level tests exercise the real nodes, which call write_trace with
    no explicit traces_root — without this they would write into the repo's
    ./traces/ directory. Tests that pass traces_root explicitly are
    unaffected (write_trace prefers the argument over the env var).
    """
    monkeypatch.setenv("internal_TRACES_DIR", str(tmp_path_factory.mktemp("internal_traces")))

