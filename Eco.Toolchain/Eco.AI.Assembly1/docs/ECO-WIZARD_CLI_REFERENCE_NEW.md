# Eco Wizard CLI - Reference

> **Migrating from 0.1.x text output:** the default text output now follows the
> PRD 7.10 contract (`Status:`/`Project:`/`Entry file:`/... instead of the old
> `✓ Project created:`/`✓ Workspace:` lines). Wrappers that parse default text
> should migrate to `--json`, which is the stable automation interface. The
> core library API `generateProject(input, options?)` still returns legacy
> `projectPath`/`workspacePath` fields for compatibility.

## Build

```bash
cd packages/cli-app
bun run build            # dist/eco-wizard (standalone binary)
bun test test/           # run the test suite
```

## Subcommands

| Command | Purpose |
|---|---|
| `new [options]` | Generate a new ACOM project |
| `validate <dir>` | Validate an existing project scaffold (rc 0 ok / 3 findings) |
| `version [--json]` | Version and machine-readable capabilities |
| `help` | Show help (also dispatched as a subcommand; positional arguments are rejected) |

## Machine-readable output contract

- `--json` (or `--format json`, also accepted as `-json` or `/json`) on every subcommand emits a **single JSON object** on stdout. Human-readable logs go to stderr in JSON mode. Human-readable text remains the default.
- On failure in JSON mode, stdout carries `{"error": "...", "code": "...", "hint": "...", "exit_code": n}`.
- Output is deterministic and locale-independent: sorted keys, UTF-8, no timestamps or ANSI, no interactive prompts.
- The full invocation is validated before any dispatch: `version --bogus` and `--help --bogus` are usage errors (exit 2), not silent successes. `--format` is the authoritative format flag (`--format text` overrides `--json`).

## Exit codes

| Code | Meaning | Examples |
|---|---|---|
| `0` | ok | generation, validation, dry-run, `--if-absent` first run, `--if-absent` re-run (`status: "reused"`) |
| `2` | usage error | unknown flag, missing value, invalid `--opt`/`--lang`/`--type`/`--target` value, malformed or mistyped `--from-json` spec, invalid dependency name/cid |
| `3` | not-found | `validate` findings, spec file missing, `ECO_FRAMEWORK` unset or path missing |
| `4` | network/transport | reserved (wizard performs no network I/O) |
| `5` | policy-denied | collision with `--if-exists fail`, unsupported type/language/option/target combination, refusing to overwrite a non-wizard directory |

## Flags for `new`

| Flag | Argument | Description |
|------|----------|-------------|
| `-o, --out` | `<dir>` | Output directory (default `.`); POSIX absolute paths preserved |
| `-n, --name` | `<name>` | Project name (default `NewProject`); no path separators |
| `-l, --lang` | `C\|CPP` | Language (default `C`) |
| `-t, --type` | `APP\|COM\|LIB\|ECOOS\|LINUX\|BOOT` | Project type (default `APP`); mapping below. `LIB`, `ECOOS`, `LINUX`, `BOOT` are policy-rejected with exit 5 (no complete scaffold) |
| `-e, --env [true\|false]` | optional | Use `$(ECO_FRAMEWORK)` paths (default: false); only the exact values `true`/`false` are accepted as arguments; requires `ECO_FRAMEWORK` to be an existing directory; `--from-env` is an accepted alias |
| `--opt` | `<csv>` | `pn, cp, ai, ao, co, ut, ts` |
| `--entry` | `<name>` | Base name for the generated entry file and identifiers |
| `--registrations` | `<csv>` | COM registration identifiers, stored in `config.json` |
| `--target` | `<os/arch/variant>` | Target triplet. Supported: `linux/{x64,aarch64,rv64}/gcc_v132`, `windows/{x64,x86}/{msvc_v140,gcc_v132}`, `ecoos/{x64,aarch64,rv64}/gcc_v132`. Other combinations are policy errors (exit 5) |
| `--no-design-docs` | - | Skip the `.fodt` design documents |
| `--if-absent` | - | Create only when the project dir is absent; exit 0 with `status: "reused"` on subsequent runs |
| `--if-exists` | `fail\|overwrite\|suffix` | Collision policy. Default: `suffix` in text mode, `fail` in `--json` mode. `overwrite` only replaces wizard-owned trees (a parseable `config.json` with `appType`) and keeps the old tree as a temporary sibling backup until the replacement is installed, restoring it on any failure |
| `--from-json` | `<spec.json>` | Read generation parameters from a JSON spec (CLI flags override spec keys; snake_case spec keys `dry_run`, `if_absent`, `keep_failed_output`, `if_exists`, `no_design_docs`, `design_docs` map to their canonical flags) |
| `--dry-run` | - | Plan only; writes nothing; returns the planned tree and resolved build command (suffix collision policy applied) |
| `--verify` | - | Requests the build dry-run explicitly; when `make` is unavailable a warning names the skipped verification (validation + `make -n` also run by default when `make` is available) |
| `--keep-failed-output` | - | Keep the temporary directory when generation fails |
| `--json` / `--format json` | - | Machine-readable JSON on stdout |
| `-v, --version`, `-h, --help` | - | Version / help |

