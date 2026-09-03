#!/usr/bin/env python3
"""Build the release manifest.json — the single version source of truth.

Manifest consumers:
  - scripts/install/install.{sh,ps1}  (wheel, per-OS binaries, index)
  - eco_harness.update (same, for `eco-harness update`)

Inputs (release staging dir, default ./release-staging):
  binaries/<tool>/<os>/<arch>/<artifact>   native eco-cli / eco-wizard builds
  index/marketplace_index.tar.gz           prebuilt RAG index + cache tarball
  dist/eco_harness-<ver>-py3-none-any.whl  wheel
  --image <repo:tag>                       published container image
  --base-url <url>                         public download root (S3/CDN)

Output: manifest.json (next to the staging dir, or --output).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entry(path: Path, base_url: str, relative: Path) -> dict:
    return {
        "url": f"{base_url.rstrip('/')}/{relative.as_posix()}",
        "sha256": sha256(path),
        "size": path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", default="release-staging", type=Path)
    parser.add_argument("--base-url", default="https://downloads.ecoos.dev/eco-harness")
    parser.add_argument("--image", default="ghcr.io/peerf-eco/eco.ai:latest")
    parser.add_argument("--output", default=None, type=Path)
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="permit empty binaries/index sections (local testing only — "
        "a manifest without them ships installs with no eco-cli and no RAG "
        "index, so release builds must NOT pass this)",
    )
    args = parser.parse_args()

    staging = args.staging
    manifest: dict = {
        "schema_version": 1,
        "binaries": {},
        "index": None,
        "wheel": None,
        "image": None,
    }

    binaries_dir = staging / "binaries"
    if binaries_dir.is_dir():
        for tool_dir in sorted(p for p in binaries_dir.iterdir() if p.is_dir()):
            tool_entry: dict = {}
            for os_dir in sorted(p for p in tool_dir.iterdir() if p.is_dir()):
                for arch_dir in sorted(p for p in os_dir.iterdir() if p.is_dir()):
                    artifacts = sorted(arch_dir.iterdir())
                    if not artifacts:
                        continue
                    tool_entry.setdefault(os_dir.name, {})[arch_dir.name] = entry(
                        artifacts[0], args.base_url,
                        artifacts[0].relative_to(staging),
                    )
            manifest["binaries"][tool_dir.name] = tool_entry

    index_tarball = staging / "index" / "marketplace_index.tar.gz"
    if index_tarball.is_file():
        manifest["index"] = entry(
            index_tarball, args.base_url, index_tarball.relative_to(staging),
        )

    wheels = sorted((staging / "dist").glob("eco_harness-*.whl")) if (
        staging / "dist"
    ).is_dir() else []
    if wheels:
        wheel = wheels[-1]
        manifest["wheel"] = {
            **entry(wheel, args.base_url, wheel.relative_to(staging)),
            "version": wheel.name.split("-")[1],
        }
        manifest["image"] = {"repo": args.image.split(":")[0], "tag": args.image.split(":", 1)[-1]}

    import datetime

    manifest["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Fail fast rather than publishing a manifest whose installs would ship
    # no native binaries and no RAG data.
    if not args.allow_empty:
        problems = []
        if not manifest["binaries"]:
            problems.append(
                "binaries section is empty — stage eco-cli/eco-wizard builds "
                "under <staging>/binaries/<tool>/<os>/<arch>/ (EcoCLI pipeline "
                "artifact) before building the manifest",
            )
        if not manifest["index"]:
            problems.append(
                "index section is empty — stage the prebuilt RAG tarball at "
                "<staging>/index/marketplace_index.tar.gz before building "
                "the manifest",
            )
        if not manifest["wheel"]:
            problems.append("wheel section is empty — run scripts/release/build_wheel.sh")
        if problems:
            for problem in problems:
                print(f"[build_manifest] ERROR: {problem}", file=sys.stderr)
            return 1

    output = args.output or staging / "manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[build_manifest] wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
