# Prompt Hardening Spec — V6 Pipeline Nodes

**Цель документа:** handoff-спека для применения правок промптов 5 LLM-нод V6-пайплайна. Документ самодостаточен — в новой сессии можно дать ссылку «применяй этот файл» и работа продолжится без потери контекста.

**Создан:** 2026-05-14, ветка `feat/v6-five-node-pipeline`.

---

## 0. Быстрый старт для новой сессии

Если ты только что подхватил это и видишь файл впервые — выполни в таком порядке:

1. Прочитай `MEMORY.md` проекта (загружается автоматически в начале сессии) — там состояние архитектуры V5/V6.
2. Прочитай этот файл целиком — здесь конкретные правки.
3. Проверь, что Docker контейнеры подняты:
   ```bash
   cd "H:/ai-hse-diploma-agent/Eco.Toolchain/Eco.AI.Assembly1"
   docker compose ps
   ```
   Должны быть `ecoos-api` (port 8100) и `ecoos-frontend` (port 3100).
4. Подтверди с пользователем: применять все 5 нод или часть.
5. Hot-reload автоматический — после `Edit`-ов на `agent/v6/nodes/*.py` контейнер `api` сам перезагрузит модуль.

---

## 1. Контекст: текущее состояние проекта

### Архитектура V6

5 LLM-нод + 2 orchestration-ноды в LangGraph StateGraph:
```
planner → plan_gate (HITL via interrupt) → setup → coder → builder → tester
                                                              ↓ failure
                                                          escalate (HITL)
```

State в `agent/v6/state.py:V6State`. Поля `target_os` / `target_arch` добавлены в этой сессии — приходят из UI селектора, используются в `setup` → `_ecoos_pull` для `-o`/`-a` флагов eco-cli.

Промпты живут как Python-константы в `agent/v6/nodes/<name>.py`:
- `planner.py` — `PLANNER_SYSTEM_PROMPT`
- `setup.py` — `SETUP_SYSTEM_PROMPT`
- `coder.py` — `CODER_SYSTEM_PROMPT`
- `builder.py` — `BUILDER_SYSTEM_PROMPT`
- `tester.py` — `TESTER_SYSTEM_PROMPT`

Каждая нода использует `EcoAgent` loop (`agent/v6/eco_agent.py`) — ReAct-style, со stream через `_stream_llm()` (для thinking/text deltas).

### Что было сделано в этой сессии (для контекста)

1. **Thinking-блоки UI** — добавлены `EventType.THINKING_DELTA`, `EventType.TEXT_DELTA` в `eco_agent.py`. `invoke` → `stream` через `_stream_llm`. На фронте: `thinking-block.tsx`, `globals.css` с keyframes `thinking-pulse-kf` и `thinking-blink-kf`. См. `use-v6-socket.ts:278-298` для backward-scan handler.

2. **Wine + eco-cli в Docker** — `Dockerfile` ставит `wine64`. `docker-compose.yml` монтирует `../../eco.sli-linux:/opt/eco-linux:ro`. `.env`: `V6_CLI_PATH=/opt/eco-linux/eco-cli`, `V6_CLI_PREFIX=/usr/lib/wine/wine64`. Бинарник из "linux"-архива — фактически Windows PE32+ (magic `MZ`), запускается под wine.

3. **UI селектор платформы** — `platform-selector.tsx`. 4 опции: Linux/x86_64 (default), Windows/x86_64, Linux/arm64, macOS/arm64. Persistence в `localStorage['ecov6.target_platform']`. Прокидывается через `target_os`/`target_arch` в WS payload → `state` → `make_setup_tools`.

4. **`_ecoos_pull` переписан под find→devkit-pull** — `_find_devkit(cli_path, cid)` парсит JSON от `eco-cli find -c CID`, находит DEVKIT fileId (MultiOS/universal), возвращает реальную version из marketplace. `pull -fid=<id>` скачивает **один** multi-platform пакет = SharedFiles/ + полное BuildFiles/{Linux,Windows}/{x86_64,amd64,x86}/{Static,Dynamic}Release/ дерево со всеми библиотеками.

5. **Нормализация input в `_ecoos_pull`** — `_normalize_cid` (strip non-hex, uppercase), `_normalize_version` (pad до N.N.N.N). LLM может передавать что угодно — `61C988E2-1B70-...` или `1.0.0` или `1.0` — нормализуется. Matching против `allowed_components` идёт по normalized CID.

