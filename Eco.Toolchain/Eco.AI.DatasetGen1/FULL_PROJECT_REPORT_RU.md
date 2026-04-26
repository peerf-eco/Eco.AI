# Eco.AI.Data — Полный отчёт по проекту

## 1. Введение и цель проекта

### 1.1 Исходная задача
Нужно было построить практический конвейер, который:

1. принимает на вход путь к локальному репозиторию или ссылку на GitHub;
2. рекурсивно проходит по файлам кода заданных языков;
3. извлекает функции/сущности;
4. формирует обучающие JSONL-датасеты для задач машинного обучения по коду.

### 1.2 Цель в терминах ML
Сформировать **качественные пары для обучения моделей**, в двух сценариях:

- **Generation (instruction-to-code)**  
  `question` + `context` (опционально) + `answer=реальный код функции`.
- **Documentation QA (code understanding)**  
  вопросы о поведении кода + контекст функции + ответ.

---

## 2. Этап 1 — первые эксперименты

Первые эксперименты выполнялись на отдельном экспериментальном контуре на датасете CodeSearchNet Python.

### 2.1 Использованный датасет
- Источник: `AISE-TUDelft/ML4SE23_G8_CodeSearchNet-Python` (HuggingFace).
- В эксперименте сравнивались подходы к извлечению и разметке функций.

### 2.2 Что сравнивали
Четыре подхода:

1. `Regex Only`
2. `Hybrid Regex + Heuristics`
3. `AST Parser`
4. `Hybrid Regex + OpenAI`

### 2.3 Итоговые метрики (из файла сравнения результатов)

- **Regex Only**  
  Precision: `0.9333`, Recall: `0.9928`, F1: `0.9622`, TP: `1386`, FP: `99`, FN: `10`
- **Hybrid Regex+Heuristics**  
  Precision: `0.9964`, Recall: `0.9979`, F1: `0.9971`, TP: `1393`, FP: `5`, FN: `3`
- **AST Parser**  
  Precision: `1.0000`, Recall: `0.9979`, F1: `0.9989`, TP: `1393`, FP: `0`, FN: `3`
- **Hybrid Regex+OpenAI**  
  Precision: `0.9964`, Recall: `0.9878`, F1: `0.9921`, TP: `1379`, FP: `5`, FN: `17`

### 2.4 Ключевой вывод первого этапа
**AST показал лучший итоговый баланс и наивысший F1 (`0.9989`) при нулевых FP**, поэтому был выбран как основной базовый путь для Python в дальнейшем пайплайне.

---

## 3. Переход к промышленному пайплайну: `Eco.AI.Data`

После экспериментов проект был переработан в полноценную систему `Eco.AI.Data`.

### 3.1 Основная идея
Сделать воспроизводимый CLI-пайплайн:

- от загрузки репозитория,
- до JSON/JSONL датасета,
- плюс отчёт с метриками.

### 3.2 Поддерживаемые сценарии входа
- локальная папка с кодом;
- ссылка на GitHub-репозиторий (через clone).

---

## 4. Архитектура проекта

Проект разбит на слои:

1. `preprocessing`  
   загрузка репо, фильтрация файлов, очистка кода;
2. `tools`  
   извлечение сущностей (`ast`, `c_ast`, `regex`, `openai`);
3. `labeling`  
   генерация датасет-пар из функций;
4. `postprocessing`  
   валидация, дедупликация, нормализация;
5. `export`  
   формирование итоговых записей и запись JSON/JSONL;
6. `reporting`  
   построение отчёта по метрикам;
7. `cli`  
   интерфейсы запуска.

---

## 5. Почему AST оставили как ядро

На основании `comparison_results.json`:

- AST дал лучший F1 и отсутствие ложных срабатываний;
- Regex-only оказался слишком шумным;
- Hybrid Regex+OpenAI не дал ожидаемого выигрыша для структурной разметки;
- Hybrid Regex+Heuristics близок к AST, но AST стабильнее как эталон для Python.

Именно поэтому AST — основной “reference-quality” путь для Python-файлов.

---

## 6. Развитие алгоритмов в проекте

### 6.1 Python
- Парсинг через `ast`.
- Выделение функций/классов/методов/параметров/возвратов/переменных.
- Для generation-режима:
  - сигнатура берётся из реального `def ...`;
  - `answer` = реальный листинг функции.
