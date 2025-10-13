#!/usr/bin/env bash
# Capture CodeRabbit feedback to a file for later review and implementation
#
# This script wraps the CodeRabbit CLI to:
# 1. Run the review
# 2. Capture output to a timestamped file
# 3. Create/update a tracking file with all feedback
# 4. Provide summary statistics

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() { echo "[capture-coderabbit] $*" >&2; }
error() { echo "❌ [capture-coderabbit] $*" >&2; }
warn() { echo "⚠️  [capture-coderabbit] $*" >&2; }

# Configuration
FEEDBACK_DIR=".coderabbit/feedback"
TRACKING_FILE=".coderabbit/feedback-tracker.md"
ARCHIVE_DIR=".coderabbit/feedback/archive"

# Create directories if they don't exist
mkdir -p "$FEEDBACK_DIR" "$ARCHIVE_DIR"

# Function to update the tracking file
update_tracker() {
    local feedback_file="$1"
    local issue_count="$2"
    local status="$3"

    # Create tracking file if it doesn't exist
    if [[ ! -f "$TRACKING_FILE" ]]; then
        cat > "$TRACKING_FILE" <<'EOF'
# CodeRabbit Feedback Tracker

This file tracks CodeRabbit review feedback for later implementation.

## How to Use

1. **Review feedback files**: Check `.coderabbit/feedback/` for detailed reviews
2. **Prioritize issues**: Mark items below as `[ ]` TODO, `[x]` DONE, or `[-]` WONTFIX
3. **Implement fixes**: Address high-priority items in focused commits
4. **Archive old feedback**: Completed items are moved to `.coderabbit/feedback/archive/`

## Feedback Status Key

- `🔴 FAILED` - Review failed (syntax errors, etc.)
- `🟡 PENDING` - Review completed with issues to address
- `🟢 CLEAN` - No issues found
- `✅ IMPLEMENTED` - Issues addressed and verified
- `⏭️ DEFERRED` - Intentionally postponed

---

## Recent Feedback

EOF
    fi

    # Determine status emoji
    local status_emoji
    case "$status" in
        "FAILED")
            status_emoji="🔴 FAILED"
            ;;
        "SUCCESS")
            if [[ "$issue_count" -eq 0 ]]; then
                status_emoji="🟢 CLEAN"
            else
                status_emoji="🟡 PENDING"
            fi
            ;;
        *)
            status_emoji="❓ UNKNOWN"
            ;;
    esac

    # Add entry to tracking file
    {
        echo ""
        echo "### $(date -u +"%Y-%m-%d %H:%M UTC") - Branch: $BRANCH - Commit: $COMMIT"
        echo ""
        echo "**Status:** $status_emoji"
        echo "**Issues Found:** $issue_count"
        echo "**Feedback File:** [\`$feedback_file\`]($feedback_file)"
        echo ""

        if [[ "$issue_count" -gt 0 ]]; then
            echo "**Issues Summary:**"
            echo ""

            # Extract issue summaries from feedback file
            awk '/^File: / {
                file=$2;
            }
            /^Type: / {
                type=$2;
            }
            /^Comment:/ {
                getline; # Skip empty line
                getline comment; # Get first line of comment
                printf "- [ ] **%s** (%s): %s\n", file, type, comment;
            }' "$feedback_file" || true

            echo ""
        fi

        echo "---"
    } >> "$TRACKING_FILE"

    log "Updated tracking file: $TRACKING_FILE"
}

# Function to show summary statistics
show_summary() {
    local feedback_file="$1"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 CODERABBIT FEEDBACK SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Count issues by type
    local total_issues
    local potential_issues
    local style_issues
    local performance_issues

    total_issues=$(grep -c "^Type: " "$feedback_file" 2>/dev/null || echo "0")
    potential_issues=$(grep -c "^Type: potential_issue$" "$feedback_file" 2>/dev/null || echo "0")
    style_issues=$(grep -c "^Type: style$" "$feedback_file" 2>/dev/null || echo "0")
    performance_issues=$(grep -c "^Type: performance$" "$feedback_file" 2>/dev/null || echo "0")

    echo "Total Issues: $total_issues"
    echo "  • Potential Issues: $potential_issues"
    echo "  • Style Issues: $style_issues"
    echo "  • Performance Issues: $performance_issues"
    echo ""

    # Count unique files with issues
    local unique_files
    unique_files=$(grep "^File: " "$feedback_file" 2>/dev/null | cut -d' ' -f2 | sort -u | wc -l | tr -d ' ')
    echo "Files Affected: $unique_files"
    echo ""

    echo "📁 FEEDBACK LOCATION"
    echo "  • Detailed feedback: $feedback_file"
    echo "  • Tracking file: $TRACKING_FILE"
    echo ""

    echo "📝 NEXT STEPS"
    echo "  1. Review feedback: cat $feedback_file"
    echo "  2. Check tracker: cat $TRACKING_FILE"
    echo "  3. Prioritize issues in tracker (mark as [ ], [x], or [-])"
    echo "  4. Create focused commits to address high-priority items"
    echo ""

    if [[ "$total_issues" -gt 0 ]]; then
        echo "💡 TIP: Small, focused commits for each issue type enable faster reviews!"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Generate timestamp and filenames
TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
FEEDBACK_FILE="$FEEDBACK_DIR/${TIMESTAMP}_${BRANCH}_${COMMIT}.txt"

# Mode from first argument
MODE="${1:-validate}"

log "Running CodeRabbit review (mode: $MODE)"
log "Branch: $BRANCH"
log "Commit: $COMMIT"
log "Output: $FEEDBACK_FILE"

# Run CodeRabbit and capture output
if ! ./scripts/run-coderabbit.sh "$MODE" 2>&1 | tee "$FEEDBACK_FILE"; then
    EXIT_CODE=$?
    error "CodeRabbit review failed with exit code $EXIT_CODE"

    # Still save the output even if it failed
    log "Feedback saved to: $FEEDBACK_FILE"

    # Extract issue count from output
    ISSUE_COUNT=$(grep -c "^============================================================================$" "$FEEDBACK_FILE" 2>/dev/null || echo "0")

    # Update tracking file
    update_tracker "$FEEDBACK_FILE" "$ISSUE_COUNT" "FAILED"

    exit $EXIT_CODE
fi

log "✅ CodeRabbit review completed successfully"
log "Feedback saved to: $FEEDBACK_FILE"

# Extract issue count from output
ISSUE_COUNT=$(grep -c "^============================================================================$" "$FEEDBACK_FILE" 2>/dev/null || echo "0")

if [[ "$ISSUE_COUNT" -eq 0 ]]; then
    log "🎉 No issues found!"
else
    warn "Found $ISSUE_COUNT issue(s) to review"
fi

# Update tracking file
update_tracker "$FEEDBACK_FILE" "$ISSUE_COUNT" "SUCCESS"

# Show summary
show_summary "$FEEDBACK_FILE"

# Optionally create GitHub issues (controlled by environment variable)
if [[ "${CODERABBIT_CREATE_ISSUES:-0}" == "1" ]] && [[ "$ISSUE_COUNT" -gt 0 ]]; then
    log ""
    log "Creating GitHub issues from feedback..."

    if ./scripts/create-issues-from-coderabbit.sh "$FEEDBACK_FILE"; then
        log "✅ GitHub issues created successfully"
    else
        warn "Failed to create GitHub issues (non-blocking)"
    fi
fi

exit 0
