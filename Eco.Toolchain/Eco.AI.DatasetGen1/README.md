# Eco.AI.Data

Инструмент извлечения структурированных данных из репозиториев кода и подготовки датасетов для обучения моделей.

---

## Структура проекта

```
Eco.AI.Data/
├── pyproject.toml, setup.py          # сборка и зависимости
├── eco-ai-data                       # скрипт запуска CLI (./eco-ai-data из корня)
├── README.md                         # эта документация
├── outputs/                          # результаты (создаётся при запуске)
│   ├── *.json / *.jsonl              # pipeline-датасеты
│   ├── *_train.jsonl                 # плоские train-наборы
│   └── *.md                          # отчёты
│
└── eco_ai_data/
    ├── __init__.py
    ├── config.py                     # настройки пайплайна
    ├── master_pipeline.py            # главный пайплайн: загрузка → разметка → экспорт → отчёт
    │
    ├── preprocessing/                # подготовка репо и кода
    │   ├── repo_loader.py            # загрузка репо: локальный путь или git clone по URL
    │   ├── file_filter.py            # фильтр файлов по расширению, каталогам и размеру
    │   └── code_cleaner.py           # нормализация переносов, табов, лишних пустых строк
    │
    ├── tools/                         # основной инструмент извлечения
    │   └── ast_tool.py               # AST: функции, классы, импорты, параметры, методы
    │   └── c_ast_tool.py             # C/C++ AST: clang/libclang + tree-sitter fallback
    │
    ├── archive_algorithms/           # архивные алгоритмы (вызываются через --tool)
    │   ├── hybrid_regex_tool.py      # Regex + эвристики, type hints, без тел
    │   └── openai_tool.py            # Regex-кандидаты + OpenAI → структурированный JSON
    │
    ├── labeling/
    │   ├── entity_schema.py          # типы сущностей, валидация
    │   └── label_engine.py           # выбор инструмента, разметка, генерация датасет-пар
    │
    ├── postprocessing/
    │   ├── validator.py              # отбор валидных сущностей
    │   ├── deduplicator.py           # дедупликация по (type, name, class, function, line)
    │   └── normalizer.py             # приведение типов и имён к единому виду
    │
    ├── export/
    │   ├── json_exporter.py          # потоковая запись большого JSON
    │   └── dataset_builder.py        # сборка записи {repo, file, entities, qa_pairs, raw_code}
    │
    ├── reporting/
    │   ├── markdown_report.py        # генерация Markdown-отчёта
    │   └── metrics_report.py        # подсчёт файлов, сущностей, QA, разбивка по типам
    │
    └── cli/
        ├── main_cli.py               # CLI #1: generation dataset (instruction → code)
        └── doc_main_cli.py           # CLI #2: documentation QA dataset
```

---

## Два режима датасета

### 1) Generation (instruction-to-code)

CLI: `eco-ai-data` / `python3 -m eco_ai_data.cli.main_cli`.

Для каждой найденной функции формируется запись:

- `question`: *Implement function with below signature using ACOM component-based architecture...*
- `context`: опционально (`--context`), генерируется через OpenAI или fallback-шаблон.
- `answer`: реальный листинг функции из исходного кода.

Тип записи: `question_type=IMPLEMENTATION`.

### 2) Documentation QA (предыдущая версия)

CLI: `eco-ai-data-doc` / `python3 -m eco_ai_data.cli.doc_main_cli`.

Для каждой функции формируются QA-пары про поведение кода:

- `FUNCTIONALITY`, `RETURN_VALUE`, `EDGE_CASES`, `BEHAVIOR`, `WHY_*`, `BUG_*` и т.д.
- `context`: листинг функции.
- `answer`: OpenAI (если доступен) либо fallback по исходнику/докстроке.

### Общий pipeline