- Для documentation-режима:
  - генерируются вопросы по смыслу/поведению;
  - ответ строится через OpenAI или fallback.

### 6.2 C/C++
- Есть `c_ast_tool.py` (clang/tree-sitter/fallback) для извлечения сущностей.
- Для generation-режима реализован C-like extractor:
  - извлекает сигнатуры и тела функций;
  - поддерживает многострочные сигнатуры, `const`, scope (`ns::Class::method`), баланс `{}`.
- `answer` = исходный C/C++ листинг функции 1:1.

---

## 7. Два типа скриптов (как просили в ТЗ)

Реализованы два отдельных CLI:

## 7.1 Скрипт 1 — Generation
- Команда: `eco-ai-data` (или `python3 -m eco_ai_data.cli.main_cli`).
- Формат:
  - `question`: “Implement function with below signature...”
  - `context`: опционально (`--context`)
  - `answer`: реальная имплементация функции
  - `question_type`: `IMPLEMENTATION`

## 7.2 Скрипт 2 — Documentation QA
- Команда: `eco-ai-data-doc` (или `python3 -m eco_ai_data.cli.doc_main_cli`).
- Формат:
  - `question`: вопросы о том, что делает функция
  - `context`: код функции
  - `answer`: объяснение (OpenAI/fallback)
  - `question_type`: `FUNCTIONALITY`, `RETURN_VALUE`, `WHY_*`, `BUG_*`, ...

---

## 8. Как работает полный pipeline (пошагово)

1. **Load**: `repo_loader` принимает путь/URL.
2. **Filter**: выбираются файлы по расширениям; служебные каталоги исключаются.
3. **Clean**: нормализация переносов, табов, лишних пустых строк.
4. **Extract entities**: выбранным инструментом (`ast/c_ast/...`).
5. **Generate pairs**:
   - generation или documentation в зависимости от режима.
6. **Postprocess entities**:
   - validation,
   - deduplication,
   - normalization.
7. **Build entry**:
   - `repo`, `file`, `entities`, `qa_pairs`, `raw_code`.
8. **Export**:
   - `json` или `jsonl`.
9. **Flatten (опционально)**:
   - в train JSONL вида `question/context/answer`.
10. **Report**:
    - summary по файлам, сущностям и QA-парам.

---

## 9. Что уже получено на практике

Подготовлены демонстрационные generation-датасеты:

- `outputs/module_py5_train.jsonl` — 5 примеров по Python (`module.py`)
- `outputs/cjson_c5_train_v2.jsonl` — 5 примеров по C (`cJSON.c`)

Проверено:
- в каждом файле ровно 5 строк;
- `question_type=IMPLEMENTATION`;
- `answer` совпадает с реальными функциями из исходников;
- `context` заполнен (при запуске с `--context`).

---

## 10. Оценка результатов (сильные/слабые стороны)

### 10.1 Сильные стороны
- Чёткая модульная архитектура пайплайна.
- Воспроизводимые CLI-сценарии.
- Поддержка Python и C/C++.
- Два типа датасетов под разные ML-задачи.
- Генерация train JSONL для прямого обучения.

### 10.2 Ограничения
- `label_engine.py` стал крупным и требует дальнейшего рефакторинга.
- C/C++ extraction улучшен, но в сложных конструкциях может требовать донастройки.
- OpenAI-зависимые шаги чувствительны к сети/квоте.

### 10.3 Текущий статус качества
- Базовая логика стабильна.
- Демо-датасеты получаются корректно.
- Архитектура готова для дальнейшего масштабирования.

---

## 11. Что можно сказать на защите как «главный результат»

1. Мы экспериментально сравнили подходы и обоснованно выбрали AST как основу по качеству.
2. Мы превратили эксперимент в полноценный инженерный pipeline.
3. Мы реализовали два независимых режима датасетов:
   - generation для code synthesis,
   - documentation QA для code understanding.
4. Мы подтвердили работу на Python и C/C++ на реальных примерах.

---

## 12. Дорожная карта (дальнейшие шаги)

1. Рефакторинг `label_engine` на отдельные модули (generation/doc/c-family).
2. Автотесты (smoke + golden samples).
3. Уточнение C/C++ extractor для edge-cases (макросы, сложные шаблоны).
4. Метрики качества generation-датасета:
   - exact/source-match checks,
   - coverage по типам функций,
   - статистика длины/сложности.
5. Подготовка release-пакета с фиксированными версиями и reproducible runbook.

