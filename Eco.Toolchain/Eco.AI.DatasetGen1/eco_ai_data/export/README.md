# export — сбор записей и запись JSONL

Преобразует внутренние записи пайплайна в файлы обучения на диске.

## Файлы

| Модуль | Назначение |
|--------|------------|
| `dataset_builder.py` | Внутренний формат entry; опционально HuggingFace |
| `repo_exporter.py` | Зеркальная структура JSONL + combined файл |

Вызывается из `EcoAIDataPipeline.analyze_and_export` → `export_repo_datasets`.

---

## dataset_builder.py

### DatasetBuilder.build_entry(...)

```python
build_entry(
    repo: str,
    file_path: str,      # относительный путь от root репо
    entities: list[dict],
    qa_pairs: list[dict],
    raw_code: str,
) -> dict
```

Возвращает единую in-memory запись: поля `repo`, `file`, `entities`, `qa_pairs`, `raw_code`.

### DatasetBuilder.to_hf_dataset(entries)

```python
to_hf_dataset(entries) -> datasets.Dataset | None
```

Требует пакет `datasets`. При ошибке импорта — `None`.  
Экспортирует **полные** entries (с `entities`, `raw_code`), не плоский train-формат.

---

## repo_exporter.py

### Структура на диске

```
outputs/<sanitized_repo_id>/
├── Lesson02/.../CEcoCalculatorA.c.jsonl   # зеркало: <rel_path>.jsonl
├── Lesson03/...
├── <repo_id>.jsonl                        # все строки, с дедупом
└── reports/                               # не создаётся здесь
```

`sanitize_repo_id(name)` — небуквенные символы → `_`.

### flatten_entry_rows(entry)

Разворачивает `qa_pairs` в плоские строки для JSONL:

```json
{
  "question": "...",
  "context": "",
  "answer": "...",
  "repo": "Lessons",
  "file": "Lesson02/.../file.c",
  "question_type": "IMPLEMENTATION"
}
```

**Пропуск строк** без непустых `question` и `answer`.  
`context` всегда строка (`""` если отсутствует).  
`question_type` добавляется, если задан в QA-паре.

### dedupe_rows(rows)

Ключ: `SHA256(question + "\n" + answer)`.  
Применяется **только** к combined-файлу при `dedupe_combined=True`.

Per-file JSONL **не** дедуплицируются — дубликаты могут остаться в зеркальных файлах.

### export_repo_datasets

```python
export_repo_datasets(
    entries: list[dict],
    *,
    repo_id: str,
    output_base: Path,
    dedupe_combined: bool = True,
) -> dict
```

**Возврат:**

| Ключ | Значение |
|------|----------|
| `repo_id` | Санитизированное имя |
| `repo_dir` | Путь к каталогу репо |
| `combined_dataset` | Путь к `<repo_id>.jsonl` |
| `combined_rows` | Число строк после дедупа |
| `per_file_count` | Число записанных per-file файлов |
| `per_file_paths` | Список путей |

**Поведение:** если после `flatten_entry_rows` нет строк — файл для этого исходника **не создаётся**.

### Вспомогательные функции

```python
per_file_dataset_path(repo_dir, file_rel)   # repo_dir / f"{rel}.jsonl"
combined_dataset_path(repo_dir, repo_id)    # repo_dir / f"{repo_id}.jsonl"
write_jsonl(path, rows)                     # UTF-8, одна JSON-строка на строку
```

---

## Связь с quality и reporting

| Этап | Источник данных |
|------|-----------------|
| `pipeline_report.md` | In-memory `entries` (есть `entities`) |
| `quality_report.*` | Перечитанный **combined** JSONL с диска |

Quality оценивает то, что реально попадёт в обучение (плоский формат).

---

## Пример программного экспорта

```python
from pathlib import Path
from eco_ai_data.export.repo_exporter import export_repo_datasets

export_repo_datasets(
    entries,
    repo_id="Lessons",
    output_base=Path("outputs"),
    dedupe_combined=True,
)
```

---

## Контракт для downstream ML

Одна строка JSONL = один обучающий пример.  
Обязательные поля для generation: `question`, `answer`.  
Рекомендуемые: `repo`, `file`, `question_type`, `context` (может быть пустым).

Имя файла: `<исходный_файл>.jsonl`, без суффикса `train`.
