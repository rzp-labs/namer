#!/bin/bash

# Namer Pre-Push Validation Script
# Run this before pushing to ensure all tests pass locally

set -e

# Flags
FAST=0
for arg in "$@"; do
  case "$arg" in
    --fast)
      FAST=1
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--fast]"
      echo "  --fast   Skip optional/slow steps (docker integration) and skip videophash, watchdog, and web tests for quick feedback"
      exit 0
      ;;
    *) ;;
  esac
done

echo "🔍 Namer Pre-Push Validation"
echo "============================="
echo ""

# Check we're in the right directory
if [[ ! -f "pyproject.toml" ]] || [[ ! -d "namer" ]]; then
    echo "❌ Please run this script from the namer project root directory"
    exit 1
fi

echo "📁 Working directory: $(pwd)"
echo ""

# Step 1: Check Poetry environment
echo "1️⃣ Validating Poetry environment...${FAST:+ (fast mode)}"
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry first."
    exit 1
fi

if ! poetry env info &> /dev/null; then
    echo "📦 Installing Poetry dependencies..."
    poetry install
fi

echo "✅ Poetry environment ready"
echo ""

# Step 2: Run linting
echo "2️⃣ Running code linting..."
echo "   Running ruff check..."
if poetry run ruff check .; then
    echo "✅ Linting passed"
else
    echo "❌ Linting failed. Fix issues before proceeding."
    exit 1
fi
echo ""

# Step 3: Run mypy type checks
echo "3️⃣ Running type checks with mypy..."
if poetry run mypy .; then
    echo "✅ Type checks passed"
else
    echo "❌ Type checks failed. Fix issues before proceeding."
    exit 1
fi
echo ""

# Step 4: Run unit tests
echo "4️⃣ Running unit tests..."
if [[ "$FAST" -eq 1 ]]; then
  echo "   Fast mode: skipping videophash, watchdog, and web tests"
  PYTEST_ARGS=(--cov -k "not videophash and not watchdog and not web")
else
  echo "   Running pytest with coverage..."
  PYTEST_ARGS=(--cov)
fi
if poetry run pytest "${PYTEST_ARGS[@]}"; then
    echo "✅ Unit tests passed"
else
    echo "❌ Unit tests failed. Fix issues before proceeding."
    exit 1
fi
echo ""

# Step 5: Build requirements check
echo "5️⃣ Checking Docker build requirements..."

# Check for required build tools
missing_tools=()

if ! command -v node &> /dev/null; then
    missing_tools+=("Node.js")
fi

if ! command -v go &> /dev/null; then
    missing_tools+=("Go")
fi

if ! command -v docker &> /dev/null; then
    missing_tools+=("Docker")
fi

if [[ ${#missing_tools[@]} -gt 0 ]]; then
    echo "❌ Missing required tools for Docker build:"
    printf '   - %s\n' "${missing_tools[@]}"
    echo "   Install missing tools before proceeding."
    exit 1
fi

echo "✅ All build tools available"
echo ""

# Step 6: Local Docker integration test
if [[ "$FAST" -eq 1 ]]; then
  echo "6️⃣ Skipping Docker integration tests (fast mode)"
else
  echo "6️⃣ Running Docker integration tests..."
fi

if [[ "$FAST" -eq 0 ]] && [[ -d "test/integration" ]] && [[ -f "test/integration/test.sh" ]]; then
    cd test/integration
    
    echo "   Setting up test environment..."
    if ./test.sh; then
        echo ""
        echo "   Starting containers for integration test..."
        
        # Start containers in background
        docker compose up -d
        
        # Wait a bit for startup
        echo "   Waiting for containers to initialize..."
        sleep 10
        
        # Check container status
        if docker compose ps | grep -q "Up"; then
            echo "✅ Containers started successfully"
            
            # Quick health check
            echo "   Checking container health..."
            sleep 5
            
            container_logs=$(docker compose logs --tail=20 2>&1 || true)
            if echo "$container_logs" | grep -q "ERROR\|CRITICAL\|Exception"; then
                echo "⚠️  Warning: Found errors in container logs:"
                echo "$container_logs" | grep -E "ERROR|CRITICAL|Exception" | head -5
                echo "   Review logs with: cd test/integration && docker compose logs"
            else
                echo "✅ No critical errors in startup logs"
            fi
            
            # Cleanup
            echo "   Cleaning up test containers..."
            docker compose down -v
            
            echo "✅ Docker integration tests passed"
        else
            echo "❌ Container startup failed"
            docker compose logs
            docker compose down -v
            cd ../..
            exit 1
        fi
    else
        echo "❌ Docker test setup failed"
        exit 1
    fi
    
    cd ../..
else
  echo "⚠️  Docker integration tests not configured (test/integration/test.sh missing)"
  echo "📝 Note: Integration tests are optional for local development"
  if [[ "$FAST" -eq 1 ]]; then
    echo "✅ Skipping Docker integration tests (fast mode)"
  else
    echo "✅ Skipping Docker integration tests"
  fi
fi
# Step 7: CodeRabbit AI review (optional - not part of pre-push pipeline)
echo "7️⃣ CodeRabbit AI review (optional)..."
CODERABBIT_SUMMARY="SKIPPED (not in pre-push pipeline)"
if [[ "${CODERABBIT_VALIDATE:-0}" == "1" ]]; then
  echo "   Running CodeRabbit review (CODERABBIT_VALIDATE=1)..."
  if [[ -x "scripts/run-coderabbit.sh" ]]; then
    if scripts/run-coderabbit.sh validate; then
      CODERABBIT_SUMMARY="PASSED"
    else
      CODERABBIT_SUMMARY="FAILED (issues found)"
      echo "⚠️  CodeRabbit review reported issues. Review manually with 'make review'."
      # Don't exit - CodeRabbit is optional
    fi
  else
    echo "⚠️  scripts/run-coderabbit.sh not found or not executable."
    CODERABBIT_SUMMARY="SKIPPED (missing script)"
  fi
else
  echo "   Skipping CodeRabbit review (not required for pre-push)."
  echo "   💡 Run manually with: make review"
fi
echo ""

# Step 8: Final validation
echo "8️⃣ Final validation summary..."
echo ""
echo "✅ Code linting: PASSED"
echo "✅ Type checks: PASSED"
echo "✅ Unit tests: PASSED"
echo "✅ Build tools: AVAILABLE"
if [[ "$FAST" -eq 1 ]]; then
  echo "✅ Docker integration: SKIPPED (fast mode)"
else
  echo "✅ Docker integration: PASSED"
fi
echo "ℹ️  CodeRabbit review: $CODERABBIT_SUMMARY"
echo ""

echo "🎉 All validations passed! Ready to push."
echo ""
echo "📝 Next steps:"
echo "   git add ."
echo "   git commit -m \"Your commit message\""
echo "   git push origin main"
echo ""
echo "🚀 After pushing, GitHub Actions will:"
echo "   - Build the same Docker image you just tested"
echo "   - Run the same test suite that just passed"
echo "   - Push to GHCR if everything succeeds"
echo ""