---

## 13. Команды для демонстрации завтра

### 13.1 Generation (Python)
```bash
cd "/Users/midasxlr/Desktop/diplom/Eco.AI.Data"
PYTHONPATH=. python3 -m eco_ai_data.cli.main_cli --strict-python-only --context --max-qa-pairs 5 analyze /path/to/repo --output-json outputs/module_py5_pipeline.jsonl --output-md outputs/module_py5_report.md
PYTHONPATH=. python3 -m eco_ai_data.cli.main_cli qa-flatten outputs/module_py5_pipeline.jsonl outputs/module_py5_train.jsonl
```

### 13.2 Generation (C/C++)
```bash
cd "/Users/midasxlr/Desktop/diplom/Eco.AI.Data"
PYTHONPATH=. python3 -m eco_ai_data.cli.main_cli --strict-c-cpp-only --context --max-qa-pairs 5 analyze /path/to/repo --output-json outputs/cjson_c5_pipeline_v2.jsonl --output-md outputs/cjson_c5_report_v2.md
PYTHONPATH=. python3 -m eco_ai_data.cli.main_cli qa-flatten outputs/cjson_c5_pipeline_v2.jsonl outputs/cjson_c5_train_v2.jsonl
```

### 13.3 Documentation QA
```bash
cd "/Users/midasxlr/Desktop/diplom/Eco.AI.Data"
PYTHONPATH=. python3 -m eco_ai_data.cli.doc_main_cli --strict-python-only --max-qa-pairs 5 analyze /path/to/repo --output-json outputs/doc_py5_pipeline.jsonl --output-md outputs/doc_py5_report.md
PYTHONPATH=. python3 -m eco_ai_data.cli.doc_main_cli qa-flatten outputs/doc_py5_pipeline.jsonl outputs/doc_py5_train.jsonl
```

---

## 14. Краткое резюме в 3 фразы

Проект прошёл путь от экспериментального сравнения алгоритмов до полноценной системы генерации датасетов по коду.  
Экспериментально подтверждено преимущество AST для Python, что стало методологической основой текущей архитектуры.  
Сейчас система поддерживает два типа датасетов и два семейства языков (Python, C/C++), с рабочими CLI и воспроизводимыми результатами.

---

## 15. Техническая спецификация модулей (детально)

Ниже — разбор того, **какой модуль что делает**, какие у него входы/выходы и какая логика внутри.

### 15.1 `preprocessing/repo_loader.py`

**Задача:** получить локальный `root_path` репозитория.

Алгоритм:
1. Если вход выглядит как URL (`http/https/git/ssh`), вызывается `_clone_remote`.
2. `_clone_remote`:
   - создаёт временный каталог,
   - делает `git clone --depth 1 <url> <tmp/repo>`,
   - возвращает `RepoSource(repo_id, root_path, temp_dir)`.
3. Если вход — локальный путь:
   - проверяется существование каталога,
   - возвращается `RepoSource(repo_id=<имя каталога>, root_path=<path>)`.

Свойство `RepoSource.cleanup()` удаляет временный каталог после обработки.

### 15.2 `preprocessing/file_filter.py`

**Задача:** отфильтровать только релевантные файлы.

Проверки для каждого файла:
- расширение в `include_extensions`;
- путь не содержит сегменты из `exclude_dirs`;
- размер файла не больше `max_file_bytes`.

Сложность: `O(N)` по количеству файлов в дереве.

### 15.3 `preprocessing/code_cleaner.py`

Минимальная нормализация:
- `\r\n`/`\r` -> `\n`,
- `\t` -> 4 пробела,
- удаление `\x00`,
- схлопывание >3 пустых строк.

Это снижает шум и делает извлечение более стабильным.

### 15.4 `tools/ast_tool.py` (Python сущности)

**Базовый структурный извлекатель для Python.**
Использует `ast.parse` и visitor-подход:
- `FUNCTION`, `CLASS`, `METHOD`,
- `IMPORT`,
- `PARAMETER`,
- `RETURN`,
- `VARIABLE` (с контекстом).

Плюс извлечение тела функции (с ограничением длины), что используется в downstream-логике.

### 15.5 `tools/c_ast_tool.py` (C/C++ сущности)

Трёхступенчатая стратегия:

1. **Clang AST JSON** (предпочтительно):
   - `clang -Xclang -ast-dump=json -fsyntax-only`.