### Что НЕ доделано (отложено)

- **Promt mental mismatch**: `nodes/setup.py:20-27` всё ещё говорит LLM «COPY VERBATIM, no dashes, no suffixes». Это **противоречит** тому что тул уже нормализует — провоцирует format-guessing loops. **Главная причина этого spec'а.**
- Промпты остальных 4 нод (planner, coder, builder, tester) не используют few-shot из реальных C-исходников и не объясняют CID-таксономию.

---

## 2. Research findings (Opus 4.7 + Codex кросс-валидация)

Оба агента анализировали `H:/ai-hse-diploma-agent/_eco_ai_repo/Eco.Toolchain/` — 8 параллельных проектов Eco-экосистемы. Кросс-валидация подтверждает:

- **3 пустых placeholder** (`ClearSet1`, `DatasetGen1`, `Trainer1` — только `.gitkeep`)
- **5 проектов** = чистые C/C++ SDK компоненты (`Engine1`, `Inference1`, `GGUF1`, `HDF5`, `ONNX1`)
- **В 0 проектах** нет: system prompts, LLM-агентов, StructuredTool, LangGraph, eco-cli wrappers, ReAct

**Но это не нулевой результат.** Сами C-исходники — canonical reference того, **что наши промпты должны учить LLM генерировать**. Это сильнее prompt-mining.

Полный отчёт codex: `H:/ai-hse-diploma-agent/_eco_ai_repo/Eco.Toolchain/agents-codex-prompt-analysis.md`.

### Главный системный инсайт

У одного компонента **8 форм идентификатора** (LLM их путает):

| Форма | Где живёт | Пример |
|---|---|---|
| **Marketplace CID** (32 UPPER hex) | для `ecoos_pull` | `6E5C5B7C979F40108F7CDC08EADFB777` |
| Hyphenated GUID (8-4-4-4-12) | display only | `6E5C5B7C-979F-4010-8F7C-DC08EADFB777` |
| **ecoPackage uguid** (32 lower hex) | в `ecoPackage.json` | `0000000000000000000000004d656d31` |
| C struct UGUID | в `Id*.h` headers | `{0x01, 0x10, {0x6E, 0x5C, ...}}` |
| Symbol suffix `_<LAST8HEX>` | в C-идентификаторах | `CEcoAIEngine1_EADFB777` |
| `IID_*` / `uguid(...)` | **INTERFACE** id, не component | `uguid(0x6E5C, ...)` в `.fodt` |
| Имя пакета | в plan, ecoPackage | `Eco.AI.Engine1` |
| Suffix `_DK_v.X.X.X.X` | folder только | `Eco.AI.Engine1_DK_v.1.0.1.2` |

### Source-of-truth ordering

1. Tool output (`ecoos_pull`, `list_components`)
2. Downloaded `SharedFiles/Id*.h` (CID_* макросы)
3. `ecoPackage.json`
4. `DesignFiles/*.fodt` — **IGNORE** для marketplace (только placeholders `n/a`)

### Эталонные файлы (gold reference)

1. `_eco_ai_repo/Eco.Toolchain/Eco.AI.Engine1/SourceFiles/CEcoAIEngine1Factory.c:285-321` — **gold few-shot** для Coder (vtable, factory global, version literal, ECO_DLL/ECO_LIB conditional).
2. `_eco_ai_repo/Eco.Toolchain/Eco.AI.Engine1/AssemblyFiles/Windows/MSVC_v140/Makefile` — entire Builder contract.
3. `_eco_ai_repo/Eco.Toolchain/Eco.AI.Engine1/DependenciesFiles/ecoPackage.json` — точный формат deps (2 JSON-массива в одном файле, не обёрнуты).
4. `_eco_ai_repo/Eco.Toolchain/Eco.AI.Engine1/README.md:33-49` — folder semantics canon.

### Реальные значения для embedding в промпты

Из `_eco_ai_repo/Eco.Toolchain/Eco.AI.Engine1/DependenciesFiles/ecoPackage.json:1-14` — **3 mandatory dependencies** в каждом компоненте:

```json
[
  { "uguid": "00000000000000000000000042757331", "name": "Eco.InterfaceBus1" },
  { "uguid": "0000000000000000000000004D656D31", "name": "Eco.MemoryManger1" },   // sic: Manger, not Manager
  { "uguid": "00000000000000000000000046534D31", "name": "Eco.FileSystemManagement1" }
]
```

