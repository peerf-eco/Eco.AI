#!/usr/bin/env python3
"""Download every component listed on the EcoOS Marketplace UI into a local cache.

Why a dedicated script instead of `eco find -n`:
    Looking up by
    name (`find -n <Name>`) returns the full profile for any component,
    so we walk a hard-coded name list (taken from the UI) and pull each one.

Output layout (matches eco-cli's own pull behaviour):
    marketplace_cache/
      <ComponentName>/
        SharedFiles/*.h ...        # extracted DEVKIT
        DesignFiles/...
      ecoPackage.json              # accumulates as eco-cli appends
      .eco/                        # eco-cli bookkeeping
      _profiles/<name>.json        # raw `find -n` profile we parsed
      _fetch_summary.json          # one-line outcome per component

Re-run is idempotent: components already extracted are skipped (presence of
the target dir or of the component's entry in ecoPackage.json is the marker).

Verified marketplace quirks this script works around (see
/tmp/kilo/eco_mkt_debug experiments, 2026-09-09):

  * eco-cli ALWAYS extracts into the process cwd ("The file directory is:
    <cwd>"), so pulls must run with cwd=CACHE_DIR.
  * The extraction folder is the DEVKIT's INNER component name, not the
    marketplace product name: EcoOS.Unikernel (a kernel-type product) ships
    `Eco.System1_DK_v*.zip` and extracts as Eco.System1/. The post-pull check
    therefore reads the authoritative `files[0].locationPath` from the
    cwd's ecoPackage.json instead of guessing CACHE_DIR/<name>.
  * Non-Component products have no DEVKIT at all: Eco.Wizard is a VS Code
    plugin whose artefacts are contentType EXECUTABLE/PACKAGE (.vsix).
    We pick the newest version's DEVKIT if present, else its first artefact.
  * `find` can die on a transient AppSync "Connection timed out" while still
    exiting rc=0 and printing the error + "No components found matching
    '<name>'." on STDOUT — indistinguishable from a real miss unless we
    retry and sniff the banner text.
  * `find -p` (published catalog) returns only a subset of the catalog
    (8 of 31 observed) as concatenated JSON objects, so the hard-coded UI
    name list below remains the authoritative source. Only 'Component'
    entities carry a real CID; kernel/application products expose a
    synthetic uguid but are pulled the same way (-c works, -i also works).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eco_harness.agent.internal.tools.binaries import describe_search_order, resolve_binary  # noqa: E402

# ── Inputs ────────────────────────────────────────────────────────────────
# Single shared binary-resolution policy (env → <repo>/bin → /opt → legacy
# platform-suffixed siblings → PATH).
ECO_CLI = resolve_binary("eco-cli")

CACHE_DIR = Path(os.environ.get(
    "MARKETPLACE_CACHE",
    str(PROJECT_ROOT / "marketplace_cache"),
))
TOKEN = os.environ.get("ECO_API_TOKEN") or ""

# Full Marketplace UI listing as of 2026-05-23.
# Order matches the catalog page; `eco-cli` is the tool itself, not pulled.
COMPONENTS: list[str] = [
    "Eco.Math.C89",
    "EcoOS.Unikernel",
    "Eco.Dictionary1",
    "Eco.List1",
    "Eco.InterfaceBus1",
    "Eco.ThreadManager1",
    "Eco.Vector1",
    "Eco.StdLib.C89",
    "Eco.Mutex1",
    "Eco.OpenGLES1",
    "Eco.Math.FFT1",
    "Eco.DateTime1",
    "Eco.Locale.C89",
    "Eco.Core1",
    "Eco.MemoryManager1",
    "Eco.Set1",
    "Eco.Map1",
    "Eco.Tree1",
    "Eco.Log1",
    "Eco.ProcessManager1",
    "Eco.Image.BMP3",
    "Eco.String.C89",
    "Eco.FileSystemManagement1",
    "Eco.String1",
    "Eco.Socket.P02",
    "Eco.Time.C89",
    "Eco.StdIO.C89",
    "Eco.Signal.C89",
    "Eco.Comparator1",
    "Eco.Wizard",
    "Eco.Stack1",
]

# Strip the ANSI colour escapes eco-cli emits on stderr/stdout — they survive
# the JSON output too if -e or --verbose were enabled.
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


# CLI emits these on stdout (rc=0!) when AppSync hiccups or the name misses.
class TransientFindError(Exception):
    """eco-cli hit a transient backend error; safe to retry."""


_NOT_FOUND = re.compile(r"No components found matching", re.IGNORECASE)
_TRANSIENT = re.compile(
    r"Connection timed out|Connection refused|timed out|"
    r"GraphQL client exception|UnknownHost|SocketTimeout",
    re.IGNORECASE,
)


# ── Helpers ───────────────────────────────────────────────────────────────
def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run eco-cli once, capture stdout/stderr as text."""
    cmd = [str(ECO_CLI), *args]
    env = {**os.environ, "ECO_API_TOKEN": TOKEN} if TOKEN else os.environ
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _parse_profile(raw: str) -> dict:
    """Strip CLI banner lines, parse remainder as JSON.

    eco-cli prints GraphQL/AppSync errors on stdout *before* (and sometimes
    around) the JSON and still exits 0, so we raw_decode the first JSON
    object and tolerate trailing banner text.
    """
    text = _ANSI.sub("", raw)
    if _NOT_FOUND.search(text) and _TRANSIENT.search(text):
        raise TransientFindError("AppSync connection error, retry advised")
    start = text.find("{")
    if start < 0:
        if _NOT_FOUND.search(text):
            raise LookupError("No components found matching (may be transient)")
        raise ValueError(f"no JSON object in CLI output:\n{text[:400]}")
    obj, _end = json.JSONDecoder().raw_decode(text[start:])
    return obj


