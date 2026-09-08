# Eco-Wizard Improvements PRD

Status: proposed · Author: harness analysis session 2026-09-08 · Target: `eco-wizard` CLI and its coder-agent integration

## 1. Summary

The Eco-Wizard CLI currently reports successful project generation even when the generated project is not buildable or when the reported paths do not match the filesystem. This creates avoidable coder-agent exploration, wrong-path build attempts, recovery calls, and unreliable project handoffs.

This PRD defines a safer CLI contract for both humans and AI agents:

- generation must be deterministic and validated before success is reported;
- paths and toolchain names must describe the actual filesystem;
- the CLI must expose an authoritative, versioned machine-readable manifest;
- invalid arguments and unsupported combinations must fail explicitly;
- collisions and partial generation must never be hidden from the caller.

The highest-priority deliverables are scaffold validation, canonical path handling, and a JSON manifest containing the exact entry file and build directory.

## 2. Evidence

The following scenarios were executed against `/home/nick/Dist/eco-wizard/eco-wizard`.

| Scenario | Observed result | Impact |
|---|---|---|
| C APP with `--out /tmp/...` | The CLI printed and created a relative `--tmp/...` path beneath the working directory instead of preserving `/tmp/...`. | The coder can write into the wrong project tree. |
| C APP generated build | `make -n` failed with `No rule to make target '../../../SourceFiles/x64/EcoHead.o'`. The generated source was `SourceFiles/EcoCalcProbe.c`. | The first build fails before compilation and triggers recovery turns. |
| Reported toolchain path | Output reported `gcc_11_4_0`; the generated tree contained `gcc_v132`. | The coder cannot safely use the reported build path. |
| C COM with `pn,cp,ut,ts` | `config.json` recorded the options, but the Linux output had no Linux Makefile. | A successful response can produce an incomplete build target. |
| C/C++ LIB | The output contained README/config/design files but no source or build scaffold. | The CLI reports success for a practically unusable project. |
| Repeated APP generation | A second run silently created `Eco.CalcProbe1`. | The caller may continue against an unexpected project name. |
| `--json` | The option was ignored and normal text output was emitted. | Agents cannot depend on a structured contract. |
| Unknown flag | `--bogus value` was ignored and generation succeeded. | Typos silently change the requested operation. |
| Invalid option | `--opt nope` succeeded and all option flags remained false. | Requested features can disappear without an error. |
| Missing option value | `--out --name ...` treated `--name` as a directory and created `--name/NewProject`. | Malformed invocations create misleading output. |
| Unsupported language | `Python` was rejected, but the error mentioned `OBJC` although help documents only `C|CPP`. | CLI documentation and validation disagree. |

## 3. Goals

- Reduce coder-agent exploration and recovery calls after scaffolding.
- Make one successful wizard response sufficient to identify the generated tree, entry file, build directory, and build command.
- Fail before writing or clearly mark output when a requested project cannot be generated completely.
- Preserve cross-platform behavior for Windows-style and POSIX-style paths.
- Make repeated invocations safe and explicit.
- Give the harness a stable schema that can evolve without prompt rewrites.
- Keep human-readable output useful while separating it from machine-readable output.

## 4. Non-goals

- Redesigning the ACOM project templates beyond fixes required for generation/build integrity.
- Replacing the existing build systems with a new build tool.
- Adding network access or package installation to the wizard.
- Making the coder infer missing project metadata from generated source files.
- Silently migrating old projects without an explicit compatibility policy.

## 5. Issue Rating

Rated by production impact and frequency, with coder-agent turn reduction as the tie-breaker. Effort: S = one parser/template area; M = several CLI and validation modules; L = cross-platform generation and manifest contract.

