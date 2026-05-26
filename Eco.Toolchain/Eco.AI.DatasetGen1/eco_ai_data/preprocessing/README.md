# preprocessing — подготовка исходников

Первый этап пайплайна: получить корень репозитория, отобрать файлы, нормализовать текст перед разметкой.

## Файлы

| Модуль | Класс | Ответственность |
|--------|-------|-----------------|
| `repo_loader.py` | `RepoLoader`, `RepoSource` | Локальный путь или git clone |
| `file_filter.py` | `FileFilter` | Обход дерева, фильтры |
| `code_cleaner.py` | `CodeCleaner` | Нормализация текста |

Вызываются из `EcoAIDataPipeline._iter_entries` и `_process_file`.

---

## repo_loader.py

### RepoSource

```python
@dataclass
class RepoSource:
    repo_id: str          # имя конечной папки (например Lessons)
    root_path: Path       # корень для FileFilter
    temp_dir: Path | None # каталог временного clone

    def cleanup(self) -> None  # shutil.rmtree(temp_dir)
```

### RepoLoader.load(repo_path_or_url: str) -> RepoSource

**Локальный путь**

- `Path.expanduser().resolve()`
- `repo_id = root.name`
- `temp_dir = None`

**URL (http/https/git/ssh)**

- Shallow clone: `git clone --depth 1 [--branch BRANCH] URL target`
- Временная директория: `eco_ai_data_*` в системном temp
- `cleanup()` удаляет её после `analyze_and_export`

### GitHub tree URL

Поддерживается формат:

```
https://github.com/<org>/<repo>/tree/<branch>/<subpath>
```

Парсер `_GITHUB_TREE_RE`:

1. Клонирует `https://github.com/<org>/<repo>.git` с веткой `branch`
2. `root_path = clone_dir / subpath`
3. `repo_id` = имя конечной папки subpath (например `Lessons`)

**Ошибки:** `FileNotFoundError` (путь / subpath), `RuntimeError` (clone failed).

### Пример

```python
source = RepoLoader().load(
    "https://github.com/peerf-eco/Eco.Education/tree/main/.../Lessons"
)
# source.root_path — только Lessons, не весь репозиторий
```

---

## file_filter.py

### FileFilter

```python
FileFilter(
    include_extensions: list[str],  # из PipelineConfig
    exclude_dirs: list[str],
    max_file_bytes: int,
)
```

### Методы

| Метод | Поведение |
|-------|-----------|
| `iter_python_files(root)` | `rglob` по `root`; имя историческое — фильтр по **всем** `include_extensions` |
| `filter_paths(paths, root)` | Тот же фильтр для готового списка путей |

### Правила отбора

1. Расширение файла ∈ `include_extensions` (регистронезависимо).
2. Размер файла ≤ `max_file_bytes`.
3. Ни один компонент **относительного** пути не совпадает с элементом `exclude_dirs` (точное совпадение имени каталога).

Исключаются, например: `.git`, `node_modules`, `venv`, `__pycache__`, `build`, `dist`.

---

## code_cleaner.py

### CodeCleaner.clean(code: str) -> str

Детерминированная нормализация **без** изменения семантики кода:

| Шаг | Действие |
|-----|----------|
| Переносы | `\r\n`, `\r` → `\n` |
| Табы | → 4 пробела |
| NUL | удаление `\x00` |
| Пустые строки | 4+ подряд → максимум 3 |

Применяется один раз на файл перед `LabelEngine.label` и `generate_qa_pairs`.

---

## Порядок в пайплайне

```
RepoLoader.load(url|path)
    → FileFilter.iter_python_files(source.root_path)
    → [Pool] read_text UTF-8 / Latin-1
    → CodeCleaner.clean(raw)
    → LabelEngine ...
```

## Зависимости

- **Внешние:** `git` (для remote), стандартная библиотека.
- **Внутренние:** нет зависимостей от других подпакетов `eco_ai_data`.

## Расширение

- Новый тип входа (GitLab, SSH alias): расширить `RepoLoader._clone_remote`.
- Исключение файлов по маске: добавить логику в `FileFilter` или поля в `PipelineConfig`.
