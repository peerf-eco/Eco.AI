# Chat Mode — Детальный план реализации

> Каждая правка: файл, цель, что менять, ожидаемый результат.
> API проверены через context7 и runtime-инспекцию установленных пакетов.

## Версии (проверено)

| Пакет | Версия | Статус |
|---|---|---|
| `langgraph` | 1.0.2 | `create_react_agent` **deprecated**, используем `create_agent` |
| `langchain` | 1.0.3 | `create_agent` + `ToolRuntime` доступны |
| `langchain-core` | 1.2.16 | `@tool` decorator, `StreamWriter` type alias |
| `Python` | 3.12.9 | `get_stream_writer()` async contextvar — поддерживается |

## Проверенные API (источники)

### `create_agent` (замена deprecated `create_react_agent`)

```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,                    # BaseChatModel или строка "openai:gpt-4"
    tools=[tool1, tool2],
    system_prompt="...",          # НЕ prompt= как в create_react_agent
    context_schema=MyContext,     # dataclass для runtime context
    checkpointer=MemorySaver(),
)
```

**Источник:** [LangChain docs — use-subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs), runtime inspect `langchain.agents.create_agent` signature.

### `ToolRuntime` (инъекция контекста в tools)

```python
from langchain_core.tools import tool
from langchain.tools import ToolRuntime

@tool
def my_tool(x: int, tool_runtime: ToolRuntime) -> str:
    """..."""
    tool_runtime.stream_writer({"type": "progress", "data": "..."})  # StreamWriter = Callable[[Any], None]
    tool_runtime.context.my_field        # Доступ к context_schema
    tool_runtime.config                  # RunnableConfig
    return "result"
```

- `tool_runtime` **скрыт от LLM** — не появляется в tool schema
- `stream_writer` — `Callable[[Any], None]`, вызывается как `writer(data)`