2. **Tree-sitter fallback**:
   - если clang недоступен/пустой результат.
3. **Regex fallback**:
   - для минимальной работоспособности.

Извлекаются сущности:
`FUNCTION`, `METHOD`, `PARAMETER`, `RETURN`, `STRUCT`, `UNION`, `ENUM`, `TYPEDEF`, `IMPORT`, `NAMESPACE`, `TEMPLATE`, `VARIABLE`.

---

## 16. Оркестрация pipeline (`master_pipeline.py`)

`EcoAIDataPipeline` — главный контроллер процесса.

### 16.1 Жизненный цикл `analyze_export_report`

1. `analyze(repo_path_or_url)`:
   - загружает `RepoSource`,
   - итерирует файлы (`_iter_entries`),
   - для каждого файла вызывает `_process_file`.
2. `_process_file`:
   - cleaning,
   - `label()` (сущности),
   - `generate_qa_pairs()` (датасет-пары),
   - build entry.
3. export (`json`/`jsonl`) через `JsonExporter`.
4. report через `MetricsReport` + `MarkdownReport`.

### 16.2 Параллелизм

- Если `processes <= 1`: последовательный режим.
- Иначе `multiprocessing.Pool` для чтения файлов и параллельного прогонки.

Ограничение по умолчанию: `min(cpu_count(), 8)`.

---

## 17. Логика `label_engine.py` — главный алгоритмический слой

`label_engine.py` сейчас совмещает:
- генерацию датасет-пар,
- часть эвристик,
- OpenAI-интеграцию.

### 17.1 Режимы (`dataset_mode`)

- `generation`:
  - instruction-to-code.
- `documentation`:
  - QA по пониманию кода.

### 17.2 Входы/выходы метода `generate_qa_pairs`

Вход:
- `code` (текст файла),
- `file_path` (для определения языка).

Выход:
- список словарей формата:
  - `question`,
  - `context`,
  - `answer`,
  - `question_type`.

---

## 18. Алгоритм generation для Python (пошагово)

1. `ast.parse(code)`; при `SyntaxError` — пустой результат.
2. Проставление `parent` для AST-узлов.
3. Сбор `FunctionDef/AsyncFunctionDef`, сортировка по позиции.
4. Фильтрация кандидатов:
   - исключение вложенных функций,
   - исключение заглушек (`pass`, `...`),
   - фильтр по длине функции (`_MIN_FUNCTION_LINES.._MAX_FUNCTION_LINES`).
5. Извлечение исходника функции `fn_src` (`ast.get_source_segment` fallback по line span).
6. Извлечение сигнатуры `_python_signature_from_source`.
7. Формирование `question` (шаблон ACOM).
8. `context`:
   - если `--context` выключен -> `""`;
   - если включён -> OpenAI-контекст (или fallback).
9. `answer = fn_src` (реальный листинг).
10. Дедуп через hash по `(qual, signature, prefix(fn_src))`.
11. Ограничение `max_qa_pairs_per_file`.

Сложность: в среднем `O(F)` по числу функций в файле + стоимость AST обхода `O(|AST|)`.

---

## 19. Алгоритм generation для C/C++ (пошагово)

### 19.1 Экстракция функций `_extract_c_like_functions`

1. Линейный проход по строкам.
2. Пропуск:
   - блоков комментариев `/* ... */`,
   - строк `//...`,
   - препроцессора `#...`.
3. Накопление кандидата header (пока не встретили `{` при закрытой скобочной глубине).
4. Проверка header в `_is_c_like_function_header`:
   - должно быть `(` и `)`,
   - не должно быть `if/for/while/switch/catch`,
   - не `typedef`,
   - не прототип с `;`.
5. Сбор тела по балансу `{}`.
6. Нормализация сигнатуры (`_normalize_c_signature`) в одну строку.

### 19.2 Формирование пары

- `question`: шаблон ACOM + сигнатура.
- `context`: OpenAI/fallback (если `--context`).
- `answer`: полный extracted body.
- `question_type = IMPLEMENTATION`.

Это обеспечивает соответствие ТЗ: ответ — реальные строки кода из `.c/.cpp`.

---

## 20. Алгоритм documentation-режима

### 20.1 Python documentation mode

Для каждой функции:
1. Скан структуры тела `_scan_body_structure`:
   - `if/else`, loops, try/except, nested conditions, mutation in loop и др.
