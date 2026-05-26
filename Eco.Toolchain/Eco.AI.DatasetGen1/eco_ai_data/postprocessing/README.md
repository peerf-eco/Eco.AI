# postprocessing — очистка списка сущностей

Тонкий слой между `LabelEngine.label()` и `DatasetBuilder`. Обрабатывает только **`entities`**, не `qa_pairs`.

## Файлы

| Модуль | Класс |
|--------|-------|
| `validator.py` | `EntityValidator` |
| `deduplicator.py` | `EntityDeduplicator` |
| `normalizer.py` | `EntityNormalizer` |

## Порядок в пайплайне

```python
entities = label_engine.label(cleaned)
entities = validator.validate(entities)
entities = deduplicator.deduplicate(entities)
entities = normalizer.normalize(entities)
qa_pairs = label_engine.generate_qa_pairs(cleaned, ...)
```

Фиксированная последовательность в `EcoAIDataPipeline._process_file` — менять порядок без причины не следует.

---

## EntityValidator

```python
def validate(self, entities: Iterable[dict]) -> list[dict]
```

**Пропускает записи, где:**

- объект не `dict`;
- `type` не непустая строка;
- `name` не непустая строка.

Не проверяет enum `EntityType` — это делает `label_engine` через `is_valid_entity` до postprocessing; validator — дополнительная страховка.

---

## EntityDeduplicator

```python
def deduplicate(self, entities: Iterable[dict]) -> list[dict]
```

Ключ дубликата (порядок сохраняется, остаётся первое вхождение):

```
(type, name, class, function, line)
```

Поля `class` / `function` могут быть `None` — участвуют в ключе как есть.

**Назначение:** убрать повторы от overlapping extractors (clang + includes, несколько visitor-проходов).

---

## EntityNormalizer

```python
def normalize(self, entities: Iterable[dict]) -> list[dict]
```

| Поле | Преобразование |
|------|----------------|
| `type` | `strip().upper()` |
| `name` | `strip()` |
| `class` | `strip()` если строка |
| `function` | `strip()` если строка |

Остальные поля (`line`, …) не изменяются.

---

## Что postprocessing не делает

| Область | Где обрабатывается |
|---------|-------------------|
| Дедуп QA-пар | `export/repo_exporter.dedupe_rows` (только combined JSONL) |
| Валидация question/answer | `quality/dataset_quality.py` |
| Фильтр плохих doc-ответов | `label_engine.py` |

---

## Расширение

Добавление правил для entities (например, отбрасывать `VARIABLE` без `line`):

1. Расширить `EntityValidator` или добавить новый класс в этой папке.
2. Вызвать в `_process_file` после существующих шагов.
3. Обновить `MetricsReport` при появлении новых счётчиков качества.

Для постобработки **train-строк** JSONL используйте `quality/` или отдельный скрипт — не этот пакет.
