#!/bin/bash
set -euo pipefail

# Configuration
REMOTE_HOST="${DOCKER_REMOTE_HOST:-example.com}"
REMOTE_USER="${DOCKER_REMOTE_USER:-docker}"
BUILD_CONTEXT="${BUILD_CONTEXT:-/tmp/namer-build}"
IMAGE_NAME="${IMAGE_NAME:-rzp-labs/namer}"
VERSION="${VERSION:-latest}"

echo "🚀 Building Docker image on remote host: $REMOTE_HOST"

# Create remote Docker context if it doesn't exist
if ! docker context ls | grep -q "remote-$REMOTE_HOST"; then
    echo "Creating remote Docker context..."
    docker context create "remote-$REMOTE_HOST" \
        --docker "host=ssh://$REMOTE_USER@$REMOTE_HOST"
fi

# Use remote context
echo "Switching to remote Docker context..."
docker context use "remote-$REMOTE_HOST"

# Build metadata
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_HASH=$(git rev-parse --verify HEAD)

# Create build directory on remote host
echo "Preparing build context on remote host..."
ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $BUILD_CONTEXT"

# Sync source code to remote host (excluding large files)
echo "Syncing source code..."
rsync -av --exclude='.git' \
          --exclude='node_modules' \
          --exclude='__pycache__' \
          --exclude='.pytest_cache' \
          --exclude='dist' \
          --exclude='*.pyc' \
          ./ "$REMOTE_USER@$REMOTE_HOST:$BUILD_CONTEXT/"

# Build on remote host
echo "Building Docker image on remote host..."
docker build "$BUILD_CONTEXT" \
    --build-arg "BUILD_DATE=$BUILD_DATE" \
    --build-arg "GIT_HASH=$GIT_HASH" \
    --build-arg "PROJECT_VERSION=$VERSION" \
    --tag "$IMAGE_NAME:$VERSION" \
    --tag "$IMAGE_NAME:latest"

# Test the build
echo "Testing built image..."
docker run --rm "$IMAGE_NAME:$VERSION" namer --help

# Clean up remote build context
echo "Cleaning up..."
ssh "$REMOTE_USER@$REMOTE_HOST" "rm -rf $BUILD_CONTEXT"

# Switch back to local context
docker context use default

echo "✅ Remote build complete! Image: $IMAGE_NAME:$VERSION"
echo "To use the remote image locally:"
echo "  docker context use remote-$REMOTE_HOST"
echo "  docker pull $IMAGE_NAME:$VERSION"
echo "  docker context use default"
