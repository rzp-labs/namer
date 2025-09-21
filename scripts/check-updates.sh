#!/bin/bash
set -euo pipefail

# Configuration  
REGISTRY="ghcr.io"
IMAGE_NAME="rzp-labs/namer"  # Update with your username/repo
CURRENT_TAG="latest"

echo "🔍 Checking for updates to $IMAGE_NAME..."

# Get local image digest
LOCAL_DIGEST=$(docker images --digests "$REGISTRY/$IMAGE_NAME:$CURRENT_TAG" --format "{{.Digest}}" 2>/dev/null || echo "none")

# Get remote image digest  
REMOTE_DIGEST=$(docker manifest inspect "$REGISTRY/$IMAGE_NAME:$CURRENT_TAG" 2>/dev/null | jq -r '.config.digest' || echo "unknown")

echo "Local digest:  $LOCAL_DIGEST"
echo "Remote digest: $REMOTE_DIGEST"

if [ "$LOCAL_DIGEST" != "$REMOTE_DIGEST" ] && [ "$REMOTE_DIGEST" != "unknown" ]; then
    echo "🆕 New version available!"
    echo "Run in Dockge: Stop → Pull → Start"
    exit 1
else
    echo "✅ Up to date!"
    exit 0
fi
