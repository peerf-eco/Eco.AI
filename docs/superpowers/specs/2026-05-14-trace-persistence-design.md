# Trace Persistence — V6 Pipeline

**Дата:** 2026-05-14
**Ветка:** `feat/v6-five-node-pipeline`
**Статус:** design approved, готов к writing-plans

---

## 1. Проблема

V6-пайплайн не сохраняет трейсы выполнения нод никуда на диск. Последствие:
анализ поведения агента (например, разбор зацикливания coder'а на поиске
`IEcoBase1.h`) возможен только по ручной копипасте из браузерного UI.

### Текущее состояние (по коду, 2026-05-14)

| Где живёт трейс | Что это | Срок жизни |
|---|---|---|
| `EcoAgentResult.history` (`agent/v6/eco_agent.py:57`) | полная ReAct-история: `SystemMessage` + seed + все `AIMessage` (с `tool_calls`, thinking в `additional_kwargs`) + все `ToolMessage` | в памяти процесса |
| `V6State.{node}_messages` (`agent/v6/state.py:26-30`) | туда нода кладёт `result.history` | **перезаписывается** при каждом входе в ноду |
| `MemorySaver()` checkpointer (`backend/server.py:666-667`) | LangGraph state в RAM | **умирает с процессом** |
| `EcoAgentEvent`-поток (`TOOL_START/END`, `THINKING_DELTA`) | `on_event` → WebSocket → фронт | не персистится вообще |

Два уровня потери:
1. `state.py:22-25` явным комментарием запрещает `add_messages`-аккумуляцию:
   каждая нода **REPLACES** свой `*_messages` — при retry трейс прошлой
   попытки затирается. Причина в коде: «cross-retry accumulation would
   quadratically grow the checkpointer payload».
2. Checkpointer = `MemorySaver` (RAM). Hot-reload (`uvicorn --reload` следит
   за `agent/`, `backend/`) стирает все трейсы при каждой правке Python-кода.

### Архитектурное следствие

Персистить трейсы **нельзя** через накопление в `V6State` — это прямо
нарушит зафиксированное в `state.py` решение о размере checkpointer-payload.
Запись должна идти **в обход state** — на диск, в момент выхода из ноды.

---

## 2. Решения (из brainstorming-сессии)

| Вопрос | Решение |
|---|---|
| Что сохранять | **Полная message-история** (`EcoAgentResult.history`) — ground truth того, что LLM видел и произвёл |
| Гранулярность | **Файл на каждую попытку ноды** — retry не затирает прошлую попытку |
| Расположение | **Центральный `traces/`** в корне `Eco.AI.Assembly1/` |
| Формат | **JSON** — один объект на файл, парсится программно и читается глазами |
| Где в коде писать | **Подход B** — shared-хелпер `write_trace`, вызывается каждой нодой после `agent.run()` |

### Почему Подход B (а не запись внутри `EcoAgent` или обёртка LangGraph)

- `EcoAgent` остаётся чистым loop-примитивом — его можно юнит-тестить без
  файловой системы. Влить запись на диск в `run()` — значит каждый тест
  EcoAgent трогает FS или мокает её.
- Нода **естественно** знает свой контекст: имя ноды = имя функции, `state`
  под рукой, thread_id берётся через `get_config()` тем же приёмом, каким
  `setup_node` уже берёт `get_stream_writer()` (`setup.py:88-91`).
- `agent.run()` сам ловит исключения `_stream_llm` и всегда возвращает
  `EcoAgentResult` со `status` и непустой `history` (`eco_agent.py:192-197`)
  — значит вызов `write_trace` после `agent.run()` ловит все 4 исхода
  (`done`/`no_tool_call`/`max_iters`/`error`) без единого `try` в ноде.

---

## 3. Дизайн

### 3.1 Расположение и структура файлов

```
Eco.AI.Assembly1/traces/                 ← новый mount в docker-compose.yml
  <thread_id>/
    01-planner.json
    02-setup.json
    03-coder.json
    04-builder.json
    05-tester.json
    06-coder.json        ← retry: pipeline вернулся в coder
    07-builder.json
    ...
```

`NN` — монотонный префикс: `write_trace` при записи считает `*.json` в
`traces/<thread_id>/`, берёт `count + 1`, дополняет нулём до 2 знаков.
V6-пайплайн внутри одного thread исполняется строго последовательно
(LangGraph гоняет по одной ноде) — гонок нет, блокировки не нужны.