| ID | Issue | Priority | Impact | Effort | Phase |
|---|---|---|---|---|---|
| WZ-1 | Generated scaffold can report success while its Makefile references missing files | P0 | Critical | L | 1 |
| WZ-2 | POSIX absolute output paths lose their leading slash | P0 | Critical | M | 1 |
| WZ-3 | Reported workspace/toolchain path differs from the generated filesystem | P0 | High | M | 1 |
| WZ-4 | No authoritative machine-readable output contract | P0 | High | M | 2 |
| WZ-5 | COM and LIB output can be incomplete while returning success | P0 | High | L | 1 |
| WZ-6 | Repeated generation silently changes the project name with a numeric suffix | P1 | High | S | 1 |
| WZ-7 | Unknown flags and invalid options are silently ignored | P1 | High | S | 1 |
| WZ-8 | Missing option arguments are interpreted as values | P1 | High | S | 1 |
| WZ-9 | Language/type/option documentation does not match validation | P1 | Medium | S | 1 |
| WZ-10 | Environment mode does not clearly validate `ECO_FRAMEWORK` | P1 | Medium | M | 2 |
| WZ-11 | Coder must infer normalized names and generated file relationships | P1 | Medium | M | 2 |
| WZ-12 | No dry-run or post-generation verification mode | P2 | Medium | M | 2 |
| WZ-13 | Human output mixes presentation with data needed by automation | P2 | Medium | S | 2 |
| WZ-14 | Generated output lacks an inventory of created, existing, and overwritten files | P2 | Medium | M | 3 |

## 6. Users and Use Cases

### 6.1 Coder agent

The coder invokes the wizard once and must immediately know:

- the canonical project directory;
- the exact entry source file;
- the exact build subdirectory;
- the build file and command;
- the generated files and warnings;
- whether the requested project was created, reused, renamed, or only partially generated.

The coder must not need `glob`, `list_dir`, or exploratory `read` calls to reconstruct this information.

### 6.2 Harness integration

The harness invokes the wizard as a subprocess and consumes its exit code and output. It must be able to:

- reject malformed output;
- distinguish a successful validated scaffold from a partial scaffold;
- persist the manifest in the session trace;
- pass `entry_file` and `build_subdir` directly to the coder;
- display useful warnings to the user without parsing decorative text.

### 6.3 Human developer

The human user needs readable output, predictable collision behavior, and a clear error when the requested type, language, environment, or option is unsupported.

## 7. Functional Requirements

### 7.1 Strict argument parsing

The parser MUST:

- reject unknown flags;
- reject a flag that requires a value when the next token is absent or another flag;
- reject invalid project types and languages;
- reject unknown `--opt` values;
- reject unexpected positional arguments;
- return exit code `2` for usage errors;
- print the offending argument and a valid-value list;
- keep Windows-style aliases without confusing them with POSIX absolute path values.

Examples:

```text
Error: --out requires a directory value.
Error: unknown option --bogus. Use --help for valid options.
Error: unknown --opt value 'nope'. Valid values: pn, cp, ai, ao, co, ut, ts.
```

### 7.2 Canonical path handling

The CLI MUST:

- preserve POSIX absolute paths such as `/tmp/project`;
- support Windows drive paths and UNC paths on Windows;
- resolve the final project directory to an absolute canonical path;
- use the same resolved path for generation, validation, output, and manifest;
- never strip a leading `/` from a value passed to `--out`;
- normalize path separators only in presentation fields, not on disk.

### 7.3 Collision policy

The CLI MUST expose an explicit policy:

```text
--if-exists fail       # recommended default for agents
--if-exists overwrite
--if-exists suffix
```

The manifest MUST report:

- requested project path;
- actual project path;
- whether a collision was detected;
- the selected collision action;
- overwritten files, if any.

The default agent mode SHOULD be `fail` to prevent an unexpected `Eco.Name1` project from being mistaken for `Eco.Name`.

### 7.4 Atomic generation

Generation SHOULD occur in a temporary sibling directory. The wizard MUST:

1. resolve and validate all arguments;
2. render the project into a temporary directory;
3. validate the generated tree;
4. run the configured build dry-run;
5. atomically rename the temporary directory into the requested destination;
6. remove the temporary directory on failure, unless `--keep-failed-output` is explicitly supplied.

If atomic replacement is not available on a target filesystem, the manifest MUST mark the generation as non-atomic.

### 7.5 Scaffold validation

After rendering, the wizard MUST validate:

- required directories for the selected project type;
- required source and header files;
- the entry-point source file;
- all files referenced by generated build scripts;
- all reported workspace files;
- all configured dependency paths;
- normalized project and target names;
- option effects recorded in `config.json`.

The wizard MUST return a nonzero exit code when validation fails. A text success line MUST NOT be printed for a partial scaffold.

