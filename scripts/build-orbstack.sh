#!/bin/bash
#
# Complete OrbStack build pipeline
# Usage: ./scripts/build-orbstack.sh [BUILD_MODE] [IMAGE_NAME] [VERSION]
#
# BUILD_MODE: "full", "fast", "dev"
#

set -euo pipefail

BUILD_MODE="${1:-fast}"
IMAGE_NAME="${2:-rzp-labs/namer}"
VERSION="${3:-$(git describe --tags --always --dirty 2>/dev/null || echo 'latest')}"
BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
GIT_HASH="$(git rev-parse --verify HEAD 2>/dev/null || echo 'unknown')"
ORBSTACK_VM="namer-build-env"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Building $IMAGE_NAME:$VERSION via OrbStack VM $ORBSTACK_VM..."

case "$BUILD_MODE" in
    "fast")
        echo "This skips tests for faster iteration during development"
        INCLUDE_TESTS="false"
        ;;
    "full")
        echo "This includes comprehensive testing (will take longer)"
        INCLUDE_TESTS="true"
        ;;
    "dev")
        echo "Development build - build stage only"
        INCLUDE_TESTS="false"
        ;;
    *)
        echo "❌ Unknown build mode: $BUILD_MODE. Use 'full', 'fast', or 'dev'" >&2
        exit 1
        ;;
esac

# Build arguments
BUILD_ARGS="--build-arg BUILD_DATE=$BUILD_DATE --build-arg GIT_HASH=$GIT_HASH --build-arg PROJECT_VERSION=$VERSION"

# Execute pipeline
echo "🔧 Step 1: Checking OrbStack setup..."
"$SCRIPT_DIR/check-orbstack.sh" "$ORBSTACK_VM"

echo "🔧 Step 2: Setting up Docker in VM..."
"$SCRIPT_DIR/setup-docker-vm.sh" "$ORBSTACK_VM"

echo "📁 Step 3: Copying build files..."
"$SCRIPT_DIR/copy-build-files.sh" "$ORBSTACK_VM" "$INCLUDE_TESTS"

echo "🏗️  Step 4: Building Docker image..."
"$SCRIPT_DIR/docker-build-vm.sh" "$ORBSTACK_VM" "$BUILD_MODE" "$IMAGE_NAME" "$VERSION" "$BUILD_ARGS"

if [ "$BUILD_MODE" != "dev" ]; then
    echo "📤 Step 5: Exporting image..."
    "$SCRIPT_DIR/export-docker-image.sh" "$ORBSTACK_VM" "$IMAGE_NAME" "$VERSION"
    
    echo "🏷️  Step 6: Ensuring latest tag exists..."
    # Ensure latest tag always exists (backup in case export script didn't create it)
    if ! docker image inspect "$IMAGE_NAME:latest" >/dev/null 2>&1; then
        echo "   Creating latest tag: $IMAGE_NAME:latest"
        docker tag "$IMAGE_NAME:$VERSION" "$IMAGE_NAME:latest"
    else
        echo "   Latest tag already exists: $IMAGE_NAME:latest"
    fi
    
    echo "✅ Build complete: $IMAGE_NAME:$VERSION"
    echo "✅ Latest tag available: $IMAGE_NAME:latest"
else
    echo "✅ Development build complete (not exported): $IMAGE_NAME:$VERSION"
fi
