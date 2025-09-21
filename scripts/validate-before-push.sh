#!/bin/bash
set -euo pipefail

echo "🔍 Pre-push validation for GitHub Actions..."

# 1. Verify essential files exist
echo "✅ Checking essential files..."
required_files=(
    "Dockerfile"
    ".github/workflows/docker-build.yml"
    "pyproject.toml"
    "namer/metadataapi.py"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
done

# 2. Test architecture detection
echo "✅ Testing architecture detection..."
ARCH=$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/')
echo "Detected architecture: $ARCH"

# 3. Validate Docker Compose syntax
echo "✅ Validating Docker Compose files..."
for compose_file in docker-compose*.yml; do
    if [[ -f "$compose_file" ]]; then
        echo "Validating $compose_file..."
        docker compose -f "$compose_file" config >/dev/null 2>&1 || {
            echo "❌ Invalid Docker Compose syntax in $compose_file"
            exit 1
        }
    fi
done

# 4. Check that key StashDB changes are present
echo "✅ Verifying StashDB integration..."
if ! grep -q "class StashDBProvider" namer/metadata_providers/stashdb_provider.py 2>/dev/null; then
    echo "❌ StashDB integration not found in metadata_providers/stashdb_provider.py"
    exit 1
fi

if ! grep -q "StashDBProvider" namer/metadata_providers/factory.py 2>/dev/null; then
    echo "❌ StashDB factory integration not found"
    exit 1
fi

# 5. Run a quick test
echo "✅ Running quick integration test..."
if ! poetry run python -c "
from namer.metadata_providers.stashdb_provider import StashDBProvider
provider = StashDBProvider()
print('StashDB provider initialized successfully')
"; then
    echo "❌ StashDB integration test failed"
    exit 1
fi

# 6. Check linting
echo "✅ Checking code format..."
if ! poetry run ruff check .; then
    echo "❌ Code formatting issues found"
    exit 1
fi

echo ""
echo "🎉 All validations passed!"
echo "Ready to push to GitHub Actions:"
echo ""
echo "  git add ."
echo "  git commit -m 'Add StashDB integration with improved CI/CD'"
echo "  git push origin main"
echo ""
echo "After push, GitHub Actions will:"
echo "  • Build multi-platform Docker images (AMD64 + ARM64)"
echo "  • Run full test suite in Linux environment"
echo "  • Push to ghcr.io/rzp-labs/namer:latest"
echo "  • Ready for deployment in Dockge/unRAID"