Retry coder'а естественно станет `03-coder.json` и `06-coder.json`:
последовательность + имя ноды рассказывают историю без вычисления «номера
попытки».

### 3.2 JSON-схема одного файла

```json
{
  "meta": {
    "thread_id": "21508ac5-0c8f-...",
    "node": "coder",
    "seq": 3,
    "phase": "coding",
    "status": "max_iters",
    "error": "",
    "retry_count": 0,
    "last_failure_origin": "",
    "iters": 18,
    "ts_written": "2026-05-14T10:56:03Z"
  },
  "messages": [ /* langchain_core.messages.messages_to_dict(history) */ ]
}
```

Поля `meta`:
- `thread_id` — из `get_config()["configurable"]["thread_id"]`
- `node` — аргумент вызова (`"setup"`, `"coder"`, ...)
- `seq` — монотонный номер (см. 3.1)
- `phase` — `state["phase"]` на входе в ноду
- `status` / `error` — из `EcoAgentResult` (фактический исход *этой* попытки)
- `retry_count` / `last_failure_origin` — `state.get(...)` (контекст пайплайна на входе)
- `iters` — число `AIMessage` в `history` (derived)
- `ts_written` — ISO-8601 UTC момента записи

**Сериализация сообщений:** через `langchain_core.messages.messages_to_dict()`
— канонический round-trippable формат. Ручная сериализация не используется:
`thinking` живёт в `additional_kwargs`, `tool_calls` имеют специфичную форму.
`messages_to_dict` сохраняет `additional_kwargs` целиком ⇒ thinking-блоки
попадают в трейс.

### 3.3 Модуль `agent/v6/trace.py`

Единственный публичный объект — функция:

```python
def write_trace(
    result: EcoAgentResult,
    *,
    node: str,
    state: V6State,
    traces_root: Path | None = None,
) -> Path | None:
    """Сериализует полную message-историю одной попытки ноды в
    traces/<thread_id>/NN-<node>.json.

    Возвращает путь записанного файла, либо None если запись пропущена
    (нет graph-контекста) или провалилась. НИКОГДА не бросает исключение.
    """
```

Алгоритм:
1. `traces_root` — по умолчанию `Path(os.getenv("V6_TRACES_DIR", "traces"))`.
   В контейнере CWD = `/app` ⇒ `/app/traces` → хостовый `traces/`.
2. thread_id — через `langgraph.config.get_config()`. Нет контекста
   (`RuntimeError`) → возврат `None`, запись пропущена. Defensive-паттерн
   тот же, что в `setup.py:88-91`.
3. `mkdir(parents=True, exist_ok=True)` на `traces/<thread_id>/`.
4. `seq = len(glob("*.json")) + 1` в этой папке.
5. Собрать `meta` (из `result` + `state.get(...)`),
   `messages = messages_to_dict(result.history)`.
6. `json.dumps(payload, indent=2, ensure_ascii=False, default=str)` —
   `default=str` как safety-net против несериализуемого в `additional_kwargs`.
7. Атомарная запись: в `NN-<node>.json.tmp`, затем `os.replace()` на финальное
   имя.

Зависимости модуля: `EcoAgentResult` (`eco_agent.py`), `V6State` (`state.py`),
`messages_to_dict`, `get_config`. Всё — V6-внутреннее; `trace.py` живёт в
`agent/v6/`, привязка к V6-типам осознанная, generic-абстракция не строится
(YAGNI).

### 3.4 Интеграция в ноды

5 LLM-нод (`planner_node`, `setup_node`, `coder_node`, `builder_node`,
`tester_node`): сразу после `result = agent.run(seed)` — одна строка:

```python
result = agent.run(seed)
write_trace(result, node="setup", state=state)   # ← новая строка
if result.status == "done":
    ...
```

Две orchestration-ноды (`plan_gate`, `escalate`) не гоняют `EcoAgent` — не
трогаются.

### 3.5 docker-compose.yml

Добавить одну строку в `api.volumes`:

```yaml
      - ./traces:/app/traces
```

Это изменение **не подхватывается hot-reload** (`--reload` следит только за
Python-кодом). Нужен разовый `docker compose up -d` для пересоздания
контейнера `api` — отдельный deploy-шаг в плане реализации, с подтверждением
от пользователя перед запуском.

---

## 4. Обработка ошибок и краевые случаи

