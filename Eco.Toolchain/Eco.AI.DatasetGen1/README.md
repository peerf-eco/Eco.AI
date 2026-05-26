# Eco.AI.DatasetGen1

Конвейер для подготовки обучающих датасетов из репозиториев исходного кода.

На вход — локальная папка или URL GitHub. На выход — JSONL с парами для ML: **instruction-to-code (ACOM)** или **documentation QA**.

---

## Содержание

- [Требования](#требования)
- [Установка и настройка](#установка-и-настройка)
- [Структура проекта](#структура-проекта)
- [Запуск](#запуск)
- [Результат работы](#результат-работы)
- [Формат JSONL](#формат-jsonl)
- [Справочник CLI](#справочник-cli)
- [Документация модулей](#документация-модулей)

---

## Требования

| Компонент | Обязательность | Назначение |
|-----------|----------------|------------|
| Python 3.10+ | да | runtime |
| `pip install -e .` | да | пакет `eco-ai-data` |
| `git` | для URL | shallow clone репозиториев |
| `clang` | опционально | лучшее извлечение C/C++ сущностей (`--tool c_ast`) |
| OpenAI API key | опционально | `--context`, documentation QA, ответы через API |

Python-зависимости (`setup.py`): `datasets`, `openai`, `python-dotenv`.

---

## Установка и настройка

### 1. Клонирование и установка пакета

```bash
cd Eco.AI.DatasetGen1
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

После установки доступны команды:

- `eco-ai-data` — generation (instruction-to-code)
- `eco-ai-data-doc` — documentation QA
- `eco-ai-data-quality` — оценка качества готового датасета

Альтернатива без entry points:

```bash
python3 -m eco_ai_data.cli.main_cli --help
./eco-ai-data --help
```

### 2. Переменные окружения (OpenAI)

Создайте `.env` в корне проекта (файл в `.gitignore`, не коммитить):

```env
OPENAI_API_KEY=sk-...
```

Ключ также ищется в родительских каталогах (до 10 уровней вверх) или передаётся флагом `--openai-api-key`.

**Когда нужен OpenAI:**

| Сценарий | Без ключа |
|----------|-----------|
| `eco-ai-data` без `--context` | работает |
| `eco-ai-data --context` | шаблонный `context` при `--no-qa-openai` |
| `eco-ai-data-doc` | fallback-ответы при `--no-qa-openai` |

### 3. Опционально: clang для C/C++

```bash
# macOS
brew install llvm

# Debian/Ubuntu
sudo apt install clang
```

Для generation по C/C++ достаточно `--strict-c-cpp-only`: тела функций извлекаются парсером в `label_engine`, независимо от `--tool`.

### 4. Каталог вывода

Папку `outputs/` создавать вручную не нужно — она появится при первом `analyze`. Путь задаётся `--output-dir` (по умолчанию `outputs`).

---

## Структура проекта

```
Eco.AI.DatasetGen1/
│
├── README.md                      # этот файл
├── setup.py, pyproject.toml       # сборка пакета eco-ai-data
├── eco-ai-data                      # bash-обёртка → main_cli
│
├── outputs/                         # артефакты прогона (не в git)
│   └── <repo_id>/
│       ├── <зеркало исходников>/*.jsonl
│       ├── <repo_id>.jsonl          # combined датасет
│       └── reports/
│
└── eco_ai_data/                     # Python-пакет
    ├── config.py                    # PipelineConfig
    ├── master_pipeline.py           # EcoAIDataPipeline
    │
    ├── cli/                         # eco-ai-data, eco-ai-data-doc, eco-ai-data-quality
    ├── preprocessing/             # загрузка репо, фильтр файлов, очистка кода
    ├── tools/                     # AST (Python), C AST (clang)
    ├── labeling/                  # сущности + генерация QA-пар
    ├── postprocessing/              # validate / dedup / normalize entities
    ├── export/                    # запись JSONL на диск
    ├── reporting/                 # pipeline_report.md
    ├── quality/                   # quality_report.json / .md
    └── archive_algorithms/        # legacy: --tool regex|openai
```

### Поток данных

```
репозиторий → preprocessing → labeling → postprocessing → export → outputs/
                                    ↓
                              reporting + quality
```

---

## Запуск

Общий синтаксис для `eco-ai-data` и `eco-ai-data-doc`:

```bash
<команда> [глобальные флаги] analyze <путь_или_url>
```

Глобальные флаги указываются **до** слова `analyze`.

---

### Generation (instruction-to-code, ACOM)

Основной сценарий для Eco C/C++:

```bash
eco-ai-data --strict-c-cpp-only --context analyze /path/to/repo
```

GitHub, только подпапка (например Lessons):

```bash
eco-ai-data --strict-c-cpp-only --context analyze \
  "https://github.com/peerf-eco/Eco.Education/tree/main/Eco.Pro.Training/001.InsideACOM/Lessons"
```

Python-репозиторий:

```bash
eco-ai-data --strict-python-only analyze /path/to/python/project
```

Быстрая проверка (не более 2 функций на файл):

```bash
eco-ai-data --strict-c-cpp-only --context --max-qa-pairs 2 analyze /path/to/repo
```

Без OpenAI (пустой или шаблонный `context`):

```bash
eco-ai-data --strict-c-cpp-only --no-qa-openai analyze /path/to/repo
```

Свой каталог вывода и параллельное чтение файлов:

```bash
eco-ai-data --output-dir ./datasets --processes 4 --strict-c-cpp-only analyze /path/to/repo
```

Через модуль Python:

```bash
python3 -m eco_ai_data.cli.main_cli --strict-c-cpp-only --context analyze /path/to/repo
```

---

### Documentation QA

Вопросы о поведении кода; `context` = листинг функции:

```bash
eco-ai-data-doc --strict-python-only analyze /path/to/repo
```

```bash
eco-ai-data-doc --strict-c-cpp-only --no-qa-openai analyze /path/to/repo
```

```bash
python3 -m eco_ai_data.cli.doc_main_cli analyze /path/to/repo
```

---

### Оценка качества датасета

После `analyze` отчёты уже лежат в `outputs/<repo>/reports/`. Пересчитать вручную:

```bash
eco-ai-data-quality outputs/Lessons
```

По одному файлу JSONL:

```bash
eco-ai-data-quality outputs/Lessons/Lessons.jsonl
```

С явными путями отчёта:

```bash
eco-ai-data-quality outputs/Lessons \
  --output-json outputs/Lessons/reports/quality_report.json \
  --output-md outputs/Lessons/reports/quality_report.md \
  --print-json
```

---

### Программный запуск (без CLI)

```python
from eco_ai_data import EcoAIDataPipeline
from eco_ai_data.config import PipelineConfig

config = PipelineConfig(
    strict_c_cpp_only=True,
    include_context=True,
    dataset_mode="generation",
)
paths = EcoAIDataPipeline(config).analyze_and_export("/path/to/repo")
print(paths["combined_dataset"])
```

---

## Результат работы

После `analyze` в консоль печатаются пути (`key=value`), например:

```
repo_dir=outputs/Lessons
combined_dataset=outputs/Lessons/Lessons.jsonl
combined_rows=159
pipeline_report=outputs/Lessons/reports/pipeline_report.md
quality_report_json=outputs/Lessons/reports/quality_report.json
...
```

Структура на диске:

```
outputs/<repo_id>/
├── Lesson02/.../CEcoCalculatorA.c.jsonl    # зеркало: один исходник → один JSONL
├── Lesson03/...
├── <repo_id>.jsonl                           # весь датасет, дедуп по question+answer
└── reports/
    ├── pipeline_report.md                    # статистика entities / qa_pairs
    ├── quality_report.json
    └── quality_report.md
```

Подробнее: [outputs/README.md](outputs/README.md).

---

## Формат JSONL

Одна строка файла = одна обучающая запись:

```json
{
  "question": "Implement function with below signature using ACOM component-based architecture.\nThe signature is:\n\nstatic int16_t ECOCALLMETHOD CEcoCalculatorA_Add(...)",
  "context": "краткое описание поведения или пустая строка",
  "answer": "полный исходный код функции из репозитория",
  "repo": "Lessons",
  "file": "Lesson02/Eco.CalculatorA/SourceFiles/CEcoCalculatorA.c",
  "question_type": "IMPLEMENTATION"
}
```

| Поле | Generation | Documentation |
|------|------------|---------------|
| `question` | ACOM + сигнатура | вопрос о коде |
| `answer` | листинг функции | объяснение |
| `context` | опционально (`--context`) | листинг функции |
| `question_type` | `IMPLEMENTATION` | `FUNCTIONALITY`, `WHY_*`, … |

Имя per-file датасета: `<исходный_файл>.jsonl` (без суффикса `train`).

---

## Справочник CLI

### Команды

| Команда | Режим | Описание |
|---------|-------|----------|
| `eco-ai-data analyze <path\|url>` | generation | Датасет instruction-to-code |
| `eco-ai-data-doc analyze <path\|url>` | documentation | QA о поведении кода |
| `eco-ai-data-quality <path>` | — | Метрики качества JSONL или каталога `outputs/<repo>` |

### Флаги (`eco-ai-data`, `eco-ai-data-doc`)

| Флаг | По умолчанию | Описание |
|------|--------------|----------|
| `--output-dir DIR` | `outputs` | Базовый каталог результатов |
| `--strict-python-only` | — | Обрабатывать только `.py` |
| `--strict-c-cpp-only` | — | Только C/C++ (`.c`, `.h`, `.cpp`, …) |
| `--tool ast\|c_ast\|regex\|openai` | `ast` | Извлечение **сущностей** (не тел функций для C) |
| `--processes N` | `0` (авто, до 8) | Параллельное чтение файлов |
| `--openai-model MODEL` | `gpt-4o-mini` | Модель OpenAI |
| `--openai-api-key KEY` | из env / `.env` | API-ключ |
| `--no-qa-openai` | — | Без вызовов OpenAI для ответов и context |
| `--max-qa-pairs N` | без лимита | Максимум записей на исходный файл |
| `--context` | — | Только `eco-ai-data`: заполнять поле `context` |

`--strict-python-only` и `--strict-c-cpp-only` нельзя включать одновременно.

### Инструменты `--tool`

| Значение | Когда использовать |
|----------|-------------------|
| `ast` | Python (по умолчанию) |
| `c_ast` | C/C++: clang / tree-sitter для entities |
| `regex` | Legacy, эвристики |
| `openai` | Legacy, regex + OpenAI для entities |

---

## Документация модулей

Подробная техническая документация для разработчиков — в `README.md` каждого пакета:

| Модуль | Документ |
|--------|----------|
| CLI | [eco_ai_data/cli/README.md](eco_ai_data/cli/README.md) |
| Preprocessing | [eco_ai_data/preprocessing/README.md](eco_ai_data/preprocessing/README.md) |
| Tools (AST / C AST) | [eco_ai_data/tools/README.md](eco_ai_data/tools/README.md) |
| Labeling | [eco_ai_data/labeling/README.md](eco_ai_data/labeling/README.md) |
| Postprocessing | [eco_ai_data/postprocessing/README.md](eco_ai_data/postprocessing/README.md) |
| Export | [eco_ai_data/export/README.md](eco_ai_data/export/README.md) |
| Reporting | [eco_ai_data/reporting/README.md](eco_ai_data/reporting/README.md) |
| Quality | [eco_ai_data/quality/README.md](eco_ai_data/quality/README.md) |
| Каталог `outputs/` | [outputs/README.md](outputs/README.md) |

Ядро пайплайна: `eco_ai_data/config.py` (`PipelineConfig`), `eco_ai_data/master_pipeline.py` (`EcoAIDataPipeline`).
