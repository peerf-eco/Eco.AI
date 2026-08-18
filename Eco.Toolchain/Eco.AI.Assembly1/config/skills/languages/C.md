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
- **No `malloc`/`calloc`/`free`.** Allocate only via `IEcoMemoryAllocator1`
  reached through the component's `m_pIMem` field:
  `pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, size);`

# 3. ACOM SHAPES (naming)
- Interfaces: `IEco` prefix, PascalCase, major version digit (e.g. `IEcoMathC89`).
- Event/sink interfaces: append `Events` / `Sink`.
- Server impl: `CEco` + component name + trailing 8 uppercase CID chars.
- Every vtable method + lifecycle fn uses `ECOCALLMETHOD`.
- First method arg is a typed self pointer named `me`.
- Methods return `int16_t` status; outputs are `/* out */` pointers.
- Ref-count manually via `IEcoUnknown::QueryInterface/AddRef/Release`.
  Release exactly once per successful `QueryInterface`/`CreateObject`.

# 4. UGUID RULE (exact byte format)
- Layout: `{0x01, Length, {Data}}`. Preamble is always `0x01`.
- Length byte: 32-bit=`0x04`, 64-bit=`0x08`, 128-bit=`0x10`, 256-bit=`0x20`.
- A comment is REQUIRED before every IID/CID: `/* Name IID = {GUID} */`.
- `CID` = 32 uppercase hex, NO dashes. `IID_*` are interface ids, never CIDs.

# 5. NAMING MACROS (when templating)
- `[GUID_CID_TARGET]` = `GetIEcoComponentFactoryPtr_<FULL 32-hex CID>`.
- `[GUID_CID_NAMESPACE]` = last 8 hex chars of the CID.
- Static-link factory symbol: `GetIEcoComponentFactoryPtr_<UPPER_HEX_CID>`,
  registered as `(IEcoUnknown*)GetIEcoComponentFactoryPtr_<UPPER_HEX_CID>`.

# 6. FILE MAPPING (exact paths)
- `SharedFiles/Eco[Name].idl`, `SharedFiles/IEco[Name].h`, `SharedFiles/IdEco[Name].h`
- `SourceFiles/CEco[Name].c` + `HeaderFiles/CEco[Name].h`
- `SourceFiles/CEco[Name]Factory.c` + `HeaderFiles/CEco[Name]Factory.h`
- App entry: `SourceFiles/EcoMain.c`. Unit tests: `UnitTestFiles/SourceFiles/Eco[Name].c`.
- Build: `AssemblyFiles/<Platform>/<Toolchain>/Makefile` (+ `MakefileExe`).

# 7. MANDATORY DEV-KIT BOUNDARY (strict API surface)
- Resolve interfaces ONLY from the project `DependenciesFiles/` or the
  `ECO_FRAMEWORK` / `ECO_FRAMEWORK_PATH` env, and ONLY from a component's
  `SharedFiles/` subfolder (the public API).
- NEVER read/use another component's `HeaderFiles/` or `SourceFiles/`.
- `Eco.Core1/SharedFiles` is the MANDATORY base of EVERY project.
- Minimum required stack for any buildable component/app:
  `Eco.Core1` + `Eco.InterfaceBus1` + `Eco.MemoryManager1`
  (+ `Eco.FileSystemManagement1` when file I/O is used; `Eco.System1` for the
  `EcoMain` entry point). Do NOT add these by rote omission either — they are
  required, not optional.

# 8. HEADER / DOC DISCIPLINE
- Every file starts with the standard file-header comment block (author,
  UTF-8 BOM encoding, summary, description, reference).
- Every function and vtable method has a function-header comment.
- Every interface method validates `me` and output pointers vs `NULL` first:
  `if (me == NULL || ppv == NULL) return ERR_ECO_POINTER;`
- Return `ERR_ECO_SUCCESES`, `ERR_ECO_POINTER`, `ERR_ECO_NOINTERFACE` as fitting.

# 9. GENERATION PROTOCOL
- Prefer `eco-wizard` for project/component/app scaffolding when available.
- When hand-authoring from a template, follow: (1) directory tree, (2) bold
  per-file path, (3) mandatory file header, (4) function docs.
- Process template conditionals: `[!if ADD_CONNECTION_POINTS]`,
  `[!if ADD_AGGREGATION_INNER/OUTER]`, `[!if ADD_CONTAINMENT_OUTER]`.
