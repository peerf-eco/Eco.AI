# PRD: eco-cli improvements for AI-coder workflows and RAG pipelines

| | |
|---|---|
| **Status** | Draft for review |
| **Date** | 2026-09-09 |
| **Author** | Eco.AI.Toolchain harness team |
| **Consumers** | eco-cli team (JVM/native), Eco.AI harness, RAG pipeline, marketplace UI |
| **Related** | `bin/SKILL.md`, `docs/RAG_SETUP.md`, `docs/ID_NAMING.md`, `scripts/fetch_marketplace.py`, `eco_harness/agent/internal/tools/eco_cli.py`, `eco_harness/agent/internal/tools/profile_cache.py`, debug evidence `/tmp/kilo/eco_mkt_debug/README_findings.md` |

---

## 1. Background

`eco-cli` is the only machine interface to the EcoOS Marketplace. Beyond the
human developer, it now has two machine consumers:

1. **The ACOM AI-coding harness** — the architect agent discovers components
   via RAG (`search_marketplace`), reads contract cards, and pulls DEVKITs
   through a raw passthrough tool (`eco_harness/agent/internal/tools/eco_cli.py`,
   whitelist: `find`, `pull`, `help`, `version`), parsing the CLI's raw stdout
   JSON itself.
2. **The RAG ingestion pipeline** — `scripts/fetch_marketplace.py` walks the
   full catalog (31 products), resolves each profile and downloads the latest
   artefact into `marketplace_cache/`, which is then chunked/embedded into
   `marketplace_index.sqlite` (see `docs/RAG_SETUP.md`).

Today both consumers must wrap the CLI in defensive glue: ANSI stripping,
banner sniffing, retry heuristics, `ecoPackage.json` scraping and truncated-
output parsing. This PRD specifies the CLI changes that remove that glue.

## 2. Evidence base (verified 2026-09-09, repro in `/tmp/kilo/eco_mkt_debug/`)

| # | Finding | Repro |
|---|---------|-------|
| E1 | Transient AppSync failure (`Connection timed out` to `appsync-api.eu-central-1`) exits **rc=0**, prints the GraphQL error **and** `No components found matching '<name>'.` on **stdout** — indistinguishable from a genuine miss | user run 2026-09-06, `Eco.InterfaceBus1` |
| E2 | Diagnostics (GraphQL client log lines, banners) go to **stdout**, not stderr, even without `-e` | same |
| E3 | `find -p` returns **8 of 31** published products; no pagination flags exist | `find_all_published.out` |
| E4 | `find -p` emits **concatenated pretty-printed JSON objects**, not a JSON array; `find -n` emits a single object — two different framings for one verb | same |
| E5 | `lastVersion` is `" "` (broken) in every profile | all profiles |
| E6 | Pull destination = **process cwd** always ("The file directory is: <cwd>"); no `--dest` flag; `ECO_FRAMEWORK` and pre-existing `ecoPackage.json` in cwd do not change it | `projA/` experiments |
| E7 | Extraction folder = DEVKIT's **inner** component name, not the marketplace product name (`EcoOS.Unikernel` ships `Eco.System1_DK_*.zip` → extracts as `Eco.System1/`); the mapping is only discoverable via `files[0].locationPath` in the cwd's `ecoPackage.json` | `projA/ecoPackage.json` |
| E8 | Single-file artefacts are not unpacked: `Eco.Wizard` pulls a bare `.vsix` into `Eco.Wizard/`; `contentType` values in the wild: `DEVKIT`, `DYNAMICLIB`, `EXECUTABLE`, `PACKAGE` | `pull_wizard_c/` |
| E9 | Every product (incl. kernel/application types) exposes `uguid`/`cid`; `pull -c` works for all; `pull -i <internal-uuid>` works equivalently | Unikernel + Wizard pulls |
| E10 | Field-name casing drift inside `versions[].files[]`: `contentType`, `fileId` (camelCase) vs `Architecture`, `OS` (title case) | all profiles |
| E11 | `bin/SKILL.md` drift: documents `find -u` as "search by name" (`-u` is actually an alias of `-c/--uguid` per `find --help`); `-n` and `-fid` are undocumented; exit-code table (1/3 on errors) contradicts observed rc=0 on failures | `find --help` vs SKILL.md |

