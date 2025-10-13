#!/usr/bin/env bash
#
# timeout-wrapper.sh - Cross-platform timeout wrapper for git hooks
#
# Usage: timeout-wrapper.sh <seconds> <command> [args...]
#
# This script provides a unified interface for running commands with timeouts
# across different platforms (macOS uses gtimeout, Linux uses timeout).
#
# Examples:
#   timeout-wrapper.sh 180 pytest --cov
#   timeout-wrapper.sh 300 docker build .
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

error() {
	echo -e "${RED}ERROR: $*${NC}" >&2
}

warn() {
	echo -e "${YELLOW}WARNING: $*${NC}" >&2
}

# Validate arguments
if [ $# -lt 2 ]; then
	error "Usage: $0 <timeout_seconds> <command> [args...]"
	exit 1
fi

TIMEOUT_SECONDS="$1"
shift

# Validate timeout is a number
if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
	error "Timeout must be a positive integer, got: $TIMEOUT_SECONDS"
	exit 1
fi

# Detect available timeout command
# Try gtimeout first (common on macOS via coreutils), then timeout (Linux)
TIMEOUT_CMD=""
if command -v gtimeout >/dev/null 2>&1; then
	TIMEOUT_CMD="gtimeout"
elif command -v timeout >/dev/null 2>&1; then
	TIMEOUT_CMD="timeout"
fi

# Execute command with or without timeout
if [ -n "$TIMEOUT_CMD" ]; then
	# Timeout available - use it
	exec "$TIMEOUT_CMD" "$TIMEOUT_SECONDS" "$@"
else
	# No timeout command available - warn and run without timeout
	warn "Neither 'timeout' nor 'gtimeout' found. Running without timeout limit."
	warn "Install coreutils (brew install coreutils) for timeout support on macOS."
	exec "$@"
fi
