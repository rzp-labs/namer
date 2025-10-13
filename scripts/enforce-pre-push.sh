#!/usr/bin/env bash
# Enforce pre-push hook execution - detects and warns about --no-verify usage
#
# This script educates developers about the importance of pre-push hooks
# and encourages proper workflow practices.

set -euo pipefail

log() { echo "[enforce-pre-push] $*" >&2; }
error() { echo "❌ [enforce-pre-push] $*" >&2; }
warn() { echo "⚠️  [enforce-pre-push] $*" >&2; }

# Check if we're in a git repository
if ! git rev-parse --git-dir >/dev/null 2>&1; then
	error "Not in a git repository"
	exit 1
fi

# Get the git directory
GIT_DIR=$(git rev-parse --git-dir)

# Check if custom hooks path is configured
if hooks_path=$(git config --get core.hooksPath 2>/dev/null); then
	# Handle relative paths
	if [[ "$hooks_path" != /* ]]; then
		repo_root=$(git rev-parse --show-toplevel)
		HOOKS_DIR="$repo_root/$hooks_path"
	else
		HOOKS_DIR="$hooks_path"
	fi
else
	HOOKS_DIR="$GIT_DIR/hooks"
fi

PRE_PUSH_HOOK="$HOOKS_DIR/pre-push"

# Check if pre-push hook exists
if [[ ! -f "$PRE_PUSH_HOOK" ]]; then
	error "Pre-push hook not installed!"
	log "Hooks directory: $HOOKS_DIR"
	log "Run: make setup-dev"
	exit 1
fi

# Check if pre-push hook is executable
if [[ ! -x "$PRE_PUSH_HOOK" ]]; then
	error "Pre-push hook exists but is not executable!"
	log "Run: chmod +x $PRE_PUSH_HOOK"
	exit 1
fi

# Create a marker file to track bypass attempts
BYPASS_LOG="$GIT_DIR/pre-push-bypass.log"

# Function to log bypass attempts
log_bypass_attempt() {
	local timestamp
	local branch
	timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
	branch=$(git branch --show-current 2>/dev/null || echo "unknown")
	echo "[$timestamp] Bypass attempt detected on branch: $branch" >>"$BYPASS_LOG"
}

# Check git command history for --no-verify usage (educational warning)
check_bypass_usage() {
	# This is informational only - we detect via hook execution
	if [[ -f "$BYPASS_LOG" ]]; then
		local count
		count=$(wc -l <"$BYPASS_LOG" 2>/dev/null || echo "0")
		if [[ "$count" -gt 0 ]]; then
			warn "Detected $count previous bypass attempt(s) in this repository"
			warn "Review: $BYPASS_LOG"
		fi
	fi
}

# Main enforcement logic
enforce_pre_push() {
	log "Checking pre-push hook enforcement..."

	# Check for common bypass patterns in shell history (educational only)
	check_bypass_usage

	# Verify hook installation
	if [[ -f "$PRE_PUSH_HOOK" ]] && [[ -x "$PRE_PUSH_HOOK" ]]; then
		log "✅ Pre-push hook is properly installed"
		return 0
	else
		error "Pre-push hook is not properly configured"
		return 1
	fi
}

# Educational message about hook bypass
show_bypass_education() {
	cat <<'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  PRE-PUSH HOOK BYPASS DETECTED ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Using --no-verify bypasses critical quality and security checks:
  ❌ Full test suite with coverage
  ❌ Codacy security vulnerability scanning
  ❌ Docker build validation

WHY PRE-PUSH HOOKS MATTER:
  • Catch security vulnerabilities before they reach the team
  • Prevent broken builds from blocking others
  • Ensure code quality standards are maintained
  • Save CI time by catching issues locally

IF HOOKS ARE TOO SLOW:
  ✅ Break your work into smaller, focused commits
  ✅ Smaller commits = easier code review
  ✅ Smaller commits = better git history

TIME BREAKDOWN:
  • pytest (full suite): ~90 seconds
  • Codacy security: ~60-90 seconds
  • Docker smoke test: ~30-60 seconds

  Total: 2-3 minutes for high-confidence code quality

OPTIONAL TOOLS:
  • CodeRabbit AI review: Run manually with 'make review'

REMEMBER:
  "Small chunks of work with appropriate complexity enable quicker
   delivery times and faster reviews."

If you believe there's a legitimate reason to bypass hooks,
discuss with the team first.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
}

# Export function for use in hooks
export -f show_bypass_education

# Main execution
if [[ "${1:-}" == "--check" ]]; then
	enforce_pre_push
elif [[ "${1:-}" == "--log-bypass" ]]; then
	log_bypass_attempt
	show_bypass_education
elif [[ "${1:-}" == "--education" ]]; then
	show_bypass_education
else
	log "Usage: $0 [--check|--log-bypass|--education]"
	log "  --check       Verify pre-push hook is installed"
	log "  --log-bypass  Log a bypass attempt and show education"
	log "  --education   Show bypass education message"
	exit 2
fi