**Контракт «никогда не бросает».** Всё тело `write_trace` обёрнуто в
`try/except Exception` → при любом сбое логирует и возвращает `None`. Трейсы
— observability, они не имеют права ронять пайплайн.

| Случай | Поведение |
|---|---|
| Нет graph-контекста (`get_config()` → `RuntimeError`) — юнит-тест ноды | Возврат `None`, запись пропущена. Лог на `DEBUG`. |
| `thread_id` отсутствует в `config["configurable"]` | Возврат `None`. Лог на `WARNING`. |
| Несериализуемое в `additional_kwargs` | `json.dumps(..., default=str)` коэрсит в строку. Файл пишется. |
| Папка `traces/` не смонтирована | `mkdir` создаст `/app/traces` внутри контейнера; на хост не попадёт. Не ошибка кода — deploy-промах, ловится integration-проверкой. |
| Параллельная запись в один thread | Не бывает: LangGraph гоняет ноды последовательно. `seq = count+1` безопасен без локов — зафиксировать допущение в docstring. |
| Полузаписанный файл (контейнер убит посреди записи) | Атомарная запись `*.json.tmp` → `os.replace()`. Битый JSON не читается; в худшем случае остаётся `.tmp`-огрызок. |

Разделение уровней логирования: «нет контекста» (юнит-тест) — *ожидаемое*
состояние, `DEBUG`. «Нет thread_id при наличии контекста» / «исключение при
записи» — *неожиданное*, `WARNING`. Иначе прогон юнит-тестов завалит лог
ложными warning'ами.

---

## 5. Тестирование

### Юнит-тест `agent/v6/tests/test_trace.py`

1. **Happy path:** фейковый `EcoAgentResult` с известной `history`
   (`System + Human + AI-с-tool_call + Tool`), вызвать `write_trace` с
   `traces_root=tmp_path`, замокав `get_config()` на фейковый thread_id.
   Ассерты: файл `01-coder.json` существует; парсится; `meta`-поля совпадают;
   `messages` round-trip через `messages_from_dict()` даёт исходные сообщения.
2. **Контракт «не бросает»:** `traces_root` указывает на файл (не папку) или
   read-only путь → ассерт: возврат `None`, исключение не вылетело.
3. **Нумерация `seq`:** два вызова для одного thread → `01-planner.json`,
   `02-setup.json`.
4. **Нет контекста:** `get_config()` бросает `RuntimeError` → возврат `None`,
   файл не создан.
5. **`default=str` safety-net:** сообщение с несериализуемым объектом в
   `additional_kwargs` → файл всё равно пишется.

Round-trip через `messages_from_dict` — ключевой ассерт: доказывает не «файл
записался», а «записанное семантически эквивалентно тому, что видел LLM».

### Integration (ручная)

Добавить mount → `docker compose up -d` → прогнать пайплайн в UI один раз →
проверить, что `traces/<thread_id>/` на **хосте** содержит файлы и они
валидный JSON.

---

## 6. Вне scope (YAGNI)

- Автоматическая ротация / cleanup старых трейсов. Накопление файлов решается
  вручную; для дипломного проекта объёмы не критичны.
- Сохранение event-потока с таймингами (отдельно от message-истории).
  Рассматривалось, отвергнуто: message-история — ground truth, события —
  производный view.
- UI для просмотра трейсов. Трейсы потребляются чтением JSON-файлов.
- Round-trip replay (перезапуск ноды из сохранённого трейса). Формат
  round-trippable, но replay-механика не реализуется сейчас.

---

## 7. Файлы, затрагиваемые реализацией

| Файл | Изменение |
|---|---|
| `agent/v6/trace.py` | **новый** — модуль `write_trace` |
| `agent/v6/nodes/planner.py` | +1 строка вызова `write_trace` |
| `agent/v6/nodes/setup.py` | +1 строка вызова `write_trace` |
| `agent/v6/nodes/coder.py` | +1 строка вызова `write_trace` |
| `agent/v6/nodes/builder.py` | +1 строка вызова `write_trace` |
| `agent/v6/nodes/tester.py` | +1 строка вызова `write_trace` |
| `docker-compose.yml` | +1 строка mount `./traces:/app/traces` |
| `agent/v6/tests/test_trace.py` | **новый** — юнит-тесты |
| `.gitignore` | +`traces/` (трейсы не коммитятся) |
