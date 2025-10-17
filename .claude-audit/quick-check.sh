#!/bin/bash
# Quick command overlap checker
# Usage: ./quick-check.sh

set -euo pipefail

COMMANDS_DIR="${HOME}/.claude/commands"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Claude Code Command Quick Check ===${NC}\n"

# Check if commands directory exists
if [ ! -d "$COMMANDS_DIR" ]; then
	echo -e "${RED}Error: Commands directory not found at $COMMANDS_DIR${NC}"
	exit 1
fi

# Count total commands
TOTAL=$(find "$COMMANDS_DIR" -name "*.md" -type f | wc -l | tr -d ' ')
echo -e "${GREEN}Total commands: $TOTAL${NC}\n"

# Find commands with similar names
echo -e "${BLUE}Commands with similar prefixes:${NC}\n"

# Extract all command names
COMMANDS=$(find "$COMMANDS_DIR" -name "*.md" -type f -exec basename {} .md \;)

# Common prefixes to check
PREFIXES=("create" "generate" "make" "start" "init" "setup" "test" "review" "git" "pr" "code")

for prefix in "${PREFIXES[@]}"; do
	MATCHES=$(echo "$COMMANDS" | grep "^${prefix}" || true)
	if [ -n "$MATCHES" ]; then
		echo -e "${YELLOW}$prefix-*:${NC}"
		# Use bash parameter expansion instead of sed for performance
		while IFS= read -r line; do
			echo "  $line"
		done <<<"$MATCHES"
		echo ""
	fi
done

# Find potential duplicates by checking for similar words
echo -e "${BLUE}Potential overlaps (commands with shared words):${NC}\n"

# Create temporary file for analysis
TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT

# List all commands
echo "$COMMANDS" | while read -r cmd1; do
	echo "$COMMANDS" | while read -r cmd2; do
		if [ "$cmd1" != "$cmd2" ]; then
			# Split commands into words and check for overlap
			WORDS1=$(echo "$cmd1" | tr '-' '\n' | sort)
			WORDS2=$(echo "$cmd2" | tr '-' '\n' | sort)

			# Find common words
			COMMON=$(comm -12 <(echo "$WORDS1") <(echo "$WORDS2") | grep -v "^$" || true)

			if [ -n "$COMMON" ]; then
				# Only show if we haven't shown this pair before
				PAIR="${cmd1}|${cmd2}"
				REVERSE="${cmd2}|${cmd1}"
				if ! grep -q "^${REVERSE}$" "$TEMP_FILE" 2>/dev/null; then
					echo "$PAIR" >>"$TEMP_FILE"
					echo -e "${YELLOW}Shared words:${NC} $(echo "$COMMON" | tr '\n' ',' | sed 's/,$//')"
					echo "  - /$cmd1"
					echo "  - /$cmd2"
					echo ""
				fi
			fi
		fi
	done
done | head -20 # Limit output

# Check for common patterns
echo -e "${BLUE}Commands by first word:${NC}\n"

# Group by first word
echo "$COMMANDS" | while read -r cmd; do
	FIRST_WORD=$(echo "$cmd" | cut -d'-' -f1)
	echo "$FIRST_WORD"
done | sort | uniq -c | sort -rn | while read -r count word; do
	if [ "$count" -gt 1 ]; then
		echo -e "${YELLOW}$word-* ($count commands)${NC}"
		echo "$COMMANDS" | grep "^${word}-" | sed 's/^/  /' || true
		echo ""
	fi
done

# Summary
echo -e "${BLUE}=== Summary ===${NC}\n"
echo "Total commands: $TOTAL"
echo ""
echo "Next steps:"
echo "  1. Run ./analyze-commands.sh for full inventory"
echo "  2. Review COMMAND_INVENTORY.md for details"
echo "  3. Categorize commands manually"
echo "  4. Create optimization proposal"
echo ""
