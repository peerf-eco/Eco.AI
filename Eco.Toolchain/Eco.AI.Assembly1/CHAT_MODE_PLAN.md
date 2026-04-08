# Chat Mode: План реализации

## Проблема

Сейчас любое сообщение пользователя (включая «привет», «что ты умеешь?») запускает полный pipeline сборки:
```
user_message → planner → resolver → writer → build → tester
```

Нужен **режим чата**: агент общается с пользователем, а pipeline сборки запускается только когда пользователь явно просит собрать приложение.

---

## Подход: Chat-first ReAct Agent + Assembly Tool

Основная идея — **ReAct-агент** как верхнеуровневый граф, который:
1. Общается с пользователем в свободной форме
2. Имеет tool `run_assembly`, который запускает V3 pipeline как подграф
3. Сам решает, когда вызвать tool (по intent пользователя)

### Почему не Router/Supervisor

| Критерий | Router (Supervisor) | Chat-first ReAct |
|---|---|---|
| Сложность | Два LLM-вызова (classifier + agent) | Один LLM — сам определяет intent |
| Гибкость | Жёсткая классификация | LLM может уточнить перед запуском |
| Контекст | Теряется между router и pipeline | Передаётся через tool args |
| Код | Новый supervisor graph + intent model | `@tool` обёртка + `create_react_agent` |

---

## Архитектура

```
┌─────────────────────────────────────────────────────┐
│                  ChatAgent (ReAct)                   │
│                                                     │
│  LLM + system prompt                                │
│    ├── tool: rag_query (поиск компонентов)           │
│    ├── tool: run_assembly (→ V3 pipeline)            │
│    └── tool: list_components (инфо о SDK)            │
│                                                     │
│  Стандартный ReAct loop:                             │
│    user → LLM → [tool_call?] → tool → LLM → answer  │
│                      │                               │
│                      ▼                               │
│              ┌──────────────┐                        │
│              │ V3 Pipeline  │ (существующий граф)     │
│              │  (subgraph)  │                        │
│              └──────────────┘                        │
└─────────────────────────────────────────────────────┘
```

---

## Детальный план реализации

### Файл 1: `agent/chat_agent.py` (НОВЫЙ)

#### 1.1. Tool `run_assembly`

```python
from langchain_core.tools import tool

@tool
def run_assembly(request: str) -> str:
    """
    Запустить сборку EcoOS приложения из SDK-компонентов.

    Используй этот инструмент ТОЛЬКО когда пользователь явно просит
    создать/собрать/написать приложение или компонент.

    Args:
        request: Описание того, что нужно собрать.
                 Пример: "Калькулятор с функциями pow, sqrt и логированием"

    Returns:
        Результат сборки: успех/ошибка, путь к проекту, результаты тестов.
    """
    from .graph_v2 import create_agent_graph_v3
    from .main import get_llm
    import uuid

    llm = get_llm()
    graph = create_agent_graph_v3(llm)

    initial_state = {
        "user_request": request,
        "component_plan": {},
        "planner_messages": [],
        "resolved_components": [],
        "framework_components": [],
        "include_dirs": [],
        "lib_dirs": [],
        "lib_files": [],
        "makefile_content": "",
        "makefile_exe_content": "",
        "project_dir": "",
        "missing_components": [],
        "ecomain_content": "",
        "writer_messages": [],
        "build_result": "",
        "is_success": False,
        "error_message": "",
        "error_type": "none",
        "test_cases": "",
        "test_results": "",
        "tests_passed": False,
        "iteration": 0,
        "max_iterations": 5,
    }

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke(initial_state, config)

    # Форматируем ответ для LLM
    status = "УСПЕХ" if result.get("is_success") else "ОШИБКА"
    tests = "пройдены" if result.get("tests_passed") else "не пройдены"
    project_dir = result.get("project_dir", "N/A")
    components = [c.get("name", "?") for c in result.get("resolved_components", [])]

    return (
        f"Результат сборки: {status}\n"
        f"Тесты: {tests}\n"
        f"Проект: {project_dir}\n"
        f"Компоненты: {', '.join(components)}\n"
        f"Итераций: {result.get('iteration', 0)}\n"
        f"Build: {result.get('build_result', 'N/A')[:300]}"
    )
```