### 7.6 Build dry-run

The CLI SHOULD support:

```text
eco-wizard new ... --verify
eco-wizard new ... --dry-run
```

`--dry-run` MUST render no files and return the planned tree and resolved build command. `--verify` MAY generate files, then validate the tree and run a build-system dry-run without compiling.

The result MUST identify missing files and unresolved variables such as `ECO_FRAMEWORK`, `ARCH`, `PLATFORM_TARGET`, or toolchain paths.

### 7.7 Type and language capability matrix

The CLI MUST maintain one authoritative support matrix for:

- project type;
- language;
- operating system;
- architecture;
- toolchain;
- supported options;
- generated build files.

Help output, validation errors, template selection, and the JSON manifest MUST use the same matrix. Unsupported combinations MUST fail before generation.

If `OBJC` is supported, it MUST be documented and included in the help output. If it is not supported, the error message MUST not mention it.

### 7.8 Environment mode

When `--env` is selected, the CLI MUST:

- define whether the flag is presence-only or accepts `true|false`;
- validate that `ECO_FRAMEWORK` is set when required;
- validate that the resolved framework path exists;
- report the resolved environment path in the manifest;
- fail clearly when the environment path is unavailable.

The reference documentation and help output MUST use the same boolean syntax.

### 7.9 Machine-readable manifest

The CLI MUST support:

```text
--format text
--format json
```

The JSON response MUST be written to stdout without decorative prefixes. Human-readable logs MUST go to stderr when JSON mode is selected.

Suggested schema:

```json
{
  "schema_version": 1,
  "status": "created",
  "wizard_version": "0.1.0",
  "project_name": "Eco.Calc",
  "project_type": "APP",
  "language": "C",
  "output_dir": "/absolute/output",
  "project_dir": "/absolute/output/Eco.Calc",
  "collision": {
    "detected": false,
    "policy": "fail",
    "action": "created"
  },
  "entry_file": "SourceFiles/EcoCalc.c",
  "build_subdir": "AssemblyFiles/Linux/gcc_v132",
  "build_file": "AssemblyFiles/Linux/gcc_v132/MakefileExe",
  "workspace_files": [
    "AssemblyFiles/Linux/gcc_v132/EcoCalc.code-workspace"
  ],
  "config_file": "config.json",
  "files": {
    "created": [],
    "existing": [],
    "overwritten": []
  },
  "validation": {
    "files_exist": true,
    "build_dry_run": true,
    "warnings": []
  },
  "warnings": []
}
```

The manifest MUST use paths that are relative to `project_dir` for project contents and absolute paths for top-level locations.

### 7.10 Human-readable output

Text output MUST include:

- status;
- actual canonical project path;
- entry file;
- build subdirectory;
- build file;
- collision action;
- validation result;
- warnings and suggested next actions.

Example:

```text
Status: created
Project: /tmp/output/Eco.Calc
Entry file: SourceFiles/EcoCalc.c
Build directory: AssemblyFiles/Linux/gcc_v132
Build file: AssemblyFiles/Linux/gcc_v132/MakefileExe
Validation: passed
Collision: none
```

## 8. Agent Integration Contract

The harness SHOULD invoke the wizard with:

```text
eco-wizard new \
  --out <project_dir> \
  --name <project_name> \
  --type APP \
  --lang C \
  --format json \
  --if-exists fail \
  --verify
```

The harness MUST:

- fail the coder handoff if the wizard exits nonzero;
- fail the coder handoff if the JSON manifest is invalid or `status` is not `created`/`reused`;
- pass the manifest’s `entry_file` and `build_subdir` verbatim to the coder;
- include manifest warnings in the coder seed only when they are actionable;
- avoid re-listing the generated tree after a validated manifest is received;
- retain the complete manifest in the session trace.

The coder prompt MUST treat the manifest as authoritative and MUST NOT reconstruct paths from the project name.

## 9. Delivery Phases

### Phase 1 - Safety and correctness

- Fix absolute path handling.
- Add strict argument validation.
- Add collision policy.
- Reconcile actual toolchain/build directory names.
- Add scaffold file-reference validation.
- Make incomplete project types fail explicitly.
- Add regression tests for APP, COM, LIB, POSIX paths, collisions, and malformed arguments.