Suffix-коды: `42757331=BuS1`, `4D656D31=MeM1`, `46534D31=FSM1`.

Из `CEcoAIEngine1Factory.c:307-321` — factory global:
```c
CEcoAIEngine1_EADFB777Factory g_x6E5C5B7C979F40108F7CDC08EADFB777Factory = {
    &g_x6E5C5B7C979F40108F7CDC08EADFB777FactoryVTbl,  // vtable: IID
    0,
    "EcoAIEngine1\0",
    "1.0.0.0\0",     // version: N.N.N.N null-terminated
    "PeerF\0"
};

#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr() { ... }
#elif ECO_LIB
IEcoComponentFactory* GetIEcoComponentFactoryPtr_6E5C5B7C979F40108F7CDC08EADFB777 = ...;
#endif
```

Из `Makefile` Builder gotchas:
- `TARGET=0` → `.dll` (`#define ECO_DLL`)
- `TARGET=1` → `.lib` (`#define ECO_LIB`)
- `ARCH=x64` → `ARCH_TARGET=amd64` (LLM путает!)
- `CONFIG_TARGET ∈ {StaticRelease, StaticDebug, DynamicRelease, DynamicDebug}`
- Output: `BuildFiles/<PLATFORM>/<ARCH_TARGET>/<CONFIG_TARGET>/<32HEX_CID>.{lib,dll}`
- `make -f Makefile TARGET={0|1} DEBUG={0|1} ARCH={x86|x64}`
- Mandatory `/I`: `../../../SharedFiles`, `../../../HeaderFiles` + 5 framework SharedFiles

Typos из реального кода (Tester должен искать буквально):
- `ERR_ECO_SUCCESES` (sic, `SUCCES**ES**`, не `SUCCESS`)
- `Eco.MemoryManger1` (sic, Manger без 'a')

---

## 3. Спецификация правок: 5 нод

Применять последовательно. После каждой ноды:
1. Дать пользователю просмотреть diff.
2. Подождать одобрения / запустить тест в UI.
3. Зафиксировать в `git commit` отдельным коммитом (per-node atomic).

### 3.1 Cross-cutting glossary (вставить в planner + setup)

Этот блок должен попасть в начало `PLANNER_SYSTEM_PROMPT` и `SETUP_SYSTEM_PROMPT`. Это единый источник истины — повторяется dosло во избежание расхождений.

```
=== Eco SDK identifier taxonomy ===

A single component has multiple ID forms — they are NOT interchangeable:

  Marketplace CID    : 32 UPPERCASE hex, no dashes  ← USE THIS for ecoos_pull
                       e.g. 6E5C5B7C979F40108F7CDC08EADFB777
  Hyphenated GUID    : 8-4-4-4-12 form              ← display/docs only
                       e.g. 6E5C5B7C-979F-4010-8F7C-DC08EADFB777
  ecoPackage uguid   : 32 lowercase hex             ← appears in deps JSON
                       e.g. 0000000000000000000000004d656d31
  C struct UGUID     : {0x01, 0x10, {0x6E, ...}}    ← header-internal only
  IID_* / uguid(...) : INTERFACE id, NOT component  ← never use as cid
  Package name       : Eco.AI.Engine1               ← stable, no version suffix
  Folder suffix      : _DK_v.1.0.1.2                ← NOT part of name

Mandatory dependencies for every component (always include in plan):
  - Eco.InterfaceBus1         uguid 42757331
  - Eco.MemoryManger1         uguid 4D656D31   (sic: Manger, not Manager)
  - Eco.FileSystemManagement1 uguid 46534D31

Source-of-truth priority (highest first):
  1. Tool output (ecoos_pull stdout, list_components results)
  2. Downloaded SharedFiles/Id*.h (CID_* macros)
  3. ecoPackage.json
  4. DesignFiles/*.fodt — IGNORE for marketplace metadata
     (these contain placeholder "n/a" fields and uguid(...) tokens
      that are interface IDs, not component CIDs)
```

### 3.2 Planner — `agent/v6/nodes/planner.py`

**Текущая проблема:** не объясняет CID-таксономию, не перечисляет 3 mandatory deps, не запрещает выдумывать версии из docs.

**Правки:**
1. Вставить **CID-glossary** (см. §3.1) сразу после первой строки промпта.
2. Добавить hard-rules секцию перед инструкцией `submit_plan`:

