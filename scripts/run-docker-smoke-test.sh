#!/usr/bin/env bash
# Wrapper script for Docker smoke test
# Provides proper error handling and clear feedback

set -Eeuo pipefail

# Color output helpers
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly GREEN='\033[0;32m'
readonly NC='\033[0m' # No Color

info() {
	echo -e "${GREEN}[INFO]${NC} $*" >&2
}

warn() {
	echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

error() {
	echo -e "${RED}[ERROR]${NC} $*" >&2
}

main() {
	# Check if Docker is available
	if ! command -v docker >/dev/null 2>&1; then
		warn "Docker not found - skipping Docker smoke test"
		warn "To enable: install Docker Desktop or Docker Engine"
		return 0 # Not an error, just skipping
	fi

	# Check if Docker daemon is running
	if ! docker info >/dev/null 2>&1; then
		warn "Docker daemon not running - skipping Docker smoke test"
		warn "To enable: start Docker daemon"
		return 0 # Not an error, just skipping
	fi

	# Check if Dockerfile exists
	if [ ! -f "./Dockerfile" ]; then
		error "Dockerfile not found"
		return 1
	fi

	info "Running Docker smoke test (build validation)..."
	info "This validates that the Dockerfile builds without errors"

	# Run Docker build with timeout (10 minutes to match pytest)
	# Build to 'build' target only for speed
	if ./scripts/timeout-wrapper.sh 600 docker build --quiet --target build . >/dev/null; then
		info "Docker smoke test passed - Dockerfile builds successfully"
		return 0
	else
		exit_code=$?
		error "Docker smoke test failed (exit code: $exit_code)"
		error "The Dockerfile has build errors - please fix before pushing"
		error "Run 'docker build .' locally to see detailed error messages"
		return $exit_code
	fi
}

main "$@"