def _find_profile(name: str, attempts: int = 3) -> subprocess.CompletedProcess[str]:
    """`find -n <name>` with retries for transient AppSync failures.

    eco-cli exits rc=0 on GraphQL connection timeouts, so success is judged
    by the parseable profile, not the return code.
    """
    last: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, attempts + 1):
        try:
            find = _run("find", "-n", name)
        except subprocess.TimeoutExpired:
            find = None
        if find is not None and find.returncode == 0:
            try:
                _parse_profile(find.stdout)
                return find  # clean, parseable profile
            except TransientFindError:
                last = find
            except (ValueError, LookupError) as e:
                # A persistent "No components found" may still be a flaky
                # network round-trip behind the scenes — retry a little.
                if attempt < attempts and _TRANSIENT.search(_ANSI.sub("", find.stdout)):
                    last = find
                    print(f"retry {attempt}/{attempts - 1} ({e})", end=" ", flush=True)
                else:
                    raise
        else:
            last = find
        if attempt < attempts:
            time.sleep(2 * attempt)
    if last is not None:
        return last
    # Every attempt hit subprocess timeout; main() records this as FIND-FAIL.
    raise ValueError(f"find -n {name}: timed out on all {attempts} attempts")


def _latest_artefact(profile: dict) -> tuple[str, str, str]:
    """Return (versionName, fileId, contentType) of the newest artefact.

    Versions are ordered chronologically in the marketplace response; we still
    sort by `date` defensively (ISO 8601, lexicographic == chronological).
    Component products carry a DEVKIT; application/plugin products (e.g.
    Eco.Wizard) only ship EXECUTABLE/PACKAGE artefacts, so we accept the
    newest version's DEVKIT if present, else its first available file.
    """
    versions = profile.get("versions") or []
    if not versions:
        raise ValueError("no versions in profile")
    versions.sort(key=lambda v: v.get("date") or "")
    latest = versions[-1]
    files = latest.get("files") or []
    if not files:
        raise ValueError(f"no files in version {latest['name']}")
    for f in files:
        if f.get("contentType") == "DEVKIT":
            return latest["name"], f["fileId"], "DEVKIT"
    return latest["name"], files[0]["fileId"], files[0].get("contentType", "?")


