# ═══════════════════════════════════════════════════════════════════════════
# Eco.AI Harness — CUSTOMER production image (single image: API + static UI).
#
# Difference from the dev Dockerfile at the repo root:
#   - NO wine: native eco-cli / eco-wizard builds for Linux exist and are
#     downloaded into the standard toolchain dirs ($ECO_TOOLCHAIN/eco-cli etc.,
#     app-home bin/ fallback) by the installer / `eco-harness update` — never
#     over binaries the user already provides via ECO_CLI / ECO_WIZARD
#   - installs the WHEEL built by CI (docker/release context), not the source
#     tree — no monorepo bind-mounts, no build tooling
#   - static UI (Next.js export) ships inside the wheel as eco_harness/web_static
#     and is served by FastAPI on the same port
#
# Build (CI: scripts/release/build_wheel.sh → dist/, then the workflow's
# "Copy wheel into image build context" step stages it at docker/wheel/):
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     -f docker/Dockerfile -t <img> <assembly-dir>
# The wheel must be present at docker/wheel/ inside the build context — the
# glob COPY below picks up whatever staged wheel is there (keeps the
# Dockerfile version-agnostic; a missing wheel fails the build loudly).
# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    # Installed-mode defaults inside the container: the mounted volume is the
    # ecosystem root (ECO_HOME), with the standard toolchain/app-home tree
    # beneath it; the project dir the user picked is mounted at /project.
    ECO_HOME=/data \
    ECO_TOOLCHAIN=/data/toolchain \
    ECO_HARNESS=/data/toolchain/eco-harness \
    ECO_PROJECT_DIR=/project

# git: worktree creation against the user's mounted project.
# curl: container healthcheck. gosu: drop-root entrypoint.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates git curl gosu && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Wheel staged into the build context at docker/wheel/ (by CI) — see the
# build note in the header comment.
COPY docker/wheel/*.whl /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /tmp/*.whl && \
    rm -f /tmp/*.whl

# Non-root runtime user; /data (app home) and /project (user project) come
# from mounts and are chowned at start via the entrypoint below.
RUN useradd --create-home --uid 1000 eco

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=10s \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["python", "-m", "eco_harness", "serve", "--host", "0.0.0.0", "--port", "8000"]
