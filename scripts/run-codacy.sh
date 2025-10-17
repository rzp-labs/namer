#!/usr/bin/env bash
# Wrapper script for Codacy security analysis
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
    # Check if Codacy token is set
    if [ -z "${CODACY_PROJECT_TOKEN:-}" ]; then
        warn "CODACY_PROJECT_TOKEN not set - skipping Codacy security analysis"
        warn "To enable: export CODACY_PROJECT_TOKEN=<your-token>"
        return 0  # Not an error, just skipping
    fi

    # Check if Codacy CLI script exists
    if [ ! -f "./.codacy/cli.sh" ]; then
        error "Codacy CLI script not found at ./.codacy/cli.sh"
        return 1
    fi

    # Make sure it's executable
    if [ ! -x "./.codacy/cli.sh" ]; then
        chmod +x "./.codacy/cli.sh"
    fi

    info "Running Codacy security analysis..."

    # Run Codacy analysis with timeout
    if ./scripts/timeout-wrapper.sh 300 ./.codacy/cli.sh analyze --verbose; then
        info "Codacy security analysis passed"
        return 0
    else
        exit_code=$?
        error "Codacy security analysis failed (exit code: $exit_code)"
        error "Please review and fix security issues before pushing"
        return $exit_code
    fi
}

main "$@"
