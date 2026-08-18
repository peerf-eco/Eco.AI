=== LANGUAGE PROFILE: C ===

Use the EcoOS C89 + ACOM conventions loaded via the `language: C` skill
(authoritative: `docs/C-lang_coder_for_ACOM_rules.md`). Key non-negotiables
the plan/code MUST encode:

- Strict C89 (no mid-block decls, no `//`, no `stdbool`); UTF-8 BOM; MISRA.
- EcoOS types only (`int16_t`/`char_t`/`byte_t`/`voidptr_t`); never `int`/`char`/`long`/`void*`.
- Allocation ONLY via `IEcoMemoryAllocator1` (`m_pIMem`); never `malloc`/`free`.
- UGUID byte format `{0x01, Len, {Data}}` with required `/* Name IID = {GUID} */` comment.
- `Eco.Core1` mandatory for EVERY project; minimum stack =
  `Eco.Core1` + `Eco.InterfaceBus1` + `Eco.MemoryManager1`
  (+ `Eco.FileSystemManagement1` for file I/O; `Eco.System1` for `EcoMain`).
  Include ONLY `SharedFiles/` of dependencies — never their `HeaderFiles`/`SourceFiles`.
- Preserve exact factory symbol `GetIEcoComponentFactoryPtr_<32-hex CID>`
  and exact interface/CID/IID/vtable spellings.
