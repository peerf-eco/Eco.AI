# Верификация кода: План реализации (A, B, C, D)

> Цель: снизить количество build-итераций за счёт предотвращения ошибок ДО компиляции.
> Основная проблема: LLM галлюцинирует имена методов, сигнатуры, include-файлы.

## Текущий pipeline

```
planner → resolver → writer → build → tester → (writer | END)
                       ↑         ↑                  │
                       │         └──────────────────┘
                       └── (compile/link error → writer fix)
```

Проблема: writer генерирует EcoMain.c "по ощущениям" из raw заголовков.
Build падает → writer фиксит → build опять падает → цикл сжирает 3-5 итераций.

## Целевой pipeline

```
planner → resolver → writer → verifier → build → tester → (writer | END)
                       ↑          │
                       └──────────┘ (verifier нашёл ошибки → writer fix)
```

Verifier — **чистый Python**, без LLM. Ловит 80% ошибок за 0 секунд и 0 токенов.

---

## Обзор правок

| # | Файл | Что | Зачем |
|---|------|-----|-------|
| 1 | `agent/header_parser.py` | **Создать** — парсер VTbl из заголовков | (A) Извлечь методы и сигнатуры из IEco*.h |
| 2 | `agent/prompts_v2.py` | **Изменить** — writer prompt | (B) Структурированный API reference вместо raw headers |
| 3 | `agent/graph_v2.py` | **Изменить** — добавить helper для формирования prompt | (B) Генерировать method map перед вызовом writer |
| 4 | `agent/verifier.py` | **Создать** — pre-build верификатор | (C) Проверить EcoMain.c до компиляции |
| 5 | `agent/graph_v2.py` | **Изменить** — добавить verifier node в граф | (D) Вставить между writer и build |
| 6 | `agent/state.py` | **Изменить** — добавить поле verification_errors | (D) Передача ошибок verifier → writer |
| 7 | `agent/prompts_v2.py` | **Изменить** — добавить WRITER_VERIFY_FIX_PROMPT | (D) Промпт для исправления по результатам верификации |

---

## Правка 1: `agent/header_parser.py` (НОВЫЙ)

### Цель (A — Symbol Validation)

Извлечь из заголовков IEco*.h **структурированную карту методов**:
какой интерфейс → какие методы → какие сигнатуры.

### Почему именно так, а не иначе

| Альтернатива | Почему не она |
|---|---|
| **clangd / libclang AST** | Требует compile_commands.json → требует CMake. У нас MSVC Makefiles. Тяжёлая зависимость ради парсинга 5-10 простых заголовков. Оверинжиниринг. |
| **tree-sitter** | Добавляет зависимость (`tree-sitter-c`). Заголовки используют нестандартные макросы (`ECOCALLMETHOD`, `interface`), tree-sitter без препроцессинга их не распарсит. |
| **Regex** | Заголовки имеют **стабильный шаблон** (VTbl struct с function pointers). Regex надёжен для стабильного формата. Ноль зависимостей. Работает за микросекунды. |
| **LLM парсинг** | Тратит токены, может галлюцинировать — ровно та проблема, которую мы решаем. |

### Что парсим

Формат VTbl в заголовках **стабилен** по всем 19 SDK компонентам:

```c
typedef struct IEcoMathC89VTbl {
    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(/* ... */);
    uint32_t (ECOCALLMETHOD *AddRef)(/* ... */);
    uint32_t (ECOCALLMETHOD *Release)(/* ... */);

    /* IEcoMathC89 */
    double (ECOCALLMETHOD *acos)(IEcoMathC89Ptr_t me, double x);
    double (ECOCALLMETHOD *pow)(IEcoMathC89Ptr_t me, double x, double y);
} IEcoMathC89VTbl;
```

Паттерн каждого метода:
```
<return_type> (ECOCALLMETHOD *<method_name>)(<params>);
```

### Что создаём