Consequence in this repo: `profile_cache.py` exists *only because* there is
no cheap name→(cid, version, fileId) lookup (the architect would have to dump
the whole catalog through a truncated 8 KiB tool result); and
`scripts/fetch_marketplace.py` carries ~100 lines of banner/retry/rename
workarounds.

## 3. Problem statement

eco-cli's output contract is optimized for an interactive human at a TTY.
For machine consumers it is hostile in three dimensions:

- **Reliability**: rc=0 lies (E1); diagnostics pollute stdout (E2).
- **Discoverability**: incomplete catalog (E3), no pagination, broken
  `lastVersion` (E5), no product-type field, no dependency-closure command —
  the AI coder must manually walk `dependencies[]` across N profiles to
  build the minimum stack (Eco.Core1 + Eco.InterfaceBus1 +
  Eco.MemoryManager1 [+ FS]) required by the architect role.
- **Ergonomics**: cwd-only pull destination (E6), undocumented inner-name
  extraction (E7), inconsistent JSON framing (E4) and field casing (E10),
  stale documentation (E11).

## 4. Goals / Non-goals

**Goals**
- G1: every eco-cli invocation machine-decidable: parseable stdout, honest rc, structured errors with retry hints.
- G2: complete, paginated, machine-readable catalog access in ≤ 1 call per page.
- G3: one-call dependency closure for a component or an `ecoPackage.json`.
- G4: deterministic pull with explicit destination and a machine-readable receipt.
- G5: one-command RAG corpus export (profiles + IDL, NDJSON).
- G6: documentation parity (SKILL.md becomes generated from the CLI, not hand-written).

**Non-goals**
- Changing the marketplace backend data model (CID/uguid semantics, version model).
- Replacing `search_marketplace` / RAG retrieval in the harness.
- GUI/UI features of the marketplace web console.

## 5. Personas & use cases

| Persona | Story |
|---|---|
| **AI coder (architect/coder agents)** | "Find the component that provides X, get its (cid, version, fileId), resolve its full dependency closure, pull all of it into my project dir — in as few tool calls as possible, never fooled by rc=0." |
| **RAG indexer** (`fetch_marketplace.py` → `build_marketplace_index.py`) | "Enumerate ALL published products with types and descriptions; fetch latest artefact (or specific file) into a cache dir; get a per-item receipt I can write to `_fetch_summary.json` without scraping `ecoPackage.json`." |
| **Human developer** | Same commands, human-readable output by default; `--json` opt-in. |
| **Release/CI** | `install -f -y` reproducibly rebuilds an environment from a committed `ecoPackage.json`; exit code reflects truth. |

## 6. Requirements

Priorities: **P0** = blocks machine consumption today; **P1** = major
convenience/efficiency win; **P2** = hygiene.

### R1 — stdout purity and `--output json` (P0)

- All diagnostics (banners, progress, GraphQL log lines, colour escapes) go to
  **stderr**. stdout carries **only** the payload.
- Global `--output=json|text` (default `text`; `json` forced automatically when
  stdout is not a TTY, overridable with `--output=text`).
- ANSI escapes never emitted when not a TTY.
- *Acceptance:* `eco find -n Eco.Math.C89 --output=json 2>/dev/null | jq .name`
  succeeds with no stripping logic on the caller side.

### R2 — structured result envelope (P0)

Every command in `--output=json` wraps the payload:

```json
{
  "schemaVersion": 1,
  "command": "find",
  "ok": true,
  "error": null,
  "data": { }
}
```

Errors populate:

```json
{
  "error": {
    "code": "TRANSIENT_NETWORK",
    "message": "GraphQL client exception: Connection timed out: …appsync…:443",
    "retryable": true,
    "retryAfterMs": 2000
  }
}
```