1. **Вход:** путь к папке с репо или URL GitHub (для URL выполняется `git clone --depth 1` во временный каталог).
2. **Preprocessing:** рекурсивный обход файлов по расширениям, исключение системных каталогов, очистка кода.
3. **Labeling:** извлечение сущностей (`ast` / `c_ast` / `regex` / `openai`) + генерация датасет-строк выбранного режима.
4. **Postprocessing:** валидация, дедупликация, нормализация сущностей.
5. **Export + Report:** запись JSON/JSONL и генерация Markdown-отчёта.

Параллельная обработка файлов — через `multiprocessing.Pool` (число процессов задаётся в конфиге или по умолчанию).

---

## Типы сущностей

`FUNCTION`, `CLASS`, `STRUCT`, `UNION`, `ENUM`, `TYPEDEF`, `NAMESPACE`, `TEMPLATE`, `IMPORT`, `METHOD`, `PARAMETER`, `RETURN`, `VARIABLE`.

---

## Инструменты извлечения

| Инструмент | Файл | Описание |
|------------|------|----------|
| `ast` | `tools/ast_tool.py` | Стандартный `ast`: функции, классы, методы, импорты, параметры, возвраты, переменные. |
| `c_ast` | `tools/c_ast_tool.py` | Качественный AST для C/C++: `clang -ast-dump=json` как основной путь, `tree-sitter` как fallback, с извлечением include/function/method/parameter/return/variable и расширенных типов (`struct/union/enum/typedef/namespace/template`). |
| `regex` | `archive_algorithms/hybrid_regex_tool.py` | Regex + эвристики: type hints, значения по умолчанию, без тел функций. |
| `openai` | `archive_algorithms/openai_tool.py` | Regex-кандидаты отправляются в OpenAI, ответ — JSON со сущностями. Нужен API-ключ. |

Выбор: `--tool ast` (по умолчанию), `--tool c_ast`, `--tool regex`, `--tool openai`.

---

## Формат датасета (JSON / JSONL)

Поддерживаются два формата:

- `json` — один большой JSON-массив (по умолчанию).
- `jsonl` — JSON Lines: одна запись на строку (удобно для стриминга/больших данных).

Одна запись содержит данные одного обработанного файла:

```json
{
  "repo": "имя_репо",
  "file": "относительный/путь/к/file.py",
  "entities": [{"type": "FUNCTION", "name": "...", "line": 1}, ...],
  "qa_pairs": [{"question": "...", "context": "...", "answer": "...", "question_type": "..."}, ...],
  "raw_code": "исходный код файла"
}
```

---

## Конфигурация

`config.py` — `PipelineConfig`:

- `max_file_bytes` — макс. размер файла (по умолчанию 2 MB).
- `include_extensions` — расширения файлов для сканирования (по умолчанию мульти-язычный список).
- `exclude_dirs` — каталоги, которые не сканируются (.git, venv, __pycache__ и т.д.).
- `processes` — число процессов (0 = авто).
- `tool_name` — `ast` / `c_ast` / `regex` / `openai`.
- `dataset_mode` — `generation` или `documentation` (устанавливается соответствующим CLI).
- `strict_python_only` — если `true`, принудительно анализируются только `.py` файлы.
- `strict_c_cpp_only` — если `true`, принудительно анализируются только C/C++-файлы (`.c/.h/.hpp/.hh/.hxx/.cpp/.cc/.cxx`).
- `output_format` — формат экспорта: `json` или `jsonl`.
- `openai_model`, `openai_api_key` — для OpenAI-запросов в контекст/ответы.
- `qa_answers_via_openai` — использовать OpenAI для генерации context/answer.
- `max_qa_pairs_per_file` — лимит записей на файл.
- `include_context` — добавлять `context` в generation-режиме.
- `output_dir` — каталог по умолчанию для вывода.

---

## CLI

Установка (из корня проекта):

```bash
pip install -e .
```

После установки доступны два скрипта:

- `eco-ai-data` — generation dataset (instruction-to-code),
- `eco-ai-data-doc` — documentation QA dataset.

Также всегда можно запускать как Python-модули:

- `python3 -m eco_ai_data.cli.main_cli ...`
- `python3 -m eco_ai_data.cli.doc_main_cli ...`

### Быстрые примеры

**Generation / Python / 5 записей на файл:**

