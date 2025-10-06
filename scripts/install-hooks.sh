#!/usr/bin/env bash
# Install Git hooks using pre-commit for this repository.
# - pre-commit: fast checks (ruff, etc.) on staged files
# - pre-push: run validate.sh --fast
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$ROOT_DIR"

log() { echo "[install-hooks] $*"; }

have_cmd() { command -v "$1" > /dev/null 2>&1; }

run_pre_commit() {
    if have_cmd poetry && poetry run pre-commit --version > /dev/null 2>&1; then
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

log "Done. You can test hooks with: pre-commit run -a"
