# Claude Code Command Inventory

This document provides a structured template for auditing slash commands in `.claude/commands/`.

## How to Generate Inventory

Since `.claude/` is gitignored, run this script to generate the inventory:

```bash
#!/bin/bash
# Generate command inventory from .claude/commands/

COMMANDS_DIR="$HOME/.claude/commands"
OUTPUT_FILE=".claude-audit/COMMAND_INVENTORY.md"

if [ ! -d "$COMMANDS_DIR" ]; then
    echo "Error: Commands directory not found at $COMMANDS_DIR"
    exit 1
fi

cat > "$OUTPUT_FILE" << 'HEADER'
# Claude Code Command Inventory

**Generated:** $(date)
**Total Commands:** $(find "$COMMANDS_DIR" -name "*.md" | wc -l)

## Command List

| Command | Description | Arguments | Category |
|---------|-------------|-----------|----------|
HEADER

# Extract metadata from each command file
find "$COMMANDS_DIR" -name "*.md" -type f | sort | while read -r file; do
    cmd_name=$(basename "$file" .md)

    # Try to extract description (first line after # heading or first paragraph)
    description=$(head -20 "$file" | grep -A 1 "^# " | tail -1 | sed 's/^[#* ]*//' | cut -c 1-80)

    # Try to extract argument hint (look for $ARGUMENTS or similar)
    has_args=$(grep -o '\$ARGUMENTS\|\$[A-Z_]*' "$file" | head -1)
    args_hint="${has_args:-None}"

    # Placeholder for category (will need manual review)
    category="Uncategorized"

    echo "| /$cmd_name | $description | $args_hint | $category |"
done >> "$OUTPUT_FILE"

echo "Inventory generated at $OUTPUT_FILE"
```

## Manual Categorization

After generating the inventory, categorize each command:

### Suggested Categories

- **git-flow** - Version control workflow (feature, release, hotfix)
- **testing** - Test generation, execution, coverage
- **ci-cd** - Build, deployment, automation
- **code-quality** - Review, refactoring, analysis
- **project-mgmt** - Planning, tracking, standup
- **documentation** - PRD, JTBD, API docs
- **dev-tools** - Debugging, profiling, optimization
- **ai-review** - Gemini, CodeRabbit integration
- **infrastructure** - Docker, deployment, config
- **other** - Miscellaneous

## Overlap Detection

Look for these patterns:

### Similar Names, Different Purposes
Commands that share words but do different things

### Similar Purposes, Different Names
Commands that solve the same problem differently

### Mergeable Commands
Functionality that could be consolidated with flags:
- /command --action1
- /command --action2

## Next Steps

1. Run the inventory generation script
2. Manually review and categorize each command
3. Identify overlaps and duplicates
4. Document recommendations in COMMAND_OPTIMIZATION_PROPOSAL.md
