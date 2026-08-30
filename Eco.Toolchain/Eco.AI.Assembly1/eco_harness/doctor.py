"""`eco-harness doctor` — one-command health report for an install.

Checks (warn, never block, unless something is truly fatal):
  - Python version (>= 3.11)
  - native binaries (eco-cli / eco-wizard) resolve AND are executable
  - RAG index exists and loads through sqlite-vec
  - .env keys (OpenRouter / marketplace token) — warn only
  - static UI bundle present
  - project dir / output root writable
"""
from __future__ import annotations

import os
import sqlite3
import sys
from dataclasses import dataclass
from eco_harness.agent.internal.tools import binaries, paths

_OK = "ok"
_WARN = "warn"
_FAIL = "fail"


@dataclass
class Check:
    name: str
    status: str
    detail: str


def _python_check() -> Check:
    version = sys.version_info
    if (version.major, version.minor) >= (3, 11):
        return Check("python", _OK, f"{version.major}.{version.minor}.{version.micro}")
    return Check(
        "python", _FAIL,
        f"{version.major}.{version.minor} — 3.11+ required",
    )


def _binary_check(name: str) -> Check:
    resolved = binaries.resolve_binary(name)
    if resolved is None:
        return Check(
            f"binary:{name}", _WARN,
            "not found — " + binaries.describe_search_order(name),
        )
    if not os.access(resolved, os.X_OK):
        return Check(f"binary:{name}", _FAIL, f"{resolved} is not executable")
    return Check(f"binary:{name}", _OK, str(resolved))


def _index_check() -> Check:
    index_path = paths.marketplace_index_path()
    if not index_path.is_file():
        return Check(
            "rag-index", _WARN,
            f"not found at {index_path} — run `eco-harness update` or build "
            "it locally (scripts/build_marketplace_index.py)",
        )
    try:
        import sqlite_vec

        connection = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
        try:
            connection.enable_load_extension(True)
            sqlite_vec.load(connection)
            chunks = connection.execute(
                "SELECT COUNT(*) FROM chunks",
            ).fetchone()[0]
        finally:
            connection.close()
        return Check("rag-index", _OK, f"{index_path} ({chunks} chunks)")
    except Exception as error:  # noqa: BLE001
        return Check("rag-index", _FAIL, f"{index_path}: {error}")


def _env_check() -> list[Check]:
    checks = []
    key = os.getenv("OPENAI_API_KEY", "")
    checks.append(
        Check(
            "openrouter-key",
            _OK if key else _WARN,
            "configured" if key else
            "missing — run the /setup wizard or add OPENAI_API_KEY to "
            f"{paths.eco_home() / '.env'} (warns only; the app still starts)",
        ),
    )
    token = os.getenv("ECO_API_TOKEN", "")
    checks.append(
        Check(
            "marketplace-token",
            _OK if token else _WARN,
            "configured" if token else
            "missing — marketplace search/pull will fail without it "
            "(ECO_API_TOKEN)",
        ),
    )
    return checks


def _ui_check() -> Check:
    static_dir = paths.package_root() / "web_static"
    if (static_dir / "index.html").is_file():
        return Check("static-ui", _OK, str(static_dir))
    return Check("static-ui", _WARN, f"no bundle at {static_dir}")


def _writable_check() -> list[Check]:
    checks = []
    for name, directory in (
        ("project-dir", paths.project_dir()),
        ("output-root", paths.output_root()),
        ("data-dir", paths.eco_home() / "data"),
    ):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".doctor-write-probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            checks.append(Check(name, _OK, str(directory)))
        except OSError as error:
            checks.append(Check(name, _FAIL, f"{directory}: {error}"))
    return checks


def run_doctor() -> tuple[list[Check], bool]:
    checks: list[Check] = [_python_check(), _binary_check("eco-cli"),
                           _binary_check("eco-wizard"), _index_check()]
    checks.extend(_env_check())
    checks.append(_ui_check())
    checks.extend(_writable_check())
    return checks, all(c.status != _FAIL for c in checks)