def _installed_locations(cache_dir: Path) -> dict[str, str]:
    """Map cid -> locationPath from the cache's ecoPackage.json.

    eco-cli appends every pull to this file with the AUTHORITATIVE extraction
    path (`files[0].locationPath`). Needed because the extraction folder is
    the DEVKIT's inner component name, which may differ from the marketplace
    product name (EcoOS.Unikernel extracts as Eco.System1).
    """
    package = cache_dir / "ecoPackage.json"
    if not package.exists():
        return {}
    try:
        data = json.loads(package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    locations: dict[str, str] = {}
    for comp in data.get("components") or []:
        cid = comp.get("cid") or comp.get("id")
        for f in comp.get("files") or []:
            loc = f.get("locationPath")
            if cid and loc:
                locations[cid] = loc
    return locations


def _count_artefacts(location: Path) -> int:
    """Count files at an extraction location (dir tree or single artefact)."""
    if location.is_dir():
        return sum(1 for p in location.rglob("*") if p.is_file())
    return 1 if location.is_file() else 0


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> int:
    if not TOKEN:
        print("ERROR: ECO_API_TOKEN env var not set.", file=sys.stderr)
        return 2
    if ECO_CLI is None or not ECO_CLI.exists():
        print(
            "ERROR: eco-cli binary not found. "
            + describe_search_order("eco-cli"),
            file=sys.stderr,
        )
        return 2

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    profiles_dir = CACHE_DIR / "_profiles"
    profiles_dir.mkdir(exist_ok=True)
    summary_path = CACHE_DIR / "_fetch_summary.json"
    summary: list[dict] = []
    installed = _installed_locations(CACHE_DIR)

    for i, name in enumerate(COMPONENTS, 1):
        target_dir = CACHE_DIR / name
        record: dict = {"name": name, "status": "", "detail": ""}

        # Idempotency — skip if the marketplace-name dir is already populated.
        if target_dir.exists() and any(target_dir.iterdir()):
            print(f"[{i:2}/{len(COMPONENTS)}] {name}: SKIP (already extracted)")
            record.update(status="skip", detail="already extracted")
            summary.append(record)
            continue

        # 1) Resolve uguid + newest artefact fileId via `find -n <name>`
        #    (retried — AppSync timeouts exit rc=0 with no JSON on stdout).
        print(f"[{i:2}/{len(COMPONENTS)}] {name}: resolving...", end=" ", flush=True)
        try:
            find = _find_profile(name)
        except (ValueError, LookupError) as e:
            print(f"FIND-FAIL ({e})")
            record.update(status="find_fail", detail=str(e)[:300])
            summary.append(record)
            continue
        try:
            profile = _parse_profile(find.stdout)
            uguid = profile["uguid"]
            ver, fid, ctype = _latest_artefact(profile)
        except (ValueError, KeyError) as e:
            print(f"PARSE-FAIL ({e})")
            record.update(status="parse_fail", detail=str(e))
            summary.append(record)
            continue

        # Save the raw profile for the catalog index later.
        (profiles_dir / f"{name}.json").write_text(
            json.dumps(profile, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Idempotency (round 2) — ecoPackage.json may already hold this cid
        # under an inner name (e.g. EcoOS.Unikernel -> Eco.System1).
        loc = installed.get(uguid)
        if loc and _count_artefacts(Path(loc)) > 0:
            print(f"SKIP (already extracted as {Path(loc).name})")
            record.update(status="skip", detail=f"already extracted as {Path(loc).name}")
            summary.append(record)
            continue

        # 2) Pull into the cache dir (cwd matters — eco-cli always extracts
        #    into the process cwd, regardless of ECO_FRAMEWORK).
        pull = _run("pull", "-c", uguid, "-v", ver, f"-fid={fid}", cwd=CACHE_DIR)
        if pull.returncode != 0:
            print(f"PULL-FAIL rc={pull.returncode}")
            record.update(
                status="pull_fail",
                detail=_ANSI.sub("", pull.stderr)[:300],
                uguid=uguid, version=ver, fileId=fid,
            )
            summary.append(record)
            continue

        # 3) Confirm files landed — via ecoPackage.json's locationPath
        #    (authoritative), falling back to the marketplace-name dir.
        extracted: Path | None = None
        installed = _installed_locations(CACHE_DIR)
        loc = installed.get(uguid)
        if loc:
            candidate = Path(loc)
            # locationPath may point at the extracted dir or at the single
            # artefact file inside it (e.g. Eco.Wizard/....vsix).
            extracted = candidate if candidate.is_dir() else candidate.parent
        if extracted is None and target_dir.exists() and any(target_dir.iterdir()):
            extracted = target_dir
        if extracted is not None and _count_artefacts(extracted) > 0:
            file_count = _count_artefacts(extracted)
            extracted_as = (
                extracted.name if extracted != target_dir else name
            )
            note = f" ver={ver} files={file_count}"
            if extracted_as != name:
                note += f" extracted_as={extracted_as}"
            if ctype != "DEVKIT":
                note += f" contentType={ctype}"
            print(f"OK{note}")
            record.update(
                status="ok", uguid=uguid, version=ver, fileId=fid,
                contentType=ctype, files=file_count,
                extracted_as=extracted_as,
            )
        else:
            print(f"DOWNLOAD-EMPTY (cwd={CACHE_DIR})")
            record.update(
                status="download_empty",
                detail="pull rc=0 but no artefacts at locationPath or target dir",
                uguid=uguid, version=ver, fileId=fid,
            )
        summary.append(record)

    summary_path.write_text(
        json.dumps(
            {
                "generated": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "cli": str(ECO_CLI),
                "cache_dir": str(CACHE_DIR),
                "total": len(COMPONENTS),
                "ok": sum(1 for r in summary if r["status"] == "ok"),
                "skip": sum(1 for r in summary if r["status"] == "skip"),
                "fail": sum(
                    1 for r in summary
                    if r["status"] not in ("ok", "skip")
                ),
                "results": summary,
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nSummary written: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
