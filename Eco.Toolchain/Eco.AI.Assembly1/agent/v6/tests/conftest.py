"""V6 test fixtures and fake LLM helpers."""
from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeChatModel(BaseChatModel):
    """LLM stub returning a single scripted AIMessage on every invoke."""
    scripted: AIMessage = Field(...)

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self.scripted)])

    def bind_tools(self, tools, **kwargs):
        # Tools bound but never inspected — the scripted reply already encodes any tool_calls.
        return self


class ScriptedChatModel(BaseChatModel):
    """LLM stub returning AIMessages from a fixed list in order, one per invoke."""
    script: list[AIMessage] = Field(default_factory=list)
    _cursor: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted-chat-model"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if self._cursor >= len(self.script):
            raise AssertionError(f"ScriptedChatModel exhausted: {self._cursor} calls, "
                                 f"only {len(self.script)} scripted replies")
        msg = self.script[self._cursor]
        object.__setattr__(self, "_cursor", self._cursor + 1)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools, **kwargs):
        return self


def make_tool_call(name: str, args: dict, call_id: str = "call_1") -> dict:
    """Build a langchain tool_call dict in the shape AIMessage.tool_calls expects."""
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def ai_text(text: str) -> AIMessage:
    return AIMessage(content=text)


def ai_tool(name: str, args: dict, call_id: str = "call_1", text: str = "") -> AIMessage:
    return AIMessage(content=text, tool_calls=[make_tool_call(name, args, call_id)])


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Empty project dir under tmp_path."""
    d = tmp_path / "Project1"
    d.mkdir()
    return d
