=== LANGUAGE PROFILE: C (EcoOS ACOM — C89 / MISRA) ===

Authoritative contract: `docs/C-lang_coder_for_ACOM_rules.md`. The rules below
are the distilled, MUST-FOLLOW subset. Load them in full for every C task.

# 1. C89 / MISRA DISCIPLINE (hard constraints)
- Standard is **strict C89 (ANSI X3.159-1989)**. Forbidden: mid-block variable
  declarations, `//` comments, `stdbool.h`, `long long`, mixed decl+code.
- All variables declared at the top of the block.
- UTF-8 **with BOM** (Codepage 65001) for every `.c`/`.h`.
- `#pragma pack` ONLY for structures serialized to file/network/strict binary.
  Never for internal component objects (preserve natural alignment).
- Follow MISRA C guidelines; prefer simplest, most maintainable design.

# 2. TYPES — NEVER use raw C primitives
- Forbidden: `int`, `char`, `long`, `void*`, `float`/`double` unless the
  interface contract specifies them.
- Use EcoOS types resolved from `Eco.Core1/SharedFiles`: `int16_t`, `int32_t`,
  `char_t`, `byte_t`, `voidptr_t`, `UGUID`, plus `ECOCALLMETHOD` calling conv.
- **No `malloc`/`calloc`/`free`.** Allocate only via `IEcoMemoryAllocator1`.
  - *Inside a component implementation*: reach it through the object's `m_pIMem`
    field: `pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, size);`
  - *Inside an application (`EcoMain` glue)*: obtain it by **`QueryInterface`**,
    never by calling a method on the manager. `IEcoMemoryManager1` exposes only
    `Init` / `get_Status` / `get_UsedBlocks` — it has **no `GetAllocator`**.
    Get the manager via the bus
    (`QueryComponent(&CID_EcoMemoryManager1, 0, &IID_IEcoMemoryManager1, …)`),
    then
    `pIMemMgr->pVTbl->QueryInterface(pIMemMgr, &IID_IEcoMemoryAllocator1, (void**)&pIAlloc)`.
    On constrained targets the bus memory extension `IEcoInterfaceBus1MemExt`
    may be used instead; either way, acquisition is always via `QueryInterface`.

# 3. ACOM SHAPES (naming)
- Interfaces: `IEco` prefix, PascalCase, major version digit (e.g. `IEcoMathC89`).
- Event/sink interfaces: append `Events` / `Sink`.
- Server impl: `CEco` + component name + trailing 8 uppercase CID chars.
- Every vtable method + lifecycle fn uses `ECOCALLMETHOD`.
- First method arg is a typed self pointer named `me`.
- Methods return `int16_t` status; outputs are `/* out */` pointers.
- Ref-count manually via `IEcoUnknown::QueryInterface/AddRef/Release`.
  Release exactly once per successful `QueryInterface`/`CreateObject`. When
  `m_cRef` reaches zero, release owned resources through the component delete
  path and the allocator (`m_pIMem->pVTbl->Free`), then free the object.
- Marketplace C-API method spellings are exact: `Eco.Math.C89` methods are
  lowercase — `pow`, `sqrt`, `sin`, `cos`.

# 4. UGUID RULE (exact byte format — single authority)
- Layout: `{0x01, Length, {Data}}`. Preamble is always `0x01`.
- Length byte: 32-bit=`0x04`, 64-bit=`0x08`, 128-bit=`0x10`, 256-bit=`0x20`.
- A comment is REQUIRED before every IID/CID: `/* Name IID = {GUID} */`.
- `CID` = 32 uppercase hex, NO dashes. `IID_*` are interface ids, never CIDs.

# 5. NAMING MACROS (when templating)
- `[GUID_CID_TARGET]` = `GetIEcoComponentFactoryPtr_<FULL 32-hex CID>`.
- `[GUID_CID_NAMESPACE]` = last 8 hex chars of the CID.

# 6. FILE MAPPING (exact paths)
- `SharedFiles/Eco[Name].idl`, `SharedFiles/IEco[Name].h`, `SharedFiles/IdEco[Name].h`
- `SourceFiles/CEco[Name].c` + `HeaderFiles/CEco[Name].h`
- `SourceFiles/CEco[Name]Factory.c` + `HeaderFiles/CEco[Name]Factory.h`
- App entry: `SourceFiles/EcoMain.c` defining
  `int16_t EcoMain(IEcoUnknown* pIUnk)` (application projects only; statically
  linked with the platform `Eco.System1` library).
- Unit tests: `UnitTestFiles/SourceFiles/Eco[Name].c`.
- Build: `AssemblyFiles/<Platform>/<Toolchain>/Makefile` (+ `MakefileExe`).

# 7. MANDATORY DEV-KIT BOUNDARY (strict API surface)
- Resolve interfaces ONLY from the project `DependenciesFiles/` or the
  `ECO_FRAMEWORK` path, and ONLY from a component's `SharedFiles/` subfolder
  (the public API). NEVER read/use another component's `HeaderFiles/` or
  `SourceFiles/`.
