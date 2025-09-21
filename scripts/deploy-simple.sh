#!/bin/bash
set -euo pipefail

# Configuration
REGISTRY="ghcr.io"
IMAGE_NAME="${IMAGE_NAME:-rzp-labs/namer}"  # Change to your GitHub username/repo
VERSION="${VERSION:-latest}"
CONTAINER_NAME="${CONTAINER_NAME:-namer}"

echo "🚀 Deploying $IMAGE_NAME:$VERSION from GitHub Container Registry"

# Pull latest image
echo "📥 Pulling image from registry..."
docker pull "$REGISTRY/$IMAGE_NAME:$VERSION"

# Stop and remove existing container
echo "🛑 Stopping existing container..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Run new container
echo "▶️  Starting new container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --restart unless-stopped \
    -p 6980:6980 \
    -v /opt/namer/config:/config \
    -v /opt/namer/media:/media \
    -v /opt/namer/logs:/logs \
    "$REGISTRY/$IMAGE_NAME:$VERSION"

# Verify deployment
echo "✅ Deployment complete!"
echo "Container status:"
docker ps --filter name="$CONTAINER_NAME"

echo "📋 To view logs:"
echo "  docker logs -f $CONTAINER_NAME"

echo "🌐 Web UI should be available at:"
echo "  http://$(hostname -I | awk '{print $1}'):6980"
