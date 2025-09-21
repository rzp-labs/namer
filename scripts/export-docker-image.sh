#!/bin/bash
#
# Export Docker image from OrbStack VM to host
# Usage: ./scripts/export-docker-image.sh [VM_NAME] [IMAGE_NAME] [VERSION] [EXPORT_DIR]
#

set -euo pipefail

ORBSTACK_VM="${1:-namer-build-env}"
IMAGE_NAME="${2:-rzp-labs/namer}"
VERSION="${3:-latest}"
EXPORT_DIR="${4:-./dist}"

echo "📤 Exporting image from VM..."

# Save image in VM
orbctl run -m "$ORBSTACK_VM" sudo docker save "$IMAGE_NAME:$VERSION" -o "/tmp/namer-$VERSION.tar"

# Fix file permissions for export
echo "🔧 Fixing file permissions for export..."
orbctl run -m "$ORBSTACK_VM" sudo chmod 644 "/tmp/namer-$VERSION.tar"

# Ensure export directory exists
echo "📁 Ensuring export directory exists..."
mkdir -p "$EXPORT_DIR"

# Pull image from VM to host
orbctl pull -m "$ORBSTACK_VM" "/tmp/namer-$VERSION.tar" "$EXPORT_DIR/namer-$VERSION.tar"

# Import to host Docker
echo "📥 Importing to host Docker..."
docker load -i "$EXPORT_DIR/namer-$VERSION.tar"

# Clean up tar file
rm "$EXPORT_DIR/namer-$VERSION.tar"

echo "✅ Image exported and loaded: $IMAGE_NAME:$VERSION"