All flags accept Unix (`-x`, `--x`) and Windows (`/x`) forms. Unknown `--*` tokens are hard errors (exit 2) — they are never interpreted as paths or silently ignored. Absolute POSIX values such as `/tmp/project` are preserved; a value position after a value-taking flag consumes the next token verbatim unless it is a dash-style flag, so `--out /json` sets the output to a directory named `/json`. Positional paths that collide with Windows flag aliases (e.g. a directory literally named `/json`) can be passed after the `--` terminator: `eco-wizard validate -- /json`.

## JSON manifest (schema_version 1)

`new --json` emits:

```json
{
  "schema_version": 1,
  "status": "created",
  "wizard_version": "0.1.0",
  "project_name": "Eco.Calc",
  "project_type": "APP",
  "language": "C",
  "output_dir": "/abs/out",
  "project_dir": "/abs/out/Eco.Calc",
  "entry_name": "EcoCalc",
  "normalized_name": "EcoCalc",
  "collision": { "detected": false, "policy": "fail", "action": "created" },
  "entry_file": "SourceFiles/EcoCalc.c",
  "build_subdir": "AssemblyFiles/Linux/gcc_v132",
  "build_file": "AssemblyFiles/Linux/gcc_v132/MakefileExe",
  "build_command": "make -C '/abs/out/Eco.Calc/AssemblyFiles/Linux/gcc_v132' -f MakefileExe ARCH=x64",
  "build_command_argv": ["make", "-C", "/abs/out/Eco.Calc/AssemblyFiles/Linux/gcc_v132", "-f", "MakefileExe", "ARCH=x64"],
  "config_file": "config.json",
  "environment_path": null,
  "workspace_files": ["AssemblyFiles/Linux/gcc_v132/EcoCalc.code-workspace"],
  "files": { "created": ["..."], "existing": [], "overwritten": [] },
  "validation": { "files_exist": true, "build_dry_run": true, "warnings": [] },
  "atomic": true,
  "warnings": []
}
```

- `entry_file`, `build_subdir`, `build_file`, and `files.created` are relative to `project_dir`; `project_dir` and `output_dir` are absolute.
- `status` is `created`, or `reused` (with `--if-absent` when the project already exists); `dry-run` emits `status: "dry-run"` and `planned: true` without touching the filesystem.
- `build_command` is shell-quoted; `build_command_argv` carries the same command as an argv array for machine consumers. Both pin `ARCH=<target arch>` so the Makefile's architecture selection matches the requested target.
- `environment_path` is the resolved canonical `ECO_FRAMEWORK` path.
- Generation happens in a temporary sibling directory and is renamed into place after validation. On filesystems where rename is unavailable, the wizard copies only when the destination is still absent and rolls the destination back on copy failure (`atomic: false`). `overwrite` requires a wizard-owned `config.json` (`appType` marker), keeps the previous tree as a hidden sibling backup until the replacement succeeds, and restores it on any failure.
- Scaffolds are validated before success: required directories, entry file, build file, workspace files (parsed as JSONC - comments and trailing commas are tolerated), every source referenced by generated Makefiles, project-local `#include` references from generated sources, and dependency link libraries derived from the configured target (`.a` for GNU toolchains, `.lib` for MSVC; `x64` maps to the `amd64` artifact directory). Dependency names and CIDs are restricted to identifier-safe characters.
- `make -n` runs with a sanitized environment (only PATH/HOME/temp/Locale variables are inherited) and a 30 s timeout; a timed-out dry run is a validation failure, not a skip.

## `validate <dir>`

Reads `<dir>/config.json` and checks required directories, the entry file, the build file for the configured target, workspace files, Makefile source references, and `ECO_FRAMEWORK` for `pathType: "Environment"`. Exit `0` when only warnings remain, `3` on any error finding.

```json
{
  "schema_version": 1,
  "dir": "/abs/project",
  "ok": false,
  "findings": [
    { "severity": "error", "code": "MISSING_ENTRY", "message": "Entry source file not found: SourceFiles/EcoCalc.c", "path": "SourceFiles/EcoCalc.c" }
  ]
}
```

