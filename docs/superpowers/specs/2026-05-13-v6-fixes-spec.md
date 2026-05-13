---
title: V6 — Fix spec (SDK layout + event streaming + escalation honesty)
status: draft
created: 2026-05-13
authors: yan, claude (Opus 4.7), codex (critique)
branch: feat/v6-five-node-pipeline
supersedes: —
related-specs:
  - 2026-05-13-v6-pipeline-design.md
related-memory:
  - v6-architecture.md (after this lands)
  - feedback_model_portability.md
---

# V6 — Fix spec

## 1. Summary

Первый полевой прогон V6 в Docker вскрыл два независимых класса дефектов:

1. **Пайплайн не доходит до сборки** — он встаёт ещё на planner (или setup) из-за structural mismatch между тем, как код ищет компоненты в `source/`, и тем, как они реально там разложены. Пользователь видит «Max retries reached» **с retry_count = 0**, потому что событие `max_retry_escalation` шлётся при любом входе в escalate-ноду, а planner/setup/coder уходят туда мгновенно при `no_tool_call / max_iters / error`.
2. **UI не показывает прогресс** — между «Phase: Planning» и «Plan review» пользователь смотрит на спиннер 30–60 секунд без единого live-события: backend эмитит только при мутации state между нодами, а EcoAgent внутри ноды бежит молча. По образцу `F:\ai-mek` (mek-ai-client) UI должен показывать tool-calls, итерации и (опционально) token streaming.

Этот документ описывает что реализовать и почему. Он **не** содержит реализацию — план реализации формируется отдельной задачей.

## 2. Симптомы (что сообщил пользователь)

> 1. ФРонтенд не выглядит, как в mek. Например, нет tool_call ячеек и я не вижу прогресс, не вижу как токены генерируются
> 2. получил ошибку max retries reached

## 3. Корневой анализ

### 3.1. Bug A — пайплайн встаёт до сборки (SDK layout mismatch)

#### A.1. Несогласованный layout `source/`

Реальная файловая структура (наблюдается в `ecoos-api`-контейнере, `/app/source/`):

| Категория | Пример | Структура |
|---|---|---|
| Versioned | `Eco.Math.C89_DK_v.1.0.1.2/` | двухуровневая: `<name>_DK_v.<ver>/<name>/SharedFiles\|BuildFiles\|DesignFiles/` |
| Flat | `Eco.MemoryManager1/`, `0000000000000000000000004D656D31/` | плоская: `<name>/SharedFiles\|BuildFiles/...` (без `_DK_v.`) |

То есть «обычный» SDK-пакет на самом деле имеет три уровня контейнеров, а framework-компоненты — два. Любой код, ищущий ровно один слой, ломается на одной из категорий.

#### A.2. `agent/v6/tools/planner.py` ищет на уровень мельче

```python
# planner.py:23-36 (_read_component)
matches = sorted(sdk_root.glob(f"{args.name}_DK_v.*"))
pkg = matches[-1]
shared = pkg / "SharedFiles"          # ← ищет в outer root
if not shared.exists():
    return ToolResult(..., is_error=True)
```

Для versioned пакета `Eco.Math.C89_DK_v.1.0.1.2/` нужный `SharedFiles/` лежит ещё на уровень ниже — в `Eco.Math.C89/SharedFiles/`. Tool возвращает `is_error=True` → LLM-планер видит «no .h files in SharedFiles/» → пытается ещё раз → крутится `max_iters=30` → `phase="failed_escalated"`.

```python
# planner.py:39-46 (_list_components)
for d in sorted(sdk_root.iterdir()):
    if d.is_dir() and "_DK_v." in d.name:
        base = d.name.split("_DK_v.")[0]
        ...
```

Этот фильтр **прячет flat-пакеты от LLM**: `Eco.MemoryManager1`, `Eco.InterfaceBus1` не имеют `_DK_v.` в имени и в список не попадают. А по memory ([Framework Components](../../../README.md) — `Eco.System1`, `Eco.InterfaceBus1`, `Eco.MemoryManager1`, `Eco.Core1`, `Eco.FileSystemManagement1` обязательны для любой сборки). LLM их не видит → пишет план без них → даже если дойдёт до builder, link errors.

#### A.3. `setup_node` system prompt ожидает неверную структуру

```python
# agent/v6/nodes/setup.py:15-22 (SETUP_SYSTEM_PROMPT)
"... call `list_dir` on the expected component directory under project_dir
to verify the package actually landed (look for SharedFiles/, BuildFiles/)."
```