```python
"""
Парсер VTbl заголовков EcoOS SDK.

Извлекает структурированную карту методов из IEco*.h для:
1. Вставки в writer prompt как API reference
2. Верификации сгенерированного EcoMain.c
"""

import re
from typing import Dict, List, Optional


# Паттерн для строки VTbl: return_type (ECOCALLMETHOD *method_name)(params);
VTBL_METHOD_RE = re.compile(
    r'^\s*'
    r'(?P<return_type>[\w\s\*]+?)\s*'      # return type (e.g. "double", "int16_t", "void *")
    r'\(\s*ECOCALLMETHOD\s*\*\s*'           # (ECOCALLMETHOD *
    r'(?P<method_name>\w+)\s*\)'            # method_name)
    r'\s*\((?P<params>[^)]*)\)\s*;',        # (params);
    re.MULTILINE
)

# Методы IEcoUnknown — пропускаем, они стандартные
BASE_METHODS = {"QueryInterface", "AddRef", "Release"}


def parse_vtbl_methods(header_content: str) -> List[Dict[str, str]]:
    """
    Извлечь методы из VTbl определения в заголовке.

    Returns:
        List of {"name": "pow", "return_type": "double",
                 "params": "IEcoMathC89Ptr_t me, double x, double y",
                 "signature": "double pow(IEcoMathC89Ptr_t me, double x, double y)"}
    """
    methods = []
    for match in VTBL_METHOD_RE.finditer(header_content):
        name = match.group("method_name").strip()
        if name in BASE_METHODS:
            continue

        ret = match.group("return_type").strip()
        params = match.group("params").strip()

        methods.append({
            "name": name,
            "return_type": ret,
            "params": params,
            "signature": f"{ret} {name}({params})",
        })

    return methods


def build_method_map(resolved_components: list) -> Dict[str, List[Dict[str, str]]]:
    """
    Построить карту: interface_name → [methods] по resolved_components.

    Args:
        resolved_components: список из state["resolved_components"]

    Returns:
        {"IEcoMathC89": [{"name": "pow", "signature": "..."}, ...], ...}
    """
    method_map = {}

    for comp in resolved_components:
        interface_name = comp.get("interface_name", "")
        if not interface_name:
            continue

        header_contents = comp.get("header_contents", {})

        # Ищем IEco*.h (не IdEco*.h — там только CID/IID)
        for hname, hcontent in header_contents.items():
            if hname.startswith("IEco") and hname.endswith(".h"):
                methods = parse_vtbl_methods(hcontent)
                if methods:
                    method_map[interface_name] = methods
                    break

    return method_map


def format_method_map_for_prompt(method_map: Dict[str, List[Dict[str, str]]]) -> str:
    """
    Отформатировать method map в текстовый блок для writer prompt.

    Пример вывода:
        ## IEcoMathC89 — доступные методы
        - double pow(IEcoMathC89Ptr_t me, double x, double y)
        - double sqrt(IEcoMathC89Ptr_t me, double x)
    """
    parts = []
    for iface, methods in method_map.items():
        parts.append(f"## {iface} — доступные методы")
        for m in methods:
            parts.append(f"  - {m['signature']}")
        parts.append("")

    return "\n".join(parts)
```

### Ожидаемый результат

```python
map = build_method_map(state["resolved_components"])
# {"IEcoMathC89": [
#     {"name": "pow", "return_type": "double", "params": "...", "signature": "double pow(...)"},
#     {"name": "sqrt", ...},
# ]}

text = format_method_map_for_prompt(map)
# ## IEcoMathC89 — доступные методы
#   - double pow(IEcoMathC89Ptr_t me, double x, double y)
#   - double sqrt(IEcoMathC89Ptr_t me, double x)
```

---

## Правка 2: `agent/prompts_v2.py` — Writer Prompt (B — Prompt Improvement)

### Цель

Дать writer'у **структурированный API reference** вместо raw заголовков,
и добавить **правило верификации**: "не используй то, чего нет в reference".

### Почему именно так

| Альтернатива | Почему не она |
|---|---|
| **Дать LLM tool `symbol_lookup`** | Требует переделать writer в ReAct-агента. Это добавляет 3-5 LLM-вызовов на каждый tool call. Дороже, медленнее, сложнее. Writer — это single-shot генератор, и это правильно. |
| **Оставить raw заголовки** | LLM видит 200+ строк на заголовок (комментарии, макросы, ifdef, Cyrillic). Методы теряются в шуме. Structured reference работает лучше. |
| **Убрать заголовки совсем** | Нельзя — LLM нужен контекст для типов, IID/CID констант, порядка параметров. |