2. На базе сигналов строится план вопросов `_question_plan`.
3. Для каждого вопроса:
   - ответ через OpenAI (если включен),
   - иначе fallback на doc_hint/шаблон.
4. Фильтрация плохих ответов:
   - запрещённые подстроки,
   - слово `context`,
   - hedge-лексика (`likely/probably/...`).

### 20.2 C/C++ documentation mode

Использует extracted C-функции:
- вопрос по функциональности,
- context = body функции,
- answer = OpenAI или fallback.

---

## 21. OpenAI-интеграция: как именно работает

### 21.1 Поиск ключа

Приоритет:
1. явный `openai_api_key` из config/CLI;
2. `OPENAI_API_KEY` в env;
3. `.env` по candidate paths.

### 21.2 Где вызывается OpenAI

- **generation mode**: для поля `context` (короткое описание функции).
- **documentation mode**: для поля `answer`.

### 21.3 Поведение при ошибках API

Если API не дал ответ:
- логируется предупреждение один раз;
- используется fallback-текст;
- pipeline не падает.

Это сделано, чтобы запуск всегда завершался даже при сетевых/квотных проблемах.

---

## 22. Форматы данных и контракты

### 22.1 Внутренний entry (pipeline JSONL)

```json
{
  "repo": "...",
  "file": "...",
  "entities": [...],
  "qa_pairs": [...],
  "raw_code": "..."
}
```

### 22.2 Плоский train JSONL (`qa-flatten`)

Каждая строка:

```json
{
  "question": "...",
  "context": "...",
  "answer": "...",
  "repo": "...",
  "file": "...",
  "question_type": "..."
}
```

Для generation: `question_type=IMPLEMENTATION`.

---

## 23. Метрики и проверка качества

### 23.1 Исторические (этап начальных экспериментов)
- Precision, Recall, F1, TP/FP/FN по методам извлечения.

### 23.2 Текущие операционные проверки

1. **Count check**: нужное число строк (например, 5 и 5).
2. **File routing check**:
   - Python датасет содержит только `module.py`;
   - C датасет содержит только `cJSON.c`.
3. **Source-match check**:
   - `answer` совпадает с реальным кодом функции.
4. **Context quality check**:
   - не пустой;
   - не fallback-шаблон (если нужен OpenAI-only результат).

---

## 24. Ограничения и технические риски

1. **Размер `label_engine.py`**  
   Риск: сложность сопровождения.
2. **C/C++ edge-cases**  
   Макросы и экзотические сигнатуры могут требовать дополнительных правил.
3. **Вариативность OpenAI**  
   Контекст может отличаться между запусками.
4. **Стоимость и зависимость от сети**  
   При больших репо включённый `--context` увеличивает время и стоимость.

---

## 25. План укрепления до «production-grade»

1. Разделить `label_engine.py` на:
   - `generation_engine.py`,
   - `documentation_engine.py`,
   - `c_like_function_extractor.py`.
2. Добавить unit + golden проверки на фиксированных файлах.
3. Ввести отчёт по покрытию extracted functions:
   - всего функций в файле,
   - сколько попало в датасет,
   - причины отфильтровки.
4. Версионировать формат датасета (schema version).
5. Добавить deterministic mode для контекста (fallback-only) для воспроизводимых научных прогонов.

---

## 26. Ключевой тезис для преподавателя

Проект реализует не один «скрипт», а полный инженерный контур подготовки данных:  
**от репозитория -> через многошаговый анализ и валидацию -> к двум ML-форматам датасета с проверяемым качеством и воспроизводимым запуском**.

---

## 27. Отдельная схема для Python (наглядно)

Ниже показан **полный путь обработки Python-файла** в generation-режиме.

### 27.1 Что используем именно для Python

- Фильтрация языка: `--strict-python-only` (расширение `.py`)
- Извлечение сущностей: `tools/ast_tool.py`
- Извлечение функций для датасета: `labeling/label_engine.py` через `ast`
- Контекст (опционально): OpenAI в `label_engine` (`_openai_generation_context`)
- Формирование записей: `export/dataset_builder.py`
- Экспорт: `export/json_exporter.py`
- Отчёт: `reporting/metrics_report.py`, `reporting/markdown_report.py`

### 27.2 Схема Python (generation)