Stable machine codes (initial set): `NOT_FOUND`, `TRANSIENT_NETWORK`,
`AUTH_FAILED`, `AUTH_EXPIRED`, `VALIDATION`, `PLATFORM_MISMATCH`,
`SERVER_ERROR`, `RATE_LIMITED`.

### R3 — exit-code discipline (P0)

- rc=0 **only** when the operation verifiably succeeded (data received /
  files written and confirmed).
- `TRANSIENT_NETWORK` → rc=1 + `error.retryable=true`; `NOT_FOUND` → rc=3
  (matches the existing SKILL.md table); auth → rc=2. No rc=0-with-error paths.
- *Acceptance:* air-gapped/sandboxed run of `eco find -n Eco.Core1` exits
  non-zero with `TRANSIENT_NETWORK`, never rc=0.

### R4 — complete catalog with pagination and product type (P0)

- `find -p` must return **all** published products (today 8/31, E3) with
  `--limit`/`--offset` (or `--cursor` + `nextToken` echo) for the AppSync
  backend.
- Output is a **single JSON array** in `--output=json` (one framing per verb;
  E4), sorted by name, each record carrying a `productType` field
  (`component` | `kernel` | `application` | `tool` | … — the marketplace UI's
  entity type; see Open Questions).
- Fix `lastVersion` (E5) to be the real max `versions[].date` version, or drop
  the field in favour of computed `latestVersion`.
- *Acceptance:* `eco find -p --output=json | jq '.data | length'` ≥ 31 and
  includes `Eco.Wizard`, `eco-cli`, `Eco.Stack1`.

### R5 — profile consistency (P1)

- Uniform camelCase in `versions[].files[]`: `contentType`, `fileId`, `os`,
  `architecture` (E10). Keep old keys one release with a deprecation note.
- `remoteS3Key` **is** the sha256 — expose it also as `sha256` alias (the
  value already appears as `sha256` in `ecoPackage.json`).
- Add `extractsAs` per file where derivable (DEVKIT zip prefix, e.g.
  `Eco.System1` for the Unikernel) so callers don't discover E7 empirically.
- `find -n` semantics documented and implemented: exact match, case-insensitive;
  multiple matches → JSON array (never concatenated objects, E4).

### R6 — pull: explicit destination + machine receipt (P0)

- New flag `--dest <dir>` (and `-d <dir>` value form documented): extraction
  root, independent of process cwd. Keep cwd fallback for compatibility.
- In `--output=json`, pull returns a receipt:

```json
{
  "data": {
    "name": "EcoOS.Unikernel",
    "cid": "00000000000000000000000000000100",
    "internalId": "9c9b3445-63d8-40de-a226-0475e1637a4e",
    "version": "1.0.1.2",
    "fileId": "58bdc5310c93",
    "contentType": "DEVKIT",
    "sha256": "58bdc5310c93…",
    "extractedPath": "/abs/dest/Eco.System1",
    "extractedAs": "Eco.System1",
    "fileCount": 30,
    "ecoPackage": "/abs/dest/ecoPackage.json"
  }
}
```

- rc≠0 if `fileCount == 0` (no silent no-op pulls; kills the DOWNLOAD-EMPTY
  class of bugs).
- *Acceptance:* the receipt's `extractedPath` is exactly where files land,
  regardless of cwd and `ECO_FRAMEWORK`.

### R7 — `eco resolve`: dependency closure (P1)

One call answering "what do I need to build with this?":

```
eco resolve -c <CID> [-v <ver>] [--os <os>] [-a <arch>] [--output=json]
eco resolve -n <name> …            # name convenience
eco resolve --package ecoPackage.json   # validate/refresh an existing set
```