Решение: **оба формата** — structured method map (для навигации) + raw заголовки (для деталей типов).

### Что менять

#### 2.1. Добавить секцию в WRITER_SYSTEM_PROMPT

После текущих правил (строка ~185 в prompts_v2.py) добавить:

```
## КРИТИЧЕСКОЕ ПРАВИЛО: Верификация символов

ПЕРЕД написанием кода проверь по секции "API REFERENCE":
1. Каждый вызываемый метод СУЩЕСТВУЕТ в списке методов интерфейса
2. Количество и типы аргументов СОВПАДАЮТ с сигнатурой
3. Вызов идёт через pVTbl: `ptr->pVTbl->method(ptr, args...)`
4. Первый аргумент — ВСЕГДА указатель на сам интерфейс (me/self)

Если метода нет в API REFERENCE — НЕ используй его. Не выдумывай методы.
```

#### 2.2. Изменить get_writer_user_prompt() в graph_v2.py

**Было:** raw заголовки для каждого компонента.

**Станет:** сначала structured API reference, потом raw заголовки.

```python
# В начало user prompt, перед заголовками:
method_map = build_method_map(resolved_components)
method_ref = format_method_map_for_prompt(method_map)

parts.append("# API REFERENCE — используй ТОЛЬКО эти методы\n")
parts.append(method_ref)
parts.append("\n# Полные заголовки (для типов и констант)\n")
# ... существующий код с raw заголовками
```

### Ожидаемый результат

Writer получает промпт вида:

```
# API REFERENCE — используй ТОЛЬКО эти методы

## IEcoMathC89 — доступные методы
  - double pow(IEcoMathC89Ptr_t me, double x, double y)
  - double sqrt(IEcoMathC89Ptr_t me, double x)
  - double sin(IEcoMathC89Ptr_t me, double x)

## IEcoStringC89 — доступные методы
  - char_t* Copy(IEcoStringC89Ptr_t me, char_t* dst, const char_t* src)
  - int32_t Compare(IEcoStringC89Ptr_t me, const char_t* s1, const char_t* s2)

# Полные заголовки (для типов и констант)
#### IEcoMathC89.h
```c
...
```
```

LLM видит чёткий список "что можно вызвать" перед raw заголовками.

---

## Правка 3: `agent/graph_v2.py` — helper для method map (B)

### Цель

Интегрировать `header_parser.build_method_map()` в writer node.

### Что менять

В функции `get_writer_user_prompt()` (и аналогично в `get_writer_fix_prompt()`, `get_writer_test_fix_prompt()`):

```python
from .header_parser import build_method_map, format_method_map_for_prompt

def get_writer_user_prompt(state):
    resolved_components = state.get("resolved_components", [])

    # Structured API reference
    method_map = build_method_map(resolved_components)
    method_ref = format_method_map_for_prompt(method_map)

    parts = []
    parts.append("# API REFERENCE — используй ТОЛЬКО эти методы\n")
    parts.append(method_ref)
    parts.append("\n# Полные заголовки (для типов и констант)\n")

    # ... существующий код с raw заголовками без изменений
```

### Почему в трёх prompt-функциях

Writer вызывается в 3 режимах (generate / build-fix / test-fix).
Во всех трёх LLM должен видеть правильный method map.
Без него fix-промпт может "починить" ошибку, выдумав новый несуществующий метод.

---

## Правка 4: `agent/verifier.py` (НОВЫЙ) — Pre-build Validation (C)

### Цель

Проверить сгенерированный EcoMain.c **до компиляции** — поймать ошибки за 0 секунд.

### Почему Python, а не LLM

| Критерий | LLM Critic | Python Verifier |
|---|---|---|
| Скорость | 5-15 сек + токены | < 10 мс |
| Стоимость | $0.01-0.05 за вызов | $0 |
| Детерминизм | Может пропустить | 100% воспроизводимость |
| Hallucination | Может выдумать ошибку | Не может — только regex/string match |
| Покрытие | Произвольные проблемы | Только известные паттерны |

LLM-Critic ловит "необычные" проблемы, но наши ошибки — **повторяющиеся и паттерновые**:
- Забыл `pVTbl` в вызове
- Выдумал метод
- Не зарегистрировал framework компоненты
- Забыл include

