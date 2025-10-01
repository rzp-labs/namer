#!/usr/bin/env bash
# Wrapper around the CodeRabbit CLI to harmonize usage across hooks and scripts.
#
# Modes:
#   pre-commit  - runs on local unstaged/staged changes (opt-in via CODERABBIT_PRECOMMIT=1)
#   validate    - runs against committed changes in the current branch (disable via CODERABBIT_VALIDATE=0)
#   branch      - runs a full branch review (used by `make review`)
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

log() { echo "[coderabbit] $*"; }

if ! command -v coderabbit >/dev/null 2>&1; then
  log "CodeRabbit CLI not found. Install it before running this script."
  exit 1
fi

MODE="${1:-}"
if [[ -z "$MODE" ]]; then
  cat <<'EOF'
Usage: scripts/run-coderabbit.sh <mode>

Modes:
  pre-commit  Run review on local (uncommitted) changes. Requires CODERABBIT_PRECOMMIT=1.
  validate    Run review on branch commits. Disable with CODERABBIT_VALIDATE=0.
  branch      Run review on full branch (manual, via make review).

Environment variables:
  CODERABBIT_BASE         Override base branch (default: main)
  CODERABBIT_PRECOMMIT    Set to 1 to enable pre-commit runs (default: 0)
  CODERABBIT_VALIDATE     Set to 0 to skip validate runs (default: 1)
  CODERABBIT_EXTRA_ARGS   Extra arguments appended to `coderabbit review` (supports shell-style quoting)
EOF
  exit 2
fi

BASE_BRANCH="${CODERABBIT_BASE:-main}"
export CODERABBIT_NON_INTERACTIVE=1

ARGS=(review --plain --no-color)
case "$MODE" in
  pre-commit)
    if [[ "${CODERABBIT_PRECOMMIT:-0}" != "1" ]]; then
      log "Skipping pre-commit review (set CODERABBIT_PRECOMMIT=1 to enable)."
      exit 0
    fi
    ARGS+=(--type uncommitted --base "$BASE_BRANCH")
    ;;
  validate)
    if [[ "${CODERABBIT_VALIDATE:-1}" == "0" ]]; then
      log "Skipping validate review (set CODERABBIT_VALIDATE=1 to enable)."
      exit 0
    fi
    ARGS+=(--type committed --base "$BASE_BRANCH")
    ;;
  branch)
    ARGS+=(--type all --base "$BASE_BRANCH")
    ;;
  *)
    log "Unknown mode: $MODE"
    exit 2
    ;;
esac

if [[ -n "${CODERABBIT_EXTRA_ARGS:-}" ]]; then
  if ! eval 'EXTRA_ARGS=('"${CODERABBIT_EXTRA_ARGS}"')'; then
    log "Failed to parse CODERABBIT_EXTRA_ARGS"
    exit 2
  fi
  ARGS+=("${EXTRA_ARGS[@]}")
fi

log "Running CodeRabbit review (mode: $MODE, base: $BASE_BRANCH)..."
if ! coderabbit "${ARGS[@]}"; then
  log "CodeRabbit review reported issues."
  exit 1
fi

log "CodeRabbit review completed successfully."