```
Plan-emission rules (FAIL the plan if violated):
  • components[].cid must be 32 UPPERCASE hex, no dashes, no suffixes.
  • components[].version must be N.N.N.N (4 dot-separated integers).
    If you don't see the exact version in tool output, DO NOT guess —
    leave it as the highest-confidence value you observed and let
    Setup discover the marketplace truth via ecoos_pull.
  • components[].name is the base package name (e.g. "Eco.AI.Engine1"),
    without _DK_v.* suffixes.
  • Every component cid MUST be traceable to a list_components observation
    or to an explicit user request — never derive from DesignFiles/*.fodt.
  • Always include the 3 mandatory framework deps (Eco.InterfaceBus1,
    Eco.MemoryManger1, Eco.FileSystemManagement1) in the components list.
```

### 3.3 Setup — `agent/v6/nodes/setup.py` (🔴 КРИТИЧЕСКИЙ)

**Текущая проблема:** строки 20-27 говорят «COPY VERBATIM, no dashes, no suffixes» — но тул уже **нормализует** все эти формы. LLM получает противоречивый сигнал → format-guessing loop.

**Полная замена** блока «1. Call `ecoos_pull` with its cid and version, COPYING THE VALUES VERBATIM ...» (от строки ~20 до закрытия пункта 1):

```
1. Call `ecoos_pull` with the cid and version from the plan. The tool will:
   • normalize dashes/whitespace/case in cid (any of these are accepted:
       61C988E21B7041378C5BDAFBB68A3FA0  ← canonical
       61C988E2-1B70-4137-8C5B-DAFBB68A3FA0  ← auto-stripped
       61c988e21b7041378c5bdafbb68a3fa0  ← auto-uppercased)
   • pad version to N.N.N.N if planner emitted 1.0 / 1.0.0
   • call `eco-cli find -c CID` to discover the marketplace's real version
   • pull the DEVKIT artifact — ONE call downloads SharedFiles/ headers +
     BuildFiles/{Linux,Windows}/{x86_64,amd64,x86}/{Static,Dynamic}Release/
     for ALL platforms (static + dynamic libs included)

   If ecoos_pull returns is_error=true:
   • READ the error message — it includes the allowed components list with
     correct canonical values. Use those EXACT values on the next call.
   • Do NOT mutate the cid format by yourself (no _DK_v1, no dashes, no
     truncation). The tool already canonicalises; manual guessing makes
     things worse, not better.

   The tool returns the absolute path of the package INNER root in
   `details.inner_root` (also embedded in `content`). The inner root is
   the directory that directly contains `SharedFiles/` and `BuildFiles/`.

   NEVER derive cid/version from DesignFiles/*.fodt placeholders, from
   uguid(...) tokens in spec docs, or from marketplace URLs in
   documentation. The source of truth is the plan + tool feedback.
```

**Также вставить CID-glossary** (см. §3.1) в начало промпта (до пункта 1).

### 3.4 Coder — `agent/v6/nodes/coder.py`

**Текущая проблема:** не объясняет конвенцию `_<LAST8HEX>` suffix, не различает SharedFiles/HeaderFiles/DesignFiles, не упоминает обязательную сигнатуру `EcoMain`.

**Добавить** в системный промпт после существующих инструкций:

```
=== Eco SDK component code conventions ===

Folder contract (from canonical Engine1/README.md):
  SharedFiles/       PUBLIC API headers (.h, .hpp) — read these for interfaces
  HeaderFiles/       PRIVATE impl headers — only when you need impl details
  SourceFiles/       .c implementation files — YOU write here
  UnitTestFiles/SourceFiles/  Test entry — YOU write here
  AssemblyFiles/<plat>/<toolchain>/Makefile  Build config — usually pre-existing
  DesignFiles/       .fodt spec docs — IGNORE for API, DO NOT read as reference
  BuildFiles/        Make OUTPUT — never author here, never include via -I

Internal symbol naming (CRITICAL, gold example from CEcoAIEngine1Factory.c):
  Every internal C symbol gets suffix _<LAST8HEX_OF_CID>.
    cid 6E5C5B7C979F40108F7CDC08EADFB777  →  suffix _EADFB777
    → struct CEcoAIEngine1_EADFB777
    → fn CEcoAIEngine1_EADFB777Factory_QueryInterface
    → global g_x<32HEX>Factory   (full CID in global name)

  vtable global uses IID (interface id, found in IEco<Name>.h):
    IEcoXxxVTbl g_x<32HEX_IID>VTbl = { fn_ptr_table };

  factory global uses CID (component id):
    CEco<Name>_<SUFFIX>Factory g_x<32HEX_CID>Factory = {
        &g_x<32HEX_IID>VTbl,    // vtable pointer
        0,                       // ref count
        "EcoComponentName\0",    // m_Name
        "1.0.0.0\0",             // m_Version — EXACTLY N.N.N.N, null-terminated
        "PeerF\0"                // m_Manufacturer
    };

  Conditional factory export:
    #ifdef ECO_DLL
    ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr() {
        return (IEcoComponentFactory*)&g_x<32HEX_CID>Factory;
    }
    #elif ECO_LIB
    IEcoComponentFactory* GetIEcoComponentFactoryPtr_<32HEX_CID> =
        (IEcoComponentFactory*)&g_x<32HEX_CID>Factory;
    #endif

Unit-test entry (REQUIRED in UnitTestFiles/SourceFiles/Eco<Name>.c):
  int16_t EcoMain(IEcoUnknown* pIUnk);

  Returns 0 (= ERR_ECO_SUCCESES, sic: SUCCESES with typo) on success.
  Non-zero return signals test failure.

Retry hygiene: when fixing a build/test failure, prefer minimal edits —
do NOT regenerate the project from scratch. Read the existing files first
to understand what's already there.
```

### 3.5 Builder — `agent/v6/nodes/builder.py`

**Текущая проблема:** generic build/run_make инструкции, не классифицирует ошибки, не упоминает ARCH→ARCH_TARGET gotcha.

**Добавить** в системный промпт после существующих инструкций:

```
=== Eco build system invariants ===

Make-flag matrix (from MSVC_v140/Makefile):
  TARGET=0 → produces .dll, defines ECO_DLL
  TARGET=1 → produces .lib, defines ECO_LIB
  DEBUG=0  → Release config
  DEBUG=1  → Debug config
  ARCH=x86 → ARCH_TARGET=x86
  ARCH=x64 → ARCH_TARGET=amd64   ← gotcha: output path uses "amd64" not "x64"

Output path: BuildFiles/<PLATFORM>/<ARCH_TARGET>/<CONFIG_TARGET>/<32HEX_CID>.{lib,dll}
  where CONFIG_TARGET ∈ {StaticRelease, StaticDebug, DynamicRelease, DynamicDebug}

Mandatory /I flags:
  ../../../SharedFiles            (own public headers)
  ../../../HeaderFiles            (own private headers)
  ../../../../Eco.InterfaceBus1/.../SharedFiles
  ../../../../Eco.MemoryManger1/.../SharedFiles    (sic: Manger)
  ... (5 framework SharedFiles total)

Build invocation:
  make -f Makefile    TARGET={0|1} DEBUG={0|1} ARCH={x86|x64}     # lib/dll
  make -f MakefileExe TARGET={0|1} DEBUG={0|1} ARCH={x86|x64}     # test exe

=== Failure classification (use these labels in report_build_fail) ===

  missing_header     #include not found in SharedFiles/ — check /I paths
                     or that Setup downloaded the dependency
  missing_lib        linker error, .lib/.a absent from
                     BuildFiles/<plat>/<arch>/Static*/ — Setup didn't pull
                     the DEVKIT for this platform
  symbol_mismatch    undefined symbol — usually wrong _<LAST8HEX> suffix,
                     factory global named with IID instead of CID, etc.
  generated_error    real bug in the generated .c source — needs Coder fix
  toolchain_error    vcvarsall/make/MSYS path issue — environment problem

Your `report_build_fail` must include:
  • failing command (exact argv)
  • first decisive error line
  • likely root cause label (one from the list above)
  • exact file/path the Coder should inspect next
```

### 3.6 Tester — `agent/v6/nodes/tester.py`

**Текущая проблема:** не делает preflight на acceptance criteria, не структурирует verdict, может пропустить тонкие фейлы.

**Добавить** в системный промпт:

```
=== Test execution contract ===

Entry point: every component's test exe calls
  int16_t EcoMain(IEcoUnknown* pIUnk);
  Returns 0 (= ERR_ECO_SUCCESES, sic — note typo) on success.
  Non-zero = failure.

Preflight on the plan's acceptance criteria:
  • If a criterion is ambiguous or unobservable from stdout/stderr/exit_code,
    state THAT before executing. Do not proceed to a vague "looks fine" verdict.
  • If criteria are missing entirely, fail the run with reason="no_criteria".

Your reason_md MUST follow this format verbatim (one entry per criterion):
  ```
  Command:    <full invocation>
  Exit code:  <int>
  Stdout:     <first 20 lines or summary, ≤500 chars>
  Stderr:     <first 20 lines or summary, ≤500 chars>

  Criterion 1: <text from plan>
    Verdict:    PASS | FAIL
    Evidence:   <quote from stdout/stderr or "exit_code==0">

  Criterion 2: ...
  ```

Verdict rules:
  • Pass the run ONLY when EVERY criterion has Verdict=PASS.
  • Partial success is FAIL with a precise delta in `reason_md`.
  • Crashes (non-zero exit, segfault, abort) are always FAIL regardless
    of stdout content.
```

---

## 4. Plan-of-attack для применения

Рекомендуемая последовательность (каждый шаг = атомарный коммит):

```
Step 1:  setup.py  — устраняет mental mismatch (наибольший impact)
         git commit -m "fix(v6/setup): align prompt with tool normalization"

Step 2:  planner.py — CID glossary + plan-emission rules
         git commit -m "feat(v6/planner): add CID taxonomy + emission rules"

Step 3:  coder.py — folder contract + few-shot из Engine1/Factory.c
         git commit -m "feat(v6/coder): teach _<LAST8HEX> suffix convention"

Step 4:  builder.py — error taxonomy + ARCH→ARCH_TARGET gotcha
         git commit -m "feat(v6/builder): classify failures + Make invariants"

Step 5:  tester.py — preflight + structured reason_md
         git commit -m "feat(v6/tester): structured verdict format"
```

После каждого шага:
1. Hot-reload api контейнера автоматический (watch on `agent/v6/nodes/*.py`).
2. Открыть UI http://localhost:3100, очистить session storage (DevTools → Application → `ecov6.thread_id` delete), отправить тестовый запрос «Собери калькулятор с pow и sqrt».
3. Наблюдать в чате что нода ведёт себя ожидаемо. **Особенно для setup** — должно сразу пуллить через find→devkit без format-guessing loops.

### Контрольные сценарии после Step 1+2 (минимально для запуска pipeline)

| Сценарий | Ожидание |
|---|---|
| Plan содержит все 4 компонента + 3 framework deps | Planner добавляет недостающие deps по hint |
| LLM передаёт `cid=61C988E2-1B70-...` (с дефисами) | Setup тула нормализует, find проходит, pull DEVKIT успешен |
| LLM передаёт `version=1.0.0` | Тула padding → `1.0.0.0`, find возвращает real `1.0.1.2` |
| После 4 pull → mark_setup_done | Pipeline переходит в Coding |

---

## 5. Технические факты (для подхвата контекста)

### Docker layout

```
H:/ai-hse-diploma-agent/Eco.Toolchain/Eco.AI.Assembly1/
├── docker-compose.yml          # 2 service: api, frontend
├── Dockerfile                   # api base — python:3.11-slim + wine64
├── .env                         # ECO_API_TOKEN + V6_CLI_PATH + V6_CLI_PREFIX
├── agent/v6/                    # backend ноды
│   ├── nodes/{planner,setup,coder,builder,tester,plan_gate,escalate}.py
│   ├── tools/{planner,setup,coder,builder,tester,common,sdk_layout}.py
│   ├── eco_agent.py             # EcoAgent ReAct loop с _stream_llm
│   ├── stream_events.py         # bridge EcoAgentEvent → custom WS event
│   ├── state.py                 # V6State + target_os/target_arch
│   └── graph.py                 # StateGraph wiring
├── backend/server.py            # FastAPI + /ws/v6/chat endpoint
└── frontend/                    # Next.js 14, App Router
    ├── components/chat/
    │   ├── chat-interface.tsx   # main UI
    │   ├── use-v6-socket.ts     # WS client + state
    │   ├── stream-message.tsx   # block renderer dispatch
    │   ├── thinking-block.tsx   # ← добавлен в этой сессии
    │   ├── tool-call-block.tsx
    │   ├── platform-selector.tsx # ← добавлен в этой сессии
    │   └── types.ts             # event/block discriminated unions
    └── app/globals.css          # keyframes thinking-pulse-kf, thinking-blink-kf
```