```bash
eco-ai-data --strict-python-only --context --max-qa-pairs 5 analyze /path/to/repo --output-json outputs/module_py5_pipeline.jsonl --output-md outputs/module_py5_report.md
eco-ai-data qa-flatten outputs/module_py5_pipeline.jsonl outputs/module_py5_train.jsonl
```

**Generation / C-C++ / 5 записей на файл:**

```bash
eco-ai-data --strict-c-cpp-only --context --max-qa-pairs 5 analyze /path/to/repo --output-json outputs/cjson_c5_pipeline_v2.jsonl --output-md outputs/cjson_c5_report_v2.md
eco-ai-data qa-flatten outputs/cjson_c5_pipeline_v2.jsonl outputs/cjson_c5_train_v2.jsonl
```

**Documentation QA / Python:**

```bash
eco-ai-data-doc --strict-python-only --max-qa-pairs 5 analyze /path/to/repo --output-json outputs/doc_py5_pipeline.jsonl --output-md outputs/doc_py5_report.md
eco-ai-data-doc qa-flatten outputs/doc_py5_pipeline.jsonl outputs/doc_py5_train.jsonl
```

**Репозиторий по ссылке GitHub:**

```bash
eco-ai-data --strict-c-cpp-only --context analyze https://github.com/org/repo.git --output-json outputs/repo_c_pipeline.jsonl --output-md outputs/repo_c_report.md
```

### Команды `eco-ai-data` (generation)

**analyze** — разбор репо + экспорт JSON + генерация отчёта.

```bash
eco-ai-data analyze . --output-json outputs/dataset.jsonl --output-md outputs/report.md
eco-ai-data analyze https://github.com/org/repo.git --output-json outputs/repo.jsonl --output-md outputs/repo.md
```

**export** — разбор репо и только экспорт (обязательно `--repo`).

```bash
eco-ai-data export outputs/out.json --repo .
```

**report** — разбор репо и только Markdown-отчёт.

```bash
eco-ai-data report outputs/report.md --repo .
```

**qa-flatten** — преобразование pipeline JSONL в train JSONL (`question/context/answer`).

Если `eco-ai-data` не в PATH, используйте: `python3 -m eco_ai_data.cli.main_cli`.

### Команды `eco-ai-data-doc` (documentation QA)

- `analyze` — сбор QA-датасета и отчёта.
- `qa-flatten` — flatten в train JSONL.

### Общие опции (до подкоманды)

- `--tool ast|c_ast|regex|openai` — инструмент извлечения (по умолчанию `ast`). Указывать **до** подкоманды: `./eco-ai-data --tool c_ast analyze . ...`
- `--processes N` — число процессов (0 — авто).
- `--output-dir DIR` — каталог по умолчанию для вывода.
- `--strict-python-only` — включить режим анализа только Python-файлов (`.py`).
- `--strict-c-cpp-only` — включить режим анализа только C/C++-файлов.
- `--output-format json|jsonl` — формат JSON-экспорта.
- `--openai-model NAME`, `--openai-api-key KEY` — для `--tool openai`.
- `--max-qa-pairs N` — лимит записей на файл.
- `--context` — (только `eco-ai-data`) включить поле `context` в generation-режиме.
- `--no-qa-openai` — отключить OpenAI (контекст/ответы будут fallback).

---

## Где смотреть результаты

- **Pipeline JSON/JSONL:** файл из `--output-json`.
- **Train JSONL:** результат `qa-flatten` (обычно `*_train.jsonl`).
- **Markdown отчёт:** файл из `--output-md`.

В отчёте: сводка по репо, число файлов/сущностей/QA-пар, разбивка по типам, краткий блок про ошибки.

### Актуальные демо-артефакты

- `outputs/module_py5_train.jsonl` — generation-датасет, Python, 5 записей.
- `outputs/cjson_c5_train_v2.jsonl` — generation-датасет, C/C++, 5 записей.

---

## Зависимости

Указаны в `setup.py`: `datasets`, `openai`, `python-dotenv`. Остальное — стандартная библиотека.