```text
Вход: repo_path_or_url
   |
   v
[repo_loader.load]
   |
   v
[file_filter.iter_python_files]
   |  (оставляем .py)
   v
[code_cleaner.clean]
   |
   v
[label_engine.label] ---> uses [ASTTool.extract] ---> entities[]
   |
   +--> [label_engine.generate_qa_pairs(mode=generation, file=.py)]
            |
            +--> ast.parse(code)
            +--> collect FunctionDef/AsyncFunctionDef
            +--> filter (nested/stub/len bounds)
            +--> signature from "def ...:"
            +--> question = ACOM template
            +--> context = OpenAI or fallback (if --context)
            +--> answer = exact function source
            |
            v
          qa_pairs[] (IMPLEMENTATION)
   |
   v
[validator -> deduplicator -> normalizer]  (для entities)
   |
   v
[dataset_builder.build_entry]
   |
   v
Entry{repo,file,entities,qa_pairs,raw_code}
   |
   v
[json_exporter.export] + [metrics_report/build] + [markdown_report.generate]
```

### 27.3 Схема Python (documentation QA)

```text
... preprocessing steps same ...
   |
   v
[label_engine.generate_qa_pairs(mode=documentation, file=.py)]
   |
   +--> ast.parse
   +--> _scan_body_structure (if/loop/try/nested/mutation signals)
   +--> _question_plan (FUNCTIONALITY, RETURN_VALUE, WHY_*, BUG_* ...)
   +--> answer = OpenAI doc answer OR fallback
   +--> quality filters (bad substrings / hedge words)
   |
   v
qa_pairs[] (question_type != IMPLEMENTATION)
```

### 27.4 Важный технический смысл

- Для Python структурный анализ основан на AST, поэтому:
  - минимальное количество ложных структурных срабатываний;
  - корректная работа с вложенными функциями/классами;
  - стабильное выделение сигнатур и тел.

---

## 28. Отдельная схема для C/C++ (наглядно)

Ниже показан **полный путь обработки C/C++-файла**.

### 28.1 Что используем именно для C/C++

- Фильтрация языка: `--strict-c-cpp-only` (`.c/.h/.hpp/.hh/.hxx/.cpp/.cc/.cxx`)
- Извлечение сущностей: `tools/c_ast_tool.py`
  - приоритет: clang AST JSON
  - fallback: tree-sitter
  - fallback: regex
- Извлечение функций для generation/doc: `label_engine._extract_c_like_functions`
- Контекст (опционально): OpenAI в `label_engine`

### 28.2 Схема C/C++ (generation)

```text
Вход: repo_path_or_url
   |
   v
[repo_loader.load]
   |
   v
[file_filter.iter_python_files]
   |  (на самом деле мульти-язычный фильтр по include_extensions)
   v
[code_cleaner.clean]
   |
   v
[label_engine.label] ---> uses [CASTTool.extract] ---> entities[]
                          |
                          +--> clang AST json (prefer)
                          +--> tree-sitter fallback
                          +--> regex fallback
   |
   +--> [label_engine.generate_qa_pairs(mode=generation, file=.c/.cpp)]
            |
            +--> _extract_c_like_functions:
                   - skip comments/preprocessor
                   - accumulate header until "{"
                   - validate function header
                   - collect body via brace balance
                   - normalize signature
            +--> question = ACOM template + signature
            +--> context = OpenAI or fallback (if --context)
            +--> answer = exact extracted body
            |
            v
          qa_pairs[] (IMPLEMENTATION)
   |
   v
Entry export + report (same as Python)
```

### 28.3 Схема C/C++ (documentation QA)

```text
... preprocessing + entities extraction same ...
   |
   v
[generate_qa_pairs(mode=documentation, file=.c/.cpp)]
   |
   +--> _extract_c_like_functions
   +--> build functionality questions
   +--> answer = OpenAI doc answer OR fallback
   |
   v
qa_pairs[] (FUNCTIONALITY ...)
```

### 28.4 Где отличия от Python принципиальные

1. Python: структурная база = `ast.parse`.
2. C/C++: сущности — через clang/tree-sitter/regex; generation extraction — C-like parser по тексту и балансу `{}`.
3. Поэтому C/C++ чувствительнее к edge-case синтаксису (макросы, нестандартные заголовки, сложные шаблоны).

---

## 29. Сводная сравнительная таблица пайплайнов Python vs C/C++