### Env vars (`.env`)

```
LLM_MODEL=moonshotai/kimi-k2.6
OPENAI_API_KEY=sk-or-v1-...                      # OpenRouter
OPENROUTER_URL=https://openrouter.ai/api/v1
ECO_API_TOKEN=eco-FwWuW8BYECSY...                # marketplace, в memory:eco-cli-token
V6_CLI_PATH=/opt/eco-linux/eco-cli
V6_CLI_PREFIX=/usr/lib/wine/wine64
V6_CLI_OS=Linux                                  # default, переопределяется UI selector
V6_CLI_ARCH=x86_64
WINEPREFIX=/tmp/wine
WINEDEBUG=-all
```

### URLs

- Frontend: http://localhost:3100
- Backend: http://localhost:8100
- WebSocket: `ws://localhost:8100/ws/v6/chat[?thread_id=<uuid>]`

### Commands

```bash
# поднять
cd "H:/ai-hse-diploma-agent/Eco.Toolchain/Eco.AI.Assembly1"
docker compose up -d

# логи
docker compose logs --tail=30 api
docker compose logs --tail=30 frontend

# проверить что hot-reload работает (mtime файла на хосте и в контейнере)
docker compose exec api ls -la /app/agent/v6/nodes/setup.py

# вызвать CLI напрямую (sanity check)
docker compose exec api /usr/lib/wine/wine64 /opt/eco-linux/eco-cli scan -d
docker compose exec api /usr/lib/wine/wine64 /opt/eco-linux/eco-cli find -c <CID>
```

---

## 6. Открытые вопросы (на будущее, не блокирует применение этого spec'а)

1. **Builder/Tester ноды на Linux** — eco-cli даёт DEVKIT с Linux .so/.a, но сам build/test через MSVC `cl.exe` в Linux контейнере не работает. Варианты: (a) добавить gcc/clang в Dockerfile + portable Makefile, (b) запустить api на Windows нативно, (c) Wine с MSVC. Пользователь выбирал «оставить sdk_root fallback» — но реально нужен build для full pipeline. Отдельная задача.

2. **Linux eco-cli** — архив `eco-cli-linux-1.0.05.zip` фактически содержит Windows PE32+ (magic `MZ`), не нативный ELF. Запускается под wine. Если разработчики дадут настоящий ELF — переключение в `.env` тривиально: `V6_CLI_PREFIX=` (пусто).

3. **`uguid(...)` в `.fodt`** — codex предупредил, но мы пока не учим LLM явно «не читай .fodt». В этом spec'е добавлено в CID glossary. После применения Step 2 проверить, не падает ли planner на чтении spec docs.

---

## 7. Готовая последовательность вызовов Edit (для машинного применения)

Если ты подхватываешь это в новой сессии и хочешь применить **всё сразу** (без чек-поинтов от пользователя), используй такую последовательность Edit-вызовов:

```
Read  agent/v6/nodes/setup.py      → найти SETUP_SYSTEM_PROMPT
Edit  agent/v6/nodes/setup.py      → заменить блок per §3.3 + добавить glossary
Bash  docker compose logs api      → подтвердить reload без ошибок

Read  agent/v6/nodes/planner.py    → найти PLANNER_SYSTEM_PROMPT
Edit  agent/v6/nodes/planner.py    → вставить glossary + emission rules per §3.2

Read  agent/v6/nodes/coder.py      → найти CODER_SYSTEM_PROMPT
Edit  agent/v6/nodes/coder.py      → append секцию per §3.4

Read  agent/v6/nodes/builder.py    → найти BUILDER_SYSTEM_PROMPT
Edit  agent/v6/nodes/builder.py    → append секцию per §3.5

Read  agent/v6/nodes/tester.py     → найти TESTER_SYSTEM_PROMPT
Edit  agent/v6/nodes/tester.py     → append секцию per §3.6
```

Каждый Edit-вызов должен использовать **полные, точные** блоки из §3.X выше. Не сокращать. Не парафразировать. Сохранить sic-typos (`Manger`, `SUCCESES`) — они нужны для matching против реального кода.

После всех 5 правок — попросить пользователя протестировать через UI и зафиксировать atomic-коммитами per ноду.

---

**Конец спеки.** Документ ~500 строк. Если что-то непонятно — спроси пользователя; не пытайся восстановить отсутствующий контекст самостоятельно.
