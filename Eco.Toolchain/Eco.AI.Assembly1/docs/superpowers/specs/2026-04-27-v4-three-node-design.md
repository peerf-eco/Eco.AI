# V4 Three-Node Pipeline — Design Spec

**Дата:** 2026-04-27
**Статус:** Draft (для ревью пользователем перед переходом в implementation plan)
**Контекст:** замена текущего V4 (architect-ReAct + coder sub-agents) на трёхнодовую архитектуру с явными handoff-ами через Markdown.

## 1. Goal

Перестроить V4 EcoOS Assembly Agent в трёх-нодовый пайплайн `Planner → Coder → Executor`, где:
- **Planner** ведёт итеративный диалог с пользователем, ищет компоненты в локальном SDK через RAG, формирует PRD как Markdown. Не имеет сайд-эффектов на файловой системе.
- **Coder** получает утверждённый PRD, скачивает SDK-компоненты, пишет custom-компоненты по шаблонам, генерирует связующий слой (EcoMain.c).
- **Executor** собирает бинарник, прогоняет тесты. На успехе — отвечает пользователю; на провале — возвращает structured Markdown-фидбэк в Coder через `back_to_code`-handoff. Цикл `Coder ↔ Executor` ограничен `max_iterations`.

Handoff-ы между нодами — через **string-arg тулы** с Markdown-нагрузкой. Routing — через `state.phase` + LangGraph conditional edges. **Никакого `with_structured_output`, никакого `interrupt()`.**

## 2. Engineering constraints

Из `memory/feedback_model_portability.md` (2026-04-27):

- **Model portability**: дизайн обязан работать на любой LLM, доступной через OpenRouter (kimi-k2.6, glm-5.1, xiaomi/mimo-v2.5-pro, deepseek-v4-pro, и другие). Конкретная модель — параметр запуска.
- **`with_structured_output` запрещён в горячем пути.** На тестах reliability колебалась 0–100% по моделям. Предпочитаем prose + детерминистический парсинг.
- **Тулы принимают только строковые аргументы.** `f(text: str)` универсален; вложенные tool-схемы реализуются провайдерами по-разному.
- **Pydantic используется как post-parse валидатор** (после `json.loads`), не как enforcement. На failure — prompt-retry с текстом ошибки.
- **Fallback при 2 неудачах подряд парсинга** — добавить ошибку в messages и заново вызвать ту же ноду; `max_iterations` защищает от бесконечного цикла.

## 3. Architecture

```
              ┌─────────────────────────────────────┐
              │  Frontend / WebSocket / chat_agent  │
              └─────────────────┬───────────────────┘
                                │ user messages
                                ▼
                       ┌──────────────────┐
        START ────────▶│      router      │ читает state.phase
                       └────────┬─────────┘
                                │
            ┌───────────────────┼───────────────────┬───────────┐
            ▼ "planning"        ▼ "coding"          ▼ "executing"  "done" → END
       ┌─────────┐         ┌─────────┐         ┌──────────┐
       │ Planner │         │  Coder  │         │ Executor │
       │ (ReAct) │         │ (ReAct) │         │  (ReAct) │
       └────┬────┘         └────┬────┘         └─────┬────┘
            │ assign()          │ done()              │ success()  → END
            └──▶ phase="coding"  └──▶ phase="exec"    │ back_to_code()
                                                       └──▶ phase="coding"
                                                            iteration++
                                                            (если ≥ max → END)
```

**Жизненный цикл сессии = одно `thread_id` + MemorySaver checkpointer.** Каждое user-сообщение = один `graph.invoke()`. State persistent между инвокациями.

## 4. State schema

