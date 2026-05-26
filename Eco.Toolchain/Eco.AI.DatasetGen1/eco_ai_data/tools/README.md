# tools — извлечение сущностей из кода

Инструменты для **структурной разметки** (entities): функции, классы, параметры и т.д. Используются в `LabelEngine.label()`, результаты идут в `entities` и в `pipeline_report.md`.

**Не путать** с извлечением **тел функций для QA** в generation-режиме C/C++ — это отдельный line-parser в `labeling/label_engine.py`.

## Файлы

| Файл | Класс | Языки |
|------|-------|-------|
| `ast_tool.py` | `ASTTool` | Python |
| `c_ast_tool.py` | `CASTTool` | C, C++, заголовки |

Выбор инструмента: `PipelineConfig.tool_name` / CLI `--tool`.

---

## ASTTool (Python)

### API

```python
ASTTool().extract(code: str, *, max_function_body_chars=150_000) -> list[dict]
```

При `SyntaxError` возвращает `[]`.

### Типы сущностей (visitor `_ASTEntityVisitor`)

| type | Источник |
|------|----------|
| `IMPORT` | `import`, `from ... import` |
| `CLASS` | `class` |
| `FUNCTION` | top-level `def` / `async def` |
| `METHOD` | методы внутри класса |
| `PARAMETER` | аргументы функций |
| `RETURN` | `return` в теле |
| `VARIABLE` | присваивания, `self.`, dataclass-поля |

Дополнительные поля (по возможности): `line`, `class`, `function`, декораторы (`property`, `staticmethod`, …).

Тело функции в entity может обрезаться при превышении `max_function_body_chars`.

### Когда использовать

- `--tool ast` (по умолчанию)
- `--strict-python-only`

---

## CASTTool (C/C++)

### API

```python
CASTTool().extract(code: str) -> list[dict]
```

### Каскад парсеров

```
1. clang -Xclang -ast-dump=json  (режимы -x c и -x c++)
       ↓ пусто / только IMPORT
2. tree-sitter (если установлен)
       ↓
3. regex fallback (_fallback_extract)
```

**clang:** ненулевой exit code допустим (неполный AST при отсутствии include). Фильтр `_node_in_source` отсекает сущности из системных заголовков.

### Типы сущностей

`NAMESPACE`, `ENUM`, `TYPEDEF`, `TEMPLATE`, `CLASS`, `STRUCT`, `UNION`, `FUNCTION`, `METHOD` (constructor, destructor, operator, friend), `PARAMETER`, `RETURN`, `VARIABLE`, `IMPORT` (`#include`, `using`).

### Regex fallback

Однострочные объявления: struct/union/enum/typedef, простые сигнатуры функций без полного разбора тела.

### Зависимости окружения

| Компонент | Назначение |
|-----------|------------|
| `clang` в PATH | Основной путь |
| `tree-sitter`, `tree-sitter-languages` | Запасной AST |
| (нет) | Только regex — меньше recall |

Рекомендация для C/C++ датасетов: `--strict-c-cpp-only` и `--tool c_ast`.

---

## Связь с LabelEngine

```python
# label_engine.py (упрощённо)
tools = {
    "ast": ASTTool(),
    "c_ast": CASTTool(),
    "regex": HybridRegexTool(),      # archive_algorithms
    "openai": HybridRegexOpenAITool(),
}
raw = tools[tool_name].extract(code)
# → normalize → is_valid_entity filter
```

`--tool regex|openai` делегирует в `archive_algorithms/` (legacy, не документируется отдельно).

---

## Сравнение с QA-извлечением

| Задача | Модуль |
|--------|--------|
| Сущности для метрик / отчёта | `tools/` |
| Python: пары question/answer | `label_engine` + `ast` |
| C/C++: полные тела функций в answer | `label_engine._extract_c_like_functions` |

Для Eco Lessons generation обычно достаточно `--strict-c-cpp-only` без смены tool: QA-тела не зависят от `CASTTool`.

---

## Формат entity (общий)

```json
{
  "type": "FUNCTION",
  "name": "CEcoCalculatorA_Add",
  "line": 120,
  "class": "CEcoCalculatorA",
  "function": null
}
```

Валидация схемы: `labeling/entity_schema.py` → `is_valid_entity`.
