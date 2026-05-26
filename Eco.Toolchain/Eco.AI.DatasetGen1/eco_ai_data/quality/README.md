# quality — оценка качества датасета

Эвристический аудит **готового** instruction-to-code JSONL (ориентир: generation, `IMPLEMENTATION`, ACOM). Запускается после экспорта и отдельно через CLI.

## Файлы

| Файл | API |
|------|-----|
| `dataset_quality.py` | `DatasetQualityAnalyzer`, `load_dataset_rows`, `analyze_dataset_paths`, `render_markdown_report` |
| `__init__.py` | Реэкспорт публичных символов |

## Точки входа

1. Автоматически: `EcoAIDataPipeline.analyze_and_export` читает combined JSONL и пишет `reports/quality_report.{json,md}`.
2. CLI: `eco-ai-data-quality` — см. [cli/README.md](../cli/README.md).

---

## Загрузка данных

### load_dataset_rows(path: Path) -> list[dict]

| path | Поведение |
|------|-----------|
| Каталог | Сначала `<dir>/<dir.name>.jsonl`; иначе все `*.jsonl` рекурсивно, кроме `reports/` |
| Файл с `qa_pairs` в начале | Legacy pipeline format → разворот пар |
| Обычный `.jsonl` | Одна dict на строку |

### analyze_dataset_paths(paths, *, output_json=None, output_md=None) -> dict

Анализирует один или несколько путей, опционально сохраняет отчёты, возвращает объединённый report.

---

## DatasetQualityAnalyzer

```python
DatasetQualityAnalyzer(rows: list[dict]).analyze() -> dict
```

### Subscores (веса → overall_score)

| Subscore | Вес | Что проверяет |
|----------|-----|----------------|
| `structural_validity` | 0.20 | Обязательные поля `question`, `answer` |
| `instruction_format` | 0.15 | Маркер ACOM, блок `The signature is:` |
| `answer_alignment` | 0.20 | Имя функции из сигнатуры встречается в answer |
| `code_heuristics` | 0.15 | Баланс `{}`, признаки C-кода |
| `context_quality` | 0.10 | Не пустой / не только fallback-шаблон |
| `deduplication` | 0.10 | Доля дубликатов question+answer |
| `diversity` | 0.10 | Энтропия по file / lesson / function |

### Grades

| Оценка | overall_score |
|--------|---------------|
| A | ≥ 90 |
| B | ≥ 80 |
| C | ≥ 70 |
| D | ≥ 60 |
| F | иначе |

### Маркеры generation

```python
_ACOM_MARKER = "ACOM component-based architecture"
_SIGNATURE_MARKER = "The signature is:"
_IMPLEMENTATION = "IMPLEMENTATION"
```

`non_implementation_type_count` штрафует doc-типы — для generation-датасета ожидается 0.

### Fallback context

Строки вида «Function receives parameters declared in the signature» считаются шаблоном, не полноценным context.

---

## Формат отчёта (JSON)

Типичные поля (имена могут дополняться в `analyze()`):

- `samples` — число строк
- `overall_score`, `grade`
- `subscores` — dict взвешенных компонент
- `issues` / counters — нарушения по категориям
- метрики дублирования и разнообразия

`render_markdown_report(report)` — краткая сводка для `quality_report.md`.

---

## Пример

```bash
eco-ai-data-quality outputs/Lessons
# → outputs/Lessons/reports/quality_report.json
```

```python
from pathlib import Path
from eco_ai_data.quality import analyze_dataset_paths

report = analyze_dataset_paths(
    [Path("outputs/Lessons")],
    output_json=Path("outputs/Lessons/reports/quality_report.json"),
)
print(report["overall_score"], report["grade"])
```

---

## Ограничения

- Метрики **не** заменяют ручную выборочную проверку кода.
- Настроены под ACOM generation; documentation QA даст другие паттерны в `question_type`.
- Читает файл с диска — изменения in-memory до `write_jsonl` не видны.

---

## Связь с литературой

В docstring модуля указаны ориентиры: instruction tuning, code LLM datasets, diversity/redundancy (EMNLP 2024, NovelSum 2025). Используются как обоснование набора эвристик, не как строгие SOTA-метрики.