**Источник:** [LangChain Reference — ToolRuntime](https://reference.langchain.com/python/langgraph.prebuilt/tool_node/ToolRuntime), runtime inspect `ToolRuntime.__init__`.

### `get_stream_writer` (альтернатива ToolRuntime для нод)

```python
from langgraph.config import get_stream_writer

def my_node(state):
    writer = get_stream_writer()
    writer({"type": "progress", "stage": "processing"})
```

- Работает в Python ≥ 3.11 для async (у нас 3.12 — ОК)
- Работает внутри StateGraph нод и functional API tasks

**Источник:** [LangGraph Reference — get_stream_writer](https://reference.langchain.com/python/langgraph/config/get_stream_writer), runtime inspect.

### `astream` с несколькими stream_mode

```python
async for chunk in agent.astream(
    {"messages": [...]},
    config=config,
    context=my_context,           # передаёт context_schema
    stream_mode=["messages", "custom"],
):
    # chunk = (mode, data)
    # mode = "messages" → (AIMessageChunk, metadata)
    # mode = "custom"   → данные из stream_writer
```

**Источник:** [LangGraph docs — streaming](https://docs.langchain.com/oss/python/langgraph/streaming), context7 snippet "Stream Graph Outputs using Multiple Modes".

---

## Правка 1: Новый файл `agent/chat_agent.py`

### Цель
Создать chat-first ReAct агент с tool `run_assembly`, который вызывает V3 pipeline.

### Что создаём

```python
"""
Chat-first agent для EcoOS.

Общается с пользователем, вызывает V3 pipeline через tool run_assembly
только когда пользователь явно просит собрать приложение.
"""

from dataclasses import dataclass
from typing import Optional

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain.tools import ToolRuntime
from langgraph.checkpoint.memory import MemorySaver

from .tools import rag_query


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT SCHEMA — передаётся в tool через ToolRuntime
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ChatContext:
    """Runtime context, доступный внутри tools через tool_runtime.context."""
    llm: object                  # ChatOpenAI instance (для V3 pipeline)
    max_iterations: int = 5      # лимит итераций сборки


# ═══════════════════════════════════════════════════════════════════════════
# TOOL: run_assembly
# ═══════════════════════════════════════════════════════════════════════════

@tool
def run_assembly(request: str, tool_runtime: ToolRuntime[ChatContext, dict]) -> str:
    """
    Собрать EcoOS приложение из SDK-компонентов.

    Вызывай этот инструмент ТОЛЬКО когда пользователь явно просит
    создать, собрать или написать приложение.

    НЕ вызывай для:
    - Вопросов ("как собрать?", "что такое EcoOS?")
    - Обсуждений и планирования
    - Поиска компонентов (используй rag_query)

    Args:
        request: Описание приложения для сборки.
                 Пример: "Калькулятор с функциями pow, sqrt и логированием"
    """
    import uuid
    from .graph_v2 import create_agent_graph_v3
    from .state_helpers import make_initial_v3_state

    ctx = tool_runtime.context
    writer = tool_runtime.stream_writer

    llm = ctx.llm
    max_iterations = ctx.max_iterations

    graph = create_agent_graph_v3(llm)
    initial_state = make_initial_v3_state(request, max_iterations)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # Стримим progress этапов V3 pipeline
    v3_nodes = ["planner", "resolver", "writer", "build", "tester"]

    # Синхронный stream (tool вызывается в sync контексте ToolNode)
    for chunk in graph.stream(initial_state, config=config, stream_mode=["updates", "custom"]):
        mode, data = chunk
        if mode == "updates":
            for node_name in data.keys():
                if node_name in v3_nodes:
                    writer({
                        "type": "progress",
                        "stage": node_name,
                        "status": "completed",
                    })

    # Получаем финальное состояние
    snapshot = graph.get_state(config)
    state = snapshot.values

    # Отправляем structured result через stream_writer
    result_data = _build_result_payload(state)
    writer({"type": "result", "data": result_data})

    # Отправляем files
    files_data = _build_files_payload(state)
    if files_data:
        writer({"type": "files", "files": files_data})

    # Возвращаем текстовое резюме для LLM
    return _format_summary(state)


def _build_result_payload(state: dict) -> dict:
    """Формирует structured result (совпадает с текущим контрактом server.py)."""
    return {
        "is_success": state.get("is_success", False),
        "tests_passed": state.get("tests_passed", False),
        "project_dir": state.get("project_dir", ""),
        "build_result": state.get("build_result", ""),
        "test_results": state.get("test_results", ""),
        "iterations": state.get("iteration", 0),
        "resolved_components": [
            {"name": c.get("name", ""), "cid": c.get("cid", "")}
            for c in state.get("resolved_components", [])
        ],
        "missing_components": state.get("missing_components", []),
    }


def _build_files_payload(state: dict) -> list:
    """Формирует files payload (совпадает с текущим контрактом server.py)."""
    from pathlib import Path

    ecomain = state.get("ecomain_content", "")
    project_dir = state.get("project_dir", "")
    if ecomain and project_dir:
        rel_path = Path(project_dir).name
        return [{
            "path": f"{rel_path}/SourceFiles/EcoMain.c",
            "type": "source",
            "url": f"/files/{rel_path}/SourceFiles/EcoMain.c",
        }]
    return []


def _format_summary(state: dict) -> str:
    """Текстовое резюме для LLM (он это перескажет пользователю)."""
    status = "УСПЕХ" if state.get("is_success") else "ОШИБКА"
    tests = "пройдены" if state.get("tests_passed") else "не пройдены"
    components = [c.get("name", "?") for c in state.get("resolved_components", [])]

    return (
        f"Результат сборки: {status}\n"
        f"Тесты: {tests}\n"
        f"Проект: {state.get('project_dir', 'N/A')}\n"
        f"Компоненты: {', '.join(components)}\n"
        f"Итераций: {state.get('iteration', 0)}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════

CHAT_SYSTEM_PROMPT = """\
Ты — ассистент по разработке приложений для EcoOS.

## Что ты умеешь

1. Отвечать на вопросы об EcoOS, SDK-компонентах и архитектуре фреймворка.
2. Искать доступные компоненты в базе знаний через rag_query.
3. Собирать приложения из SDK-компонентов через run_assembly.

## Когда вызывать run_assembly

Вызывай run_assembly ТОЛЬКО когда пользователь явно просит СОБРАТЬ/СОЗДАТЬ приложение прямо сейчас:
- "Собери калькулятор с pow и sqrt" → вызвать run_assembly
- "Создай приложение для сортировки списков" → вызвать run_assembly

## Когда НЕ вызывать run_assembly

- "Привет" → ответить текстом
- "Что ты умеешь?" → ответить текстом
- "Какие компоненты есть для математики?" → использовать rag_query, ответить текстом
- "Как собрать калькулятор?" → объяснить текстом, НЕ собирать
- "Давай спроектируем приложение" → обсудить текстом, дождаться явного "собери"
- "Покажи пример приложения" → объяснить текстом

## Если запрос неясный

Если пользователь хочет что-то собрать, но запрос неясный — уточни:
- Какие компоненты нужны?
- Что приложение должно делать?

## После сборки

Расскажи результат на русском: что собралось, какие компоненты использованы, \
прошли ли тесты, где лежит проект.

## Доступные SDK-компоненты EcoOS

Можно найти больше через rag_query:
- Eco.Math.C89 — математика (pow, sqrt, sin, cos)
- Eco.String.C89 — строки
- Eco.List.C89 — связные списки
- Eco.StdIO.C89 — ввод/вывод
- Eco.Log1 — логирование
- Eco.Matrix.C89 — матрицы
"""


# ═══════════════════════════════════════════════════════════════════════════
# AGENT FACTORY
# ═══════════════════════════════════════════════════════════════════════════

def create_chat_agent(llm, checkpointer=None):
    """
    Создаёт chat-first агент.

    Args:
        llm: ChatOpenAI instance
        checkpointer: checkpointer для persistence (default: MemorySaver)
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    agent = create_agent(
        model=llm,
        tools=[rag_query, run_assembly],
        system_prompt=CHAT_SYSTEM_PROMPT,
        context_schema=ChatContext,
        checkpointer=checkpointer,
    )
    return agent
```

### Ожидаемый результат
- `create_chat_agent(llm)` возвращает compiled graph
- При обычном сообщении ("привет") — LLM отвечает текстом, tool не вызывается
- При запросе сборки — LLM вызывает `run_assembly`, который:
  - Стримит `progress` через `stream_writer` (штатный LangGraph механизм)
  - Стримит `result` и `files` через `stream_writer`
  - Возвращает текстовое резюме для LLM

---

## Правка 2: Новый файл `agent/state_helpers.py`

### Цель
Убрать дублирование initial state (сейчас копипаста в 3 местах: `main.py`, `server.py`, план).

### Что создаём

```python
"""Helper для создания начального состояния V3 pipeline."""


def make_initial_v3_state(user_request: str, max_iterations: int = 5) -> dict:
    """
    Создаёт initial state для AgentStateV3.

    Единственное место, где определяются дефолты.
    Используется в: main.py, server.py, chat_agent.py.
    """
    return {
        "user_request": user_request,
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
        "max_iterations": max_iterations,
    }
```

### Ожидаемый результат
- Одно место для initial state
- `main.py`, `server.py`, `chat_agent.py` импортируют `make_initial_v3_state`
- При добавлении нового поля в `AgentStateV3` — менять только здесь

---

## Правка 3: `backend/server.py`

### Цель
Заменить прямой вызов V3 pipeline на ChatAgent. Сохранить текущий WebSocket-контракт (`token`, `progress`, `result`, `files`, `done`, `error`).

### Файл
`backend/server.py`

### Что менять

#### 3.1. Импорты (строки 23-24)

**Было:**
```python
from agent.graph_v2 import create_agent_graph_v3
from agent.main import get_llm
```

**Станет:**
```python
from agent.chat_agent import create_chat_agent, ChatContext
from agent.main import get_llm
```

#### 3.2. Инициализация (строки 48-50)

**Было:**
```python
llm = get_llm()
graph = create_agent_graph_v3(llm)
```

**Станет:**
```python
llm = get_llm()
chat_agent = create_chat_agent(llm)
```

#### 3.3. `run_pipeline` (строки 102-212)

**Было:** Прямой вызов `graph.astream_events(inputs, ...)` с ручным парсингом `on_chain_start`/`on_chain_end`.

**Станет:** Вызов `chat_agent.astream(...)` с `stream_mode=["messages", "custom"]`.

```python
async def run_pipeline(session: PipelineSession, user_message: str, thread_id: str):
    """Пропускает сообщение через ChatAgent, стримит ответ."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        context = ChatContext(
            llm=llm,
            max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "5")),
        )

        inputs = {"messages": [{"role": "user", "content": user_message}]}
        await session.emit({"type": "status", "content": "Обработка запроса..."})

        async for chunk in chat_agent.astream(
            inputs,
            config=config,
            context=context,
            stream_mode=["messages", "custom"],
        ):
            mode, data = chunk

            if mode == "messages":
                msg_chunk, metadata = data
                # Стримим только ответы агента (не tool messages)
                if hasattr(msg_chunk, "content") and msg_chunk.content:
                    if metadata.get("langgraph_node") == "agent":
                        await session.emit({
                            "type": "token",
                            "content": msg_chunk.content,
                        })

            elif mode == "custom":
                # data = то, что tool_runtime.stream_writer() отправил
                # Типы: progress, result, files — совпадают с текущим контрактом
                await session.emit(data)

        await session.emit({"type": "done", "content": "Готово"})

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        await session.emit({"type": "error", "content": str(e)})
        await session.emit({"type": "done", "content": f"Ошибка: {e}"})
    finally:
        session.is_done = True
```

### Ожидаемый результат
- "Привет" → клиент получает `token` events с текстовым ответом, потом `done`. Никаких `progress`.
- "Собери калькулятор" → клиент получает `token` (начало ответа) → `progress` (planner, resolver, ...) → `result` (structured) → `files` → `token` (резюме от LLM) → `done`.
- Формат `result` и `files` **идентичен текущему** — фронтенд `ResultCard` и ссылки работают без изменений.

---

## Правка 4: `agent/main.py`

### Цель
Добавить `--chat` режим CLI. НЕ трогать `--interactive` (обратная совместимость).

### Файл
`agent/main.py`

### Что менять

#### 4.1. Новый аргумент (после строки 65)

```python
parser.add_argument(
    "--chat", "-c",
    action="store_true",
    help="Chat mode — общение с агентом, сборка по запросу"
)
```

#### 4.2. Ветвление в `main()` (строки 109-115)

**Было:**
```python
if args.interactive:
    run_interactive(graph, args)
elif args.query:
    run_single_query(graph, args.query, args)
else:
    parser.print_help()
```

**Станет:**
```python
if args.chat:
    from .chat_agent import create_chat_agent
    chat = create_chat_agent(llm)
    run_chat_mode(chat, llm, args)
elif args.interactive:
    run_interactive(graph, args)
elif args.query:
    run_single_query(graph, args.query, args)
else:
    parser.print_help()
```

#### 4.3. Новая функция `run_chat_mode`

```python
def run_chat_mode(chat_agent, llm, args):
    """Chat mode — разговор с агентом, сборка только по запросу."""
    from .chat_agent import ChatContext

    print("[MODE] Chat mode — общайтесь с агентом или попросите собрать приложение")
    print("Type 'quit' to exit")
    print()

    thread_id = "cli-chat"
    config = {"configurable": {"thread_id": thread_id}}
    context = ChatContext(llm=llm, max_iterations=args.max_iterations)

    while True:
        try:
            query = input(">>> ").strip()
            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            inputs = {"messages": [{"role": "user", "content": query}]}

            for chunk in chat_agent.stream(
                inputs,
                config=config,
                context=context,
                stream_mode=["messages", "custom"],
            ):
                mode, data = chunk
                if mode == "messages":
                    msg_chunk, metadata = data
                    if hasattr(msg_chunk, "content") and msg_chunk.content:
                        if metadata.get("langgraph_node") == "agent":
                            print(msg_chunk.content, end="", flush=True)
                elif mode == "custom":
                    event_type = data.get("type", "")
                    if event_type == "progress":
                        print(f"\n  [{data['stage']}] {data.get('status', '')}")
                    elif event_type == "result":
                        res = data["data"]
                        status = "SUCCESS" if res["is_success"] else "FAILED"
                        tests = "PASSED" if res.get("tests_passed") else "FAILED"
                        print(f"\n  [Build: {status}] [Tests: {tests}] [{res.get('iterations', 0)} iter.]")

            print()  # Новая строка после ответа

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break
```

#### 4.4. Замена дублирования state в `run_single_query` (строки 126-149)

**Было:** 25 строк hardcoded dict.

**Станет:**
```python
from .state_helpers import make_initial_v3_state

initial_state = make_initial_v3_state(query, args.max_iterations)
```

### Ожидаемый результат
- `python -m agent.main --interactive` — работает как раньше (прямой V3 pipeline)
- `python -m agent.main --chat` — новый режим: чат с агентом, сборка по запросу
- `python -m agent.main "Собери калькулятор"` — работает как раньше (прямой V3 pipeline)

---

## Правка 5: `frontend/components/chat/progress-viewer.tsx`

### Цель
Привести стадии progress bar в соответствие с V3 бэкендом (сейчас сломано — V1 имена).

### Файл
`frontend/components/chat/progress-viewer.tsx`

### Что менять (строки 5-24)

**Было:**
```ts
export type Stage =
  | "analyze_request"
  | "select_components"
  | "retrieve_context"
  | "generate_code"
  | "review_code"
  | "complete";

const STAGES: { id: Stage; label: string }[] = [
  { id: "analyze_request", label: "Analysis" },
  { id: "select_components", label: "Selection" },
  { id: "retrieve_context", label: "Retrieval (RAG)" },
  { id: "generate_code", label: "Generation" },
  { id: "review_code", label: "Review" },
];
```

**Станет:**
```ts
export type Stage =
  | "planner"
  | "resolver"
  | "writer"
  | "build"
  | "tester"
  | "complete";

const STAGES: { id: Stage; label: string }[] = [
  { id: "planner", label: "Planner" },
  { id: "resolver", label: "Resolver" },
  { id: "writer", label: "Writer" },
  { id: "build", label: "Build" },
  { id: "tester", label: "Tester" },
];
```

### Ожидаемый результат
- Progress bar двигается по этапам: Planner → Resolver → Writer → Build → Tester
- `currentStage="planner"` → `findIndex` возвращает 0 (сейчас возвращает -1!)
- Исправляется pre-existing баг

---

## Правка 6: `frontend/components/chat/chat-interface.tsx`

### Цель
1. Не показывать progress bar при обычном чате (только при сборке)
2. Показывать "thinking" индикатор для чат-ответов
3. Обновить placeholder и примеры

### Файл
`frontend/components/chat/chat-interface.tsx`

### 6.1. Новый state `isAssembling` (после строки 55)

**Было:** только `isProcessing`

**Станет:** добавить `isAssembling`:
```ts
const [isAssembling, setIsAssembling] = useState(false);
```

Логика:
- `isProcessing` = агент думает (показываем "typing..." спиннер)
- `isAssembling` = запущена сборка (показываем progress bar)

### 6.2. `handleWsMessage` — показывать progress bar только при сборке (строки 128-196)

**Было (case "progress", строки 144-149):**
```ts
case "progress":
  if (data.status === "running") {
    setCurrentStage(data.stage);
    setIsProcessing(true);
  }
  break;
```

**Станет:**
```ts
case "progress":
  setCurrentStage(data.stage);
  setIsAssembling(true);  // progress пришёл = сборка идёт
  break;
```

**Было (case "done", строки 181-185):**
```ts
case "done":
  setIsProcessing(false);
  setCurrentStage("complete");
  setStatusMessage("");
  break;
```

**Станет:**
```ts
case "done":
  setIsProcessing(false);
  setIsAssembling(false);
  setCurrentStage("complete");
  setStatusMessage("");
  break;
```

### 6.3. `sendMessage` — не ставить isProcessing сразу (строки 203-212)

**Было (строки 208-211):**
```ts
setIsProcessing(true);
setCurrentStage("planner");
setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
```

**Станет:**
```ts
setIsProcessing(true);
// НЕ ставим setCurrentStage — будет установлен из progress event
// НЕ ставим setIsAssembling — будет установлен если придёт progress
```

### 6.4. Progress bar — показывать только при сборке (строки 378-393)

**Было:**
```tsx
{isProcessing && (
  <motion.div ...>
    ...
    <ProgressViewer currentStage={currentStage} isProcessing={isProcessing} />
  </motion.div>
)}
```

**Станет:**
```tsx
{isProcessing && (
  <motion.div ...>
    <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
      <Bot size={16} className="text-blue-400" />
      <span>{statusMessage || (isAssembling ? "Сборка..." : "Думаю...")}</span>
    </div>
    {isAssembling && (
      <ProgressViewer currentStage={currentStage} isProcessing={isProcessing} />
    )}
  </motion.div>
)}
```

### 6.5. Placeholder и примеры (строки 299-313)

**Было:**
```tsx
<p className="text-sm ...">
  Describe the EcoOS application you want to create. The agent will search SDK components,
  resolve dependencies, generate code, build, and run tests.
</p>
<div className="flex gap-2 mt-6">
  {["Calculator app", "Linked list", "Matrix operations"].map((ex) => (
    ...
  ))}
</div>
```

**Станет:**
```tsx
<p className="text-sm ...">
  Спросите про EcoOS или попросите собрать приложение из SDK-компонентов.
</p>
<div className="flex flex-wrap gap-2 mt-6">
  {[
    "Что ты умеешь?",
    "Какие компоненты есть?",
    "Собери калькулятор с pow и sqrt",
  ].map((ex) => (
    ...
  ))}
</div>
```

**Placeholder инпута (строка 409):**

**Было:** `"Describe the EcoOS application you want to create..."`

**Станет:** `"Спросите про EcoOS или опишите приложение для сборки..."`

### Ожидаемый результат
- "Привет" → показывается "Думаю..." спиннер → текстовый ответ → спиннер исчезает. **Нет progress bar.**
- "Собери калькулятор" → "Думаю..." → приходит `progress` → появляется progress bar (Planner → ... → Tester) → `result` карточка → `files` ссылки → текст резюме → всё исчезает.
- Интерфейс на русском.

---

## Порядок реализации

| Шаг | Файл | Действие | Зависимости |
|-----|-------|----------|-------------|
| 1 | `agent/state_helpers.py` | Создать | Нет |
| 2 | `agent/chat_agent.py` | Создать | state_helpers |
| 3 | `agent/main.py` | Добавить `--chat`, заменить state на helper | state_helpers, chat_agent |
| 4 | `backend/server.py` | Переключить на ChatAgent | chat_agent |
| 5 | `progress-viewer.tsx` | Обновить стадии V3 | Нет |
| 6 | `chat-interface.tsx` | isAssembling, placeholder, примеры | progress-viewer |

Шаги 1-4 (бэкенд) и 5-6 (фронтенд) можно делать параллельно.

---

## Тест-план

### Чат без сборки
1. Отправить "Привет" → текстовый ответ, нет progress
2. Отправить "Что ты умеешь?" → текстовый ответ, нет progress
3. Отправить "Какие компоненты есть для математики?" → rag_query + текст, нет progress
4. Отправить "Как собрать калькулятор?" → текстовое объяснение, нет progress

### Сборка
5. Отправить "Собери калькулятор с pow и sqrt" → progress bar → result card → files → текст
6. Проверить что `ResultCard` рендерится с компонентами и тестами
7. Проверить что ссылка на EcoMain.c работает

### CLI
8. `python -m agent.main --interactive` → старое поведение (прямой pipeline)
9. `python -m agent.main --chat` → чат с агентом
10. `python -m agent.main "Собери калькулятор"` → старое поведение

### Edge cases
11. Отправить два сообщения подряд — второе должно дождаться завершения первого
12. Переподключение WebSocket во время сборки — replay buffered events
13. Отправить пустое сообщение — игнорируется
