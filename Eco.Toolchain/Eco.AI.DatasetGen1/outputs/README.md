# outputs — артефакты запуска пайплайна

Runtime-каталог результатов `eco-ai-data analyze`. **Не коммитится** в git (см. `.gitignore`: `outputs/`, `*.jsonl`).

Создаётся автоматически: `PipelineConfig.output_path()` → `outputs/`, затем `outputs/<repo_id>/` при экспорте.

---

## Назначение

Хранить воспроизводимый результат прогона:

1. **Per-file JSONL** — зеркало структуры исходного репозитория.
2. **Combined JSONL** — весь датасет одним файлом с дедупом.
3. **reports/** — отчёты пайплайна и качества.

Папка не содержит исполняемого кода; это контракт данных между DatasetGen1 и обучением моделей.

---

## Структура каталога

```
outputs/
└── <repo_id>/                          # sanitize_repo_id (например Lessons)
    ├── <mirror>/<source_file>.jsonl    # один исходный файл → один JSONL
    ├── <repo_id>.jsonl                 # combined, дедуп по question+answer
    └── reports/
        ├── pipeline_report.md          # метрики entities/qa из прогона
        ├── quality_report.json         # оценка combined датасета
        └── quality_report.md
```

### Именование

| Элемент | Правило |
|---------|---------|
| `<repo_id>` | Имя корня анализируемого репо (`RepoSource.repo_id`) |
| Зеркало | Относительный путь исходника + суффикс `.jsonl` |
| Combined | `<repo_id>.jsonl` в корне каталога репо |

Пример:

```
outputs/Lessons/
  Lessons.jsonl
  Lesson02/Eco.CalculatorA/SourceFiles/CEcoCalculatorA.c.jsonl
  reports/quality_report.json
```

---

## Формат строки JSONL (train)

Одна строка = один обучающий пример:

```json
{
  "question": "Implement function with below signature using ACOM component-based architecture.\nThe signature is:\n\nstatic int16_t ECOCALLMETHOD CEcoCalculatorA_Add(...)",
  "context": "краткое описание или пустая строка",
  "answer": "полный исходный код функции",
  "repo": "Lessons",
  "file": "Lesson02/Eco.CalculatorA/SourceFiles/CEcoCalculatorA.c",
  "question_type": "IMPLEMENTATION"
}
```

| Поле | Обязательность | Примечание |
|------|----------------|------------|
| `question` | да | ACOM + сигнатура (generation) |
| `answer` | да | Листинг из исходника |
| `context` | нет | Часто `""` без `--context` |
| `repo`, `file` | рекомендуется | Трассировка происхождения |
| `question_type` | рекомендуется | `IMPLEMENTATION` для generation |

В JSONL **нет** `entities` и `raw_code` — они только во внутренних entries пайплайна.

---

## Per-file vs combined

| Файл | Дедуп | Назначение |
|------|-------|------------|
| `.../file.c.jsonl` | нет | Локальная выборка по одному исходнику |
| `<repo_id>.jsonl` | SHA256(question\nanswer) | Обучение, quality-отчёт |

Если для файла нет подходящих функций — per-file JSONL **не создаётся**.

---

## reports/

| Файл | Генератор | Содержание |
|------|-----------|------------|
| `pipeline_report.md` | [reporting/](../eco_ai_data/reporting/README.md) | Файлы, entities, qa_pairs, типы |
| `quality_report.json` | [quality/](../eco_ai_data/quality/README.md) | Числовые subscores, grade |
| `quality_report.md` | `render_markdown_report` | Краткая сводка для человека |

Пересчёт quality без полного analyze:

```bash
eco-ai-data-quality outputs/Lessons
```

---

## Пример в репозитории

В workspace может присутствовать демо `outputs/Lessons/` (Eco Education, C/C++ generation):

- ~160 строк в `Lessons.jsonl`;
- зеркала по урокам `Lesson02` … `Lesson09`;
- quality grade A при типичном ACOM-прогоне.

Это **снимок** прогона, не часть исходного кода пакета.

---

## Использование в ML-пайплайне

```python
import json
from pathlib import Path

path = Path("outputs/Lessons/Lessons.jsonl")
for line in path.read_text(encoding="utf-8").splitlines():
    row = json.loads(line)
    # row["question"], row["answer"], ...
```

HuggingFace (полные entries с entities):

```python
pipeline.analyze("/path/to/repo")
ds = pipeline.to_hf_dataset()
```

---

## Очистка и CI

- Удаление: `rm -rf outputs/<repo_id>` перед повторным прогоном.
- В CI обычно генерируют заново или кэшируют как artifact, не хранят в git.