```python
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AppState(TypedDict):
    # User input (initial)
    user_request: str

    # Per-node ReAct conversations (isolated)
    planner_messages:  Annotated[list, add_messages]
    coder_messages:    Annotated[list, add_messages]
    executor_messages: Annotated[list, add_messages]

    # Handoff payloads (Markdown, set by handoff tools)
    plan_md:          str   # by Planner.assign()
    coder_summary_md: str   # by Coder.done()
    feedback_md:      str   # by Executor.back_to_code(); empty on first iteration

    # Phase routing
    phase: Literal["planning", "coding", "executing", "done"]

    # Project artifacts
    project_dir:  str   # output/<project_name>/
    project_name: str

    # Bounded loop control
    iteration:      int
    max_iterations: int   # default 5
    last_status:    str   # "" (in-progress) | "success" | "max_iterations_reached" | "parse_failure" | "user_aborted"
```

**Замечание по message-историям:** Каждая нода имеет свою `*_messages`. Это:
- ограничивает context bloat на больших сессиях,
- делает каждую ноду тестируемой изолированно (можно собирать synthetic state и прогонять только Coder),
- избегает проблемы "Coder видит весь planning-диалог, который ему не нужен".

Обмен между нодами — **только через handoff payloads** (`plan_md`, `coder_summary_md`, `feedback_md`).

## 5. Per-node design

### 5.1 Node 1 — Planner

**Назначение.** Итеративный диалог с пользователем, поиск компонентов в локальном SDK, формирование PRD.

**Tools (только string args):**

| Имя | Args | Возвращает | Side-effects |
|---|---|---|---|
| `list_all_components` | none | Markdown-список локальных DK | none |
| `rag_query` | `query: str` | top-k ChromaDB chunks с источниками | none |
| `read_component` | `name: str` | содержимое `IEco{name}.h` + `IdEco{name}.h` | none |
| `assign` | `plan_md: str` | `""` (пусто), но в `Command` обновляет `state.plan_md` и `state.phase="coding"` | terminal |

**Поведение.**
- ReAct sub-agent (`create_react_agent`) с системным промптом, описывающим задачу и формат PRD.
- Может вызывать поисковые тулы много раз. Plain-content ответы между тул-вызовами — **естественный механизм диалога**: ReAct-цикл завершается, plain content отдаётся пользователю, на новое сообщение пользователя ход возобновляется (через checkpointer).
- Когда пользователь явно одобряет план ("да, начинаем", "build it" и т.п.) — модель вызывает `assign(plan_md)` с финальным Markdown-PRD. После этого conditional edge переводит в Coder.
- **Никакого download'а или write_file внутри Planner** — это инвариант обратимости планирования.

**PRD format (`plan_md`):**
```markdown
## Project: <project_name>

<one-paragraph description>

## Components

- **<name>** — source: sdk — <reason>
- **<name>** — source: marketplace — <reason>
- **<name>** — source: develop — <reason>
  - spec: <interface description, methods, dependencies>

## Build target

- Platform: <Windows|Linux>
- Output: <executable name>

## Acceptance criteria

- <criterion 1>
- <criterion 2>
```

Coder парсит секции детерминистическим regex'ом (компоненты по списку bullet'ов с `source: <kind>`).

### 5.2 Node 2 — Coder

**Назначение.** Скачать SDK-компоненты, написать custom-компоненты по шаблонам, написать связующий слой EcoMain.c.

**Tools (только string args):**

| Имя | Args | Возвращает | Side-effects |
|---|---|---|---|
| `download_component` | `name: str` | OK/ERROR | eco-cli pull → DependenciesFiles/ |
| `write_file` | `path: str, content: str` | OK | пишет в `project_dir` |
| `read_file` | `path: str` | content | none |
| `list_files` | none | tree | none |
| `load_skill` | `language: str` (`c`, `cpp`, `asm`) | template content | none |
| `done` | `summary_md: str` | `""` + `state.coder_summary_md = summary_md` + `state.phase="executing"` | terminal |