Для паттерновых ошибок Python-верификатор лучше: быстрее, дешевле, надёжнее.

### Что проверяем (чеклист)

Каждая проверка — отдельная функция, возвращает список ошибок:

```python
"""
Pre-build verifier для EcoMain.c.

Чистый Python, без LLM. Проверяет сгенерированный код
против resolved_components до отправки на компиляцию.
"""

import re
from typing import List, Dict, Any
from .header_parser import build_method_map


def verify_ecomain(
    ecomain_content: str,
    resolved_components: list,
    framework_components: list,
) -> List[Dict[str, str]]:
    """
    Проверить EcoMain.c до компиляции.

    Returns:
        Список ошибок: [{"check": "...", "message": "...", "severity": "error|warning"}]
        Пустой список = всё ОК.
    """
    errors = []
    errors.extend(_check_includes(ecomain_content, resolved_components))
    errors.extend(_check_factory_declarations(ecomain_content, resolved_components))
    errors.extend(_check_framework_registration(ecomain_content, framework_components))
    errors.extend(_check_method_calls(ecomain_content, resolved_components))
    errors.extend(_check_vtbl_pattern(ecomain_content))
    errors.extend(_check_eco_os_macro(ecomain_content))
    return errors
```

#### Проверка 1: Includes

```python
def _check_includes(code: str, resolved_components: list) -> list:
    """
    Каждый resolved component должен иметь #include для IEco*.h и IdEco*.h.
    """
    errors = []
    for comp in resolved_components:
        if comp.get("is_framework"):
            continue
        iface = comp.get("interface_name", "")
        name = comp.get("name", "")

        # Проверяем IEco*.h
        iface_header = f"I{iface[1:]}.h" if iface.startswith("I") else f"{iface}.h"
        for hname in comp.get("header_contents", {}):
            if hname.startswith("IEco") and hname.endswith(".h"):
                if f'#include "{hname}"' not in code:
                    errors.append({
                        "check": "missing_include",
                        "message": f'Missing #include "{hname}" for component {name}',
                        "severity": "error",
                    })

        # Проверяем IdEco*.h
        for hname in comp.get("header_contents", {}):
            if hname.startswith("IdEco") and hname.endswith(".h"):
                if f'#include "{hname}"' not in code:
                    errors.append({
                        "check": "missing_id_include",
                        "message": f'Missing #include "{hname}" for component {name} (needed for CID)',
                        "severity": "error",
                    })

    return errors
```

#### Проверка 2: Factory function declarations

```python
def _check_factory_declarations(code: str, resolved_components: list) -> list:
    """
    Каждый компонент с ECO_LIB должен иметь extern declaration для factory.
    """
    errors = []
    for comp in resolved_components:
        factory = comp.get("factory_func", "")
        if not factory:
            continue
        # factory = "GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0"
        if factory not in code:
            errors.append({
                "check": "missing_factory",
                "message": f"Factory function {factory} for {comp.get('name', '?')} not found in code",
                "severity": "warning",  # warning потому что может быть внутри #ifdef ECO_LIB
            })
    return errors
```

#### Проверка 3: Framework registration order

```python
def _check_framework_registration(code: str, framework_components: list) -> list:
    """
    InterfaceBus1 и FileSystemManagement1 должны регистрироваться ДО user components.
    """
    errors = []

    # Ищем все RegisterComponent вызовы
    register_calls = [
        (m.start(), m.group(1))
        for m in re.finditer(r'RegisterComponent\s*\([^,]+,\s*&(\w+)', code)
    ]

    if not register_calls:
        return errors

    bus_pos = None
    fsm_pos = None
    first_user_pos = None

    for pos, cid_name in register_calls:
        if "InterfaceBus" in cid_name:
            bus_pos = pos
        elif "FileSystem" in cid_name:
            fsm_pos = pos
        elif "MemoryManager" not in cid_name and "System1" not in cid_name:
            if first_user_pos is None:
                first_user_pos = pos

    if first_user_pos is not None:
        if bus_pos is None:
            errors.append({
                "check": "missing_bus_registration",
                "message": "InterfaceBus1 must be registered before user components",
                "severity": "error",
            })
        elif bus_pos > first_user_pos:
            errors.append({
                "check": "wrong_registration_order",
                "message": "InterfaceBus1 registered AFTER user components — must be BEFORE",
                "severity": "error",
            })

        if fsm_pos is None:
            errors.append({
                "check": "missing_fsm_registration",
                "message": "FileSystemManagement1 must be registered before user components",
                "severity": "error",
            })
        elif fsm_pos > first_user_pos:
            errors.append({
                "check": "wrong_registration_order",
                "message": "FileSystemManagement1 registered AFTER user components — must be BEFORE",
                "severity": "error",
            })

    return errors
```

