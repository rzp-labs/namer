# Migration Utilities

This document provides shared utilities and scripts for the `fix/ambiguity-review` migration. All workstream engineers should use these tools to ensure consistency and efficiency.

---

## Quick Reference

| Utility | Purpose | Usage |
|---------|---------|-------|
| [Cherry-Pick Helper](#cherry-pick-helper) | Safely cherry-pick and stage specific files | `./scripts/cherry-pick-helper.sh <sha> <files>` |
| [Time Tracker](#time-tracking) | Track actual vs estimated time per PR | `./scripts/migration-time-tracker.sh <PR-ID> start` |
| [Coverage Comparison](#coverage-comparison) | Compare test coverage against baseline | `./scripts/compare-coverage.sh` |
| [Smoke Test Runner](#smoke-test-runner) | Run post-merge validation | `./scripts/smoke-test.sh <workstream> <pr-id>` |

---

## Installation

```bash
# Make scripts executable
chmod +x scripts/cherry-pick-helper.sh
chmod +x scripts/migration-time-tracker.sh
chmod +x scripts/compare-coverage.sh
chmod +x scripts/smoke-test.sh

# Verify installation
./scripts/cherry-pick-helper.sh --version
./scripts/migration-time-tracker.sh --version
```

---

## Cherry-Pick Helper

Automates the process of cherry-picking a commit and staging only specific files.

### Script

Create file: `scripts/cherry-pick-helper.sh`

```bash
#!/bin/bash
set -e

VERSION="1.0.0"

# Handle version flag
if [ "$1" == "--version" ]; then
    echo "cherry-pick-helper version $VERSION"
    exit 0
fi

COMMIT_SHA=$1
FILES=$2

if [ -z "$COMMIT_SHA" ] || [ -z "$FILES" ]; then
    echo "Usage: ./cherry-pick-helper.sh <commit-sha> <file1,file2,...>"
    echo ""
    echo "Example:"
    echo "  ./cherry-pick-helper.sh 5960020 .github/workflows/pr-validate.yml"
    echo "  ./cherry-pick-helper.sh 260e27d 'namer/ffmpeg.py,namer/ffmpeg_enhanced.py'"
    exit 1
fi

echo "🍒 Cherry-picking commit: $COMMIT_SHA"
git cherry-pick -n "$COMMIT_SHA"

echo "📝 Unstaging all files..."
git reset HEAD

echo "✅ Staging requested files..."
IFS=',' read -ra FILE_ARRAY <<< "$FILES"
for file in "${FILE_ARRAY[@]}"; do
    if [ -f "$file" ]; then
        git add "$file"
        echo "  ✓ $file"
    else
        echo "  ⚠️  File not found: $file"
    fi
done

echo ""
echo "📊 Staged changes:"
git status --short

echo ""
echo "🔍 Review staged changes:"
echo "  git diff --staged"
echo ""
echo "✏️  Commit changes:"
echo "  git commit -m '<commit-message>'"
```

### Usage

```bash
# Example: A1 - Pin hadolint action
./scripts/cherry-pick-helper.sh 5960020 .github/workflows/pr-validate.yml

# Example: B2 - Use secrets for temp files
./scripts/cherry-pick-helper.sh 260e27d namer/ffmpeg.py,namer/ffmpeg_enhanced.py

# Example: Multiple files
./scripts/cherry-pick-helper.sh 091cc71 '.github/workflows/pr-validate.yml,Dockerfile,poetry.lock,pyproject.toml'
```

---

## Time Tracking

Track actual time spent on each PR to improve future estimates and identify bottlenecks.

### Script

Create file: `scripts/migration-time-tracker.sh`

```bash
#!/bin/bash

VERSION="1.0.0"

# Handle version flag
if [ "$1" == "--version" ]; then
    echo "migration-time-tracker version $VERSION"
    exit 0
fi

PR_ID=$1
ACTION=$2  # start|end

if [ -z "$PR_ID" ] || [ -z "$ACTION" ]; then
    echo "Usage: ./migration-time-tracker.sh <PR-ID> <start|end>"
    echo ""
    echo "Examples:"
    echo "  ./migration-time-tracker.sh A1 start"
    echo "  ./migration-time-tracker.sh A1 end"
    echo ""
    echo "View report:"
    echo "  ./migration-time-tracker.sh report"
    exit 1
fi

# Handle report action
if [ "$PR_ID" == "report" ]; then
    if [ ! -f ~/.namer-migration-time.csv ]; then
        echo "No time tracking data found."
        exit 0
    fi

    echo "📊 Migration Time Report"
    echo ""
    python3 - <<EOF
import csv
from datetime import datetime
from collections import defaultdict

times = defaultdict(dict)

with open('$HOME/.namer-migration-time.csv', 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        if len(row) != 3:
            continue
        timestamp, pr_id, action = row
        times[pr_id][action] = datetime.fromisoformat(timestamp)

for pr_id in sorted(times.keys()):
    if 'start' in times[pr_id] and 'end' in times[pr_id]:
        duration = times[pr_id]['end'] - times[pr_id]['start']
        hours = duration.total_seconds() / 3600
        print(f"{pr_id}: {hours:.1f} hours")
    elif 'start' in times[pr_id]:
        print(f"{pr_id}: ⏱️  In progress")
    else:
        print(f"{pr_id}: ⚠️  Invalid data")
EOF
    exit 0
fi

TIMESTAMP=$(date -Iseconds 2>/dev/null || date -u +"%Y-%m-%dT%H:%M:%S%z")
LOG_FILE="$HOME/.namer-migration-time.csv"

echo "$TIMESTAMP,$PR_ID,$ACTION" >> "$LOG_FILE"

if [ "$ACTION" == "start" ]; then
    echo "⏱️  Started tracking: $PR_ID at $TIMESTAMP"
elif [ "$ACTION" == "end" ]; then
    echo "✅ Stopped tracking: $PR_ID at $TIMESTAMP"
    echo ""
    echo "📊 Run './migration-time-tracker.sh report' to see summary"
fi
```

### Usage

```bash
# Start tracking PR A1
./scripts/migration-time-tracker.sh A1 start

# ... work on PR ...

# Stop tracking PR A1
./scripts/migration-time-tracker.sh A1 end

# View time report
./scripts/migration-time-tracker.sh report
```

### Example Output

```
📊 Migration Time Report

A1: 2.3 hours
A2: 4.7 hours
B1: 1.8 hours
B2: ⏱️  In progress
```

---

## Coverage Comparison

Compare current test coverage against the baseline established during pre-migration validation.

### Script

Create file: `scripts/compare-coverage.sh`

```bash
#!/bin/bash

VERSION="1.0.0"

# Handle version flag
if [ "$1" == "--version" ]; then
    echo "compare-coverage version $VERSION"
    exit 0
fi

BASELINE_FILE=${1:-coverage-baseline.txt}

if [ ! -f "$BASELINE_FILE" ]; then
    echo "❌ Error: Baseline file not found: $BASELINE_FILE"
    echo ""
    echo "Create baseline first:"
    echo "  poetry run pytest --cov=namer --cov-report=term | tee coverage-baseline.txt"
    exit 1
fi

echo "📊 Comparing test coverage..."
echo ""

# Extract coverage percentage from baseline
BASELINE_COV=$(grep "TOTAL" "$BASELINE_FILE" | awk '{print $NF}' | tr -d '%')

if [ -z "$BASELINE_COV" ]; then
    echo "❌ Error: Could not parse baseline coverage from $BASELINE_FILE"
    exit 1
fi

echo "📋 Baseline coverage: ${BASELINE_COV}%"

# Run current coverage
echo "🧪 Running current tests..."
poetry run pytest --cov=namer --cov-report=term | tee coverage-current.txt

CURRENT_COV=$(grep "TOTAL" coverage-current.txt | awk '{print $NF}' | tr -d '%')

if [ -z "$CURRENT_COV" ]; then
    echo "❌ Error: Could not parse current coverage"
    exit 1
fi

echo ""
echo "📊 Results:"
echo "  Baseline: ${BASELINE_COV}%"
echo "  Current:  ${CURRENT_COV}%"

# Compare using bc for floating point comparison
if command -v bc &> /dev/null; then
    if (( $(echo "$CURRENT_COV < $BASELINE_COV" | bc -l) )); then
        DIFF=$(echo "$BASELINE_COV - $CURRENT_COV" | bc)
        echo "  ❌ Coverage regression: -${DIFF}%"
        exit 1
    elif (( $(echo "$CURRENT_COV > $BASELINE_COV" | bc -l) )); then
        DIFF=$(echo "$CURRENT_COV - $BASELINE_COV" | bc)
        echo "  ✅ Coverage improved: +${DIFF}%"
        exit 0
    else
        echo "  ✅ Coverage maintained"
        exit 0
    fi
else
    # Fallback to integer comparison if bc not available
    BASELINE_INT=${BASELINE_COV%.*}
    CURRENT_INT=${CURRENT_COV%.*}

    if [ "$CURRENT_INT" -lt "$BASELINE_INT" ]; then
        echo "  ❌ Coverage regression detected!"
        exit 1
    else
        echo "  ✅ Coverage maintained or improved"
        exit 0
    fi
fi
```

### Usage

```bash
# During pre-migration validation, establish baseline:
poetry run pytest --cov=namer --cov-report=term | tee coverage-baseline.txt

# Before merging each PR, compare:
./scripts/compare-coverage.sh

# Or specify custom baseline file:
./scripts/compare-coverage.sh my-baseline.txt
```

---

## Smoke Test Runner

Automated smoke tests for each workstream's PRs.

### Script

Create file: `scripts/smoke-test.sh`

```bash
#!/bin/bash
set -e

VERSION="1.0.0"

# Handle version flag
if [ "$1" == "--version" ]; then
    echo "smoke-test version $VERSION"
    exit 0
fi

WORKSTREAM=$1
PR_ID=$2

if [ -z "$WORKSTREAM" ] || [ -z "$PR_ID" ]; then
    echo "Usage: ./smoke-test.sh <workstream> <PR-ID>"
    echo ""
    echo "Examples:"
    echo "  ./smoke-test.sh A A1"
    echo "  ./smoke-test.sh C C2"
    echo "  ./smoke-test.sh E E1"
    exit 1
fi

echo "🧪 Running smoke test for $WORKSTREAM-$PR_ID"
echo ""

case "$WORKSTREAM" in
    A)
        case "$PR_ID" in
            A1)
                echo "Testing: Hadolint pinned to specific commit..."
                gh workflow run pr-validate.yml 2>/dev/null || echo "⚠️  gh CLI not available, skipping workflow test"
                grep -q "54c9adbab1582c2ef04b2016b760714a4bfde3cf" .github/workflows/pr-validate.yml && echo "✅ Hadolint SHA verified" || exit 1
                ;;
            A2)
                echo "Testing: Static analysis workflow added..."
                grep -q "mypy" .github/workflows/pr-validate.yml && echo "✅ mypy found" || exit 1
                grep -q "bandit" .github/workflows/pr-validate.yml && echo "✅ bandit found" || exit 1
                ;;
            A3)
                echo "Testing: CI validation enhanced..."
                grep -q "trivy" .github/workflows/pr-validate.yml && echo "✅ Trivy found" || exit 1
                ;;
            *)
                echo "✅ No specific smoke test for $PR_ID"
                ;;
        esac
        ;;

    B)
        case "$PR_ID" in
            B1)
                echo "Testing: defusedxml dependency added..."
                poetry show defusedxml &>/dev/null && echo "✅ defusedxml installed" || exit 1
                ;;
            B2)
                echo "Testing: secrets module used for temp files..."
                grep -q "import secrets" namer/ffmpeg.py && echo "✅ secrets imported in ffmpeg.py" || exit 1
                grep -q "import secrets" namer/ffmpeg_enhanced.py && echo "✅ secrets imported in ffmpeg_enhanced.py" || exit 1
                ;;
            B3)
                echo "Testing: Token constants extracted..."
                grep -q "PLACEHOLDER_TOKEN" namer/configuration.py && echo "✅ Constants defined" || exit 1
                ;;
            *)
                echo "✅ No specific smoke test for $PR_ID"
                ;;
        esac
        ;;

    C)
        case "$PR_ID" in
            C1)
                echo "Testing: Directory error logging improved..."
                poetry run pytest test/namer_test.py test/command_test.py -v
                echo "✅ Directory creation tests pass"
                ;;
            C2)
                echo "Testing: Directory creation refactored..."
                grep -q "ensure_directory" namer/namer.py && echo "✅ ensure_directory used" || exit 1
                poetry run pytest test/namer_test.py test/command_test.py -v
                echo "✅ Refactored directory tests pass"
                ;;
            C3)
                echo "Testing: Watchdog path validation..."
                poetry run pytest test/watchdog_test.py -v
                echo "✅ Watchdog tests pass"
                ;;
            *)
                echo "✅ No specific smoke test for $PR_ID"
                ;;
        esac
        ;;

    D)
        case "$PR_ID" in
            D1)
                echo "Testing: Comparison path handling..."
                poetry run pytest test/comparison_results_test.py -v
                echo "✅ Comparison results tests pass"
                ;;
            D2)
                echo "Testing: Phash setter method..."
                grep -q "set_phash_match_used" namer/comparison_results.py && echo "✅ Setter method found" || exit 1
                poetry run pytest test/comparison_results_test.py -v
                echo "✅ Setter tests pass"
                ;;
            D3)
                echo "Testing: Phash result handling..."
                poetry run pytest test/stashdb_phash_ambiguity_test.py -v
                echo "✅ Phash ambiguity tests pass"
                ;;
            D4)
                echo "Testing: ThePornDB error handling..."
                poetry run pytest test/metadata_providers_test.py -v
                echo "✅ Provider tests pass"
                ;;
            *)
                echo "✅ No specific smoke test for $PR_ID"
                ;;
        esac
        ;;

    E)
        case "$PR_ID" in
            E1)
                echo "Testing: Ambiguous file handling..."
                grep -q "move_to_ambiguous_directory" namer/namer.py && echo "✅ Ambiguous handling found" || exit 1
                poetry run pytest test/namer_test.py -k ambiguous -v
                echo "✅ Ambiguous file tests pass"
                ;;
            E2)
                echo "Testing: Watchdog event processing..."
                poetry run pytest test/watchdog_test.py -v
                echo "✅ Watchdog event tests pass"
                ;;
            E3)
                echo "Testing: Workflow validation for ambiguous files..."
                grep -q "ambiguous" .github/workflows/pr-validate.yml && echo "✅ Workflow includes ambiguous validation" || exit 1
                ;;
            *)
                echo "✅ No specific smoke test for $PR_ID"
                ;;
        esac
        ;;

    *)
        echo "❌ Unknown workstream: $WORKSTREAM"
        exit 1
        ;;
esac

echo ""
echo "✅ Smoke test passed for $WORKSTREAM-$PR_ID"
```

### Usage

```bash
# After merging A1
./scripts/smoke-test.sh A A1

# After merging C2
./scripts/smoke-test.sh C C2

# After merging E1
./scripts/smoke-test.sh E E1
```

---

## Common Workflows

### Starting a New PR

```bash
# 1. Start time tracking
./scripts/migration-time-tracker.sh A1 start

# 2. Create branch
git checkout -b chore/a1-pin-hadolint-action origin/main

# 3. Cherry-pick and stage files
./scripts/cherry-pick-helper.sh 5960020 .github/workflows/pr-validate.yml

# 4. Review changes
git diff --staged

# 5. Commit
git commit -m "chore(ci): pin hadolint-action to specific commit

Source: fix/ambiguity-review@5960020"

# 6. Push
git push -u origin chore/a1-pin-hadolint-action
```

### Before Merging a PR

```bash
# 1. Run linting
poetry run ruff check .

# 2. Run tests
poetry run pytest

# 3. Compare coverage
./scripts/compare-coverage.sh

# 4. Verify CI passes
gh pr checks

# 5. All green? Request review
gh pr review --approve  # (as reviewer)
```

### After Merging a PR

```bash
# 1. Run smoke test
./scripts/smoke-test.sh A A1

# 2. Stop time tracking
./scripts/migration-time-tracker.sh A1 end

# 3. Post handoff message (if sequential PR)
# See workstream docs for handoff protocol

# 4. Update status dashboard
gh pr comment <pr-number> --body "✅ Merged and smoke tested"
```

---

## Troubleshooting

### Cherry-Pick Conflicts

```bash
# If cherry-pick-helper.sh fails with conflicts:
git status  # See conflicting files
git diff    # Review conflicts

# Option 1: Resolve manually
vim <conflicting-file>  # Fix conflicts
git add <conflicting-file>
git cherry-pick --continue

# Option 2: Abort and try different approach
git cherry-pick --abort
```

### Coverage Regression

```bash
# If compare-coverage.sh reports regression:

# 1. Identify uncovered lines
poetry run pytest --cov=namer --cov-report=html
open htmlcov/index.html

# 2. Add tests for uncovered code

# 3. Re-run comparison
./scripts/compare-coverage.sh

# 4. If coverage cannot be increased, document why:
echo "Coverage dropped 0.5% due to removal of dead code" >> PR-description.md
```

### Smoke Test Failures

```bash
# If smoke-test.sh fails:

# 1. Check what failed
./scripts/smoke-test.sh A A1  # Read error output

# 2. Investigate root cause
git diff main...HEAD  # What changed?

# 3. Fix or rollback
git revert HEAD  # If critical
# OR
# Fix the issue and force-push

# 4. Re-run smoke test
./scripts/smoke-test.sh A A1
```

---

## Best Practices

1. **Always use cherry-pick-helper.sh** instead of manual cherry-picking to avoid staging wrong files
2. **Track time for every PR** to identify bottlenecks and improve estimates
3. **Compare coverage before every merge** to prevent regression
4. **Run smoke tests immediately after merge** to catch issues early
5. **Keep scripts updated** - if you improve a script, update this doc

---

**Document Version:** 1.0
**Last Updated:** 2025-10-06
**Maintained By:** Migration Team