**Поведение.**
- ReAct sub-agent. На вход получает `state.plan_md` (через стартовое сообщение в `coder_messages`) **и** `state.feedback_md`, если итерация > 0 (после `back_to_code`).
- Парсит `plan_md` regex'ом: список компонентов с source, спеки для develop, acceptance criteria. (Парсер — pure Python, без LLM, см. секцию 7.)
- Скачивает sdk/marketplace компоненты, пишет develop-компоненты по шаблонам skills (`load_skill("c")`), пишет EcoMain.c.
- На итерациях > 0 фокусируется на `feedback_md`, а не на полном плане заново.
- Заканчивает `done(summary_md)` со списком созданных/изменённых файлов.

**Coder summary format (`coder_summary_md`):**
```markdown
## Iteration: <N>
## Files written
- output/<project>/EcoMain.c
- output/<project>/DependenciesFiles/<comp>/...

## Files modified (if iteration > 0)
- output/<project>/EcoMain.c — fixed include order

## Notes
- <any non-trivial decisions>
```

### 5.3 Node 3 — Executor

**Назначение.** Сборка + тестирование. Возврат фидбэка либо результата.

**Tools (только string args):**

| Имя | Args | Возвращает | Side-effects |
|---|---|---|---|
| `build` | none | full compiler/linker output as Markdown | вызывает make/cl.exe в `project_dir` |
| `run_tests` | none | test results as Markdown | запускает бинарник с тест-входами |
| `success` | `summary_md: str` | `""` + `state.phase="done"` + `state.last_status="success"` | terminal |
| `back_to_code` | `feedback_md: str` | `""` + `state.feedback_md` + `state.phase="coding"` + `iteration++` | terminal |

**Поведение.**
- ReAct sub-agent. На вход — `state.coder_summary_md`.
- Сначала `build()`. На failure — анализирует output и сразу `back_to_code(feedback_md)` с указанием compile/link errors.
- На успешной сборке — `run_tests()`. На failure — `back_to_code(feedback_md)` с тест-failures.
- На полном успехе — `success(summary_md)`.
- **Bounded loop:** если `state.iteration >= state.max_iterations` И executor хочет вызвать `back_to_code` — вместо этого вызывает `success(summary_md)` с прикреплённой пометкой "max_iterations_reached, тесты не все прошли", чтобы пользователь увидел текущее состояние.

**Feedback format (`feedback_md`) — детерминистически парсимый:**
```markdown
## Stage: build|test
## Status: FAIL

## Errors
- {file_path}:{line}: {error_message}
- {file_path}:{line}: {error_message}

## Test failures (if stage=test)
- {test_name}: expected {expected}, got {actual}

## Suggested focus
- {short hint about what likely needs fixing — optional}
```

Coder regex'ом извлекает `Errors` секцию, для каждой строки `file:line:` фокусирует правки.

## 6. Routing & handoff mechanics

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

def route_by_phase(state: AppState) -> str:
    return state["phase"]  # "planning" | "coding" | "executing" | "done"

builder = StateGraph(AppState)
builder.add_node("planner",  planner_node)
builder.add_node("coder",    coder_node)
builder.add_node("executor", executor_node)

# Entry point: route by current phase
builder.add_conditional_edges(START, route_by_phase, {
    "planning":  "planner",
    "coding":    "coder",
    "executing": "executor",
    "done":      END,
})

# After planner: либо handoff, либо ход юзера закончен
builder.add_conditional_edges("planner", route_by_phase, {
    "planning": END,
    "coding":   "coder",
})

# After coder: всегда переход к executor (coder.done() — единственный handoff)
builder.add_conditional_edges("coder", route_by_phase, {
    "executing": "executor",
    "coding":    END,  # safety, не должно срабатывать
})

# After executor: либо успех, либо петля
builder.add_conditional_edges("executor", route_by_phase, {
    "done":     END,
    "coding":   "coder",
    "executing": END,  # safety
})

graph = builder.compile(checkpointer=MemorySaver())
```

**Handoff-тул реализуется через `Command`:**
```python
from langgraph.types import Command
from langchain_core.tools import tool