#### Проверка 4: Method calls exist in VTbl

```python
def _check_method_calls(code: str, resolved_components: list) -> list:
    """
    Проверить, что вызываемые методы реально существуют в VTbl.
    """
    errors = []
    method_map = build_method_map(resolved_components)

    # Паттерн вызова: ->pVTbl->method_name(
    call_pattern = re.compile(r'(\w+)->pVTbl->(\w+)\s*\(')

    for match in call_pattern.finditer(code):
        var_name = match.group(1)      # e.g. "g_pIMath"
        method_name = match.group(2)   # e.g. "pow"

        # Пропускаем базовые методы IEcoUnknown
        if method_name in ("QueryInterface", "AddRef", "Release",
                           "QueryComponent", "RegisterComponent"):
            continue

        # Пытаемся определить, какому интерфейсу принадлежит переменная
        # По объявлению: IEcoMathC89* g_pIMath
        var_decl = re.search(rf'(IEco\w+)\s*\*\s*{re.escape(var_name)}', code)
        if not var_decl:
            continue

        iface_name = var_decl.group(1)  # e.g. "IEcoMathC89"

        if iface_name in method_map:
            known_methods = {m["name"] for m in method_map[iface_name]}
            if method_name not in known_methods:
                errors.append({
                    "check": "unknown_method",
                    "message": (
                        f"Method '{method_name}' not found in {iface_name} VTbl. "
                        f"Available: {', '.join(sorted(known_methods))}"
                    ),
                    "severity": "error",
                })

    return errors
```

#### Проверка 5: pVTbl pattern

```python
def _check_vtbl_pattern(code: str) -> list:
    """
    Проверить, что вызовы идут через pVTbl, а не напрямую.
    Ловит ошибку: g_pIMath->pow(...)  вместо  g_pIMath->pVTbl->pow(...)
    """
    errors = []

    # Ищем прямые вызовы (без pVTbl) на интерфейсных переменных
    # Паттерн: g_pIXxx->method( но НЕ g_pIXxx->pVTbl
    direct_calls = re.finditer(
        r'(g_pI\w+)->(?!pVTbl)(\w+)\s*\(',
        code
    )

    for match in direct_calls:
        var_name = match.group(1)
        method = match.group(2)
        errors.append({
            "check": "missing_pvtbl",
            "message": f"Direct call {var_name}->{method}() — should be {var_name}->pVTbl->{method}()",
            "severity": "error",
        })

    return errors
```

#### Проверка 6: ECO_OS macro

```python
def _check_eco_os_macro(code: str) -> list:
    """
    ECO_OS не должен быть определён (конфликт с CRT на Windows).
    """
    errors = []
    if re.search(r'#\s*define\s+ECO_OS', code):
        errors.append({
            "check": "eco_os_defined",
            "message": "#define ECO_OS found — this conflicts with CRT on Windows, remove it",
            "severity": "error",
        })
    return errors
```

### Ожидаемый результат

```python
errors = verify_ecomain(code, resolved_components, framework_components)
# [] → всё ОК, отправляем на build
# [{"check": "unknown_method", "message": "Method 'power' not found in IEcoMathC89...", ...}]
#   → отправляем обратно в writer с этим списком ошибок
```

---

## Правка 5: `agent/graph_v2.py` — Verifier Node (D — Builder/Critic Split)

### Цель

Вставить verifier между writer и build. Если verifier находит ошибки — отправить
обратно в writer с описанием ошибок. Если ОК — отправить на build.

### Почему отдельная нода, а не часть writer

