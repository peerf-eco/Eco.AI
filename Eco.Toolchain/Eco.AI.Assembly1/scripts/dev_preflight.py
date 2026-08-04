#!/usr/bin/env python3
"""Validate host files and directories required by the development compose stack."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import os
from pathlib import Path


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    index_path = root / "marketplace_index.sqlite"
    cache_path = root / "marketplace_cache"
    if not index_path.is_file():
        errors.append(
            f"{index_path} must be a regular SQLite file; "
            "build it with scripts/build_marketplace_index.py"
        )
    if not cache_path.is_dir():
        errors.append(
            f"{cache_path} must be a directory; populate it with "
            "scripts/fetch_marketplace.py"
        )
    elif not any(cache_path.iterdir()):
        errors.append(f"{cache_path} is empty; fetch marketplace components first")
    for executable, env_name in (
        ("eco-cli", "ECO_CLI_PATH"),
        ("eco-wizard", "ECO_WIZARD_PATH"),
    ):
        configured = os.getenv(env_name)
        if configured and Path(configured).is_file():
            continue
        if not shutil.which(executable):
            errors.append(
                f"{executable} was not found on PATH; set its configured "
                f"{env_name} override"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"[preflight] ERROR: {error}", file=sys.stderr)
        return 1
    print("[preflight] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())