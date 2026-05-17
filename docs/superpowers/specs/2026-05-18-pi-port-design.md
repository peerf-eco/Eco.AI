# pi-mono → Python port (1:1 architectural translation)

> **Status:** Draft, awaiting user review
> **Author:** Claude Opus 4.7 (brainstorming session, 2026-05-18)
> **Branch:** `feat/v6-five-node-pipeline` (содержит v7 архитектуру)
> **Replaces:** prior handoff plan to migrate via hermes-agent (rejected — user clarified «pi-harness, not hermes»)

## Why this spec exists

EcoOS V7 agent loop (`agent/v6/eco_agent.py`) использует `langchain_openai 1.2.1`, который **молча выкидывает** поле `delta.reasoning` / `delta.reasoning_content` от reasoning-моделей через OpenRouter (Kimi K2.6, GLM, MiMo, MiniMax, Nemotron). Это приводит к двум проблемам:

1. **UX:** UI thinking-блоки остаются пустыми, хотя модель генерирует chain-of-thought.
2. **Cost:** Мы платим за невидимые reasoning_tokens (на простом запросе «17×23» к Kimi K2.6 — 37 из 62 completion-токенов = 60%).

Прямые curl-эксперименты подтвердили, что reasoning поле приходит на wire (см. `handoff.md:64-69`). Проблема — в адаптере, не в провайдере.

Пользователь сформулировал требование: «Нужно один в один, как в pi, но на Python». **pi** = TypeScript-фреймворк `@mariozechner/pi-*` в `F:/pi-harness/pi-mono/packages/`. Цель этого спека — портировать архитектуру pi на Python с сохранением API surface (семантически идиоматично, без попыток имитировать TypeScript-only фичи типа declaration merging).

## Scope

Финализированный после 5-вопросной brainstorming-сессии:

| Параметр | Значение | Обоснование |
|---|---|---|
| Провайдер | `openai-completions` (один) | Покрывает все нужные модели через OpenRouter (Kimi/GLM/MiMo/MiniMax/Nemotron). Другие провайдеры — позже отдельным спеком. |
| Слои | `pi_ai` + `pi_agent_core` (2 из 3) | `pi-coding-agent` (read/bash/edit/write tools) нарушит capability gating нашего tester'а; EcoOS-tools уже реализованы. |
| Размещение | `Eco.Toolchain/Eco.AI.Assembly1/agent/pi_ai/` + `agent/pi_agent_core/` | Прямое вложение в проект, без отдельного pyproject.toml. |
| Imports | `from agent.pi_ai import ...`, `from agent.pi_agent_core import Agent, AgentTool` | Без префикса `eco_` — нет конфликта на PyPI (проверено). |
| Integration с v7 | Целиком заменить `EcoAgent` | Адаптерный слой не оправдан — port должен сразу обеспечить идиоматичный API. |
| Стиль | Async-first (1:1 с TS pi) | TS pi полностью async; FastAPI native await; orchestrator/tools тоже переписываются на async. |
| Дисциплина тестов | Code-first + smoke-тесты per layer | Не TDD, но safety net против накопления багов. |
| Timeline | ~3 недели (port 2 нед + integration 0.5 нед + cutover 0.5 нед) | См. migration plan ниже. |

## Out of scope (explicit)

Чтобы избежать scope creep:

- Любые провайдеры кроме `openai-completions`.
- `pi-coding-agent` слой (третий слой pi-mono).
- Browser proxy (`pi_agent_core/proxy.py` — будет stub'ом).
- OAuth для любого провайдера (только `OPENROUTER_API_KEY` через env).
- Prompt caching beyond OpenRouter's default behavior.
- MCP-server integration.
- Telemetry / OpenTelemetry layer.
- Web UI / TUI (фронтенд у нас свой Next.js).

## Architecture overview

### Two-layer port

```
agent/
├── pi_ai/                              ← Layer 1: provider abstraction
│   ├── __init__.py                     reexports: complete, stream_simple, get_model,
│   │                                              AssistantMessageEvent, Tool, Model, ...
│   ├── types.py                        Message, AssistantMessage, ToolResultMessage, ToolCall,
│   │                                   TextContent, ThinkingContent, ImageContent,
│   │                                   AssistantMessageEvent (discriminated union),
│   │                                   StopReason, StreamOptions, SimpleStreamOptions, Usage,
│   │                                   Model, Tool, Context, OpenAICompletionsCompat,
│   │                                   OpenRouterRouting, StreamFunction (Protocol)
│   ├── stream.py                       complete() and stream_simple() — thin wrappers
│   │                                   selecting provider by model.api
│   ├── models.py                       get_model(provider, id) → Model factory
│   ├── env_api_keys.py                 OPENAI_API_KEY / OPENROUTER_API_KEY / etc lookup
│   ├── api_registry.py                 maps api: str → StreamFunction (registry pattern,
│   │                                   mirrors register-builtins.ts)
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── openai_completions.py       async def stream_openai_completions(model, ctx, opts)
│   │   │                               → AsyncIterator[AssistantMessageEvent]
│   │   ├── transform_messages.py       AssistantMessage[] → OpenAI message array
│   │   │                               (handle thinking-as-text, tool_results, ...)
│   │   ├── simple_options.py           thinking-level + reasoning-effort mapping
│   │   │                               (reasoning_effort, thinkingFormat="openrouter", ...)
│   │   └── faux.py                     scripted message-sequence provider for tests
│   └── utils/
│       ├── event_stream.py             SSE chunk parser (async generator over httpx stream)
│       ├── json_parse.py               partial-JSON accumulator (для toolcall_delta args,
│       │                               замена @sinclair/partial-json)
│       ├── validation.py               pydantic-based tool args validation (замена AJV)
│       ├── hash.py                     simple sha256 для cache hint
│       └── overflow.py                 context-window detection helpers
│
└── pi_agent_core/                      ← Layer 2: agent loop + state
    ├── __init__.py                     reexports: Agent, AgentTool, AgentEvent,
    │                                              AgentState, AgentToolResult, ...
    ├── types.py                        AgentMessage (= Message | CustomAgentMessages),
    │                                   AgentState, AgentTool, AgentToolResult,
    │                                   AgentEvent (discriminated union), AgentLoopConfig,
    │                                   BeforeToolCallContext, AfterToolCallContext,
    │                                   StreamFn, ToolExecutionMode
    ├── agent.py                        class Agent — high-level: state mgmt,
    │                                   event subscribers, prompt(), append(), abort()
    ├── agent_loop.py                   async def run_agent_loop(...) — low-level:
    │                                   turn loop, tool execution, hook orchestration
    └── proxy.py                        (stub) browser-relay для будущего web UI
```

### Что НЕ портируется из pi-mono

- `pi-ai/providers/`: anthropic, google*, bedrock, mistral, openai-responses*, azure-openai-responses, openai-codex-responses, gemini-cli, github-copilot-headers
- `pi-ai/cli.ts` (отдельный pi-ai CLI)
- `pi-ai/oauth/` (только Anthropic/Google OAuth)
- `pi-ai/bedrock-provider.ts`
- весь `pi-mono/packages/coding-agent/`, `tui/`, `web-ui/`, `pods/`, `mom/`

### Размер итогового кода

| Модуль | Python LOC (оценка) |
|---|---|
| `pi_ai/types.py` | ~350 |
| `pi_ai/stream.py + models.py + api_registry.py + env_api_keys.py` | ~250 |
| `pi_ai/providers/openai_completions.py + transform_messages.py + simple_options.py + faux.py` | ~1100 |
| `pi_ai/utils/*` | ~400 |
| `pi_agent_core/types.py` | ~300 |
| `pi_agent_core/agent.py` | ~500 |
| `pi_agent_core/agent_loop.py` | ~600 |
| Smoke-тесты (per layer + integration) | ~940 |
| **Итого port** | **~4440** |
| Integration changes (orchestrator/tools/agents/server переписать на async) | ~600 |
| **GRAND TOTAL** | **~5040 LOC Python** |

## Data flow

```
                 ┌─────────────────────────────────────────────────────────────┐
USER       ──>   │ orchestrator.run(user_prompt)                              │
                 │   await agent.prompt(user_prompt)                          │
                 └──────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
                 ┌─────────────────────────────────────────────────────────────┐
Agent.prompt     │ 1. append UserMessage to state.messages                    │
                 │ 2. emit AgentEvent{type:"agent_start"}                     │
                 │ 3. await run_agent_loop(config, signal)                    │
                 │ 4. emit AgentEvent{type:"agent_end", messages}             │
                 └──────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼  (turn loop)
                 ┌─────────────────────────────────────────────────────────────┐
run_agent_loop   │ for turn in count():                                       │
                 │   emit AgentEvent{type:"turn_start"}                       │
                 │                                                             │
                 │   messages = await transformContext(state.messages)        │ ← hook
                 │   llm_messages = await convertToLlm(messages)              │ ← hook
                 │                                                             │
                 │   stream = stream_simple(model, ctx, opts)                 │ ← LAYER 1
                 │   async for pi_event in stream:                            │
                 │     emit AgentEvent{type:"message_update", pi_event}       │ ← bridge
                 │     accumulate into partial AssistantMessage               │
                 │                                                             │
                 │   if pi_event.type == "done":                              │
                 │     for tc in final_message.tool_calls:                    │
                 │       await execute_tool(tc)                               │ ← parallel|sequential
                 │     if no tool_calls: BREAK                                │
                 │   elif pi_event.type == "error":                          │
                 │     emit AgentEvent{type:"turn_end", error}; BREAK         │
                 │                                                             │
                 │   if no more tool_calls AND no steering: BREAK             │
                 └──────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
                 ┌─────────────────────────────────────────────────────────────┐
stream_simple    │ provider = api_registry[model.api]    # "openai-completions"│
                 │ return provider(model, ctx, opts)                          │ ← LAYER 1, async iter
                 └──────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
                 ┌─────────────────────────────────────────────────────────────┐
openai_completions│  async with httpx.AsyncClient() as client:                │
                 │    async with client.stream("POST", url, json=...) as r:   │
                 │      async for chunk in event_stream.parse_sse(r):         │
                 │        delta = chunk["choices"][0]["delta"]                │
                 │        if delta.reasoning|reasoning_content:               │ ★ HERE
                 │          yield {type:"thinking_delta", delta:...}          │
                 │        if delta.content:                                   │
                 │          yield {type:"text_delta", delta:...}              │
                 │        if delta.tool_calls:                                │
                 │          accumulate via partial_json, yield toolcall_delta │
                 │  yield {type:"done", message: final_AssistantMessage}     │
                 └─────────────────────────────────────────────────────────────┘
```

## Event protocol

### Layer 1: `pi_ai.AssistantMessageEvent`

Внутренний поток одного LLM-call'а:

| event | when | data |
|---|---|---|
| `start` | первый chunk пришёл | `partial: AssistantMessage` |
| `text_start` / `text_delta` / `text_end` | model emits visible content | `delta: str`, `content_index: int` |
| `thinking_start` / `thinking_delta` / `thinking_end` | reasoning_content приходит ★ | `delta: str` |
| `toolcall_start` / `toolcall_delta` / `toolcall_end` | tool_calls accumulate | `delta: str` (JSON fragments), затем full `ToolCall` |
| `done` | stop_reason in {stop, length, tool_use} | `message: AssistantMessage` |
| `error` | provider error / network / abort | `error: AssistantMessage{stop_reason: error\|aborted}` |

### Layer 2: `pi_agent_core.AgentEvent`

Внешний поток всего Agent'а:

| event | when | покрывает |
|---|---|---|
| `agent_start` | `Agent.prompt()` начало | один раз на prompt |
| `agent_end` | весь loop завершён | один раз |
| `turn_start` | начало одной LLM-итерации | повторяется N раз |
| `turn_end` | LLM-call + tools завершены | повторяется N раз |
| `message_start` | UserMessage / AssistantMessage / ToolResultMessage добавлено | один раз на message |
| `message_update` | **обёртка вокруг AssistantMessageEvent** ← bridge | streaming во время LLM-call'а |
| `message_end` | message финализирован | один раз на message |
| `tool_execution_start` / `update` / `end` | tool вызывается | по одному set'у на tool_call |

### Bridge между слоями

`message_update` инкапсулирует raw `AssistantMessageEvent` в поле `assistant_message_event`. Подписчик (backend WebSocket handler) разбирает inner type:
- `thinking_delta` → `{phase: "thinking", content: delta}` для thinking-block UI
- `text_delta` → `{phase: "text", content: delta}` для main content
- `toolcall_*` → progress markers

## Reasoning passthrough — критическая часть

В `providers/openai_completions.py`, цикл по SSE chunks (точная replica `hermes-agent/run_agent.py:5673-5677`):

```python
async for chunk_dict in parse_sse(response):
    choices = chunk_dict.get("choices") or []
    if not choices:
        if usage := chunk_dict.get("usage"):
            final_usage = usage
        continue
    delta = choices[0].get("delta") or {}

    # ★ Это то, чего НЕ делает langchain_openai 1.2.1:
    reasoning = delta.get("reasoning") or delta.get("reasoning_content")
    if reasoning:
        yield AssistantMessageEvent(type="thinking_delta", delta=reasoning, ...)

    if content := delta.get("content"):
        yield AssistantMessageEvent(type="text_delta", delta=content, ...)

    if tool_calls := delta.get("tool_calls"):
        # accumulate via partial_json, emit toolcall_delta with each chunk
        ...
```

Также читаем `reasoning_details[]` (OpenRouter unified format) если присутствует.

## Error handling

Три источника ошибок:

| Источник | Where caught | Result |
|---|---|---|
| Provider HTTP error / network / SSE parse fail | `providers/openai_completions.py` try/except вокруг httpx.stream | `yield AssistantMessageEvent(type="error", error=AssistantMessage(stop_reason="error", error_message=str(e)))`. **Никогда не raise** из stream — контракт TS pi. |
| `AbortSignal` (asyncio.Event set externally) | `providers/openai_completions.py` проверяет signal в loop body | `yield error event` со `stop_reason="aborted"` |
| Tool `execute` throws | `agent_loop.py` оборачивает `await tool.execute(...)` в try/except | Создаёт `ToolResultMessage(is_error=True, content=[TextContent(text=str(e))])`, передаёт LLM на retry |

**Никаких exceptions из публичного API.** `Agent.prompt()` либо успешно дойдёт до `agent_end`, либо последнее `AssistantMessage` будет иметь `stop_reason in {"error", "aborted"}` + `error_message`.

**AbortSignal:** `asyncio.Event` устанавливается извне (например, websocket disconnect). Каждый layer проверяет `if signal.is_set(): yield error_event; return`. `httpx.AsyncClient` поддерживает abort через `asyncio.wait_for` с таймаутом или гонкой через `asyncio.create_task`.

## Capability gating — preserved

Текущий load-bearing инвариант: tester не имеет write/edit/build/pull tools (см. `feedback_tester_honest_stop.md`). После port'а:

```python
# agents/tester.py (после миграции)
def make_tester(*, model, project_dir, on_event):
    read_tools = make_read_tools(project_dir)         # async list_dir, read_file
    runtime_tools = [make_run_artifact_tool(...)]     # async run_artifact (read-only)
    report_tools = [make_done_tool(), make_fail_tool(), make_to_coder_tool()]

    return Agent(
        initial_state={
            "system_prompt": TESTER_SYSTEM_PROMPT,
            "model": model,
            "tools": [*read_tools, *runtime_tools, *report_tools],
            # NO write_file, NO run_build, NO ecoos_pull — STRUCTURAL invariant
        },
        on_event=on_event,
    )
```

Тест `test_tester_CANNOT_modify_anything_structural_check` переписывается на проверку `agent.state.tools`. Инвариант сохраняется.

## Stop-tools — preserved

Текущий контракт: `to_coder(message: str)`, `to_tester(message: str)`, `done(message: str)`, `fail(message: str)` — все принимают **только `message: str`** (см. `feedback_no_structured_stop_tools.md`).

```python
class HandoffMessage(BaseModel):
    message: str = Field(description="Markdown handoff payload")

def make_to_coder_tool() -> AgentTool[HandoffMessage]:
    return AgentTool(
        name="to_coder",
        label="Hand off to coder",
        description="...",
        parameters=HandoffMessage,
        execute=...,  # noop: stop-tool, orchestrator handles routing by tool name
    )
```

Routing по `tool_name` сохраняется (orchestrator смотрит на final assistant message's tool_calls). Инвариант сохраняется.

## Testing strategy

Code-first + smoke-тест на каждый слой как safety net:

| Слой | Smoke-тест | Что проверяет | LOC |
|---|---|---|---|
| `pi_ai/types.py` | `test_types_smoke.py` | Discriminated unions сериализуются через pydantic. `AssistantMessageEvent` round-trip. `Model.compat` constrained. | ~80 |
| `pi_ai/providers/openai_completions.py` | `test_openai_completions_smoke.py` | Через `respx` mock: SSE → text_delta + done. SSE с reasoning → thinking_delta + text_delta + done. SSE с tool_calls → toolcall_start + delta (accumulation) + end + done. Network error mid-stream → error event с partial message. | ~250 |
| `pi_ai/utils/json_parse.py` | `test_partial_json.py` | Аккумуляция `{"a":` + `1,"b":` + `"x"}` → `{"a": 1, "b": "x"}`. Невалидный JSON → ValueError. | ~60 |
| `pi_agent_core/agent.py` | `test_agent_smoke.py` | Agent с faux-провайдером: один-turn без tools → done. С one tool_call → execute → done. Tool throws → ToolResultMessage{is_error=True}. abort() → error event с stop_reason="aborted". | ~200 |
| `pi_agent_core/agent_loop.py` | `test_agent_loop_smoke.py` | Hooks fire в правильном порядке: transformContext → convertToLlm → beforeToolCall → execute → afterToolCall. beforeToolCall blocks → tool не выполняется. Parallel execution: 2 tool_calls с asyncio.sleep — completion order detected. | ~200 |
| **Integration** | `test_v7_integration_with_pi.py` | Полный pipeline architect→coder→tester с faux-моделью. Capability gating: tester не имеет write_file в bound tools. | ~150 |
| **ИТОГО smoke** | | | **~940 LOC** |

**Существующие 119 тестов** переписываются под новый `Agent` API на phase 3. Большинство остаются 1:1 (orchestrator/handoff/tools тесты не трогают EcoAgent внутренности). Переписать нужно `test_agents.py` (13 тестов) и `test_entry.py` (11 тестов).

**Faux-provider** в `pi_ai/providers/faux.py` (port `pi-mono/packages/ai/src/providers/faux.ts`, ~499 LOC TS → ~400 Python). Принимает scripted message sequence и эмитит через AssistantMessageEvent stream. Critical для тестирования без реального LLM-call'а.

## Migration plan

### Phase 1: pi_ai (Week 1)

| Day | Work |
|---|---|
| 1-2 | `types.py`, `env_api_keys.py`, `models.py`, `utils/*` (event_stream, json_parse, validation, hash, overflow) |
| 3-5 | `providers/openai_completions.py` + `transform_messages.py` + `simple_options.py` |
| 5 | `providers/faux.py` + `test_openai_completions_smoke.py` + `test_partial_json.py` + `test_types_smoke.py` |

**Checkpoint:** `pi_ai/__init__.py` exports работают, smoke-тесты зелёные.

### Phase 2: pi_agent_core (Week 2)

| Day | Work |
|---|---|
| 6-7 | `types.py`, `AgentEvent` dispatch |
| 8-10 | `agent_loop.py` (run_agent_loop с tool execution, hooks, abort) |
| 11 | `agent.py` (Agent class facade, state mgmt, subscribers) |
| 12 | `test_agent_smoke.py` + `test_agent_loop_smoke.py` |

**Checkpoint:** end-to-end faux-провайдер прогоняется через `Agent.prompt()`, события эмитятся, hooks работают.

### Phase 3: Integration (Week 2.5)

| Day | Work |
|---|---|
| 13 | Переписать `tools/io.py`, `build.py`, `runtime.py`, `marketplace.py`, `components.py` на async (asyncio.create_subprocess_exec) |
| 14 | Переписать `agents/architect.py`, `coder.py`, `tester.py` на pi_agent_core.Agent |
| 15 | Переписать `orchestrator.py` (async), `entry.py` (Model вместо llm) |
| 16 | Переписать 119 тестов под новый API |
| 17 | Переписать `backend/server.py @app.websocket("/ws/v7/chat")` под AgentEvent |

**Checkpoint:** 119 тестов + новые ~940 smoke-тестов зелёные.

### Phase 4: Cutover + smoke в UI (Days 18-19)

| Day | Work |
|---|---|
| 18 | Запуск через `docker compose up -d`, smoke prompt «Собери калькулятор» на Kimi K2.6. Architect должен скачать `Eco.Math.C89`, hand-off coder'у. UI должен показывать thinking-блоки с реальным reasoning текстом ★ |
| 19 | Исправление найденных регрессий, удаление dead-code (старый EcoAgent), update MEMORY.md (новый feedback-файл «pi-port completed») |

**Final checkpoint:** v7 работает на pi-portированной инфраструктуре, reasoning passthrough видим в UI, MEMORY.md обновлён.

## Files to change in v7 integration

| Файл | Сейчас | После port'а | Δ LOC |
|---|---|---|---|
| `agent/v6/eco_agent.py` | 291 LOC, кастомный класс | **Удалён**. Заменён на pi_agent_core.Agent | -291 |
| `agent/v6/agents/architect.py` | EcoAgent + EcoTool | `from agent.pi_agent_core import Agent, AgentTool` | ~+30 |
| `agent/v6/agents/coder.py` | то же | то же | ~+30 |
| `agent/v6/agents/tester.py` | то же | то же | ~+30 |
| `agent/v6/orchestrator.py` | sync `def run(...)` | `async def run(...)` | ~+50 |
| `agent/v6/entry.py` | `build_v7_pipeline(llm, ...)` | `build_v7_pipeline(model, ...)` где model — `pi_ai.Model` | ~+10 |
| `agent/v6/tools/handoff.py` | возвращает EcoTool | возвращает AgentTool | ~+10 |
| `agent/v6/tools/io.py, build.py, runtime.py, marketplace.py, components.py` | sync subprocess | `async def`, `asyncio.create_subprocess_exec` | ~+150 |
| `backend/server.py @app.websocket("/ws/v7/chat")` | `asyncio.to_thread(orch.run, ...)` | прямой `await orch.run(...)`, event handler читает AgentEvent | ~+40 |
| `agent/v6/tests/*.py` (119 тестов) | mock EcoAgent | mock pi_agent_core.Agent + AgentTool | ~+200 |

## Risks + mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `partial-json-parser` pip-пакет неактивный/багованный → пишем свой | Medium | Low (~100 LOC своего кода) | Сразу подготовить fallback custom-парсер; не блокирующий. |
| OpenRouter routing вызывает upstream который НЕ поддерживает reasoning passthrough (e.g. DeepInfra endpoints) | Medium | Medium | В `OpenAICompletionsCompat.openRouterRouting.ignore: [...]` для блэклиста; задокументировать known-good endpoints. |
| Использовать `openai` SDK vs `httpx.AsyncClient` напрямую — spec mismatch | Low | Low | Выбираем `httpx.AsyncClient` напрямую (как в `hermes-agent`). OpenAI SDK добавит лишний слой Pydantic-парсинга, который может потерять `reasoning` (как langchain). |
| Pydantic v2 strict mode отвергает provider responses с unknown fields | Medium | Medium | В наших моделях ставим `model_config = ConfigDict(extra="allow")`. |
| Переписка orchestrator + tools на async ломает что-то непредвиденное | Medium | High | Phase 3 — отдельный milestone с smoke-тестами **перед** cutover. Откат к sync-only EcoAgent через `git revert` если что. |
| `asyncio.create_subprocess_exec` на Windows ведёт себя иначе чем на Linux | Medium | Medium | `WindowsProactorEventLoopPolicy` + явный `asyncio.set_event_loop_policy(...)` в Agent.__init__ если `sys.platform == "win32"`. |
| Тестировать reasoning passthrough без real Kimi API — невозможно | Low | Low | Используем `respx` mock + capture'нутые curl-ответы от Kimi (формат known из предыдущей сессии). |

## Mapping TS → Python (key abstractions)

| TS-абстракция | Python-эквивалент | Заметки |
|---|---|---|
| `@sinclair/typebox` `Type.Object({...})` + `Static<typeof>` | `pydantic.BaseModel` subclass | Менее лаконично, идиоматичнее Python. |
| `AsyncIterable<AssistantMessageEvent>` | `AsyncIterator` через `async def __aiter__` + `yield` (PEP 525) | Прямой эквивалент. |
| Discriminated unions (`{type:"a",...} \| {type:"b",...}`) | `pydantic.Field(discriminator="type")` + `Annotated[Union[...], Field(...)]` | Прямой эквивалент. |
| `AbortSignal` + `AbortController` | `asyncio.Event` + `task.cancel()` | Эквивалент по семантике. |
| Hooks (`beforeToolCall: async (ctx, signal) => ...`) | `Callable[[Context, asyncio.Event], Awaitable[Result]]` | Прямой эквивалент. |
| Accessor properties (`set tools(...)`, `get tools()`) | `@property` декораторы | Прямой эквивалент. |
| Conditional generic types (`compat?: TApi extends "openai-completions" ? ... : never`) | `Generic[TApi]` + runtime-проверка | Compile-time гарантию НЕ получим. Runtime — да. |
| Declaration merging (`CustomAgentMessages`) | Subclassing `AgentMessage` или `Protocol` | TS-only фича; replaced. |
| `partial-json` | `partial-json-parser` (pip) или ~100 LOC custom | Pip-пакет существует; если работает плохо — пишем свой. |
| `undici` (Node HTTP) | `httpx.AsyncClient` | Прямой эквивалент. |
| `openai` (Node SDK) | `httpx.AsyncClient` направую (НЕ Python `openai` SDK!) | Чтобы избежать Pydantic-парсинга, который теряет `reasoning`. |

## Reference: pi-mono structure (для верификации)

```
F:/pi-harness/pi-mono/packages/
├── ai/                          (портируется частично)
│   └── src/
│       ├── types.ts             412 LOC → ~350 Python
│       ├── stream.ts            59 LOC  → ~50 Python
│       ├── models.ts            82 LOC  → ~80 Python
│       ├── api-registry.ts      → ~60 Python
│       ├── env-api-keys.ts      → ~40 Python
│       ├── providers/
│       │   ├── openai-completions.ts   894 LOC → ~700 Python  ★ единственный портируемый
│       │   ├── transform-messages.ts   160 LOC → ~150 Python
│       │   ├── simple-options.ts       47 LOC  → ~50 Python
│       │   ├── faux.ts                 499 LOC → ~400 Python (для тестов)
│       │   └── [9 других]              НЕ портируется
│       └── utils/
│           ├── event-stream.ts         → ~120 Python
│           ├── json-parse.ts           → ~80 Python (или partial-json-parser pip)
│           ├── validation.ts           → ~80 Python (pydantic wrapper)
│           ├── hash.ts                 → ~30 Python
│           └── overflow.ts             → ~90 Python
└── agent/                       (портируется полностью)
    └── src/
        ├── types.ts             341 LOC → ~300 Python
        ├── agent.ts             543 LOC → ~500 Python
        ├── agent-loop.ts        636 LOC → ~600 Python
        └── proxy.ts             → stub
```

## Acceptance criteria

Port считается готовым когда:

1. ✅ Smoke-тесты для каждого слоя (`pi_ai`, `pi_agent_core`) зелёные.
2. ✅ Существующие 119 тестов v7 переписаны под новый API и зелёные.
3. ✅ `docker compose up -d` запускает ecoos-api + ecoos-frontend без ошибок.
4. ✅ Smoke-prompt «Собери калькулятор с графическим интерфейсом» через UI:
   - architect скачивает `Eco.Math.C89`,
   - делает план с разделением «marketplace components» + «to-be-written code»,
   - hand-off coder'у,
   - coder пишет C-код, build (через `make` в Linux контейнере),
   - tester проверяет.
5. ✅ **UI показывает thinking-блоки с реальным reasoning текстом** на Kimi K2.6 (не «~1 tok»). Это критерий успеха pri-fix'а.
6. ✅ `agent/v6/eco_agent.py` удалён, dead-code очищен.
7. ✅ MEMORY.md обновлён ссылкой на новый feedback-файл «v7 migration to pi-port completed».

## Related memory + handoff context

- [`MEMORY.md`](C:\Users\gaevy\.claude\projects\H--ai-hse-diploma-agent\memory\MEMORY.md) — общий индекс
- [`feedback_no_structured_stop_tools`](C:\Users\gaevy\.claude\projects\H--ai-hse-diploma-agent\memory\feedback_no_structured_stop_tools.md) — stop-tools всегда `message:str`
- [`feedback_tester_honest_stop`](C:\Users\gaevy\.claude\projects\H--ai-hse-diploma-agent\memory\feedback_tester_honest_stop.md) — tester без write/edit/build
- [`feedback_architect_must_bridge_gaps`](C:\Users\gaevy\.claude\projects\H--ai-hse-diploma-agent\memory\feedback_architect_must_bridge_gaps.md) — architect мостит пробелы
- [`feedback_agent_iteration_discipline`](C:\Users\gaevy\.claude\projects\H--ai-hse-diploma-agent\memory\feedback_agent_iteration_discipline.md) — efficiency rules в промптах
- [`Eco.Toolchain/Eco.AI.Assembly1/handoff.md`](H:\ai-hse-diploma-agent\Eco.Toolchain\Eco.AI.Assembly1\handoff.md) — handoff от предыдущей сессии
- [`F:/obsidian/wiki/concepts/pi-harness-agent-building-guide.md`](F:\obsidian\wiki\concepts\pi-harness-agent-building-guide.md) — wiki-гайд по pi-mono архитектуре
- `hermes-agent/run_agent.py:5599-5800` — reference для streaming reasoning extraction pattern