| Этап | Python | C/C++ |
|---|---|---|
| Фильтр файлов | `.py` (при strict) | `.c/.h/.hpp/.cpp/...` (при strict) |
| Извлечение сущностей | `ASTTool` | `CASTTool (clang -> tree-sitter -> regex)` |
| Извлечение функций для generation | AST function nodes | C-like function extractor |
| Сигнатура | из `def ...:` | из заголовка функции + нормализация |
| `answer` | точный source segment функции | точное extracted body по балансу `{}` |
| `context` | OpenAI/fallback | OpenAI/fallback |
| Надёжность структуры | очень высокая (AST) | высокая, но ниже Python AST на edge-cases |

---

## 30. Мини-схема «что показывать преподавателю на слайдах»

### Слайд 1: Общая архитектура
`Repo -> Preprocess -> Extract -> Generate -> Export -> Report`

### Слайд 2: Python branch
`ASTTool + AST generation pipeline`

### Слайд 3: C/C++ branch
`CASTTool + C-like function extractor`

### Слайд 4: Результаты
- метрики начальных экспериментов (AST лучший),
- текущие demo JSONL (5 Python + 5 C),
- пример совпадения `answer` с исходником.

---

## 31. Как работает ИЗНУТРИ на уровне одной функции (Python, generation)

Ниже не «названия файлов», а точная механика преобразования:  
**входной код функции -> объекты в памяти -> JSONL-строка**.

### 31.1 Входной фрагмент (пример)

```python
def foo(a: int, b: int) -> int:
    if a < 0:
        return 0
    return a + b
```

### 31.2 Что делает пайплайн шаг за шагом

1. Файл читается как строка `code: str`.
2. `ast.parse(code)` строит дерево Python AST.
3. В AST выбирается узел `FunctionDef(name="foo", ...)`.
4. Для узла вычисляются служебные признаки:
   - вложенная ли функция (`parent`),
   - длина в строках (`lineno/end_lineno`),
   - не является ли заглушкой (`pass`, `...`).
5. Из исходника извлекается точный текст функции `fn_src`:
   - сначала `ast.get_source_segment(code, node)`,
   - если `None`, fallback по диапазону строк.
6. Из `fn_src` извлекается сигнатура:
   - начинается с `def`/`async def`,
   - накапливается до `:`,
   - результат: `def foo(a: int, b: int) -> int:`.
7. Формируется `question` по шаблону ACOM.
8. Формируется `context`:
   - если `--context` выключен -> `""`;
   - если включен -> OpenAI summary от `signature + fn_src`;
   - если OpenAI не ответил -> fallback-шаблон.
9. `answer` присваивается как **точный `fn_src` без генерации**.
10. Строится hash-дедуп ключ (по сигнатуре/префиксу функции), чтобы убрать повторы.
11. Формируется объект пары:
   - `question`, `context`, `answer`, `question_type="IMPLEMENTATION"`.
12. Пара добавляется в `qa_pairs` текущего файла.

### 31.3 Результат в памяти (до записи)

```json
{
  "question": "Implement function with below signature using ACOM component-based architecture. The signature is:\n\ndef foo(a: int, b: int) -> int:",
  "context": "<openai_or_fallback>",
  "answer": "def foo(a: int, b: int) -> int:\n    if a < 0:\n        return 0\n    return a + b",
  "question_type": "IMPLEMENTATION"
}
```

---

## 32. Внутренний разбор Python documentation-mode (как рождается QA)

Здесь `answer` уже не код, а текст объяснения.

### 32.1 Внутренняя структура сигналов

При обходе тела функции считается `_BodySignals`:

- `has_if`, `has_if_with_else`
- `has_loop`, `loop_with_if`, `loop_has_else`
- `has_try`, `try_with_if_body`, `if_with_try_body`
- `nested_if`, `if_count`
- `mutation_in_loop`, `has_break_continue`
- `has_return`, `return_bool_flags`

Это нужно, чтобы не задавать «слепые» вопросы, а делать их по реальной структуре.

### 32.2 Как из сигналов строятся вопросы

Функция `_question_plan(qual, sig)` добавляет вопросы по правилам:

- всегда: `FUNCTIONALITY`;
- если есть return: `RETURN_VALUE`;
- if/try -> `EDGE_CASES`;
- loop -> `BEHAVIOR` про итерацию;
- if -> `WHY_CHECK`, `COUNTERFACTUAL`;
- try/alt returns -> `WHY_FALLBACK`;
- всегда для зрелых функций -> `BUG_SAFETY`;
- сложные сигналы -> `NESTED_LOGIC`, `TRY_CONTROL_MIX`, `FLOW_COMPLEXITY` и т.д.