Для versioned пакетов `SharedFiles/BuildFiles/` лежат на уровень глубже. LLM делает `list_dir(<pkg>)` → видит только `<name>/` (один подкаталог) → отчитывается «не нашёл» → не вызывает `mark_setup_done` → `max_iters=30` → `failed_escalated`.

#### A.4. `_ecoos_pull` копирует не тот слой

```python
# agent/v6/tools/setup.py:83-100 (Linux pathway)
src = Path(sdk_root) / pkg_dir_name        # outer package root
dst = Path(project_dir) / pkg_dir_name
shutil.copytree(src, dst, dirs_exist_ok=True)
```

Структурно идентично источнику, но coder/builder через `downloaded_paths` получают outer package root, тогда как реальные `.h`/`.a` файлы лежат на уровень ниже. Coder LLM либо угадывает путь, либо нет.

### 3.2. Bug B — событие escalation перегружено

```python
# agent/v6/nodes/escalate.py:6-22
def escalate_node(state):
    resume = interrupt({
        "failure_origin": state.get("last_failure_origin", ""),
        ...
    })
```

`escalate_node` не различает источники входа. А ноды входят в него по разным причинам:

| Источник | Поведение |
|---|---|
| `builder` или `tester` исчерпал `retry_count >= max_retries` | Истинный retry-ceiling |
| `planner` упал на `max_iters / no_tool_call / error` | НЕ retry, **первая попытка** |
| `setup` упал так же | НЕ retry, первая попытка |
| `coder` упал так же | НЕ retry, первая попытка |

Все четыре случая шлют клиенту одно и то же событие `max_retry_escalation`. UI рендерит «Max retries reached × <N>», что ложь при `retry_count == 0`.

Дополнительно: `builder.py:49-54` и `tester.py:52-57` на non-done статус **не выставляют** `last_failure_origin` — escalation payload может прийти с пустым полем.

### 3.3. Bug C — отсутствие event streaming в UI

#### C.1. Backend: пустой `custom`-канал

`backend/server.py:877-883`:
```python
async for kind, data in graph.astream(
    graph_input, config=config, stream_mode=["updates", "custom"]
):
    if kind == "updates":
        await emit_updates(data)
    elif kind == "custom":
        await websocket.send_json(data)
```

`stream_mode=["updates", "custom"]` слушает оба канала, но **никто в codebase V6 не вызывает `langgraph.config.get_stream_writer()`**. Custom-канал пустой → live-телеметрия не идёт.

#### C.2. EcoAgent имеет хук, но он не подключён

`agent/v6/eco_agent.py:81-117` принимает `on_event: Callable[[EcoAgentEvent], None] | None`. EventType: `START / TEXT_DELTA / TOOL_START / TOOL_END / TOOL_UPDATE / ITERATION / DONE / NO_TOOL_CALL / MAX_ITERS / ERROR`.

Все ноды создают агент без хука:
```python
# agent/v6/nodes/coder.py:52-58 (типично)
agent = EcoAgent(
    llm=llm,
    system_prompt=CODER_SYSTEM_PROMPT,
    tools=tools,
    stop_tool="mark_code_done",
    max_iters=max_iters,
)  # ← no on_event
```

#### C.3. LLM вызывается через `.invoke()`, не `.stream()`

`agent/v6/eco_agent.py:133-141`:
```python
resp = self._llm_bound.invoke(history)
```

Token streaming в принципе невозможен — `.invoke()` возвращает целый AIMessage за один shot. `TEXT_DELTA` существует в enum но никогда не эмитится.

#### C.4. Frontend не готов отображать прогресс даже если backend начнёт слать

`frontend/components/chat/types.ts:69-138` — `Block` discriminated union содержит: `text | phase_header | node_done | build_fail | test_fail | plan_review | escalation | pipeline_done | error`. **Нет** типа `tool_call`, `iteration`, `thinking`, `tool_update`.

`stream-message.tsx:88-265` — switch по `block.type` рендерит только перечисленные выше. Нет компонента типа `ToolBlock` (как `mek-ai/StreamMessage.tsx:29-94`).

`use-v6-socket.ts:96-205` — `handleEvent` switch покрывает только текущие 9 типов serverEvent. Не подготовлен к `node_event`/`tool_start`/`tool_end`.

### 3.4. Bug D — stale-thread risk (low priority)

`frontend/components/chat/use-v6-socket.ts:25, 223-228` хранит `thread_id` в `sessionStorage` и не очищает на terminal state. `backend/server.py:660-668` держит `_v6_checkpointer` как module-global.

