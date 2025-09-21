#!/bin/bash
#
# Build Docker image in OrbStack VM
# Usage: ./scripts/docker-build-vm.sh [VM_NAME] [BUILD_MODE] [IMAGE_NAME] [VERSION] [BUILD_ARGS...]
#
# BUILD_MODE: "full" (default), "fast" (skip tests), "dev" (development target only)
#

set -euo pipefail

ORBSTACK_VM="${1:-namer-build-env}"
BUILD_MODE="${2:-full}"
IMAGE_NAME="${3:-rzp-labs/namer}"
VERSION="${4:-latest}"
shift 4 2>/dev/null || true  # Remove first 4 args, ignore error if less than 4
BUILD_ARGS="$*"

case "$BUILD_MODE" in
    "fast")
        echo "🛠️  Starting FAST Docker build in VM (skipping tests)..."
        DOCKERFILE_PATCH='sed -i "s/poetry run poe build_all/poetry run poe build_fast/" Dockerfile'
        ;;
    "dev")
        echo "🚀 Starting development build (build stage only)..."
        BUILD_ARGS="--target build $BUILD_ARGS"
        DOCKERFILE_PATCH="true"  # No patch needed
        ;;
    "full"|*)
        echo "🏗️  Starting Docker build in VM (this will take several minutes)..."
        DOCKERFILE_PATCH="true"  # No patch needed
        ;;
esac

echo "   You should see Docker build output below:"

# Build the Docker image
orbctl run -m "$ORBSTACK_VM" bash -c "
    cd /tmp/namer-build && 
    $DOCKERFILE_PATCH && 
    echo \"Starting build at \$(date)...\" && 
    sudo docker build --platform linux/amd64 $BUILD_ARGS -t \"$IMAGE_NAME:$VERSION\" -t \"$IMAGE_NAME:latest\" . && 
    echo \"✓ Build completed at \$(date)\"
"

echo "✅ Docker build complete in VM: $IMAGE_NAME:$VERSION"