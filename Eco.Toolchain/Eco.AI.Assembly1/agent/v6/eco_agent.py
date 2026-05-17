"""EcoAgent — claude-code-style agent loop for V6 nodes."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Literal, Optional, Union
from pydantic import BaseModel
from langchain_core.messages import BaseMessage


@dataclass(frozen=True)
class ToolResult:
    """Outcome of a single tool execution.

    `content` is sent to the LLM as ToolMessage.content. `details` is for
    UI/logs and is NOT sent to the model.
    """
    content: str
    details: Optional[dict] = None
    is_error: bool = False


@dataclass(frozen=True)
class EcoTool:
    """A tool the agent can call. Mirrors pi-harness `Tool`."""
    name: str
    description: str
    args_schema: type[BaseModel]
    execute: Callable[[BaseModel], ToolResult]


class EventType(str, Enum):
    START          = "start"
    TEXT_DELTA     = "text_delta"        # streaming visible content (final answer tokens)
    THINKING_DELTA = "thinking_delta"    # streaming reasoning/thinking tokens
    TOOL_START     = "tool_call_start"
    TOOL_END       = "tool_call_end"
    TOOL_UPDATE    = "tool_update"
    ITERATION      = "iteration"
    DONE           = "done"
    NO_TOOL_CALL   = "no_tool_call"
    MAX_ITERS      = "max_iters"
    ERROR          = "error"


@dataclass(frozen=True)
class EcoAgentEvent:
    type: EventType
    data: dict


@dataclass(frozen=True)
class EcoAgentResult:
    status: Literal["done", "no_tool_call", "max_iters", "error"]
    stop_tool_name: str
    stop_payload: dict
    history: list[BaseMessage]
    error: str


# ── append below the data types ───────────────────────────────────────────
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import ValidationError


def _to_langchain_tool(t: EcoTool) -> StructuredTool:
    """Wrap an EcoTool as a LangChain StructuredTool — the model side only
    needs `name`/`description`/`args_schema` for bind_tools; we never let
    LangChain dispatch the execute (we do that manually in the loop)."""
    def _stub(**_kw):
        raise RuntimeError("EcoTool must be executed via EcoAgent loop, not StructuredTool")
    return StructuredTool.from_function(
        func=_stub,
        name=t.name,
        description=t.description,
        args_schema=t.args_schema,
    )


class EcoAgent:
    """Claude-code-style agent loop. Synchronous. Mirrors pi-harness Agent."""

    def __init__(
        self,
        *,
        llm: BaseChatModel,
        system_prompt: str,
        tools: list[EcoTool],
        stop_tool: Union[str, list[str], None] = None,
        max_iters: int = 25,
        prepare_arguments: Optional[Callable[[str, dict], dict]] = None,
        before_tool_call:  Optional[Callable[[str, BaseModel], Optional[dict]]] = None,
        after_tool_call:   Optional[Callable[[str, BaseModel, ToolResult], ToolResult]] = None,
        on_event:          Optional[Callable[[EcoAgentEvent], None]] = None,
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.tools = {t.name: t for t in tools}
        self.stop_tools = (
            set() if stop_tool is None
            else {stop_tool} if isinstance(stop_tool, str)
            else set(stop_tool)
        )
        self.max_iters = max_iters
        self.prepare_arguments = prepare_arguments
        self.before_tool_call = before_tool_call
        self.after_tool_call = after_tool_call
        self.on_event = on_event or (lambda _e: None)

        self._llm_bound = llm.bind_tools(
            [_to_langchain_tool(t) for t in tools]
        )

    # ── helpers ────────────────────────────────────────────────────────────
    def _emit(self, event_type: EventType, data: Optional[dict] = None):
        self.on_event(EcoAgentEvent(type=event_type, data=data or {}))

    def _normalize_seed(self, seed) -> list[BaseMessage]:
        if isinstance(seed, str):
            return [HumanMessage(content=seed)]
        return list(seed)

    @staticmethod
    def _extract_chunk_text(chunk_content) -> str:
        """`content` on AIMessageChunk is usually a string but providers may
        send a list of typed parts ({"type": "text", "text": "..."}). Pull
        only the text fragments so tool_use / image_url parts don't leak
        into the stream as garbage."""
        if isinstance(chunk_content, str):
            return chunk_content
        if isinstance(chunk_content, list):
            parts: list[str] = []
            for part in chunk_content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    parts.append(str(part.get("text", "")))
            return "".join(parts)
        return ""

    @staticmethod
    def _extract_chunk_reasoning(chunk) -> str:
        """OpenRouter forwards reasoning models' chain-of-thought in
        AIMessageChunk.additional_kwargs under one of several keys depending
        on the provider/version. Coalesce them so the UI sees a single
        thinking-stream regardless of vendor."""
        ak = getattr(chunk, "additional_kwargs", None) or {}
        for key in ("reasoning_content", "reasoning", "thinking"):
            val = ak.get(key)
            if isinstance(val, str) and val:
                return val
        return ""

    def _stream_llm(self, history: list[BaseMessage]) -> BaseMessage:
        """Stream the bound LLM, emit token deltas, return the merged AIMessage.

        Two execution paths:
        - pi_ai bridge (preferred): when llm is a langchain_openai.ChatOpenAI
          pointed at an OpenAI-compat endpoint, route through pi_ai to get
          correct reasoning passthrough (langchain_openai 1.2.1 drops
          delta.reasoning silently).
        - legacy llm.stream(): for ScriptedChatModel in tests and any other
          BaseChatModel that doesn't expose the ChatOpenAI shape.

        Why streaming inside a synchronous loop: LangGraph nodes are invoked
        synchronously by `astream(stream_mode="updates")`, so we cannot await
        here. The pi_ai bridge uses asyncio.run() inside; ChatModel.stream()
        yields chunks synchronously.
        """
        # Try the pi_ai bridge first — it's the whole reason we're here.
        from agent.v6._pi_ai_bridge import is_chat_openai_like, stream_eco_via_pi_ai
        if is_chat_openai_like(self.llm):
            return stream_eco_via_pi_ai(
                llm=self.llm,
                history=history,
                eco_tools=list(self.tools.values()),
                on_text_delta=lambda d: self._emit(EventType.TEXT_DELTA, {"content": d}),
                on_thinking_delta=lambda d: self._emit(EventType.THINKING_DELTA, {"content": d}),
            )

        # Legacy path: ScriptedChatModel in tests and other non-ChatOpenAI providers.
        merged = None
        for chunk in self._llm_bound.stream(history):
            merged = chunk if merged is None else merged + chunk
            text = self._extract_chunk_text(chunk.content)
            if text:
                self._emit(EventType.TEXT_DELTA, {"content": text})
            reasoning = self._extract_chunk_reasoning(chunk)
            if reasoning:
                self._emit(EventType.THINKING_DELTA, {"content": reasoning})
        if merged is None:
            from langchain_core.messages import AIMessage
            return AIMessage(content="")
        return merged

    # ── main entrypoint ────────────────────────────────────────────────────
    def run(self, seed) -> EcoAgentResult:
        self._emit(EventType.START)
        history: list[BaseMessage] = [SystemMessage(content=self.system_prompt)]
        history.extend(self._normalize_seed(seed))

        for i in range(self.max_iters):
            self._emit(EventType.ITERATION, {"i": i})

            try:
                resp = self._stream_llm(history)
            except Exception as e:
                self._emit(EventType.ERROR, {"reason": str(e)})
                return EcoAgentResult(
                    status="error", stop_tool_name="", stop_payload={},
                    history=history, error=str(e),
                )
            history.append(resp)

            tool_calls = getattr(resp, "tool_calls", None) or []
            if not tool_calls:
                self._emit(EventType.NO_TOOL_CALL)
                return EcoAgentResult(
                    status="no_tool_call", stop_tool_name="", stop_payload={},
                    history=history, error="",
                )

            for tc in tool_calls:
                name = tc["name"]
                raw_args = tc.get("args", {})
                call_id = tc["id"]
                self._emit(EventType.TOOL_START, {"name": name, "args": raw_args})

                if name not in self.tools and name not in self.stop_tools:
                    history.append(ToolMessage(
                        content=f"UNKNOWN TOOL: {name}",
                        tool_call_id=call_id,
                        status="error",
                    ))
                    continue

                # 1. prepare_arguments shim
                cooked = self.prepare_arguments(name, raw_args) if self.prepare_arguments else raw_args

                # 2. resolve schema (stop tool may or may not be in self.tools)
                tool = self.tools.get(name)
                schema = tool.args_schema if tool else None
                if schema is None:
                    # Stop-only tool with no schema — accept the raw dict
                    args_obj = type("StopArgs", (), {"model_dump": lambda self=cooked: cooked})()
                else:
                    try:
                        args_obj = schema.model_validate(cooked)
                    except ValidationError as ve:
                        history.append(ToolMessage(
                            content=f"ARGS ERROR: {ve}",
                            tool_call_id=call_id,
                            status="error",
                        ))
                        continue

                # 3. before_tool_call gate
                if self.before_tool_call:
                    gate = self.before_tool_call(name, args_obj)
                    if gate and gate.get("block"):
                        history.append(ToolMessage(
                            content=f"BLOCKED: {gate.get('reason', '')}",
                            tool_call_id=call_id,
                            status="error",
                        ))
                        continue

                # 4. stop tool — short-circuit return
                if name in self.stop_tools:
                    payload = args_obj.model_dump() if hasattr(args_obj, "model_dump") else dict(cooked)
                    self._emit(EventType.DONE, {"stop_tool": name, "payload": payload})
                    return EcoAgentResult(
                        status="done", stop_tool_name=name,
                        stop_payload=payload, history=history, error="",
                    )

                # 5. execute
                try:
                    result = tool.execute(args_obj)
                except Exception as e:
                    history.append(ToolMessage(
                        content=f"TOOL ERROR: {e}",
                        tool_call_id=call_id,
                        status="error",
                    ))
                    continue

                # 6. after_tool_call hook
                if self.after_tool_call:
                    result = self.after_tool_call(name, args_obj, result)

                self._emit(EventType.TOOL_END, {
                    "name": name, "is_error": result.is_error, "details": result.details,
                })
                history.append(ToolMessage(
                    content=result.content,
                    tool_call_id=call_id,
                    status="error" if result.is_error else "success",
                ))

        self._emit(EventType.MAX_ITERS)
        return EcoAgentResult(
            status="max_iters", stop_tool_name="", stop_payload={},
            history=history, error="",
        )