Сценарий: пользователь дошёл до `pipeline_done`, перезагрузил вкладку — фронт отдаёт старый `thread_id` → backend поднимает «мёртвый» граф (без pending interrupts) → возвращает фейковый heartbeat → новая `user_request` шлётся как продолжение завершённой беседы → undefined behavior.

Дополнительно: при `uvicorn --reload` (HMR) `_v6_checkpointer` пересоздаётся, теряя ВСЕ thread'ы; sessionStorage клиента продолжает удерживать «обещание» старого thread.

## 4. Что реализовать

Структурированный список изменений. Каждый пункт привязан к корневой причине из §3.

### 4.1. SDK layout resolver (фикс A.1/A.2/A.3/A.4)

**Где:** новый модуль `agent/v6/tools/sdk_layout.py` (или extension в `tools/common.py`).

**Что:**
```python
def resolve_component_root(sdk_root: Path, base_name: str, version: str | None = None) -> Path | None:
    """
    Найти "inner root" — каталог, в котором лежит SharedFiles/BuildFiles.
    Поддерживает три варианта layout:
    - versioned двухуровневый: <sdk_root>/<base>_DK_v.<ver>/<base>/
    - versioned одноуровневый: <sdk_root>/<base>_DK_v.<ver>/   (на случай старых пакетов)
    - flat:                    <sdk_root>/<base>/
    Возвращает каталог, где гарантированно есть SharedFiles/ (или BuildFiles/, для no-header пакетов).
    """
```

**Где переиспользовать:**
- `agent/v6/tools/planner.py:_read_component` — через resolver.
- `agent/v6/tools/planner.py:_list_components` — собирать ВСЕ каталоги (и `_DK_v.*` и flat), исключая каталоги CID-формата (если они не нужны планеру в list).
- `agent/v6/tools/setup.py:_ecoos_pull` (Linux pathway) — копировать **inner root**, чтобы `downloaded_paths` в state указывали на каталог с `SharedFiles/BuildFiles/`.

**Почему:** одна точка ветвления вместо трёх отдельных fix'ов в трёх tools. Так legacy/новые layout не разъедутся в будущем.

**Альтернатива, отвергнутая:** мигрировать `source/` к единому layout. Отвергнуто — мы не контролируем выход eco-cli (на Windows), а на Linux уже копируем «как есть»: нам важно адаптироваться к разнообразию, а не диктовать форму.

### 4.2. Setup prompt + verification (фикс A.3)

**Где:** `agent/v6/nodes/setup.py:SETUP_SYSTEM_PROMPT`.

