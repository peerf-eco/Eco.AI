#!/usr/bin/env python3
"""Validate host files and directories required by the development compose stack.

With ``--fix``, performs the safe remediations automatically (create missing
directories, seed ``.env`` from ``env.example``) and prints copy-paste hints
for everything that needs a human (building the index, fetching components,
installing binaries).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eco_harness.agent.internal.tools.binaries import describe_search_order, resolve_binary  # noqa: E402


class Issue:
    def __init__(self, message: str, fix_hint: str = "") -> None:
        self.message = message
        self.fix_hint = fix_hint


def validate(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    index_path = root / "marketplace_index.sqlite"
    cache_path = root / "marketplace_cache"
    if not index_path.is_file():
        issues.append(Issue(
            f"{index_path} must be a regular SQLite file",
            "python scripts/build_marketplace_index.py  "
            "(requires OPENAI_API_KEY in .env)",
        ))
    if not cache_path.is_dir():
        issues.append(Issue(
            f"{cache_path} must be a directory",
            "python scripts/fetch_marketplace.py  (requires ECO_API_TOKEN in .env)",
        ))
    elif not any(cache_path.iterdir()):
        issues.append(Issue(
            f"{cache_path} is empty; fetch marketplace components first",
            "python scripts/fetch_marketplace.py",
        ))
    for executable in ("eco-cli", "eco-wizard"):
        env_name = f"ECO_{executable.upper().replace('-', '_')}_PATH"
        configured = os.getenv(env_name)
        resolved = resolve_binary(executable, explicit=configured or None)
        if resolved:
            continue
        issues.append(Issue(
            f"{executable} was not found ({describe_search_order(executable)})",
            f"copy it to <repo>/bin/{executable}  — or —  set {env_name} in .env",
        ))
    return issues


def try_fix(root: Path, issues: list[Issue]) -> list[Issue]:
    """Apply safe fixes; return the remaining issues with printed hints."""
    remaining: list[Issue] = []
    cache_path = root / "marketplace_cache"
    index_path = root / "marketplace_index.sqlite"
    env_path = root / ".env"

    for issue in issues:
        fixed = False
        if "must be a directory" in issue.message and not cache_path.exists():
            cache_path.mkdir(parents=True, exist_ok=True)
            print(f"[preflight] FIX: created {cache_path}")
            fixed = True
        if not env_path.exists() and (
            "must be a regular SQLite" in issue.message or "is empty" in issue.message
        ):
            shutil.copy(root / "env.example", env_path)
            print(f"[preflight] FIX: seeded {env_path} from env.example")
        if not fixed:
            remaining.append(issue)

    if any("must be a regular SQLite" in i.message for i in remaining):
        print("[preflight] HINT: build the RAG index:")
        print("    python scripts/build_marketplace_index.py")
    if any("is empty" in i.message or "must be a directory" in i.message for i in remaining):
        print("[preflight] HINT: fetch marketplace components:")
        print("    python scripts/fetch_marketplace.py")
    if any("was not found" in i.message for i in remaining):
        print("[preflight] HINT: place the vendored binaries in <repo>/bin/:")
        print("    mkdir -p bin && cp /path/to/eco-cli bin/ && cp /path/to/eco-wizard bin/")
        print("  or point .env at them:")
        print("    ECO_CLI=/absolute/path/eco-cli")
        print("    ECO_WIZARD=/absolute/path/eco-wizard")
    return remaining


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="apply safe fixes and print actionable hints for the rest",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    issues = validate(root)
    if issues and args.fix:
        issues = try_fix(root, issues)
    if issues:
        for issue in issues:
            print(f"[preflight] ERROR: {issue.message}", file=sys.stderr)
            if issue.fix_hint:
                print(f"[preflight]   fix → {issue.fix_hint}", file=sys.stderr)
        return 1
    print("[preflight] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
