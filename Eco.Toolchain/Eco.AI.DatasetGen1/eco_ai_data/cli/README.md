# cli — интерфейсы командной строки

Три точки входа, зарегистрированные в `setup.py` как `console_scripts`. Все команды строят `PipelineConfig` и вызывают `EcoAIDataPipeline`.

## Файлы

| Файл | Команда | Режим `dataset_mode` |
|------|---------|----------------------|
| `main_cli.py` | `eco-ai-data` | `generation` |
| `doc_main_cli.py` | `eco-ai-data-doc` | `documentation` |
| `quality_cli.py` | `eco-ai-data-quality` | только quality, без пайплайна |

Обёртка в корне проекта: скрипт `eco-ai-data` → `python3 -m eco_ai_data.cli.main_cli`.

---

## eco-ai-data (generation)

**Назначение:** датасет instruction-to-code (ACOM): вопрос с сигнатурой → ответ = реальный листинг функции.

### Синтаксис

```bash
eco-ai-data [глобальные флаги] analyze <repo_path_or_url>
```

Глобальные флаги указываются **до** `analyze`.

### Флаги

| Флаг | `PipelineConfig` | Описание |
|------|------------------|----------|
| `--tool ast\|c_ast\|regex\|openai` | `tool_name` | Инструмент извлечения **сущностей** (не тел функций для C) |
| `--processes N` | `processes` | Параллельное чтение файлов; `0` = авто |
| `--output-dir DIR` | `output_dir` | База вывода (по умолчанию `outputs`) |
| `--strict-python-only` | `strict_python_only` | Только `.py` |
| `--strict-c-cpp-only` | `strict_c_cpp_only` | Только C/C++ |
| `--openai-model MODEL` | `openai_model` | Модель OpenAI |
| `--openai-api-key KEY` | `openai_api_key` | Ключ (иначе env / `.env`) |
| `--no-qa-openai` | `qa_answers_via_openai=False` | Без OpenAI: шаблонный context и fallback-ответы |
| `--context` | `include_context=True` | Заполнять поле `context` в JSONL |
| `--max-qa-pairs N` | `max_qa_pairs_per_file` | Лимит пар на исходный файл |

### Примеры

```bash
eco-ai-data --strict-c-cpp-only --context analyze /path/to/Lessons

eco-ai-data --strict-c-cpp-only --max-qa-pairs 2 analyze \
  "https://github.com/org/repo/tree/main/path/to/Lessons"
```

### Вывод

Печатает `key=value` для каждого пути из `analyze_and_export` (см. [README.md](../../README.md#результат-работы)).

---

## eco-ai-data-doc (documentation QA)

**Назначение:** вопросы о поведении кода; `context` = листинг функции; ответ — объяснение (OpenAI или fallback).

### Отличия от main_cli

- Нет флага `--context` (контекст всегда задаётся в `LabelEngine` для doc-режима).
- `dataset_mode="documentation"`.
- Типы вопросов: `FUNCTIONALITY`, `RETURN_VALUE`, `WHY_*`, `BUG_*` и др. (см. [labeling/README.md](../labeling/README.md)).

```bash
eco-ai-data-doc --strict-python-only analyze /path/to/repo
```

---

## eco-ai-data-quality

**Назначение:** пересчёт метрик качества по уже экспортированному датасету, без полного прогона пайплайна.

### Синтаксис

```bash
eco-ai-data-quality <dataset_path> [--output-json PATH] [--output-md PATH] [--print-json]
```

| Аргумент | Описание |
|----------|----------|
| `dataset_path` | Каталог `outputs/<repo>/` или один `.jsonl` |
| `--output-json` | Путь к JSON-отчёту |
| `--output-md` | Путь к Markdown-отчёту |
| `--print-json` | Дублировать JSON в stdout |

Если `--output-json` и `--output-md` не заданы, пишет в `<dataset>/reports/` или `<parent>/reports/` для файла.

### Пример

```bash
eco-ai-data-quality outputs/Lessons
```

Детали метрик: [quality/README.md](../quality/README.md).

---

## Связь с пайплайном

```
argparse → PipelineConfig → EcoAIDataPipeline.analyze_and_export()
                              └─ (quality_cli) analyze_dataset_paths()
```

Для встраивания в другие инструменты предпочтительнее импорт `EcoAIDataPipeline` напрямую, а не subprocess CLI.

## Типичные ошибки

| Симптом | Причина |
|---------|---------|
| `Repository path does not exist` | Неверный локальный путь |
| `Failed to clone repository` | Нет `git` или недоступен URL |
| `Subpath not found` | Неверный путь в GitHub tree URL |
| Пустой `combined_rows` | Нет подходящих функций / слишком строгий `--max-qa-pairs` |
