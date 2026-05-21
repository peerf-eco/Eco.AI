# Eco.AI.DatasetGen1

Инструмент для подготовки датасетов из репозиториев кода: instruction-to-code (ACOM) и documentation QA.

---

## Быстрый старт

```bash
pip install -e .

# Папку outputs/ создавать вручную не нужно — она появится при первом analyze
eco-ai-data --strict-c-cpp-only --context analyze /path/to/repo
```

Результат:

```
outputs/<имя_репо>/
  Lesson02/.../CEcoCalculatorA.c.jsonl   # зеркало структуры исходного репо
  <имя_репо>.jsonl                       # весь датасет одним файлом
  reports/
    pipeline_report.md
    quality_report.json
    quality_report.md
```

---

## Режимы

| CLI | Назначение |
|-----|------------|
| `eco-ai-data` | Generation: `question` + `answer` (листинг функции), `IMPLEMENTATION` |
| `eco-ai-data-doc` | Documentation QA: вопросы о поведении кода |
| `eco-ai-data-quality` | Повторный пересчёт метрик качества (по умолчанию уже есть после `analyze`) |

### Generation

- `question` — инструкция ACOM + сигнатура функции
- `context` — при флаге `--context` (OpenAI или шаблон)
- `answer` — реальный код из исходника

### Documentation QA

Типы вопросов: `FUNCTIONALITY`, `WHY_*`, `BUG_*` и др.; `context` — листинг функции.

---

## Структура проекта

```
Eco.AI.DatasetGen1/
├── setup.py, pyproject.toml
├── eco-ai-data                 # обёртка: python3 -m eco_ai_data.cli.main_cli
├── README.md
├── FULL_PROJECT_REPORT_RU.md   # технический отчёт (диплом)
└── eco_ai_data/
    ├── master_pipeline.py
    ├── config.py
    ├── cli/                    # main_cli, doc_main_cli, quality_cli
    ├── export/                 # repo_exporter, dataset_builder
    ├── preprocessing/          # repo_loader, file_filter, code_cleaner
    ├── labeling/               # label_engine
    ├── postprocessing/
    ├── reporting/
    ├── quality/
    ├── tools/                  # ast_tool, c_ast_tool
    └── archive_algorithms/     # regex, openai (--tool)
```

`outputs/` в репозиторий не коммитится (см. `.gitignore`), создаётся при запуске.

---

## Формат JSONL

Одна строка = одна обучающая запись:

```json
{
  "question": "Implement function with below signature using ACOM component-based architecture...",
  "context": "краткое описание поведения",
  "answer": "static int16_t ECOCALLMETHOD Foo(...) { ... }",
  "repo": "Lessons",
  "file": "Lesson02/Eco.CalculatorA/SourceFiles/CEcoCalculatorA.c",
  "question_type": "IMPLEMENTATION"
}
```

Имя файла датасета: `<исходный_файл>.jsonl` (например `CEcoCalculatorA.c.jsonl`), без суффикса `train`.

---

## Примеры команд

**C/C++, локальный репозиторий:**

```bash
eco-ai-data --strict-c-cpp-only --context analyze /path/to/repo
```

**GitHub, подпапка (Lessons):**

```bash
eco-ai-data --strict-c-cpp-only --context analyze \
  "https://github.com/peerf-eco/Eco.Education/tree/main/Eco.Pro.Training/001.InsideACOM/Lessons"
```

**Smoke-тест (2 функции на файл):**

```bash
eco-ai-data --strict-c-cpp-only --context --max-qa-pairs 2 analyze /path/to/repo
```

**Documentation QA:**

```bash
eco-ai-data-doc --strict-python-only analyze /path/to/repo
```

**Пересчёт quality-отчёта:**

```bash
eco-ai-data-quality outputs/Lessons
```

---

## Опции CLI

Указывать **до** подкоманды `analyze`:

| Опция | Описание |
|-------|----------|
| `--output-dir DIR` | Базовый каталог (по умолчанию `outputs`) |
| `--strict-python-only` | Только `.py` |
| `--strict-c-cpp-only` | Только C/C++ (`.c`, `.h`, `.cpp`, …) |
| `--tool ast\|c_ast\|regex\|openai` | Инструмент извлечения сущностей (по умолчанию `ast`) |
| `--processes N` | Параллелизм (`0` = авто) |
| `--context` | Заполнять `context` через OpenAI (`eco-ai-data`) |
| `--no-qa-openai` | Без OpenAI (шаблоны / fallback) |
| `--max-qa-pairs N` | Лимит записей на исходный файл |
| `--openai-model`, `--openai-api-key` | Модель и ключ |

---

## OpenAI

Ключ в `.env` в корне проекта или родительских каталогах:

```env
OPENAI_API_KEY=sk-...
```

Или флаг `--openai-api-key`. Файл `.env` не коммитить.

---

## Конфигурация (`PipelineConfig`)

- `output_dir` — база для вывода (`outputs`)
- `max_file_bytes`, `include_extensions`, `exclude_dirs`
- `dataset_mode` — `generation` / `documentation` (задаётся CLI)
- `include_context`, `qa_answers_via_openai`, `max_qa_pairs_per_file`

Каталоги создаются автоматически: `config.output_path()`, затем `outputs/<repo_id>/` и вложенные пути при экспорте.

---

## Инструменты `--tool`

| Инструмент | Описание |
|------------|----------|
| `ast` | Python AST (по умолчанию) |
| `c_ast` | C/C++ через clang / tree-sitter |
| `regex` | Regex-эвристики |
| `openai` | Regex + OpenAI для сущностей |

Для generation C/C++ достаточно `--strict-c-cpp-only`; тела функций извлекаются отдельным парсером в `label_engine`.

---

## Зависимости

`setup.py`: `datasets`, `openai`, `python-dotenv`.
