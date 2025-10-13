#!/usr/bin/env bash
# Install Git hooks using pre-commit for this repository.
# - pre-commit: fast checks (ruff, etc.) on staged files
# - pre-push: run validate.sh --fast
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$ROOT_DIR"

log() { echo "[install-hooks] $*"; }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

run_pre_commit() {
	if have_cmd poetry && poetry run pre-commit --version >/dev/null 2>&1; then
		poetry run pre-commit "$@"
	elif have_cmd pre-commit; then
		pre-commit "$@"
	else
		log "pre-commit is not installed. Install via one of:"
		log "  - poetry add --group dev pre-commit"
		log "  - pipx install pre-commit"
		log "  - python3 -m pip install --user pre-commit"
		exit 1
	fi
}

log "Installing pre-commit hooks..."
run_pre_commit install

log "Installing pre-push hook..."
run_pre_commit install --hook-type pre-push

log "Hooks installed. Verifying configuration..."
run_pre_commit validate-config || {
	log "Invalid .pre-commit-config.yaml"
	exit 1
}

log "Verifying pre-push hook enforcement..."
if [[ -x "$ROOT_DIR/scripts/enforce-pre-push.sh" ]]; then
	"$ROOT_DIR/scripts/enforce-pre-push.sh" --check || {
		log "⚠️  Pre-push hook verification failed"
		exit 1
	}
else
	log "⚠️  enforce-pre-push.sh not found or not executable"
fi

log ""
log "✅ Git hooks installed successfully!"
log ""
log "Hook configuration:"
log "  • Pre-commit (~15-20s): Fast quality + functional validation"
log "  • Pre-push (~3-5min): Deep validation + security"
log ""
log "IMPORTANT: Pre-push hooks MUST NOT be bypassed (--no-verify)"
log "  → Small, focused commits = faster reviews = quicker delivery"
log ""
log "Test hooks with:"
log "  • pre-commit run --all-files"
log "  • pre-commit run --hook-stage pre-push --all-files"
