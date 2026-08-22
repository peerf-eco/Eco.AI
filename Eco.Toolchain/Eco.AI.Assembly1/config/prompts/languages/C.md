=== LANGUAGE PROFILE: C ===

The full C89 + MISRA / ACOM rules are injected once per run from the
`config/skills/languages/C.md` language skill (authoritative contract:
`docs/C-lang_coder_for_ACOM_rules.md`). Do not duplicate them here —
follow the skill section of this system prompt as the binding rules.

Mode-specific reminders only:

- Plans and code MUST encode the skill's hard constraints: strict C89,
  EcoOS types only, allocation via `IEcoMemoryAllocator1`, exact UGUID /
  factory-symbol spellings, `SharedFiles/`-only dev-kit boundary.
- Minimum stack: `Eco.Core1` + `Eco.InterfaceBus1` + `Eco.MemoryManager1`
  (+ `Eco.FileSystemManagement1` for file I/O; `Eco.System1` when the
  target is an application with an `EcoMain` entry point).