| Альтернатива | Почему не она |
|---|---|
| **Проверка внутри writer node** | Writer — LLM-нода. Verifier — Python-нода. Смешивать — нарушение разделения ответственности. Verifier работает с output writer'а, это другой этап. |
| **Проверка внутри build node** | Build уже делает компиляцию. Если добавить pre-checks туда, build станет "умным" — ему придётся отличать pre-check ошибки от compile ошибок. Лучше разделить. |
| **Middleware/hook** | LangGraph не имеет middleware для нод. Можно сделать edge callback, но нода — идиоматичнее и видна в progress UI. |

### Что менять в graph_v2.py

#### 5.1. Новая нода `verifier_node`

```python
from .verifier import verify_ecomain

def verifier_node(state: dict) -> dict:
    """
    Pre-build verification. Pure Python, no LLM.
    Checks EcoMain.c against resolved headers.
    """
    print("[VERIFIER] Checking EcoMain.c...")

    ecomain = state.get("ecomain_content", "")
    resolved = state.get("resolved_components", [])
    framework = state.get("framework_components", [])

    if not ecomain:
        return {"verification_errors": "No EcoMain.c content to verify"}

    errors = verify_ecomain(ecomain, resolved, framework)

    if errors:
        error_text = "Pre-build verification found issues:\n"
        for e in errors:
            error_text += f"  [{e['severity'].upper()}] {e['message']}\n"
        print(f"[VERIFIER] Found {len(errors)} issues")
        return {"verification_errors": error_text}
    else:
        print("[VERIFIER] All checks passed")
        return {"verification_errors": ""}
```

#### 5.2. Routing function

```python
def route_after_verification(state: dict) -> str:
    """
    После верификации: если есть ошибки → writer fix, иначе → build.
    """
    errors = state.get("verification_errors", "")
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 5)

    if errors and iteration < max_iter:
        print(f"[ROUTE] Verification failed → writer (iter {iteration})")
        return "writer"

    print(f"[ROUTE] Verification passed → build")
    return "build"
```

#### 5.3. Граф: writer → verifier → build

**Было:**
```python
graph.add_edge("writer", "build")
```

**Станет:**
```python
graph.add_edge("writer", "verifier")
graph.add_conditional_edges("verifier", route_after_verification, {
    "writer": "writer",
    "build": "build",
})
```

#### 5.4. Progress streaming

Verifier — новый этап в pipeline. Фронтенд уже использует `progress` events.
ChatAgent (stream_mode=["updates"]) автоматически стримит имена нод.

Добавить "verifier" в `v3_nodes` в `chat_agent.py`:
```python
v3_nodes = ["planner", "resolver", "writer", "verifier", "build", "tester"]
```

И в `progress-viewer.tsx`:
```typescript
const STAGES: { id: Stage; label: string }[] = [
  { id: "planner", label: "Planner" },
  { id: "resolver", label: "Resolver" },
  { id: "writer", label: "Writer" },
  { id: "verifier", label: "Verifier" },
  { id: "build", label: "Build" },
  { id: "tester", label: "Tester" },
];
```

---

## Правка 6: `agent/state.py` — поле verification_errors

### Что добавить

В `AgentStateV3`:

```python
# ═══════════════════════════════════════════════════════════════
# VERIFIER OUTPUT (pure Python, pre-build checks)
# ═══════════════════════════════════════════════════════════════
verification_errors: str       # Empty = OK, non-empty = issues found
```

В `state_helpers.py` — `make_initial_v3_state()`:

```python
"verification_errors": "",
```

### Почему `str`, а не `list`

Writer получает это поле как часть промпта. Строка проще вставляется в промпт.
Структурированный список уже сериализован в `verify_ecomain()` → текст.

---

## Правка 7: `agent/prompts_v2.py` — WRITER_VERIFY_FIX_PROMPT

### Цель

Когда verifier нашёл ошибки, writer должен получить **другой промпт** —
не "compile error" (это build fix), а "pre-build verification errors".

### Почему отдельный промпт, а не reuse WRITER_FIX_PROMPT

| Критерий | WRITER_FIX_PROMPT | WRITER_VERIFY_FIX_PROMPT |
|---|---|---|
| Источник ошибок | Компилятор (cl.exe stderr) | Python verifier (structured) |
| Формат | Raw compiler output | Чеклист с именами проверок |
| Типичные ошибки | Syntax error, undeclared identifier | Missing include, unknown method, wrong call pattern |
| Инструкции | "Fix the compilation error" | "Fix the verification issues, use API REFERENCE" |