- The required framework stack (`Eco.Core1` base + minimum system components,
  `Eco.System1` for applications) is declared once in the STATIC ACOM DOMAIN
  block above — encode it exactly as written there.
- Link the platform `Eco.System1` **system library** for applications — default
  `StaticRelease` (see the ACOM domain block for the two variants). It has no
  CID and is never registered on the bus.
- **Eco.System1 statically links AND INTERNALLY REFERENCES the Interface Bus
  factory** (`GetIEcoComponentFactoryPtr_<bus CID>`). Even when the
  application code never calls the bus directly, the bus `.a` MUST be
  on the link line — the unikernel's microkernel calls
  `pIBus->QueryComponent(...)` during startup, before `EcoMain` runs.
  The C89 prior-art calculator below demonstrates this: line 1 of
  "Register statically-linked components" registers the bus factory
  by calling `RegisterComponent(pIBus, &CID_EcoInterfaceBus1, …)` —
  the bus symbol must be linked for the linker to resolve that call.
  Bug history: the `ses-6acd93e6` (sin/cos) plan asserted "Interface
  Bus has no separate .a" and the link failed with `undefined
  reference to GetIEcoComponentFactoryPtr_00000000000000000000000042757331`.
  The fix was to add `lib…42757331.a` to the link line.
- **ACOM app code uses ONLY Eco.Framework components and glue code
  (or new components you author).** No `<math.h>`, no glibc, no
  standard-library calls. The math component's *object code*
  internally references libm (`cos`, `sin`, `pow`, etc.) and the
  linker needs `-lm`; that libm dependency is invisible to your
  source. Use `-std=gnu89` (NOT strict `-std=c89`) because the
  EcoOS devkit headers legitimately use C++-style `//` comments and
  some have their own (empty) `#define HUGE_VAL` that conflicts with
  ISO C90 — GNU89 accepts the vendor headers while keeping your
  source C89-style. Reference: `make -pn` on a working `MakefileExe`
  shows the exact `-lm` link line.

# 7a. TARGET TRIPLE (mandatory plan field)
- The architect's seed always carries a `=== Target triple ===` block with
  three user-selected values: `OS` (Linux/Windows/Mac/iOS/Android/EcoOS),
  `arch` (x86_64/x86/arm64/arm64-v8a/rv64gcv/mips/mips64/avr), and
  `build_variant` (StaticRelease | DynamicRelease). The plan must:
  (a) copy those three values into a `## Target triple` section verbatim;
  (b) include the **literal `.a` path** for every linked component and for
  the `Eco.System1` unikernel; (c) include the **exact
  `GID_IEcoSystem_<arch>` UGUID** the app must `QueryInterface` on
  `pIUnk` (read it once from `Eco.Core1/SharedFiles/IEcoSystem1.h` and
  quote the line number in the plan). Never `glob('**/BuildFiles/**/*.a')`
  across the whole marketplace — that wastes a tool call and truncates.
- If the user did not provide a triple, the plan must FAIL the closed-plan
  gate and call `fail` with a clear message rather than guess.

# 7b. ASCII-ONLY IN SOURCE LITERALS
- All `.c` / `.h` / `Makefile` content is 7-bit ASCII. UTF-8 BOM is required
  for the file header (per §1) but every other byte must be ASCII. No
  Unicode in `printf` / `scanf` format strings, in identifier names, or in
  test-expected output. Plan-time narrative MAY use Unicode (e.g.
  `F≈98.60`); the coder must rewrite it as ASCII (`F~98.60` or
  `F=98.60`) before pasting it into a string literal.

# 8. HEADER / DOC DISCIPLINE
- Every file starts with the standard file-header comment block (author,
  UTF-8 BOM encoding, summary, description, reference).
- Every function and vtable method has a function-header comment.
- Every interface method validates `me` and output pointers vs `NULL` first:
  `if (me == NULL || ppv == NULL) return ERR_ECO_POINTER;`
- Return `ERR_ECO_OK`, `ERR_ECO_POINTER`, `ERR_ECO_NOINTERFACE` as fitting.

# 9. GENERATION PROTOCOL
- Prefer `eco-wizard` for project/component/app scaffolding when available.
- When hand-authoring from a template, follow: (1) directory tree, (2) bold
  per-file path, (3) mandatory file header, (4) function docs.
- Process template conditionals: `[!if ADD_CONNECTION_POINTS]`,
  `[!if ADD_AGGREGATION_INNER/OUTER]`, `[!if ADD_CONTAINMENT_OUTER]`.

# 10. REFERENCE — ACOM application bootstrap (prior art)

Embedded from `eco_framework/Lessons/Lesson04/Eco.DemoCalculator1` so the
canonical System → Bus → Component → Release flow is always in context. The
allocator is acquired by `QueryInterface` — **never** by calling
`GetAllocator` on `IEcoMemoryManager1` (that method does not exist).

