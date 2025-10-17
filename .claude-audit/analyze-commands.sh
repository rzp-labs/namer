#!/bin/bash
# Analyze Claude Code commands and generate comprehensive inventory
# Usage: ./analyze-commands.sh

set -euo pipefail

# Configuration
CLAUDE_DIR="${HOME}/.claude"
COMMANDS_DIR="${CLAUDE_DIR}/commands"
OUTPUT_DIR=".claude-audit"
INVENTORY_FILE="${OUTPUT_DIR}/COMMAND_INVENTORY.md"
CATEGORIES_FILE="${OUTPUT_DIR}/COMMAND_CATEGORIES.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if commands directory exists
if [ ! -d "$COMMANDS_DIR" ]; then
    error "Commands directory not found at $COMMANDS_DIR"
    echo "Expected location: ${HOME}/.claude/commands/"
    echo "Please ensure you have Claude Code slash commands configured."
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
info "Created output directory: $OUTPUT_DIR"

# Count commands
TOTAL_COMMANDS=$(find "$COMMANDS_DIR" -name "*.md" -type f | wc -l | tr -d ' ')
info "Found $TOTAL_COMMANDS commands to analyze"

# Generate markdown inventory
info "Generating command inventory..."

cat > "$INVENTORY_FILE" << HEADER
# Claude Code Command Inventory

**Generated:** $(date)
**Total Commands:** $TOTAL_COMMANDS
**Source:** \`$COMMANDS_DIR\`

## Quick Stats

- Total commands: $TOTAL_COMMANDS
- Categories: (To be categorized)
- Duplicates detected: (To be analyzed)

## Command Reference

| Command | Description | Arguments | Lines | Category |
|---------|-------------|-----------|-------|----------|
HEADER

# Process each command file
find "$COMMANDS_DIR" -name "*.md" -type f | sort | while read -r file; do
    cmd_name=$(basename "$file" .md)
    line_count=$(wc -l < "$file" | tr -d ' ')

    # Extract first heading
    description=$(grep -m 1 "^# " "$file" | sed 's/^# *//' | cut -c 1-60 || echo "No description")

    # Check for argument placeholders
    if grep -q '\$ARGUMENTS\|\$[A-Z_][A-Z_]*' "$file"; then
        args="Yes"
    else
        args="No"
    fi

    # Placeholder category
    category="?"

    printf "| %-30s | %-60s | %-3s | %5s | %-15s |\n" \
        "/$cmd_name" \
        "$description" \
        "$args" \
        "$line_count" \
        "$category" >> "$INVENTORY_FILE"
done

# Add detailed sections
cat >> "$INVENTORY_FILE" << 'SECTIONS'

## Categorization Guidelines

### Suggested Categories

1. **git-flow** - Git Flow workflow commands (feature, release, hotfix, branch management)
2. **testing** - Test generation, execution, coverage analysis
3. **ci-cd** - Build, deployment, CI/CD automation
4. **code-quality** - Code review, refactoring, linting, analysis
5. **project-mgmt** - Planning, tracking, standup, retrospectives
6. **documentation** - PRD, JTBD, API docs, README generation
7. **dev-tools** - Debugging, profiling, optimization utilities
8. **ai-review** - AI-assisted review (Gemini, CodeRabbit integration)
9. **infrastructure** - Docker, deployment, environment setup
10. **other** - Miscellaneous or utility commands

## Overlap Analysis Checklist

### Similar Names
- [ ] Commands with similar prefixes (create-, generate-, setup-)
- [ ] Commands with similar suffixes (-test, -tests, -testing)
- [ ] Verb variations (start vs init vs create)

### Similar Functions
- [ ] Multiple test-related commands
- [ ] Multiple review commands
- [ ] Multiple documentation commands
- [ ] Multiple git workflow commands

### Consolidation Opportunities
- [ ] Commands that could share base with flags
- [ ] Commands with overlapping functionality
- [ ] Commands that are subsets of others

## Next Steps

1. **Categorize Commands**
   - Review each command's purpose
   - Assign appropriate category
   - Update the table above

2. **Identify Overlaps**
   - Mark similar commands
   - Document functional overlap
   - Propose consolidation strategies

3. **Generate Optimization Proposal**
   - Document specific recommendations
   - Create migration plan
   - Define naming standards

4. **Update Categories JSON**
   - Generate machine-readable categorization
   - Enable automated tooling
   - Support command discovery

SECTIONS

info "Inventory generated: $INVENTORY_FILE"

# Generate JSON categories structure
info "Generating categories JSON template..."

cat > "$CATEGORIES_FILE" << 'JSON'
{
  "version": "1.0.0",
  "generated": "TO_BE_UPDATED",
  "total_commands": 0,
  "categories": {
    "git-flow": {
      "name": "Git Flow Workflow",
      "description": "Version control and branching commands",
      "commands": []
    },
    "testing": {
      "name": "Testing & Quality",
      "description": "Test generation, execution, and coverage",
      "commands": []
    },
    "ci-cd": {
      "name": "CI/CD & Build",
      "description": "Build, deployment, and automation",
      "commands": []
    },
    "code-quality": {
      "name": "Code Quality",
      "description": "Review, refactoring, and analysis",
      "commands": []
    },
    "project-mgmt": {
      "name": "Project Management",
      "description": "Planning, tracking, and coordination",
      "commands": []
    },
    "documentation": {
      "name": "Documentation",
      "description": "PRD, JTBD, API docs, and README",
      "commands": []
    },
    "dev-tools": {
      "name": "Development Tools",
      "description": "Debugging, profiling, optimization",
      "commands": []
    },
    "ai-review": {
      "name": "AI Code Review",
      "description": "AI-assisted review and analysis",
      "commands": []
    },
    "infrastructure": {
      "name": "Infrastructure",
      "description": "Docker, deployment, environment",
      "commands": []
    },
    "other": {
      "name": "Other",
      "description": "Miscellaneous utilities",
      "commands": []
    }
  },
  "overlaps": [],
  "recommendations": []
}
JSON

info "Categories JSON template generated: $CATEGORIES_FILE"

# Generate summary report
echo ""
echo "======================================"
echo "Command Analysis Complete"
echo "======================================"
echo ""
echo "Generated files:"
echo "  - $INVENTORY_FILE"
echo "  - $CATEGORIES_FILE"
echo ""
echo "Next steps:"
echo "  1. Review $INVENTORY_FILE"
echo "  2. Categorize each command manually"
echo "  3. Identify overlaps and duplicates"
echo "  4. Run optimization analysis"
echo ""
echo "To view inventory:"
echo "  cat $INVENTORY_FILE"
echo ""