Итог: список `(question_type, question_text)`, потом дедуп и ограничение max count.

### 32.3 Как рождается answer

Для каждого вопроса:
1. Пробуем OpenAI (`_openai_doc_answer`).
2. Если OpenAI недоступен/пусто -> fallback:
   - doc_hint, если есть,
   - иначе шаблон «infer from source».
3. Прогон через quality-фильтры:
   - запрещённые подстроки,
   - `context` word ban,
   - hedge ban (`likely/probably/...`).

---

## 33. Как работает ИЗНУТРИ для C/C++ generation

Главный момент: здесь нельзя использовать Python AST, поэтому идёт структурный парсинг по тексту и скобкам.

### 33.1 Вход

Текст `.c/.cpp` файла как `code: str`.

### 33.2 Экстракция функции `_extract_c_like_functions`

Алгоритм:

1. Линейный проход по строкам `i=0..n-1`.
2. Состояние `in_block_comment`:
   - если `/* ... */`, строки пропускаются.
3. Пропуск строк:
   - начинающихся с `//`, `#`, `*` (шум/препроцессор/комментарии).
4. Сбор кандидата header:
   - накапливаем строки, считаем `paren_depth` (`(`/`)`);
   - ждём `{` только при `paren_depth == 0`.
5. Валидация header (`_is_c_like_function_header`):
   - есть `(` и `)`,
   - не `if/for/while/switch/catch`,
   - не `typedef`,
   - не прототип с `;`.
6. Сбор тела:
   - с позиции начала функции считаем баланс `{`/`}`,
   - как только баланс вернулся к 0 -> тело завершено.
7. Нормализация сигнатуры в одну строку.
8. Возврат пары `(signature, fn_src)`.

### 33.3 Формирование датасет-строки

Из `(signature, fn_src)`:
- `question` = ACOM шаблон + signature;
- `context` = OpenAI/fallback (если `--context`);
- `answer` = `fn_src` (вырезанный блок функции как есть);
- `question_type=IMPLEMENTATION`.

---

## 34. Формирование финального JSONL: буквально по шагам

После обработки файла создаётся entry:

```json
{
  "repo": "...",
  "file": "...",
  "entities": [...],
  "qa_pairs": [...],
  "raw_code": "..."
}
```

Потом `qa-flatten` делает:

```text
for each entry in pipeline_jsonl:
    for each pair in entry["qa_pairs"]:
        write line {
          question, context, answer,
          repo=entry.repo, file=entry.file,
          question_type
        }
```

Именно так появляются `module_py5_train.jsonl` и `cjson_c5_train_v2.jsonl`.

---

## 35. Где и почему функция может быть ОТФИЛЬТРОВАНА

Это важный блок для вопросов «почему функция не попала в датасет».

### Python функция исключается, если:
- вложенная (`def` внутри `def`);
- заглушка (`pass`, `...`);
- слишком короткая/длинная по лимитам строк;
- не удалось извлечь сигнатуру;
- duplicate по hash.

### C/C++ функция исключается, если:
- header не прошёл проверку;
- найден прототип без тела;
- не сошёлся баланс `{}` до конца;
- duplicate по hash.

---

## 36. Пример трассировки одной строки датасета (от и до)

Возьмём `cJSON_GetStringValue`:

1. `_extract_c_like_functions` нашёл header и body.
2. Header нормализован:
   `CJSON_PUBLIC(char *) cJSON_GetStringValue(const cJSON * const item) { ... }`
3. `question` построен по шаблону.
4. `context`:
   - в последнем прогоне успешно сгенерирован OpenAI.
5. `answer`:
   - равен блоку функции:
   `if (!cJSON_IsString(item)) return NULL; ...`
6. `qa-flatten` добавил поля `repo/<repo_id>`, `file/cJSON.c`.

Результат — одна JSONL-строка в `outputs/cjson_c5_train_v2.jsonl`.

---

## 37. Важно для защиты: коротко «как работает изнутри»

Одна фраза:

> Мы не генерируем код в `answer`; мы детерминированно извлекаем реальные функции из исходника, а OpenAI используем только для опционального `context` (или для answer в documentation-mode).

Это ключевое инженерное отличие от «чисто LLM-генерации».
