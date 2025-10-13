#!/usr/bin/env bash
# Create GitHub issues from CodeRabbit feedback
#
# This script parses CodeRabbit feedback and creates GitHub issues
# for each finding, allowing them to be tracked, prioritized, and
# implemented alongside other project issues.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() { echo "[create-issues] $*" >&2; }
error() { echo "❌ [create-issues] $*" >&2; }
# shellcheck disable=SC2317
warn() { echo "⚠️  [create-issues] $*" >&2; }

# Function to create a GitHub issue from parsed data
create_issue_from_data() {
    local data_file="$1"

    # Extract fields from the data
    local file_path=""
    local line_info=""
    local issue_type=""
    local comment=""
    local diff=""
    local prompt=""

    local in_comment=false
    local in_diff=false
    local in_prompt=false

    while IFS= read -r line; do
        if [[ "$line" =~ ^File:\ (.+)$ ]]; then
            file_path="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^Line:\ (.+)$ ]]; then
            line_info="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^Type:\ (.+)$ ]]; then
            issue_type="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^Comment:$ ]]; then
            in_comment=true
            in_diff=false
            in_prompt=false
            comment=""
        elif [[ "$line" =~ ^Apply\ this\ diff ]]; then
            in_comment=false
            in_diff=true
            in_prompt=false
            diff="## Suggested Fix\n\n"
        elif [[ "$line" =~ ^Prompt\ for\ AI\ Agent:$ ]]; then
            in_comment=false
            in_diff=false
            in_prompt=true
            prompt="## AI Agent Prompt\n\n"
        elif [[ -n "$line" ]]; then
            if $in_comment; then
                comment+="$line\n"
            elif $in_diff; then
                diff+="$line\n"
            elif $in_prompt; then
                prompt+="$line\n"
            fi
        fi
    done < "$data_file"

    # Skip if no file path (invalid issue)
    if [[ -z "$file_path" ]]; then
        return
    fi

    # Determine priority label based on type
    local priority_label="priority:medium"
    case "$issue_type" in
        "potential_issue")
            priority_label="priority:high"
            ;;
        "security")
            priority_label="priority:critical"
            ;;
        "performance")
            priority_label="priority:medium"
            ;;
        "style")
            priority_label="priority:low"
            ;;
    esac

    # Determine type label
    local type_label="type:refactor"
    case "$issue_type" in
        "potential_issue"|"security")
            type_label="type:bug"
            ;;
        "performance")
            type_label="type:enhancement"
            ;;
    esac

    # Create issue title
    local title="[CodeRabbit] ${file_path}"
    if [[ -n "$line_info" ]]; then
        title+=" (${line_info})"
    fi

    # Build issue body
    local body="## CodeRabbit Feedback\n\n"
    body+="**File:** \`${file_path}\`\n"
    if [[ -n "$line_info" ]]; then
        body+="**Line:** ${line_info}\n"
    fi
    body+="**Type:** ${issue_type}\n"
    body+="**Source Branch:** ${BRANCH}\n"
    body+="**Source Commit:** ${COMMIT}\n\n"

    if [[ -n "$comment" ]]; then
        body+="## Issue Description\n\n"
        body+="${comment}\n"
    fi

    if [[ -n "$diff" ]]; then
        body+="\n${diff}\n"
    fi

    if [[ -n "$prompt" ]]; then
        body+="\n${prompt}\n"
    fi

    body+="\n---\n\n"
    body+="_This issue was automatically created from CodeRabbit feedback during pre-push validation._\n"
    body+="_Feedback file: \`${FEEDBACK_FILE}\`_\n"

    # Create the issue
    log "Creating issue: $title"

    if gh issue create \
        --title "$title" \
        --body "$(printf "%b" "$body")" \
        --label "coderabbit,${priority_label},${type_label}" \
        > /tmp/issue_url.txt 2>&1; then
        local issue_url
        issue_url=$(cat /tmp/issue_url.txt)
        ((ISSUE_COUNT++))
        CREATED_ISSUES+=("$issue_url")
        log "  ✓ Created: $issue_url"
    else
        error "  ✗ Failed to create issue"
    fi
}

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    error "GitHub CLI (gh) is not installed"
    log "Install with: brew install gh"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    error "Not authenticated with GitHub CLI"
    log "Run: gh auth login"
    exit 1
fi

# Get feedback file from argument or find latest
FEEDBACK_FILE="${1:-}"

if [[ -z "$FEEDBACK_FILE" ]]; then
    # Find the latest feedback file
    FEEDBACK_FILE=$(find .coderabbit/feedback -name "*.txt" -type f ! -path "*/archive/*" | sort -r | head -1)

    if [[ -z "$FEEDBACK_FILE" ]]; then
        error "No CodeRabbit feedback files found"
        log "Run a CodeRabbit review first or specify a feedback file"
        exit 1
    fi

    log "Using latest feedback file: $FEEDBACK_FILE"
fi

if [[ ! -f "$FEEDBACK_FILE" ]]; then
    error "Feedback file not found: $FEEDBACK_FILE"
    exit 1
fi

# Extract branch and commit from filename
FILENAME=$(basename "$FEEDBACK_FILE" .txt)
BRANCH=$(echo "$FILENAME" | cut -d'_' -f2)
COMMIT=$(echo "$FILENAME" | cut -d'_' -f3)

log "Processing CodeRabbit feedback from:"
log "  Branch: $BRANCH"
log "  Commit: $COMMIT"
log "  File: $FEEDBACK_FILE"
log ""

# Parse feedback file and create issues
ISSUE_COUNT=0
CREATED_ISSUES=()

# Temporary file to store current issue data
TEMP_ISSUE=$(mktemp)
trap 'rm -f "$TEMP_ISSUE"' EXIT

# Parse the feedback file
while IFS= read -r line; do
    # Detect issue boundaries
    if [[ "$line" == "============================================================================" ]]; then
        # Process previous issue if we have data
        if [[ -f "$TEMP_ISSUE" ]] && [[ -s "$TEMP_ISSUE" ]]; then
            create_issue_from_data "$TEMP_ISSUE"
        fi

        # Reset for next issue
        : > "$TEMP_ISSUE"
        continue
    fi

    # Collect issue data
    echo "$line" >> "$TEMP_ISSUE"
done < "$FEEDBACK_FILE"

# Process last issue if exists
if [[ -s "$TEMP_ISSUE" ]]; then
    create_issue_from_data "$TEMP_ISSUE"
fi

log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "📊 ISSUE CREATION SUMMARY"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log ""
log "Total issues created: $ISSUE_COUNT"
log ""

if [[ "$ISSUE_COUNT" -gt 0 ]]; then
    log "Created issues:"
    for issue_url in "${CREATED_ISSUES[@]}"; do
        log "  • $issue_url"
    done
    log ""
    log "View all issues:"
    log "  gh issue list --label coderabbit"
fi

log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit 0
