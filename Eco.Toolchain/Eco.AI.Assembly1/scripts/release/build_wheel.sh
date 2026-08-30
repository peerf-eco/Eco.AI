#!/usr/bin/env bash
# Build the releasable eco-harness wheel: static frontend export + config +
# env.example baked in as package data.
#
# Prereqs: node/npm (frontend), python 3.11+ with `build` (pip install build).
# Output: dist/eco_harness-<version>-py3-none-any.whl
set -euo pipefail
cd "$(dirname "$0")/../.."

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=".venv/bin/python"

WHEEL_FROM="${1:-}"   # optional: prebuilt frontend out/ dir (CI cache)
FRONTEND_OUT="${WHEEL_FROM:-frontend/out}"

# 1. Static UI export → eco_harness/web_static (served by FastAPI at "/").
if [ ! -f "$FRONTEND_OUT/index.html" ]; then
  echo "[build_wheel] frontend export not found — building..."
  (cd frontend && npm ci && NEXT_TELEMETRY_DISABLED=1 npm run build)
fi
rm -rf eco_harness/web_static
mkdir -p eco_harness/web_static
cp -R "$FRONTEND_OUT"/. eco_harness/web_static/

# 2. env.example ships inside the wheel (installed-mode reference template).
cp env.example eco_harness/env.example

# 3. Wheel (config/ is mapped to eco_harness.config in pyproject.toml).
"$PYTHON" -m pip install --quiet build 2>/dev/null || true
"$PYTHON" -m build --wheel --outdir dist .

echo "[build_wheel] done:"
ls -la dist/*.whl