@tool
def assign(plan_md: str) -> Command:
    """Approved plan — handoff to Coder. Call ONLY after user explicitly approves the PRD."""
    return Command(update={"plan_md": plan_md, "phase": "coding"})
```

`Command` с `update` обновляет state и завершает текущий node-step. LangGraph routes согласно следующим conditional edges.

## 7. PRD parser (Coder side)

```python
import re

_BULLET = re.compile(
    r"^-\s+\*\*(?P<name>[^*]+)\*\*\s*[—-]\s*source:\s*(?P<source>sdk|marketplace|develop)"
    r"(?:\s*[—-]\s*(?P<reason>.+))?$",
    re.MULTILINE,
)
_SPEC = re.compile(r"^\s+-\s*spec:\s*(?P<spec>.+)$", re.MULTILINE)

def parse_plan(plan_md: str) -> dict:
    components = []
    for m in _BULLET.finditer(plan_md):
        components.append({
            "name": m["name"].strip(),
            "source": m["source"],
            "reason": (m["reason"] or "").strip(),
            "spec": None,
        })
    # Naive spec attachment: bullet at line N, spec at line N+1 with deeper indent
    # (полная реализация в коде; здесь — суть подхода)
    return {"components": components}
```

Если `parse_plan` возвращает 0 компонентов или у develop-компонента нет spec — Coder добавляет в свои messages prompt-fixup и просит LLM привести `plan_md` к формату. Это обработка hand-off-payload-ошибки внутри ноды, без вылета из графа.

## 8. Life-cycle example

**Сценарий: пользователь просит HTTP-сервер с математикой.**

| Шаг | User → | Phase before | Что происходит | Phase after |
|---|---|---|---|---|
| 1 | "Сделай HTTP-сервер с математическим API" | `planning` | Planner: rag_query("http server"), rag_query("math"), list_all_components. Отвечает: "Нашёл Eco.Math.C89, Eco.StdIO.C89. HTTP-сервера в SDK нет — нужно либо marketplace, либо develop. Что выбрать?" | `planning` |
| 2 | "Marketplace" | `planning` | Planner: rag_query("marketplace http"). Отвечает с предложенным PRD draft. | `planning` |
| 3 | "Добавь логирование" | `planning` | Planner: обновляет PRD, добавляет Eco.Logger1 в список. Показывает обновлённый Markdown. | `planning` |
| 4 | "Да, начинай" | `planning` | Planner: вызывает `assign(plan_md=...)`. State.phase="coding". | `coding` |
| 5 | (автомат.) | `coding` | Coder: парсит PRD, download(Eco.HttpServer1@marketplace), download(Eco.Logger1@marketplace), пишет EcoMain.c. Вызывает `done(summary_md)`. | `executing` |
| 6 | (автомат.) | `executing` | Executor: build() → OK. run_tests() → 1 of 3 failed. Вызывает `back_to_code(feedback_md=...)`. iteration=1. | `coding` |
| 7 | (автомат.) | `coding` | Coder: видит feedback_md, фиксит EcoMain.c (плохая регистрация callback). Вызывает `done(summary_md)`. | `executing` |
| 8 | (автомат.) | `executing` | Executor: build OK, tests OK. Вызывает `success(summary_md)`. | `done` |
| 9 | UI показывает summary | `done` | END. | — |

Шаги 5–8 идут без прерывания пользователя — стримятся как progress events на фронт.

## 9. Failure modes

| Failure | Detection | Handling |
|---|---|---|
| Planner не вызывает `assign` после явного approval | LLM-bug; редко | Не специальная обработка — пользователь повторяет команду чётче |
| `plan_md` не парсится regex'ом | `parse_plan` вернул 0 components | Coder добавляет в свои messages: "Plan not parseable, please rewrite in the required format" + текст ошибки. Re-invoke LLM. После 2 неудач — Coder вызывает `done` с empty summary, Executor пропускает (или граф завершается с last_status="parse_failure") |
| `feedback_md` пуст или малосодержателен | Coder regex'ом не нашёл Errors | Coder обращается к build_output напрямую (читает state.coder_summary_md или просит executor по new tool) — fallback |
| `iteration >= max_iterations` | счётчик в state | Executor вызывает `success` с пометкой "tests partially failed" вместо `back_to_code`. Пользователь видит текущее состояние и решает |
| Process restart mid-session | MemorySaver in-memory | Сессия теряется. Acceptable для thesis demo; persistent backend (SqliteSaver) — out of scope этого spec'a |
| User закрывает чат во время `coding`/`executing` | WebSocket disconnect | Граф продолжает в фоне (asyncio.Task), на reconnect фронт получает текущий phase + последние events. PipelineSession (PR #10) уже это поддерживает |

## 10. Implementation plan (high-level)

**Файлы для создания:**
- `agent/planner.py` — `create_planner_node(llm)` + tools (`assign`, `read_component`)
- `agent/executor.py` — `create_executor_node(llm)` + tools (`success`, `back_to_code`)
- `agent/parsers.py` — `parse_plan`, `parse_feedback` (pure Python regex)
- `agent/three_node_graph.py` — сборка графа
- `agent/state_v5.py` — `AppState` TypedDict (новое имя, чтобы не ломать AgentStateV3)

**Файлы для модификации:**
- `agent/coder.py` — добавить `done` handoff-тул, добавить логику чтения `plan_md` и `feedback_md` из state, упростить prompt
- `agent/chat_agent.py` — заменить `assemble_ecoos_app` + `resume_assembly` на новую обёртку, которая инвочит трёх-нодовый граф с устойчивым thread_id
- `backend/server.py` — стримить новые типы событий: `phase_change`, `planner_message`, `coder_progress`, `executor_progress`, `final_result`
- `frontend/components/chat/chat-interface.tsx` — отображать phase, рендерить `plan_md` Markdown'ом с кнопкой Approve, показывать прогресс по фазам

**Файлы для удаления (после стабилизации):**
- `agent/architect.py` — заменяется new-граф'ом
- `agent/graph_v2.py:create_agent_graph_v3` — V3 pipeline остаётся как fallback в `chat_agent_v3`, но не основной путь

**Тесты:**
- Unit: `test_parsers.py` (regex на 5+ примерах PRD), `test_routing.py` (state transitions)
- Integration: synthetic state → Coder только → Executor только; проверить, что parser robust на разных моделях
- E2E: реальная сборка простого калькулятора через всю цепочку

## 11. Open questions

1. **Прогресс-стриминг для Planner.** В фазе planning planner может долго думать (RAG-запросы, чтение компонентов). Стримить ли token-by-token, или ждать full response каждый ход? **Предложение:** token streaming через `stream_mode="messages"` на planner_messages; для coder/executor — тоже, но фронт показывает только latest assistant message, не всю историю. Финализируется в impl plan.
2. **Cancel mid-flight.** Если пользователь закрывает чат во время `coding`/`executing`, нужно ли отменять asyncio.Task? **Предложение:** сейчас не нужно (PR #10 уже сделал PipelineSession robust к disconnect'ам). Cancellation — отдельный эпик.
3. **Multi-user.** `MemorySaver` хранит state per `thread_id`, но в одном Python-процессе. Для multi-user — нужен SqliteSaver или Postgres. **Out of scope этого spec'a.**

## 12. Out of scope

- Persistent checkpointer (SqliteSaver/PostgresSaver) — оставлено на потом.
- Параллельная разработка нескольких develop-компонентов (Coder делает sequentially).
- Streaming token-level из инсайдов handoff-тулов (handoff — atomic act).
- Cancellation через `Command(graceful=True)` — V2 API LangGraph, оставлено на будущее.
- Метрики: latency per phase, iteration counts, success rate — instrumentation отдельным эпиком.
