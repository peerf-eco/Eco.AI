# reporting — отчёты по прогону пайплайна

Статистика **внутренних** записей (`entries`) после `analyze`, до или параллельно с экспортом. Не заменяет [quality/](../quality/README.md) (оценка готового JSONL).

## Файлы

| Модуль | Класс / функция |
|--------|-----------------|
| `metrics_report.py` | `MetricsReport.build` |
| `markdown_report.py` | `MarkdownReport.generate` |

## Когда вызывается

```python
# master_pipeline.analyze_and_export
metrics = metrics_report.build(entries)
markdown_report.generate(repo_id, metrics, tool_name, repo_dir / "reports/pipeline_report.md")
```

Только при полном `analyze_and_export`, не при `analyze()` без экспорта.

---

## MetricsReport

### build(entries: Iterable[dict]) -> dict

Агрегирует по всем файлам репозитория.

**Верхний уровень:**

| Поле | Смысл |
|------|-------|
| `files` | Число обработанных исходных файлов |
| `entities` | Сумма сущностей |
| `qa_pairs` | Сумма QA-пар |
| `entity_types` | `{TYPE: count}` |

**data_quality:**

| Поле | Смысл |
|------|-------|
| `files_with_empty_entities` | Файлы без entities |
| `files_with_empty_qa_pairs` | Файлы без QA (не попадут в JSONL) |
| `entities_missing_line` | Сущности без `line` |
| `entities_without_class_or_function` | Нет ни `class`, ни `function` |
| `duplicate_entities` | Повторы по ключу (file, type, name, class, function, line) |
| `qa_question_types` | Распределение `question_type` |

**Использование:** вход для Markdown; отладка покрытия репозитория; сравнение прогонов с разными `--tool`.

---

## MarkdownReport

### generate(repo, metrics, tool_name, output_path)

Пишет `pipeline_report.md` в `outputs/<repo>/reports/`.

**Типичные секции:**

- идентификатор репозитория и инструмент (`tool_name`);
- сводные числа (файлы, entities, qa_pairs);
- таблица типов сущностей;
- блок data quality;
- breakdown `qa_question_types`.

Формат человекочитаемый; для машинной обработки используйте агрегаты из `MetricsReport.build` напрямую.

---

## Отличие от quality_report

| | pipeline_report | quality_report |
|--|-----------------|----------------|
| Источник | In-memory entries | Combined JSONL |
| Фокус | Покрытие кода, entities | Качество train-строк |
| Поля | entities, raw_code | question, answer, context |
| CLI | Автоматически после analyze | `eco-ai-data-quality` |

Пустой `qa_pairs` в файле виден в pipeline_report, но не создаёт per-file JSONL.

---

## Пример

```python
from eco_ai_data.reporting.metrics_report import MetricsReport
from eco_ai_data.reporting.markdown_report import MarkdownReport

entries = pipeline.analyze("/path/to/repo")
metrics = MetricsReport().build(entries)
MarkdownReport().generate("Lessons", metrics, "c_ast", Path("outputs/Lessons/reports/pipeline_report.md"))
```
