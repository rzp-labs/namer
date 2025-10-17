#!/usr/bin/env bash
#
# Git Push Wrapper with Appropriate Timeout
#
# This script wraps 'git push' to ensure sufficient timeout for pre-push hooks.
#
# Pre-push hooks in this project:
# - pytest-full: ~90s typical, 600s timeout
# - docker-smoke-test: ~30-60s typical, 600s timeout (via run-docker-smoke-test.sh)
# Total typical: ~2 minutes, but can be longer on slow systems or cold builds
#
# Timeout Strategy:
# - Use 5 minutes (300s) as a reasonable default
# - Generous enough for typical execution + buffer
# - Not excessive (10min would be too long)
# - Can be overridden via GIT_PUSH_TIMEOUT environment variable
#
# Usage:
#   ./scripts/git-push-wrapper.sh [git push arguments...]
#
# Examples:
#   ./scripts/git-push-wrapper.sh origin main
#   ./scripts/git-push-wrapper.sh -u origin feature/my-branch
#   GIT_PUSH_TIMEOUT=600 ./scripts/git-push-wrapper.sh origin main  # Override timeout

set -euo pipefail

# Default timeout: 5 minutes (300 seconds)
TIMEOUT="${GIT_PUSH_TIMEOUT:-300}"

# Detect timeout command (macOS uses gtimeout, Linux uses timeout)
TIMEOUT_CMD=$(command -v gtimeout || command -v timeout || echo "")

if [ -n "$TIMEOUT_CMD" ]; then
	echo "🕐 Running git push with ${TIMEOUT}s timeout..."
	exec "$TIMEOUT_CMD" "$TIMEOUT" git push "$@"
else
	echo "⚠️  Warning: No timeout command available (install coreutils on macOS)"
	echo "🕐 Running git push without timeout limit..."
	exec git push "$@"
fi
