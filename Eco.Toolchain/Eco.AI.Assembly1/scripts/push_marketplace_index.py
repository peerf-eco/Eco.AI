#!/usr/bin/env python3
"""Push the prebuilt marketplace index and cache to S3 for release hosting.

Packages marketplace_index.sqlite + marketplace_cache/ into a zip and uploads
it to the release S3 bucket so the release workflow can fetch it.

Run this once after building the index, and again whenever the marketplace
snapshot changes (new components fetched, index rebuilt).

Usage:
    python scripts/push_marketplace_index.py
    python scripts/push_marketplace_index.py --bucket my-bucket --prefix index/
    python scripts/push_marketplace_index.py --index-only   # skip marketplace_cache/
    python scripts/push_marketplace_index.py --dry-run      # zip only, no upload

Prerequisites:
    pip install boto3          # or: aws CLI must be on PATH (falls back to aws s3 cp)
    AWS credentials configured (OIDC, env vars, ~/.aws/credentials, or instance role)
    RELEASE_S3_BUCKET env var set (or pass --bucket)

The script reads .env via python-dotenv if present.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Load .env so RELEASE_S3_BUCKET etc. are available without exporting them.
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_zip(
    index_path: Path,
    cache_path: Path | None,
    output: Path,
) -> None:
    print(f"[push_marketplace_index] building {output.name} ...")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(index_path, index_path.name)
        print(f"  + {index_path.name}  ({index_path.stat().st_size:,} bytes)")
        if cache_path and cache_path.is_dir():
            for f in sorted(cache_path.rglob("*")):
                if f.is_file():
                    arcname = cache_path.name + "/" + f.relative_to(cache_path).as_posix()
                    zf.write(f, arcname)
            cache_files = sum(1 for f in cache_path.rglob("*") if f.is_file())
            print(f"  + {cache_path.name}/  ({cache_files} files)")
    size_mb = output.stat().st_size / (1024 * 1024)
    sha = _sha256(output)
    print(f"[push_marketplace_index] {output.name}: {size_mb:.1f} MB  sha256={sha[:16]}...")


def _upload_boto3(local: Path, bucket: str, key: str) -> None:
    import boto3  # type: ignore[import]
    s3 = boto3.client("s3")
    print(f"[push_marketplace_index] uploading s3://{bucket}/{key} ...")
    s3.upload_file(
        str(local), bucket, key,
        ExtraArgs={"CacheControl": "public, max-age=300"},
    )
    print(f"[push_marketplace_index] uploaded s3://{bucket}/{key}")


def _upload_cli(local: Path, bucket: str, key: str) -> None:
    uri = f"s3://{bucket}/{key}"
    print(f"[push_marketplace_index] uploading {uri} ...")
    result = subprocess.run(
        ["aws", "s3", "cp", str(local), uri,
         "--cache-control", "public, max-age=300"],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"aws s3 cp failed with exit code {result.returncode}")
    print(f"[push_marketplace_index] uploaded {uri}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bucket", default=os.getenv("RELEASE_S3_BUCKET"),
                        help="S3 bucket name (default: $RELEASE_S3_BUCKET)")
    parser.add_argument("--prefix", default="index/",
                        help="S3 key prefix (default: index/)")
    parser.add_argument("--index", default=str(REPO_ROOT / "marketplace_index.sqlite"),
                        type=Path, help="Path to marketplace_index.sqlite")
    parser.add_argument("--cache", default=str(REPO_ROOT / "marketplace_cache"),
                        type=Path, help="Path to marketplace_cache/ directory")
    parser.add_argument("--index-only", action="store_true",
                        help="Zip only marketplace_index.sqlite, skip marketplace_cache/")
    parser.add_argument("--dry-run", action="store_true",
                        help="Build the zip but do not upload to S3")
    args = parser.parse_args()

    index_path: Path = args.index
    cache_path: Path = args.cache
    index_only: bool = args.index_only

    if not index_path.is_file():
        print(f"[push_marketplace_index] ERROR: index not found: {index_path}", file=sys.stderr)
        print("  Run: python scripts/build_marketplace_index.py", file=sys.stderr)
        return 1

    if not index_only and not cache_path.is_dir():
        print(f"[push_marketplace_index] WARNING: cache dir not found: {cache_path} — uploading index only")
        index_only = True

    if not args.dry_run and not args.bucket:
        print("[push_marketplace_index] ERROR: --bucket or $RELEASE_S3_BUCKET required", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="eco-index-push-") as tmp:
        zip_path = Path(tmp) / "marketplace_index.zip"
        _build_zip(
            index_path,
            None if index_only else cache_path,
            zip_path,
        )

        if args.dry_run:
            dest = REPO_ROOT / "marketplace_index.zip"
            shutil.copy2(zip_path, dest)
            print(f"[push_marketplace_index] dry-run: zip written to {dest}")
            return 0

        key = args.prefix.rstrip("/") + "/marketplace_index.zip"
        try:
            _upload_boto3(zip_path, args.bucket, key)
        except ImportError:
            if shutil.which("aws") is None:
                print("[push_marketplace_index] ERROR: neither boto3 nor aws CLI found.", file=sys.stderr)
                print("  Install boto3: pip install boto3  or install the AWS CLI.", file=sys.stderr)
                return 1
            _upload_cli(zip_path, args.bucket, key)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
