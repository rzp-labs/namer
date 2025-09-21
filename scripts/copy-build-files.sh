#!/bin/bash
#
# Copy essential build files to OrbStack VM
# Usage: ./scripts/copy-build-files.sh [VM_NAME] [INCLUDE_TESTS]
#
# INCLUDE_TESTS: "true" to include test directory, "false" or unset to exclude
#

set -euo pipefail

ORBSTACK_VM="${1:-namer-build-env}"
INCLUDE_TESTS="${2:-false}"

echo "📁 Creating efficient project copy for VM..."
echo "   📏 Project size: $(du -sh . | cut -f1) (test_dirs: $(du -sh test_dirs | cut -f1))"
echo "   ℹ️  Excluding test_dirs (29GB of test videos) from Docker build"

# Clean and create build directory
orbctl run -m "$ORBSTACK_VM" rm -rf /tmp/namer-build
orbctl run -m "$ORBSTACK_VM" mkdir -p /tmp/namer-build

echo "📄 Copying only essential Docker build files..."

# Copy essential files individually (much faster than tar with exclusions)
echo "   • Dockerfile and build configs..."
orbctl push -m "$ORBSTACK_VM" Dockerfile /tmp/namer-build/Dockerfile
orbctl push -m "$ORBSTACK_VM" docker-entrypoint-user.sh /tmp/namer-build/docker-entrypoint-user.sh
orbctl push -m "$ORBSTACK_VM" pyproject.toml /tmp/namer-build/pyproject.toml
orbctl push -m "$ORBSTACK_VM" poetry.lock /tmp/namer-build/poetry.lock
orbctl push -m "$ORBSTACK_VM" package.json /tmp/namer-build/package.json || true
orbctl push -m "$ORBSTACK_VM" pnpm-lock.yaml /tmp/namer-build/pnpm-lock.yaml || true
orbctl push -m "$ORBSTACK_VM" webpack.prod.js /tmp/namer-build/webpack.prod.js || true

echo "   • Source code directories..."
orbctl push -m "$ORBSTACK_VM" namer /tmp/namer-build/namer
orbctl push -m "$ORBSTACK_VM" src /tmp/namer-build/src || true

# Conditionally include test directory
if [ "$INCLUDE_TESTS" = "true" ]; then
    echo "   • Test directory..."
    orbctl push -m "$ORBSTACK_VM" test /tmp/namer-build/test || true
fi

echo "   • Essential scripts and configs..."
orbctl push -m "$ORBSTACK_VM" scripts /tmp/namer-build/scripts || true
orbctl push -m "$ORBSTACK_VM" config /tmp/namer-build/config || true
orbctl push -m "$ORBSTACK_VM" docs /tmp/namer-build/docs || true

echo "   • Build system files..."
orbctl push -m "$ORBSTACK_VM" .dockerignore /tmp/namer-build/.dockerignore || true
orbctl push -m "$ORBSTACK_VM" readme.rst /tmp/namer-build/readme.rst || true
orbctl push -m "$ORBSTACK_VM" videohashes /tmp/namer-build/videohashes || true

echo "   ✓ Essential files copied (excluded 29GB test_dirs, included all build essentials)"