Finding codes: `DIR_NOT_FOUND`, `MISSING_CONFIG`, `UNSUPPORTED_TYPE`, `MISSING_DIR`, `MISSING_ENTRY`, `MISSING_BUILD_FILE`, `MISSING_WORKSPACE` (warning), `INVALID_WORKSPACE`, `MAKEFILE_REF_MISSING`, `INCLUDE_REF_MISSING`, `LINK_LIB_MISSING`, `ENV_NOT_SET`, `ENV_PATH_MISSING`.

## `version --json`

```json
{
  "name": "eco-wizard",
  "version": "0.1.0",
  "capabilities": ["flag.dry-run", "json-output", "manifest-v1", "new", "validate", "..."],
  "exit_codes": { "ok": 0, "usage": 2, "not-found": 3, "network": 4, "policy-denied": 5 }
}
```

Wrappers should feature-detect via `capabilities` instead of hard-failing on older binaries.

## `--from-json` spec

A JSON object whose keys mirror the long flags:

```json
{
  "out": "./out",
  "name": "Eco.Spec",
  "type": "COM",
  "lang": "C",
  "opt": "pn,ut",
  "env": false,
  "entry": "EcoSpecEntry",
  "registrations": ["IList"],
  "target": "linux/x64/gcc_v132",
  "design_docs": true,
  "if_exists": "fail",
  "verify": true,
  "dependencies": { "com_list": [{ "name": "Eco.List1", "cid": "GUID" }], "b_relative": false }
}
```

Unknown keys are usage errors (exit 2), as are mistyped values (strings for `name`/`out`/..., booleans for `dry_run`/`if_absent`/..., string arrays for `registrations`). A missing file is exit 3. CLI flags override spec keys. Dependency `name`/`cid` values are restricted to identifier-safe characters because they are interpolated into generated Makefiles.

## Type / language capability matrix

| `--type` value | Internal `appType` | Languages | Options | Notes |
|---|---|---|---|---|
| `APP` | `Application` | C | all except `ut` | Entry `SourceFiles/<name>.c`, `MakefileExe` per toolchain dir |
| `COM` | `Component` | C, CPP | all | Interfaces, factory, connection points with `cp`, `Makefile` per toolchain dir. VS project files (`.sln`/`.vcxproj`) are emitted for C only; CPP builds via the makefiles |
| `LIB` | `Library` | - | - | Rejected before generation (exit 5): templates produce no sources or build files |
| `ECOOS` | `Microkernel` | - | - | Rejected before generation (exit 5): templates produce no sources or build files |
| `LINUX` | `Kernel` | - | - | Rejected before generation (exit 5): templates produce no sources or build files |
| `BOOT` | `Bootloader` | - | - | Rejected before generation (exit 5): templates produce no sources or build files |

The full type list remains valid as *input* (`--type LIB` parses cleanly); it is the capability matrix that refuses to generate an incomplete scaffold, distinguishing "typo'd value" (usage, exit 2) from "known type the templates cannot build" (policy, exit 5).

## Options (`--opt`)

| Code | Name | Description |
|------|------|-------------|
| `pn` | postfix namespace | Add namespace postfix to identifiers |
| `cp` | connection points | Generate COM connection points support |
| `ai` | aggregation inner | Add inner aggregation support |
| `ao` | aggregation outer | Add outer aggregation support |
| `co` | containment outer | Add outer containment support |
| `ut` | unit test project | Generate unit test project structure |
| `ts` | thread safe | Generate thread-safe code |

## Examples

```bash
eco-wizard new -o ./out -n Eco.List1 -t COM -l C --opt pn,cp,ut
eco-wizard new --out /tmp/output --name Eco.Calc --type APP --lang C --format json --if-exists fail --verify
eco-wizard new -o ./out -n Eco.Reg -t COM --registrations IList,IEnum --no-design-docs
eco-wizard new -o ./out -n Eco.T -t APP --entry EcoMain
eco-wizard new --from-json spec.json --json
eco-wizard new -o ./out -n Eco.P -t APP --dry-run
eco-wizard validate ./out/Eco.List1
eco-wizard version --json
```

## Notes

- Text output remains the default; existing prompts and wrappers keep working.
- The wizard never prompts, never accesses the network, and never emits timestamps in JSON mode.
- `config.json` in generated projects records `language`, `entry`, `registrations`, `target`, `design_docs`, `template_version` (2), and `wizard_version` alongside the pre-existing fields.