Компилятор говорит "undeclared identifier 'power'" — LLM должен понять, что это не опечатка,
а несуществующий метод. Verifier говорит "Method 'power' not found in IEcoMathC89. Available: pow, sqrt, sin" — LLM сразу знает правильное имя.

### Что добавить

```python
WRITER_VERIFY_FIX_PROMPT = """\
Ты — инженер по исправлению EcoMain.c.

Pre-build верификация нашла проблемы в твоём коде. Исправь их.

ПРАВИЛА:
1. Используй ТОЛЬКО методы из секции API REFERENCE
2. Не выдумывай методы — если метода нет в reference, его НЕ существует
3. Вызовы через pVTbl: ptr->pVTbl->method(ptr, args...)
4. Первый аргумент метода — всегда указатель на интерфейс
5. Framework компоненты (InterfaceBus1, FileSystemManagement1) регистрируются ДО пользовательских

Верни ПОЛНЫЙ исправленный EcoMain.c.
"""
```

### Интеграция в writer node

В `create_writer_node_v3()` добавить третий путь:

```python
# Определяем режим writer'а
verification_errors = state.get("verification_errors", "")
error_message = state.get("error_message", "")
ecomain = state.get("ecomain_content", "")

if verification_errors and ecomain:
    # Mode 4: Verification fix
    system_prompt = WRITER_VERIFY_FIX_PROMPT
    user_prompt = get_writer_verify_fix_prompt(state)
elif error_message and ecomain:
    # Mode 2: Build fix (existing)
    ...
elif test_results and not tests_passed and ecomain:
    # Mode 3: Test fix (existing)
    ...
else:
    # Mode 1: Generate (existing)
    ...
```

---

## Порядок реализации

```
Правка 1 (header_parser.py)     ← нет зависимостей, можно сразу
Правка 6 (state.py)             ← нет зависимостей, можно сразу
    │
    ├──→ Правка 2 (prompts_v2.py — prompt improvement) ← зависит от 1
    ├──→ Правка 3 (graph_v2.py — method map в prompt) ← зависит от 1, 2
    │
    ├──→ Правка 4 (verifier.py) ← зависит от 1
    ├──→ Правка 7 (prompts_v2.py — verify fix prompt) ← зависит от 4
    └──→ Правка 5 (graph_v2.py — verifier node) ← зависит от 4, 6, 7
```

Правки 1, 6 можно делать параллельно.
Правки 2-3 (prompt) и 4-5-7 (verifier) можно делать параллельно после 1.

---

## Тест-план

### Unit-тесты для header_parser

```
1. parse_vtbl_methods(IEcoMathC89.h) → находит pow, sqrt, sin, cos, acos, ...
2. parse_vtbl_methods(IEcoStringC89.h) → находит Copy, Compare, Length, ...
3. parse_vtbl_methods("garbage text") → возвращает []
4. build_method_map(resolved_components) → карта по всем компонентам
5. Пропускает QueryInterface, AddRef, Release
```

### Unit-тесты для verifier

```
6. Правильный EcoMain.c → verify_ecomain() = []
7. Пропущен #include "IEcoMathC89.h" → ошибка missing_include
8. Вызов несуществующего метода power() → ошибка unknown_method
9. Прямой вызов без pVTbl → ошибка missing_pvtbl
10. RegisterComponent user перед framework → ошибка wrong_registration_order
11. #define ECO_OS → ошибка eco_os_defined
```

### Integration-тест

```
12. Полный pipeline: "Собери калькулятор с pow и sqrt"
    → writer генерирует код
    → verifier проверяет (0 ошибок ожидаем при хорошем prompt)
    → build
    → tester
    Сравнить: количество итераций ДО (без verifier) vs ПОСЛЕ (с verifier)
```

---

## Метрики успеха

| Метрика | До | Цель |
|---|---|---|
| Среднее число build-итераций | 3-5 | 1-2 |
| % первых сборок без ошибок | ~20% | ~60% |
| Время до успешной сборки | 2-5 мин | 30-90 сек |
| Стоимость токенов на запрос | ~$0.15 | ~$0.08 (меньше fix-итераций) |
