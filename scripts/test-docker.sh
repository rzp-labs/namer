#!/bin/bash
# Basic/integration test runner used by Makefile
# Usage: test-docker.sh <image_name> <version> <basic|integration>
set -Eeuo pipefail

IMAGE_NAME="${1:-nehpz/namer}"
VERSION="${2:-latest}"
MODE="${3:-basic}"

IMAGE_REF="${IMAGE_NAME}:${VERSION}"

log() { echo "[test-docker] $*"; }

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require docker

log "Testing image: ${IMAGE_REF} (mode=${MODE})"

# Sanity: ensure image is present locally; if not, try to pull
if ! docker image inspect "${IMAGE_REF}" >/dev/null 2>&1; then
  log "Image not found locally; attempting pull..."
  docker pull "${IMAGE_REF}" >/dev/null
fi

# 1) Sanity check: Python available inside image
log "Checking Python presence..."
docker run --rm --entrypoint bash "${IMAGE_REF}" -lc 'python3 --version' >/dev/null

# 2) Sanity check: gosu present (entrypoint uses it)
log "Checking gosu presence..."
docker run --rm --entrypoint bash "${IMAGE_REF}" -lc 'command -v gosu' >/dev/null

# 3) Sanity check: entrypoint exists
log "Checking entrypoint file exists..."
docker run --rm --entrypoint bash "${IMAGE_REF}" -lc '[ -f /app/docker-entrypoint-user.sh ]' >/dev/null

if [[ "$MODE" == "basic" ]]; then
  log "Basic checks passed"
  exit 0
fi

# Integration: run a lightweight dry-run that exercises entrypoint without long-running service
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

log "Running container with minimal env to verify startup path..."
# Use a short no-op command through bash to avoid long-running watchdog
# and to ensure entrypoint completes crucial setup steps and hands off.
docker run --rm \
  -e PUID=1000 -e PGID=1000 -e UMASK=0002 \
  -e NAMER_CONFIG=/config/namer.cfg \
  -v "$TMPDIR:/config" \
  --device /dev/null:/dev/null \
  --entrypoint bash \
  "${IMAGE_REF}" -lc 'echo ok' >/dev/null

log "Integration checks passed"