#### 1.2. Chat Agent

```python
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

CHAT_SYSTEM_PROMPT = """Ты — ассистент по разработке приложений для EcoOS.

Ты можешь:
1. Отвечать на вопросы об EcoOS, SDK-компонентах и архитектуре фреймворка
2. Искать доступные компоненты в базе знаний через rag_query
3. Собирать приложения из SDK-компонентов через run_assembly

ПРАВИЛА:
- Если пользователь здоровается или задаёт общий вопрос — отвечай текстом, НЕ вызывай run_assembly
- Если пользователь просит "создай", "собери", "напиши приложение" — вызови run_assembly
- Перед сборкой можешь уточнить требования, если запрос неясен
- После сборки расскажи результат: что собралось, какие компоненты, прошли ли тесты

Доступные SDK-компоненты EcoOS (можно найти больше через rag_query):
- Eco.Math.C89 — математика (pow, sqrt, sin, cos)
- Eco.String.C89 — строки (copy, compare, length)
- Eco.List.C89 — связные списки
- Eco.StdIO.C89 — ввод/вывод
- Eco.Log1 — логирование
"""


def create_chat_agent(llm):
    """Создаёт chat-first ReAct агент с tool для запуска pipeline."""
    tools = [rag_query, run_assembly]

    agent = create_react_agent(
        llm,
        tools=tools,
        prompt=CHAT_SYSTEM_PROMPT,
        checkpointer=MemorySaver(),
    )
    return agent
```

---

### Файл 2: `backend/server.py` (ИЗМЕНЕНИЯ)

#### 2.1. Два режима работы WebSocket

Сервер должен уметь отличать:
- **Чат-сообщение** → передать в ChatAgent, получить текстовый ответ
- **Сборка** → ChatAgent сам вызовет `run_assembly`, нужно стримить progress

#### 2.2. Изменения в `run_pipeline`

```python
# Вместо прямого вызова create_agent_graph_v3:
from agent.chat_agent import create_chat_agent

chat_agent = create_chat_agent(llm)

async def run_pipeline(session: PipelineSession, user_message: str, thread_id: str):
    """Пропускает сообщение через ChatAgent."""
    try:
        config = {"configurable": {"thread_id": thread_id}}

        # ChatAgent использует messages-based state
        inputs = {"messages": [{"role": "user", "content": user_message}]}

        await session.emit({"type": "status", "content": "Обработка запроса..."})

        async for event in chat_agent.astream_events(inputs, config=config, version="v1"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    await session.emit({"type": "token", "content": content})

            elif kind == "on_tool_start":
                tool_name = event["name"]
                if tool_name == "run_assembly":
                    await session.emit({
                        "type": "progress",
                        "stage": "planner",
                        "status": "running"
                    })

            elif kind == "on_tool_end":
                tool_name = event["name"]
                if tool_name == "run_assembly":
                    # Парсим результат для отправки клиенту
                    output = event["data"].get("output", "")
                    await session.emit({
                        "type": "assembly_result",
                        "content": output
                    })

        # Финальное сообщение
        await session.emit({"type": "done", "content": "Готово"})

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        await session.emit({"type": "error", "content": str(e)})
        await session.emit({"type": "done", "content": f"Ошибка: {e}"})
    finally:
        session.is_done = True
```

---

### Файл 3: `agent/main.py` (ИЗМЕНЕНИЯ)

Добавить `--chat` режим в CLI:

```python
# В argparse:
parser.add_argument("--chat", action="store_true", help="Chat mode (без прямого запуска pipeline)")

# В main():
if args.chat or args.interactive:
    from .chat_agent import create_chat_agent
    chat = create_chat_agent(llm)
    run_chat_interactive(chat)
```

---

## Стриминг progress из вложенного pipeline

### Проблема
Когда `run_assembly` tool вызывает V3 pipeline синхронно внутри tool, мы теряем granular progress (planner → resolver → writer → build → tester).

### Решение: Callback + глобальная сессия

