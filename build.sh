#!/bin/bash
#
# Build script for Namer with Intel GPU hardware acceleration
#
set -e

echo "Building Namer with Intel GPU hardware acceleration support..."
echo "This supports Intel Arc GPUs, UHD Graphics, and other Intel GPUs with QSV"

# Set build variables
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
PROJECT_VERSION=$(grep version pyproject.toml 2>/dev/null | cut -d'"' -f2 || echo "dev")

echo "Build info:"
echo "  Date: $BUILD_DATE"
echo "  Git Hash: $GIT_HASH"
echo "  Version: $PROJECT_VERSION"

# Build the Docker image
echo "Building Docker image..."
docker build \
    -f Dockerfile \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg GIT_HASH="$GIT_HASH" \
    --build-arg PROJECT_VERSION="$PROJECT_VERSION" \
    -t namer:intel-hwaccell \
    .

echo "Build complete!"
echo ""
echo "To test Intel GPU detection, run:"
echo "  docker run --rm --device /dev/dri:/dev/dri -e DEBUG=true -e TEST_GPU=true namer:intel-hwaccell /usr/local/bin/detect-gpu.sh"
echo ""
echo "To run with Intel GPU hardware acceleration:"
echo "  docker run -d --name namer-intel-hwaccell --device /dev/dri:/dev/dri -v ./config:/config -v ./media:/app/media -p 6980:6980 namer:intel-hwaccell"
echo ""
echo "Supported Intel GPUs:"
echo "  ✅ Arc B-series (B580, B570, B770) - AV1 + H.264/H.265"
echo "  ✅ Arc A-series (A770, A750, A580, A380) - H.264/H.265"  
echo "  ✅ Intel UHD Graphics (770, 730, 710) - H.264/H.265"
echo "  ✅ Intel Xe Graphics - H.264/H.265"
echo "  ✅ Other Intel GPUs with QSV support"