### Phase 2 - Agent contract

- Add versioned JSON manifest.
- Include exact entry file, build directory, build file, workspace, and warnings.
- Add `--verify` and `--dry-run`.
- Update the harness wizard wrapper and coder prompt to consume the manifest.
- Add manifest fixtures to the harness tests.

### Phase 3 - Reproducibility and diagnostics

- Add atomic generation.
- Add created/existing/overwritten file inventory.
- Add resolved environment/toolchain metadata.
- Add deterministic name normalization fields.
- Add stable error codes and machine-readable diagnostics.

### Phase 4 - Documentation and compatibility

- Align `docs/eco-wizard-reference.md` with the implemented support matrix.
- Document JSON schema versioning.
- Document collision and environment policies.
- Add migration guidance for callers that parse current text output.

## 10. Acceptance Criteria

- [ ] A POSIX absolute `--out` remains absolute in both filesystem and output.
- [ ] A Windows absolute path remains valid on Windows.
- [ ] Unknown flags, invalid options, and missing values exit with code `2`.
- [ ] Re-running into an existing path follows the selected collision policy.
- [ ] A generated APP passes the build dry-run before success is reported.
- [ ] Every Makefile-referenced source exists in the generated tree.
- [ ] The reported workspace path exists and matches the filesystem.
- [ ] COM and LIB support is either complete for the selected target or rejected before generation.
- [ ] `--format json` emits valid JSON only on stdout.
- [ ] The manifest contains exact `project_dir`, `entry_file`, `build_subdir`, and `build_file` values.
- [ ] The manifest reports warnings, collision action, and validation results.
- [ ] Coder-agent integration completes scaffolding without a follow-up `glob` or `list_dir` call for generated paths.
- [ ] Regression tests cover all observed failures listed in Section 2.

## 11. Test Matrix

| Test | Expected result |
|---|---|
| APP/C/Linux/relative output | Complete validated scaffold and manifest |
| APP/C/Linux/POSIX absolute output | Same canonical path in filesystem, text, and JSON |
| COM/C/Linux | Complete Linux build scaffold or explicit unsupported error |
| LIB/C/Linux | Complete library scaffold or explicit unsupported error |
| LIB/CPP/`--env` | Environment path validated and reported |
| Existing project with `--if-exists fail` | Exit code `3`, no files changed |
| Existing project with `--if-exists suffix` | New path reported explicitly in manifest |
| Existing project with `--if-exists overwrite` | Overwritten files listed in manifest |
| Unknown flag | Exit code `2`, valid option guidance |
| Missing option value | Exit code `2`, no project created |
| Unknown `--opt` value | Exit code `2`, valid option list |
| `--dry-run` | No files written, complete planned manifest emitted |
| `--verify` with broken template | Nonzero exit and missing-file diagnostics |
| JSON output redirected to parser | Parses without stripping prefixes or emoji |

## 12. Risks and Decisions

- **Template compatibility:** Fixing generated Makefiles may affect existing projects. Preserve a template version in `config.json` and test old projects separately.
- **Collision defaults:** Agent callers should default to `fail`; interactive human callers may prefer `suffix`.
- **Build verification cost:** `make -n` is cheap compared with an agent recovery loop and should be enabled by default for supported build systems.
- **Manifest evolution:** Every breaking schema change requires a new `schema_version`; additive fields are preferred.
- **Partial output recovery:** Keep failed output only when explicitly requested, otherwise remove temporary generation directories.

## 13. Implementation Checklist

- [ ] Add strict parser tests and stable exit codes.
- [ ] Fix canonical path resolution on POSIX and Windows.
- [ ] Implement collision policy.
- [ ] Add template/tree/build-reference validation.
- [ ] Reconcile toolchain naming and workspace reporting.
- [ ] Define the supported type/language/environment matrix.
- [ ] Implement `--format json` with schema version `1`.
- [ ] Implement `--dry-run` and `--verify`.
- [ ] Update the harness wizard wrapper.
- [ ] Update coder prompt to consume manifest fields verbatim.
- [ ] Update `docs/eco-wizard-reference.md`.
- [ ] Run the full CLI and harness regression suites.