```python
# В chat_agent.py — run_assembly получает доступ к текущей PipelineSession:

import contextvars

# Контекстная переменная для текущей сессии
_current_session: contextvars.ContextVar[Optional["PipelineSession"]] = \
    contextvars.ContextVar("_current_session", default=None)

@tool
async def run_assembly(request: str) -> str:
    """..."""
    session = _current_session.get()

    llm = get_llm()
    graph = create_agent_graph_v3(llm)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    initial_state = { ... }  # как выше

    if session:
        # Стримим progress в WebSocket
        v3_nodes = ["planner", "resolver", "writer", "build", "tester"]
        async for event in graph.astream_events(initial_state, config=config, version="v1"):
            kind = event["event"]
            if kind == "on_chain_start" and event["name"] in v3_nodes:
                await session.emit({"type": "progress", "stage": event["name"], "status": "running"})
            elif kind == "on_chain_end" and event["name"] in v3_nodes:
                await session.emit({"type": "progress", "stage": event["name"], "status": "completed"})

        result = await graph.aget_state(config)
        state = result.values
    else:
        # CLI mode — синхронный invoke
        state = graph.invoke(initial_state, config)

    return _format_result(state)
```

В `server.py` перед вызовом chat_agent:
```python
from agent.chat_agent import _current_session

_current_session.set(session)
# ... run chat_agent ...
```

---

## Протокол WebSocket (обновлённый)

| Тип сообщения | Когда | Данные |
|---|---|---|
| `token` | Стриминг ответа чата | `{content: "..."}` |
| `status` | Статусные сообщения | `{content: "..."}` |
| `progress` | Этап pipeline (только при сборке) | `{stage, status}` |
| `assembly_result` | Результат сборки | `{content: "..."}` |
| `files` | Сгенерированные файлы | `{files: [...]}` |
| `result` | Финальный результат сборки | `{data: {...}}` |
| `done` | Конец обработки | `{content: "..."}` |
| `heartbeat` | Keep-alive | `{}` |

---

## Фронтенд (минимальные изменения)

Текущий фронтенд уже поддерживает:
- `token` → отображение стримящегося текста
- `progress` → `ProgressViewer` с этапами

Нужно добавить:
1. **Отображение `token` как обычного чат-сообщения** (уже работает)
2. **`ProgressViewer` показывать только когда приходит первый `progress`** (сейчас показывается всегда)
3. **`assembly_result`** → показать как карточку результата (аналог текущего `result`)

---

## Порядок реализации

### Этап 1: Минимальный chat mode (2-3 часа)
1. Создать `agent/chat_agent.py` с `run_assembly` tool и `create_chat_agent`
2. Изменить `server.py` — заменить прямой вызов V3 pipeline на ChatAgent
3. Проверить: «привет» → текстовый ответ, «собери калькулятор» → pipeline

### Этап 2: Стриминг progress (1-2 часа)
4. Добавить `contextvars` для передачи PipelineSession в tool
5. Сделать `run_assembly` async, стримить progress через сессию
6. Проверить: frontend показывает planner→resolver→writer→build→tester

### Этап 3: CLI chat mode (30 мин)
7. Добавить `--chat` флаг в `main.py`
8. Реализовать `run_chat_interactive` с текстовым вводом

### Этап 4: Фронтенд polish (1 час)
9. Скрыть `ProgressViewer` до первого `progress` event
10. Обработать `assembly_result` тип сообщения
11. Показывать чат-ответы без карточки результата

---

## Критические моменты

1. **LLM и checkpointer** — ChatAgent использует свой `MemorySaver`, V3 pipeline внутри tool использует отдельный. Thread ID чата ≠ thread ID pipeline.

2. **Таймауты** — `run_assembly` может работать 2-5 минут. Нужно убедиться, что WebSocket не отвалится (heartbeat уже есть).

3. **Обратная совместимость** — V3 pipeline (`create_agent_graph_v3`) не меняется. ChatAgent — это обёртка поверх него.

4. **Prompt engineering** — системный промпт ChatAgent должен чётко разграничивать чат и сборку. Тесты: «привет», «что ты умеешь?», «какие компоненты есть?», «собери калькулятор».
