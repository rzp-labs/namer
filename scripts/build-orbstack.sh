#!/bin/bash
# Lightweight build wrapper used by Makefile targets
# Usage: build-orbstack.sh <fast|full|dev> <image_name> <version>
set -Eeuo pipefail

MODE="${1:-fast}"
IMAGE_NAME="${2:-nehpz/namer}"
VERSION="${3:-latest}"

BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
PROJECT_VERSION=$(grep -E 'version\s*=\s*"' pyproject.toml 2>/dev/null | head -1 | cut -d'"' -f2 || echo "dev")

COMMON_ARGS=(
  -f Dockerfile \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --build-arg GIT_HASH="$GIT_HASH" \
  --build-arg PROJECT_VERSION="$PROJECT_VERSION" \
  -t "$IMAGE_NAME:$VERSION" \
  -t "$IMAGE_NAME:latest" \
  .
)

echo "[build-orbstack] Mode: $MODE"
echo "[build-orbstack] Image: $IMAGE_NAME:$VERSION"
echo "[build-orbstack] Build date: $BUILD_DATE"
echo "[build-orbstack] Git hash: $GIT_HASH"
echo "[build-orbstack] Project version: $PROJECT_VERSION"

case "$MODE" in
  fast)
    docker build "${COMMON_ARGS[@]}"
    ;;
  full)
    if [[ -x ./validate.sh ]]; then
      echo "[build-orbstack] Running validation before full build..."
      ./validate.sh
    fi
    docker build --no-cache "${COMMON_ARGS[@]}"
    ;;
  dev)
    # If your Dockerfile has a dedicated builder stage, feel free to add --target here.
    docker build --progress=plain "${COMMON_ARGS[@]}"
    ;;
  *)
    echo "Usage: $0 <fast|full|dev> <image_name> <version>" >&2
    exit 2
    ;;
 esac