**Что:** заменить расплывчатое «look for SharedFiles/, BuildFiles/» на конкретное:
- Указать, что после `ecoos_pull` нужный каталог лежит в `<project_dir>/<component_root>/` (path возвращается tool'ом — добавить его в `details` `ToolResult`).
- Описать обязательные подкаталоги (`SharedFiles/`, `BuildFiles/Linux/x86_64/StaticRelease/` или `BuildFiles/Windows/amd64/StaticRelease/`).
- Дать пример валидного списка `downloaded_paths` для `mark_setup_done`.

**Почему:** даже после resolver fix LLM нужен contract — что считается «успешно скачанным». Без явного prompt'а LLM продолжит угадывать.

### 4.3. Honest escalation protocol (фикс B)

**Где:** `agent/v6/state.py`, `agent/v6/nodes/escalate.py`, `agent/v6/nodes/{planner,setup,coder,builder,tester}.py`, `backend/server.py`, `frontend/components/chat/types.ts`, `frontend/components/chat/escalation-block.tsx`.

**Что:**
1. Добавить в state `last_status` варианты с явным указанием reason: `"planner_max_iters"`, `"setup_max_iters"`, `"coder_max_iters"`, `"builder_retry_limit"`, `"tester_retry_limit"`. (Уже частично есть в коде — `f"planner_{result.status}"`).
2. `escalate_node` собирает payload с явным `reason: Literal["retry_limit" | "planner_max_iters" | "setup_max_iters" | "coder_max_iters" | "..."]`.
3. На non-done в `builder.py:49-54`/`tester.py:52-57` ставить `last_failure_origin = "builder"|"tester"`.
4. Backend переименовать `max_retry_escalation` → `escalation_required`, передавать `reason`.
5. Frontend `EscalationBlock` рендерит правильный заголовок: «Planner timed out», «Setup failed», «Max retries reached» — в зависимости от `reason`.

**Почему:** текущее сообщение «Max retries reached × 0» — это лживая телеметрия. Пользователь принимает решение Continue/Abort на основе этого текста; если он лжёт — решение неинформированное.

**Альтернатива, отвергнутая:** разделить escalate на несколько нод (`escalate_planner`, `escalate_builder`, ...). Отвергнуто — раздутие графа, та же информация решается одним enum-полем.

### 4.4. Event streaming через `get_stream_writer` (фикс C.1/C.2)

**Где:** все `agent/v6/nodes/*.py`, `backend/server.py`, `frontend/components/chat/types.ts`, `frontend/components/chat/stream-message.tsx`, `frontend/components/chat/use-v6-socket.ts`.

**Что:**
1. В каждой ноде получить writer:
   ```python
   from langgraph.config import get_stream_writer
   writer = get_stream_writer()
   def on_ev(ev):
       writer({"type": "node_event", "node": "<this-node>", "event": ev.type.value, "data": ev.data})
   agent = EcoAgent(..., on_event=on_ev)
   ```
2. В `backend/server.py` `kind == "custom"` уже emit'ит — не нужно ничего менять.
3. Frontend `types.ts` добавить:
   - `NodeEventEvent` в `ServerEvent` union.
   - `ToolCallBlock`, `IterationBlock` (или объединить под `progress_block`) в `Block` union.
4. `use-v6-socket.ts` — handler для `node_event`: маппит `tool_call_start` → создаёт `ToolCallBlock(running=true)`; `tool_call_end` → обновляет тот же блок (`running=false, output, isError`); `iteration` → опционально обновляет счётчик в `PhaseHeaderBlock` или отдельный indicator.
5. `stream-message.tsx` рендерит `ToolCallBlock` как у mek (`F:\ai-mek\repos\mek-ai-client\src\chat\StreamMessage.tsx:29-94` — collapsible, status badge, duration).

**Почему:** это даёт пользователю реальную обратную связь во время 30–60-секундного LLM-вызова. Без этого agentic UI выглядит как обычный chat-bot со spinner'ом.

**Что НЕ делаем сразу:** token streaming через `llm.stream()`. См. §6.

### 4.5. Frontend reset thread on terminal (фикс D, частичный)

**Где:** `frontend/components/chat/use-v6-socket.ts` (handler `pipeline_done` и `escalation` с `status=abort`).

**Что:** при terminal state очищать `sessionStorage[THREAD_ID_KEY]` и `setThreadId(null)`, чтобы следующий `user_request` создал новый thread.

**Почему:** убирает «оживление мёртвого графа» после reload. Это не полное решение stale-thread (HMR-уязвимость остаётся), но 80% реальных сценариев покрывает.

**Альтернатива, отвергнутая полностью:** persistent storage backend-graph (Sqlite). Решено [ранее](2026-05-13-v6-pipeline-design.md) — оставить MemorySaver. Возвращаться к этому решению — отдельный спор.

## 5. Порядок работ

Приоритет по тому, что без чего бесполезно:

| # | Шаг | Что разблокирует | LOC | Время |
|---|-----|------------------|----:|------:|
| 1 | SDK resolver + planner tools fix (§4.1) | Планер начинает корректно читать SDK | ~80 | 0.5–1ч |
| 2 | Setup tool + setup prompt (§4.1+§4.2) | Setup корректно копирует и верифицирует | ~50 | 0.5ч |
| 3 | Honest escalation (§4.3) | Frontend получает осмысленные reason'ы | ~120 | 1ч |
| 4 | Event streaming backend (§4.4 backend-part) | Custom-канал начинает наполняться | ~40 | 0.5ч |
| 5 | Event streaming frontend (§4.4 frontend-part) | UI рендерит tool/iteration | ~200 | 1.5–2ч |
| 6 | Frontend reset thread (§4.5) | Terminal-resilience | ~10 | 0.2ч |
| **Итого** | | | ~500 | **4–6ч** |

После #1–#2 пайплайн должен дойти до coder. После #3 пользователь узнает истинный reason любого failure. После #4–#5 UI станет похож на mek. #6 — гигиена.

**Параллелизация:** #1–#3 независимы между собой и от #4–#5 (фронт не знает про новые серверные изменения). Можно делить на двух исполнителей.

## 6. Что НЕ делаем сейчас (out of scope)

| Пункт | Почему отложено |
|---|---|
| Token streaming через `llm.stream()` | Требует переписать `EcoAgent.run()` цикл. Польза маржинальна, если уже есть tool/iteration события. Отдельная задача. |
| Multi-stage Dockerfile (9 GB → ~3 GB) | Не влияет на функциональность. Performance-task. |
| Persistent SqliteSaver checkpointer | Решено [в design spec](2026-05-13-v6-pipeline-design.md) — отложено. |
| Удаление `progress-viewer.tsx` (V4 legacy) | Orphan-файл, не мешает. Subject отдельного cleanup-PR. |
| Coder/Planner prompt enrichment (Linux makefile templates, framework components list) | Стоит сделать, но **после** того, как пайплайн стабильно доходит до coder. Без resolver'а это лечение симптомов. |
| Stream-mode `messages` в LangGraph (агрегация LLM-токенов отдельно от наших custom-событий) | Дублирует token streaming. См. первую строку. |

## 7. Acceptance criteria

Реализация принимается, если **все** следующие тесты проходят:

### 7.1. Unit / integration (`pytest`)

1. `resolve_component_root` корректно находит inner root для трёх layout'ов (versioned-2-level, versioned-1-level, flat) и возвращает `None` для несуществующих пакетов.
2. `planner._read_component` возвращает `.h` файлы и для versioned, и для flat пакетов (новый тест в `test_tools_planner.py`).
3. `planner._list_components` показывает И versioned-пакеты, И flat-framework-пакеты (Eco.MemoryManager1 виден).
4. `setup._ecoos_pull` (Linux pathway) копирует inner root, и `downloaded_paths` в state указывает на каталог, где реально есть `SharedFiles/`.
5. Все escalation paths (`planner_max_iters`, `setup_max_iters`, `coder_max_iters`, `builder_retry_limit`, `tester_retry_limit`) корректно ставят `reason` в payload escalate-interrupt.
6. `builder_node`/`tester_node` на non-done статус выставляют `last_failure_origin`.

### 7.2. Backend endpoint test (`test_v6_endpoint.py`)

7. Тест: при planner-fail (mock LLM возвращает text без tool_calls) frontend получает `escalation_required` с `reason="planner_max_iters"`.
8. Тест: при normal happy path frontend получает события `node_event` с типами `tool_call_start`/`tool_call_end` хотя бы один раз на каждой ноде.

### 7.3. Frontend build

9. `npm run build` зелёный — TS-проверка discriminated union на новые типы не валит type-checker.

### 7.4. Manual smoke в Docker

10. `docker compose up -d` → открыть `http://localhost:3100` → отправить «Собери калькулятор с pow и sqrt».
11. UI показывает phase change Planning → следом видны **tool-call ячейки** (`list_components`, `read_component`).
12. После approve плана видны tool-calls в Setup (`ecoos_pull`, `list_dir`).
13. Если случается escalation — UI показывает **правильный reason** (например «Setup timed out»), не «Max retries reached × 0».

## 8. Источники гипотез и кому что приписать

- §3.1 (SDK layout) — найдено в critique-сессии run-codex (см. журнал ниже).
- §3.2 (escalation overload) — найдено в той же critique-сессии. Я был уверен, что max_retries означает retry ceiling — это оказалось неверно.
- §3.3 (event streaming) — мой первоначальный диагноз, подтверждён codex.
- §3.4 (stale thread) — поднято codex как дополнительный риск.

Этот документ — **отчёт после самокритики**, не оригинальный анализ. Codex напомнил, что я свалился в confirmation bias («раз max_retries — значит builder»), не проверив, доходит ли пайплайн до builder вообще.

## 9. Связь с другими спеками

- [v6-pipeline-design.md](2026-05-13-v6-pipeline-design.md) — первичная архитектура V6. Этот файл не меняет архитектуру, только дотачивает её под реальный SDK.
- [Plan-then-confirm UX](2026-05-13-v6-pipeline-design.md#1-summary) сохраняется без изменений.
- Memory `feedback_model_portability.md` — остаётся в силе: новые prompts должны работать на kimi/glm/deepseek без `with_structured_output`.

## 10. Open questions

1. **`Eco.MemoryManager1`** — flat-пакет без `_DK_v.` суффикса. Это **намеренно** (framework-инфра не версионируется) или legacy? Если намеренно — `_list_components` должен явно мечать их как «framework, обязательные».
2. **CID-named каталоги** типа `0000000000000000000000004D656D31` в `source/` — это что? Static lib для SYS3 (по memory). Должны ли они отображаться в `_list_components`? Скорее нет.
3. **`uvicorn --reload`** в Docker compose: подходит для dev, но `_v6_checkpointer` теряется при HMR. На production должен быть без `--reload`. Документировать отдельно.
4. **Сколько ретраев builder/tester** реально комфортно? Сейчас `max_retries=3` (комбинированно). С обогащёнными промптами после fix'а можно понизить до 2 и сэкономить токены.
