#!/usr/bin/env python3
"""Create a portable copy of the shared marketplace RAG SQLite index."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.index.is_file():
        parser.error(f"RAG index is not a file: {args.index}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.index, args.out)
    print(f"exported {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())