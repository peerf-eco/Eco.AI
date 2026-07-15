# EcoOS frontend (Next.js 14). Node 20 LTS, digest-pinned.
# (node:18 reached end-of-life 2025-04-30 — do not use.)
# Refresh the pin: docker buildx imagetools inspect node:20.18-alpine
FROM node:20.18-alpine@sha256:053c1d99e608fe9fa0db6821edd84276277c0a663cd181f4a3e59ee20f5f07ea

WORKDIR /app

# Install from the lockfile for reproducible builds. `npm ci` requires
# package-lock.json and fails if it has drifted from package.json — that is
# the intended guarantee (vs `npm install`, which silently resolves ^ ranges).
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

# Production build. NOTE: docker-compose currently overrides CMD with
# `npm run dev` (hot-reload) and bind-mounts ./frontend over /app, so for the
# dev stack this build is unused. For a production run, remove that override
# and the source bind-mount so this built image is what actually serves.
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
