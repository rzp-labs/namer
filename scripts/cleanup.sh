#!/bin/bash
# Cleanup helper used by Makefile 'clean' and 'clean-deep' targets
# Usage: cleanup.sh <light|medium|deep>
set -Eeuo pipefail

MODE="${1:-medium}"

log() { echo "[cleanup] $*"; }

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require docker

case "$MODE" in
  light)
    log "Pruning stopped containers and dangling images (light)"
    docker container prune -f || true
    docker image prune -f || true
    ;;
  medium)
    log "Pruning containers, images, and builder cache (medium)"
    docker container prune -f || true
    docker image prune -f || true
    docker builder prune -f || true
    ;;
  deep)
    log "Performing deep prune of all unused data (deep)"
    docker system prune -af || true
    docker volume prune -f || true
    ;;
  *)
    echo "Usage: $0 <light|medium|deep>" >&2
    exit 2
    ;;
 esac

log "Cleanup complete"