Returns the transitive closure over `dependencies[]` from profiles, plus the
platform-mandatory minimum stack (Eco.Core1, Eco.InterfaceBus1,
Eco.MemoryManager1; Eco.FileSystemManagement1 when file I/O appears), each
node with `{name, cid, resolvedVersion, devkitFileId, depth, requiredBy[]}`,
flagged `missing:true` when a dep has no resolvable version. This replaces
the manual closure walk the architect currently performs across
`find -c` profiles (see architect role prompt: "resolve every dependency …
MANDATORY minimum stack").

### R8 — non-interactive batch install (P1)

- `eco install -y` (assume-yes), `--continue-on-error`, and in JSON mode a
  per-component receipt array + summary `{ok, failed, skipped}` — the JSON
  counterpart of `scripts/fetch_marketplace.py`'s `_fetch_summary.json`.
- `install` must honour `--dest` like `pull`.

### R9 — `eco export`: RAG corpus in one command (P1)

```
eco export catalog [--output-format=ndjson] [--with-idl] [--out <file>]
```

One NDJSON record per published product: profile fields (name, cid, internal
id, productType, description, all versions with per-file
`{fileId, contentType, sha256, size, os, architecture}`), optionally inline
`idl[]` content. This is exactly what `fetch_marketplace.py` assembles today
via 31 × `find -n` + `_profiles/` snapshots — replacing E3's 8-of-31 dump and
the profile-cache workaround (`profile_cache.py` reads pre-fetched snapshots
only because this command doesn't exist).

### R10 — batch name lookup (P2)

`find -n A -n B -n C --output=json` (repeatable flag) → array of profiles +
`notFound: []` per name. Removes the sequential loop in
`fetch_marketplace.py` and gives agents a single-call bulk fetch.

### R11 — auth ergonomics (P2)

- Uniform token handling (`ECO_API_TOKEN` / `-t`) on **all** subcommands;
  never echo the token in any output.
- Distinct `AUTH_FAILED` vs `AUTH_EXPIRED` codes; `-s/--session` precedence
  documented (SKILL.md today says both "token used by default" and shows
  `-s` override — make it normative and tested).

### R12 — documentation parity (P2)

- `--help` works on every subcommand (`pull --help` currently errors:
  `Unknown option: '--help'`).
- Regenerate `SKILL.md` from the CLI's own option model each release (it
  currently documents `-u` as name search, omits `-n`/`-fid`, and its exit-code
  table is contradicted by E1).
- Document `pull` flag semantics: `-d` bare vs `-d <path>` (the harness passes
  `-d $ECO_FRAMEWORK` with a value; SKILL.md shows a bare flag).

## 7. Proposed surface (summary)

| Change | Type | Priority |
|---|---|---|
| `--output json` global + stdout/stderr split | flag | P0 |
| Result envelope + stable error codes | contract | P0 |
| rc truthfulness (no rc=0 on failure) | behaviour | P0 |
| `find -p` complete + pagination + `productType` | fix/flag | P0 |
| `pull --dest` + JSON receipt + rc≠0 on empty | flag | P0 |
| `pull -i <id>` for non-Component products documented | docs | P1 |
| `eco resolve` (closure, min-stack) | new command | P1 |
| `install -y --continue-on-error --dest` | flags | P1 |
| `eco export catalog` NDJSON (+IDL) | new command | P1 |
| `find -n` repeatable batch | flag | P2 |
| `extractsAs` + camelCase file fields | schema | P1 |
| SKILL.md regeneration, `pull --help` | docs | P2 |

## 8. Rollout

- **Phase 0 (P0 fixes)**: rc honesty, stderr split, catalog completeness,
  `pull --dest` + receipt. No new commands; existing parsers keep working
  (stdout payload is a strict subset of today's output).
- **Phase 1**: `resolve`, `export`, `install` flags, schema normalization.
- **Phase 2**: batch `find -n`, SKILL.md generation, deprecation of
  concatenated-JSON framing.

Compatibility rule: text mode output never changes for a released subcommand;
new capabilities ship behind `--output=json` and new flags only.

## 9. Impact on this repository (expected, after adoption)

- `scripts/fetch_marketplace.py`: banner-stripping/retry/`ecoPackage.json`
  workarounds replaced by `--output=json`, `pull --dest` + receipt;
  `_fetch_summary.json` becomes the receipts array verbatim.
- `eco_harness/agent/internal/tools/eco_cli.py`: whitelist gains `resolve`,
  `export`; the "you parse the JSON yourself" description is replaced by the
  envelope contract; truncation pressure drops (receipts are small).
- `eco_harness/agent/internal/tools/profile_cache.py`: the name→(cid,
  version, fileId) snapshot workaround can be retired in favour of
  `resolve -n` / `export` once R7/R9 ship (cache stays as offline fallback).
- `docs/RAG_SETUP.md`: `fetch` stage simplifies; catalog completeness no
  longer depends on the hard-coded 31-name list (R4/R9).

## 10. Acceptance criteria (conformance suite)

A conformance script (proposed: `scripts/eco_cli_conformance.py`, runnable in
CI against any eco-cli build) asserts, using only public CLI surface:

1. `find -n Eco.Core1 --output=json` → envelope, `data.name == "Eco.Core1"`, stderr may be non-empty, stdout parses standalone.
2. `find -n Definitely.Not.Here` → rc=3, `error.code=NOT_FOUND`.
3. With network blocked: `find -n Eco.Core1` → rc=1, `error.code=TRANSIENT_NETWORK`, `retryable=true`.
4. `find -p --output=json --limit 10 --offset 0` → 10 records + cursor; walking cursors yields ≥ 31 products incl. `Eco.Wizard` with `productType != component`.
5. `pull -c <Unikernel-cid> -v 1.0.1.2 -fid 58bdc5310c93 --dest <tmp> --output=json` → receipt with `extractedAs=Eco.System1`, `fileCount=30`, `extractedPath` under `<tmp>` even when cwd ≠ `<tmp>`.
6. `pull` of a `contentType=PACKAGE` artefact (Eco.Wizard 0.1.0.0) → receipt, `fileCount=1`, no DEVKIT requirement.
7. `resolve -n Eco.List1 --output=json` → closure includes Eco.InterfaceBus1 + Eco.MemoryManager1 + Eco.Core1; every node has `devkitFileId`.
8. `export catalog --with-idl --output-format=ndjson` → line count ≥ products, every line has `cid`, `versions[]`, and non-empty `descriptionShort`.
9. No output line anywhere contains the API token.
10. `pull --help` exits 0 on every subcommand.

## 11. Open questions

1. **Product type source of truth** — the UI distinguishes Component /
   Kernel / Application / Tool; profiles today carry no `type` field. Can the
   AppSync record expose it, or must it be derived (DEVKIT ⇒ component,
   PACKAGE/EXECUTABLE-only ⇒ application/tool)?
2. **Pagination support** in the AppSync query backing `find -p` — does the
   backend already return a cursor the CLI drops?
3. **CID stability** — are synthetic CIDs (e.g. `0000…0100` for the
   Unikernel) guaranteed stable across versions? `resolve` output depends on it.
4. **Rate limits** for token auth (the RAG pipeline bursts 31 × (find + pull));
   documented limits would shape `retryAfterMs`.
5. **Inner-name derivation** — is `extractsAs` always the DEVKIT zip prefix,
   or are there exceptions (e.g. versioned inner names)?
6. Should `eco find` gain tag/keyword search (SKILL.md mentions "Tags"; no
   flag exists in `--help`)?

## 12. Success metrics

- `fetch_marketplace.py` workaround code (ANSI strip, retry sniffing,
  ecoPackage.json scraping) reduced to zero; fetch success 31/31 across
  Windows/Linux hosts without per-run manual intervention.
- Harness architect: name→pull flow drops from ≥ 3 tool calls
  (search → find -p dump → find -c) to 2 (search → resolve), and tool-result
  bytes under the 8 KiB truncation budget.
- Zero occurrences of "rc=0 but nothing downloaded" in the RAG pipeline logs.
