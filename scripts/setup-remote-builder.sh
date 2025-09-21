#!/bin/bash
set -euo pipefail

# Configuration
REMOTE_HOST="${BUILDX_REMOTE_HOST:-example.com}"
REMOTE_USER="${BUILDX_REMOTE_USER:-docker}"
BUILDER_NAME="${BUILDER_NAME:-namer-remote}"

echo "🏗️  Setting up remote buildx builder: $BUILDER_NAME"

# Create remote buildx builder
docker buildx create \
    --name "$BUILDER_NAME" \
    --driver docker-container \
    --driver-opt network=host \
    "ssh://$REMOTE_USER@$REMOTE_HOST"

# Use the remote builder
docker buildx use "$BUILDER_NAME"

# Bootstrap the builder (download/start container)
echo "Bootstrapping remote builder..."
docker buildx inspect --bootstrap

echo "✅ Remote builder setup complete!"
echo "Builder details:"
docker buildx inspect "$BUILDER_NAME"

# Example usage script
cat << 'EOF' > scripts/build-with-remote.sh
#!/bin/bash
set -euo pipefail

BUILDER_NAME="${BUILDER_NAME:-namer-remote}"
IMAGE_NAME="${IMAGE_NAME:-rzp-labs/namer}"
VERSION="${VERSION:-$(git describe --tags --always)}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"

# Ensure we're using the remote builder
docker buildx use "$BUILDER_NAME"

# Build metadata
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_HASH=$(git rev-parse --verify HEAD)

echo "🚀 Building multi-platform image on remote builder..."
echo "Platforms: $PLATFORMS"
echo "Version: $VERSION"

# Multi-platform build and push
docker buildx build \
    --platform "$PLATFORMS" \
    --build-arg "BUILD_DATE=$BUILD_DATE" \
    --build-arg "GIT_HASH=$GIT_HASH" \
    --build-arg "PROJECT_VERSION=$VERSION" \
    --tag "$IMAGE_NAME:$VERSION" \
    --tag "$IMAGE_NAME:latest" \
    --push \
    .

echo "✅ Multi-platform build complete!"
echo "Images pushed with tags: $VERSION, latest"
EOF

chmod +x scripts/build-with-remote.sh
echo "Created scripts/build-with-remote.sh for multi-platform builds"
