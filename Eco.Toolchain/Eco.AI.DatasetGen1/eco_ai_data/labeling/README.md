# labeling — разметка сущностей и QA-пар

Ядро семантики датасета: из кода извлекаются **entities** (через tools) и генерируются **qa_pairs** (обучающие примеры).

## Файлы

| Файл | Содержимое |
|------|------------|
| `entity_schema.py` | Enum типов сущностей, `is_valid_entity` |
| `label_engine.py` | `LabelEngine`: `label()`, `generate_qa_pairs()` |

Зависимости: `tools/`, `archive_algorithms/` (при `--tool regex|openai`), OpenAI API.

---

## entity_schema.py

### EntityType

`FUNCTION`, `CLASS`, `STRUCT`, `UNION`, `ENUM`, `TYPEDEF`, `NAMESPACE`, `TEMPLATE`, `IMPORT`, `METHOD`, `PARAMETER`, `RETURN`, `VARIABLE`.

### is_valid_entity(entity: dict) -> bool

- `type` — допустимое значение enum (регистр нормализуется в engine);
- `name` — непустая строка.

---

## LabelEngine

### Конструктор

```python
LabelEngine(
    tool_name="ast",
    openai_model="gpt-4o-mini",
    openai_api_key="",
    *,
    dataset_mode="generation",       # generation | documentation
    qa_answers_via_openai=True,
    max_qa_pairs_per_file=None,
    include_context=False,           # только generation + CLI --context
)
```

### label(code: str) -> list[dict]

1. `tool.extract(code)` — см. [tools/README.md](../tools/README.md)
2. `_normalize_entity`: `type` → UPPER, `name` strip, `line` → int
3. Фильтр `is_valid_entity`

Результат → postprocessing → поле `entities` во внутренней записи.

### generate_qa_pairs(code: str, file_path: str = "") -> list[dict]

Формат одной пары:

```json
{
  "question": "...",
  "context": "...",
  "answer": "...",
  "question_type": "IMPLEMENTATION"
}
```

Остановка по `max_qa_pairs_per_file` после достижения лимита.

---

## Режим generation (instruction-to-code)

### Python

**Отбор функций:**

- top-level `def` / `async def` (не вложенные в другую функцию);
- не stub (`pass` / `...` только);
- **4–60** физических строк (`_MIN_FUNCTION_LINES`, `_MAX_FUNCTION_LINES`).

**question:**

```
Implement function with below signature using ACOM component-based architecture.
The signature is:

<реальная сигнатура из исходника>
```

**answer:** полный исходный сегмент функции (AST `lineno`–`end_lineno`).

**context:** только если `include_context=True`:

- OpenAI (до ~120k символов файла) или
- `_fallback_generation_context` — шаблон по именам параметров из сигнатуры.

**question_type:** `IMPLEMENTATION`.

### C/C++

Отдельный парсер `_extract_c_like_functions` (построчный):

- многострочные сигнатуры, `const`, scope (`Class::method`);
- баланс `{}` для тела;
- фильтр `_is_c_like_function_header`;
- **без** лимита 4–60 строк (в отличие от Python).

**answer** = исходный листинг `header { ... }` один в один.

Для C/C++ generation типичный запуск: `--strict-c-cpp-only`; `--tool c_ast` влияет на entities, не обязателен для QA-тел.

---

## Режим documentation

### Python

До **22** типов вопросов на функцию — план `_question_plan` по AST-сигналам тела:

| Тип | Когда добавляется (упрощённо) |
|-----|-------------------------------|
| `FUNCTIONALITY` | всегда |
| `RETURN_VALUE` | есть `return` |
| `EDGE_CASES` | ветвления / исключения |
| `WHY_CHECK`, `WHY_FALLBACK` | условия / fallback-логика |
| `BUG_SAFETY`, `BUG_EDGE` | рискованные конструкции |
| `NESTED_LOGIC`, `TRY_CONTROL_MIX` | вложенность if/try |
| … | см. `_BodySignals` в `label_engine.py` |

**context:** листинг функции.

**answer:** OpenAI (`temperature=0.15`, max ~900 tokens) или fallback (docstring / generic).

**Фильтры ответов** (`_BAD_ANSWER_*`): отсекаются упоминания docstring/dataset/context, hedge-слова (likely, probably, …).

### C/C++

Один вопрос `FUNCTIONALITY` на функцию (без полного `_question_plan`).

---

## OpenAI

Порядок получения ключа:

1. `openai_api_key` из CLI/config
2. переменная `OPENAI_API_KEY`
3. `.env` в cwd и до 10 уровней вверх от `label_engine.py`

`--no-qa-openai` отключает и doc-ответы, и AI-generated context.

---

## Поток в пайплайне

```
cleaned code
  → label() → entities → Validator → Dedup → Normalizer
  → generate_qa_pairs() → qa_pairs
  → DatasetBuilder.build_entry()
```

QA-пары **не** проходят postprocessing на уровне пайплайна (дедуп только в combined export).

---

## Известные ограничения

| Область | Ограничение |
|---------|-------------|
| C/C++ entities | Зависимость от clang/includes |
| C/C++ doc | Только FUNCTIONALITY |
| Вложенные Python-функции | Не попадают в QA |
| `label_engine.py` | Крупный модуль; логика QA и C-parser в одном файле |