```c
/*
 * <character encoding> Cyrillic (UTF-8 with signature) - Codepage 65001 </character encoding>
 * <summary> Reference: ACOM application entry (EcoMain) </summary>
 * <description> Canonical bootstrap for a console calculator using
 *   Eco.Math.C89 (pow/sqrt) and Eco.StdIO.C89. Memory is obtained via
 *   QueryInterface, NOT via GetAllocator. </description>
 * <author> Copyright (c) 2026 [AUTHOR]. All rights reserved. </author>
 */

#include "IEcoSystem1.h"
#include "IEcoInterfaceBus1.h"
#include "IEcoMemoryManager1.h"
#include "IEcoMemoryAllocator1.h"
#include "IEcoMathC89.h"
#include "IEcoStdIOC89.h"
#include "IdEcoInterfaceBus1.h"
#include "IdEcoMemoryManager1.h"
#include "IdEcoMathC89.h"
#include "IdEcoStdIOC89.h"

int16_t EcoMain(IEcoUnknown* pIUnk) {
    int16_t result = -1;
    IEcoSystem1* pISys = 0;
    IEcoInterfaceBus1* pIBus = 0;
    IEcoMemoryManager1* pIMemMgr = 0;
    IEcoMemoryAllocator1* pIAlloc = 0;
    IEcoMathC89* pIMath = 0;
    IEcoStdIOC89* pIStdIO = 0;
    double x = 0.0, y = 0.0, res_pow = 0.0, res_sqrt = 0.0;

    if (pIUnk == 0) {
        return ERR_ECO_POINTER;
    }
    /* 1. System -> Bus (IEcoSystem1 comes from Eco.Core1, via pIUnk) */
    result = pIUnk->pVTbl->QueryInterface(pIUnk, &GID_IEcoSystem, (void**)&pISys);
    if (result != ERR_ECO_OK || pISys == 0) {
        goto Release;
    }
    result = pISys->pVTbl->QueryInterface(pISys, &IID_IEcoInterfaceBus1, (void**)&pIBus);
    if (result != ERR_ECO_OK || pIBus == 0) {
        goto Release;
    }
    /* 2. Register statically-linked components (factory symbols, no CID for Eco.System1) */
    pIBus->pVTbl->RegisterComponent(pIBus, &CID_EcoMemoryManager1,
        (IEcoUnknown*)GetIEcoComponentFactoryPtr_0000000000000000000000004D656D31);
    pIBus->pVTbl->RegisterComponent(pIBus, &CID_EcoMathC89,
        (IEcoUnknown*)GetIEcoComponentFactoryPtr_61C988E21B7041378C5BDAFBB68A3FA0);
    pIBus->pVTbl->RegisterComponent(pIBus, &CID_EcoStdIOC89,
        (IEcoUnknown*)GetIEcoComponentFactoryPtr_00000000000000000000000053494F31);
    /* 3. Component -> acquire interfaces */
    pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoMemoryManager1, 0,
        &IID_IEcoMemoryManager1, (void**)&pIMemMgr);
    /* Allocator via QueryInterface — NOT GetAllocator */
    pIMemMgr->pVTbl->QueryInterface(pIMemMgr, &IID_IEcoMemoryAllocator1, (void**)&pIAlloc);
    pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoMathC89, 0,
        &IID_IEcoMathC89, (void**)&pIMath);
    pIBus->pVTbl->QueryComponent(pIBus, &CID_EcoStdIOC89, 0,
        &IID_IEcoStdIOC89, (void**)&pIStdIO);
    /* 4. Use (pow/sqrt) */
    pIStdIO->pVTbl->scanf(pIStdIO, "%lf %lf", &x, &y);
    res_pow = pIMath->pVTbl->pow(pIMath, x, y);
    res_sqrt = pIMath->pVTbl->sqrt(pIMath, x);
    pIStdIO->pVTbl->printf(pIStdIO, "pow=%lf sqrt=%lf\n", res_pow, res_sqrt);

Release:
    /* Release in reverse order, one per successful QueryInterface/QueryComponent */
    if (pIStdIO != 0) { pIStdIO->pVTbl->Release(pIStdIO); }
    if (pIMath != 0) { pIMath->pVTbl->Release(pIMath); }
    if (pIAlloc != 0) { pIAlloc->pVTbl->Release(pIAlloc); }
    if (pIMemMgr != 0) { pIMemMgr->pVTbl->Release(pIMemMgr); }
    if (pIBus != 0) { pIBus->pVTbl->Release(pIBus); }
    if (pISys != 0) { pISys->pVTbl->Release(pISys); }
    return result;
}
```

On constrained targets the bus memory extension `IEcoInterfaceBus1MemExt`
(`QueryInterface` on the bus) can supply the allocator instead; the acquisition
rule is identical — **always `QueryInterface`, never `GetAllocator`**.
