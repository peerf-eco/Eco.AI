#!/usr/bin/env python3
"""Refresh the prebuilt RAG artifacts and publish them to S3/CloudFront.

Maintainer-only pipeline behind the marketplace RAG bundle that the release
workflow ships to end-users:

    1. fetch   — scripts/fetch_marketplace.py   (eco-cli pull of every
                 Marketplace component into marketplace_cache/; needs
                 ECO_API_TOKEN and an eco-cli binary, resolved from the
                 environment/.env)
    2. build   — scripts/build_marketplace_index.py (re-embeds the corpus
                 into marketplace_index.sqlite; needs OPENAI_API_KEY)
    3. package — zip marketplace_index.sqlite + marketplace_cache/ into
                 marketplace_index.zip. The installer's update step extracts
                 this zip flat into ~/.eco-harness/data, so the layout must
                 stay exactly: marketplace_index.sqlite at the zip root plus
                 the marketplace_cache/ tree. The installer never regenerates
                 these locally — this zip is the only delivery channel.
    4. upload  — aws s3 cp to s3://<bucket>/<key> using the standard AWS
                 credential chain (env vars / .env, ~/.aws, SSO profiles)

Afterwards set the release pipeline's RAG_INDEX_URL repository variable to
the CloudFront distribution URL of the uploaded key, e.g.
    https://d<id>.cloudfront.net/index/marketplace_index.zip
CI downloads it with plain curl — no AWS credentials in the workflow.
NOTE: overwriting an existing S3 key does not immediately purge CloudFront
edge caches; consider an invalidation for that path (or use a new key name
and update RAG_INDEX_URL) if users must see the new index immediately.

Usage::

    python scripts/publish_rag.py                     # full pipeline
    python scripts/publish_rag.py --skip-fetch        # reuse existing cache
    python scripts/publish_rag.py --skip-build        # reuse existing index
    python scripts/publish_rag.py --rebuild           # force full re-embed
    python scripts/publish_rag.py --no-upload         # package only
    python scripts/publish_rag.py --bucket my-bucket --key index/marketplace_index.zip

Credentials & targets come from the environment or .env (see env.example):
AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION (or AWS_PROFILE / SSO),
RAG_S3_BUCKET, RAG_S3_KEY.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / "marketplace_cache"
INDEX_PATH = PROJECT_ROOT / "marketplace_index.sqlite"
ZIP_PATH = PROJECT_ROOT / "marketplace_index.zip"

SKIP_DIRS = {"__pycache__", ".git"}
SKIP_FILES = {".DS_Store", "Thumbs.db"}

# Keys accepted from .env (standard AWS chain names + this script's targets).
ENV_KEYS = [
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_REGION",
    "AWS_PROFILE",
    "RAG_S3_BUCKET",
    "RAG_S3_KEY",
    # Passed through for the child scripts (fetch/build read the env).
    "ECO_API_TOKEN",
    "OPENAI_API_KEY",
    "ECO_CLI",
    "ECO_CLI_PATH",
    "MARKETPLACE_CACHE",
]


def _load_env_file(path: Path) -> int:
    """Load KEY=VALUE pairs into os.environ; existing env vars win.

    Returns the number of variables injected (not already present).
    """
    if not path.is_file():
        return 0
    injected = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            injected += 1
    return injected


def _load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(PROJECT_ROOT / ".env")  # existing env wins
        return
    except ImportError:
        pass
    _load_env_file(PROJECT_ROOT / ".env")


def _run(cmd: list[str]) -> None:
    print(f"[publish_rag] $ {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd)
    except FileNotFoundError as error:
        raise SystemExit(f"[publish_rag] ERROR: {error}; install it or adjust PATH")
    if result.returncode != 0:
        raise SystemExit(f"[publish_rag] ERROR: command failed: {' '.join(cmd)}")


def step_fetch() -> None:
    print("[publish_rag] step 1/4 — fetching marketplace components into marketplace_cache/")
    _run([sys.executable, str(PROJECT_ROOT / "scripts" / "fetch_marketplace.py")])


def step_build(args: argparse.Namespace) -> None:
    print("[publish_rag] step 2/4 — building marketplace_index.sqlite")
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "build_marketplace_index.py")]
    if args.rebuild:
        cmd.append("--rebuild")
    if args.build_args:
        cmd.extend(args.build_args)
    _run(cmd)


def step_package(zip_path: Path) -> tuple[int, str]:
    print(f"[publish_rag] step 3/4 — packaging {zip_path.name}")
    if not INDEX_PATH.is_file():
        raise SystemExit(f"[publish_rag] ERROR: {INDEX_PATH} not found — run the build step first")
    if not CACHE_DIR.is_dir():
        raise SystemExit(f"[publish_rag] ERROR: {CACHE_DIR} not found — run the fetch step first")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(INDEX_PATH, INDEX_PATH.name)
        for path in sorted(CACHE_DIR.rglob("*")):
            rel = path.relative_to(PROJECT_ROOT)
            if path.is_dir():
                continue
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            if path.name in SKIP_FILES:
                continue
            zf.write(path, rel.as_posix())
    data = zip_path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


def step_upload(zip_path: Path, bucket: str, key: str, region: str, profile: str) -> str:
    print(f"[publish_rag] step 4/4 — uploading to s3://{bucket}/{key}")
    if not shutil.which("aws"):
        raise SystemExit(
            "[publish_rag] ERROR: AWS CLI ('aws') not found on PATH — "
            "install it (https://docs.aws.amazon.com/cli/) or upload "
            f"{zip_path} manually to s3://{bucket}/{key}"
        )
    cmd = ["aws"]
    if profile:
        cmd += ["--profile", profile]
    if region:
        cmd += ["--region", region]
    cmd += ["s3", "cp", str(zip_path), f"s3://{bucket}/{key}"]
    _run(cmd)
    return f"s3://{bucket}/{key}"


def verify_public_url(url: str, zip_path: Path) -> None:
    import urllib.request

    print(f"[publish_rag] verifying public URL: {url}")
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            remote_len = response.headers.get("Content-Length")
            print(f"[publish_rag] HTTP {response.status}; Content-Length={remote_len}")
            if remote_len is not None and int(remote_len) != zip_path.stat().st_size:
                print(
                    "[publish_rag] WARNING: remote size differs from the local zip — "
                    "a CDN cache is likely serving the previous object; "
                    "invalidate the CloudFront path or wait for TTL."
                )
    except OSError as error:
        print(f"[publish_rag] WARNING: public URL not reachable yet: {error}")


def main() -> int:
    # Load .env BEFORE building the parser so its values act as argparse
    # defaults (AWS_PROFILE, RAG_S3_BUCKET, RAG_S3_KEY, AWS_REGION).
    _load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-fetch", action="store_true", help="skip marketplace refresh (reuse marketplace_cache/)")
    parser.add_argument("--skip-build", action="store_true", help="skip index build (reuse marketplace_index.sqlite)")
    parser.add_argument("--rebuild", action="store_true", help="pass --rebuild to build_marketplace_index.py (full re-embed)")
    parser.add_argument("--no-upload", action="store_true", help="package only; skip the S3 upload")
    parser.add_argument("--zip-out", default=str(ZIP_PATH), help="output zip path (default: <repo>/marketplace_index.zip)")
    parser.add_argument("--bucket", default=os.environ.get("RAG_S3_BUCKET", ""), help="target bucket (or RAG_S3_BUCKET in .env)")
    parser.add_argument("--key", default=os.environ.get("RAG_S3_KEY", "index/marketplace_index.zip"), help="object key (or RAG_S3_KEY in .env)")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", ""), help="AWS region (or AWS_REGION in .env)")
    parser.add_argument("--profile", default=os.environ.get("AWS_PROFILE", ""), help="AWS profile (or AWS_PROFILE in .env)")
    parser.add_argument("--public-url", default="", help="CloudFront/public URL to verify after upload (optional)")
    parser.add_argument(
        "build_args", nargs="*",
        help="extra args forwarded to build_marketplace_index.py (e.g. --source framework)",
    )
    args = parser.parse_args()

    zip_path = Path(args.zip_out)

    if not args.skip_fetch:
        step_fetch()
    else:
        print("[publish_rag] step 1/4 — skipped (--skip-fetch)")
    if not args.skip_build:
        step_build(args)
    else:
        print("[publish_rag] step 2/4 — skipped (--skip-build)")

    size, sha = step_package(zip_path)
    print(f"[publish_rag] zip ready: {zip_path} ({size} bytes, sha256 {sha})")

    if args.no_upload:
        print("[publish_rag] upload skipped (--no-upload)")
        return 0
    if not args.bucket:
        raise SystemExit(
            "[publish_rag] ERROR: no upload target — pass --bucket or set "
            "RAG_S3_BUCKET in the environment/.env (use --no-upload to stop "
            "after packaging)"
        )
    uri = step_upload(zip_path, args.bucket, args.key, args.region, args.profile)
    print(f"[publish_rag] uploaded: {uri}")
    if args.public_url:
        verify_public_url(args.public_url, zip_path)
    print(
        "[publish_rag] done. Ensure the release pipeline reads this key via the "
        "public distribution: set the RAG_INDEX_URL repository variable to the "
        f"CloudFront URL of {args.key} "
        "(consider a CloudFront invalidation if you overwrote an existing key)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
