#!/bin/bash
#
# Test Docker container functionality
# Usage: ./scripts/test-docker.sh [IMAGE_NAME] [VERSION] [TEST_TYPE]
#
# TEST_TYPE: "basic", "integration"
#

set -euo pipefail

IMAGE_NAME="${1:-rzp-labs/namer}"
VERSION="${2:-latest}"
TEST_TYPE="${3:-basic}"

case "$TEST_TYPE" in
    "basic")
        echo "🧪 Running basic functionality tests..."
        echo "   Testing namer CLI help..."
        docker run --rm --entrypoint="" "$IMAGE_NAME:$VERSION" namer --help > /dev/null
        echo "   Testing namer suggest help..."
        docker run --rm --entrypoint="" "$IMAGE_NAME:$VERSION" namer suggest --help > /dev/null
        echo "✅ Basic tests passed"
        ;;
    
    "integration")
        echo "🧪 Running integration tests..."
        if [ -d "test/integration" ] && [ -f "test/integration/test.sh" ]; then
            cd test/integration
            ./test.sh
            echo "✅ Integration tests passed"
        elif [ -d "test_dirs" ] && [ -f "test_dirs/test.sh" ]; then
            cd test_dirs
            ./test.sh
            echo "✅ Integration tests passed"
        else
            echo "❌ Integration test directory not found"
            exit 1
        fi
        ;;
esac
