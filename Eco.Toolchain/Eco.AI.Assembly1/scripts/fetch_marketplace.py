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
target dir is the marker).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Inputs ────────────────────────────────────────────────────────────────
# Try to find eco-cli with Linux priority
ECO_CLI = None
for path in [
    os.environ.get("ECO_CLI_BIN"),
    "../../eco-cli-linux/eco-cli",  # Linux ELF (preferred)
    "../../eco-cli-windows/eco-cli.exe",  # Windows .exe (fallback)
    "eco-cli",  # System PATH
    "eco-cli.exe",  # System PATH Windows
]:
    if not path:
        continue
    candidate = Path(path)
    if candidate.exists():
        ECO_CLI = candidate
        break

if ECO_CLI is None:
    ECO_CLI = Path("../../../../Dist/eco-cli/eco-cli")  # Default fallback for Linux

CACHE_DIR = Path(os.environ.get(
    "MARKETPLACE_CACHE",
    "marketplace_cache",  # Relative to project root
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
    """Strip CLI banner lines, parse remainder as JSON."""
    text = _ANSI.sub("", raw)
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON object in CLI output:\n{text[:400]}")
    return json.loads(text[start:])


def _latest_devkit(profile: dict) -> tuple[str, str]:
    """Return (versionName, fileId) of the latest DEVKIT artefact.

    Versions are ordered chronologically in the marketplace response; we still
    sort by `date` defensively (ISO 8601, lexicographic == chronological).
    """
    versions = profile.get("versions") or []
    if not versions:
        raise ValueError("no versions in profile")
    versions.sort(key=lambda v: v.get("date") or "")
    latest = versions[-1]
    for f in latest.get("files") or []:
        if f.get("contentType") == "DEVKIT":
            return latest["name"], f["fileId"]
    raise ValueError(f"no DEVKIT artefact in version {latest['name']}")


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> int:
    if not TOKEN:
        print("ERROR: ECO_API_TOKEN env var not set.", file=sys.stderr)
        return 2
    if not ECO_CLI.exists():
        print(f"ERROR: eco-cli binary not found at {ECO_CLI}", file=sys.stderr)
        return 2

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    profiles_dir = CACHE_DIR / "_profiles"
    profiles_dir.mkdir(exist_ok=True)
    summary_path = CACHE_DIR / "_fetch_summary.json"
    summary: list[dict] = []

    for i, name in enumerate(COMPONENTS, 1):
        target_dir = CACHE_DIR / name
        record: dict = {"name": name, "status": "", "detail": ""}

        # Idempotency — skip if the dir is already populated.
        if target_dir.exists() and any(target_dir.iterdir()):
            print(f"[{i:2}/{len(COMPONENTS)}] {name}: SKIP (already extracted)")
            record.update(status="skip", detail="already extracted")
            summary.append(record)
            continue

        # 1) Resolve uguid + latest DEVKIT fileId via `find -n <name>`.
        print(f"[{i:2}/{len(COMPONENTS)}] {name}: resolving...", end=" ", flush=True)
        find = _run("find", "-n", name)
        if find.returncode != 0:
            print(f"FIND-FAIL rc={find.returncode}")
            record.update(status="find_fail",
                          detail=_ANSI.sub("", find.stderr)[:300])
            summary.append(record)
            continue
        try:
            profile = _parse_profile(find.stdout)
            uguid = profile["uguid"]
            ver, fid = _latest_devkit(profile)
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

        # 2) Pull DEVKIT into the cache dir (cwd matters — eco-cli extracts
        #    into cwd/<ComponentName>/).
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

        # 3) Confirm files landed.
        if target_dir.exists() and any(target_dir.iterdir()):
            file_count = sum(1 for _ in target_dir.rglob("*") if _.is_file())
            print(f"OK ver={ver} files={file_count}")
            record.update(
                status="ok", uguid=uguid, version=ver, fileId=fid,
                files=file_count,
            )
        else:
            print(f"DOWNLOAD-EMPTY (cwd={CACHE_DIR})")
            record.update(
                status="download_empty",
                detail="pull rc=0 but target dir empty",
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
