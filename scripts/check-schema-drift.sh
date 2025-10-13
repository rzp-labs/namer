#!/usr/bin/env bash
# Schema Drift Detection Script
# Compares current GraphQL schemas with documented baseline to detect API changes

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCS_DIR="docs/api"
TEMP_DIR=$(mktemp -d)
ARTIFACT_DIR="${RUNNER_TEMP:-/tmp}"
INTROSPECTION_QUERY='query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      kind
      name
      description
      fields(includeDeprecated: true) {
        name
        description
        args {
          name
          type { name kind ofType { name kind } }
        }
        type { name kind ofType { name kind } }
        isDeprecated
        deprecationReason
      }
      inputFields {
        name
        type { name kind ofType { name kind } }
      }
      interfaces { name }
      enumValues(includeDeprecated: true) {
        name
        description
        isDeprecated
        deprecationReason
      }
      possibleTypes { name }
    }
    directives {
      name
      description
      locations
      args {
        name
        type { name kind ofType { name kind } }
      }
    }
  }
}'

# Cleanup on exit
trap 'rm -rf "$TEMP_DIR"' EXIT

# Function to fetch schema from API
fetch_schema() {
	local service=$1
	local endpoint=$2
	local auth_header=$3
	local token=$4

	echo -e "${BLUE}Fetching current schema for ${service}...${NC}"

	local response
	response=$(curl -fsS -X POST "$endpoint" \
		-H "$auth_header: $token" \
		-H "Content-Type: application/json" \
		-d "{\"query\":$(echo "$INTROSPECTION_QUERY" | jq -Rs .)}")

	if echo "$response" | jq -e '.errors' >/dev/null 2>&1; then
		echo -e "${RED}Error fetching ${service} schema:${NC}"
		echo "$response" | jq '.errors'
		return 1
	fi

	echo "$response" | jq '.data' >"$TEMP_DIR/${service}_current.json"
	echo -e "${GREEN}✓ Successfully fetched ${service} schema${NC}"
}

# Function to normalize schema for comparison
normalize_schema() {
	local input=$1
	local output=$2

	# Sort and format consistently
	jq 'walk(if type == "array" then sort_by(.name // .) else . end)' "$input" >"$output"
}

# Function to compare schemas and generate diff
compare_schemas() {
	local service=$1
	local baseline="$DOCS_DIR/${service}_schema.json"
	local current="$TEMP_DIR/${service}_current.json"
	local normalized_baseline="$TEMP_DIR/${service}_baseline_normalized.json"
	local normalized_current="$TEMP_DIR/${service}_current_normalized.json"

	if [[ ! -f "$baseline" ]]; then
		echo -e "${YELLOW}⚠ No baseline found for ${service}${NC}"
		return 2
	fi

	normalize_schema "$baseline" "$normalized_baseline"
	normalize_schema "$current" "$normalized_current"

	if diff -q "$normalized_baseline" "$normalized_current" >/dev/null 2>&1; then
		echo -e "${GREEN}✓ ${service}: No schema drift detected${NC}"
		return 0
	else
		echo -e "${YELLOW}⚠ ${service}: Schema drift detected!${NC}"
		echo -e "${BLUE}Generating detailed diff...${NC}"

		# Generate human-readable diff
		local diff_file="$ARTIFACT_DIR/${service}_drift.diff"
		diff -u "$normalized_baseline" "$normalized_current" >"$diff_file" || true

		# Extract and summarize key changes
		echo -e "\n${YELLOW}Summary of changes:${NC}"

		# Count type changes
		local types_added types_removed fields_changed
		types_added=$(grep -c '^\+.*"name":' "$diff_file" || echo "0")
		types_removed=$(grep -c '^\-.*"name":' "$diff_file" || echo "0")
		fields_changed=$((types_added + types_removed))

		echo "  • Fields changed: $fields_changed"

		# Show first 50 lines of diff
		echo -e "\n${BLUE}First 50 lines of diff:${NC}"
		head -n 50 "$diff_file"

		echo -e "\n${YELLOW}Full diff saved to: $diff_file${NC}"
		return 1
	fi
}

# Function to generate drift report
generate_report() {
	local output_file="$ARTIFACT_DIR/schema_drift_report.md"

	cat >"$output_file" <<EOF
# GraphQL Schema Drift Report
Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## Summary

EOF

	if [[ ${STASHDB_DRIFT:-0} -eq 0 && ${TPDB_DRIFT:-0} -eq 0 ]]; then
		cat >>"$output_file" <<EOF
✅ **All schemas are up to date**

No drift detected in either StashDB or ThePornDB schemas.
EOF
	else
		cat >>"$output_file" <<EOF
⚠️ **Schema drift detected**

EOF
		if [[ ${STASHDB_DRIFT:-0} -eq 1 ]]; then
			cat >>"$output_file" <<EOF
### StashDB Schema Changes

See detailed diff: \`$ARTIFACT_DIR/stashdb_drift.diff\`

EOF
		fi

		if [[ ${TPDB_DRIFT:-0} -eq 1 ]]; then
			cat >>"$output_file" <<EOF
### ThePornDB Schema Changes

See detailed diff: \`$ARTIFACT_DIR/tpdb_drift.diff\`

EOF
		fi

		if [[ ${STASHDB_DRIFT:-0} -eq 2 ]]; then
			cat >>"$output_file" <<EOF
### StashDB Baseline Missing

No baseline file found. Run \`make update-schema-docs\` to create it.

EOF
		fi

		if [[ ${TPDB_DRIFT:-0} -eq 2 ]]; then
			cat >>"$output_file" <<EOF
### ThePornDB Baseline Missing

No baseline file found. Run \`make update-schema-docs\` to create it.

EOF
		fi

		cat >>"$output_file" <<EOF

## Recommended Actions

1. Review the diffs to understand the changes
2. Update integration code if breaking changes exist
3. Update documentation: \`make update-schema-docs\`
4. Update tests if API behavior changed
5. Commit updated schema files to baseline
EOF
	fi

	echo -e "\n${GREEN}Report generated: $output_file${NC}"
}

# Main execution
main() {
	echo -e "${BLUE}=== GraphQL Schema Drift Detection ===${NC}\n"

	# Check for required dependencies
	for dep in curl jq; do
		if ! command -v "$dep" >/dev/null 2>&1; then
			echo -e "${RED}Error: required dependency '$dep' not found${NC}"
			echo "Please install: sudo apt-get install curl jq"
			exit 127
		fi
	done

	# Check for required environment variables
	if [[ -z "${STASHDB_TOKEN:-}" ]]; then
		echo -e "${RED}Error: STASHDB_TOKEN environment variable not set${NC}"
		exit 1
	fi

	if [[ -z "${TPDB_TOKEN:-}" ]]; then
		echo -e "${RED}Error: TPDB_TOKEN environment variable not set${NC}"
		exit 1
	fi

	# Fetch current schemas
	echo -e "${BLUE}Step 1: Fetching current schemas${NC}"
	fetch_schema "stashdb" "https://stashdb.org/graphql" "APIKey" "$STASHDB_TOKEN"
	fetch_schema "tpdb" "https://theporndb.net/graphql" "Authorization" "Bearer $TPDB_TOKEN"

	echo -e "\n${BLUE}Step 2: Comparing with baseline${NC}"

	# Compare schemas
	STASHDB_DRIFT=0
	TPDB_DRIFT=0

	compare_schemas "stashdb" || STASHDB_DRIFT=$?
	compare_schemas "tpdb" || TPDB_DRIFT=$?

	echo -e "\n${BLUE}Step 3: Generating report${NC}"
	generate_report

	# Exit with appropriate code based on validation results
	# Check for missing baselines first (exit code 2)
	if [[ $STASHDB_DRIFT -eq 2 || $TPDB_DRIFT -eq 2 ]]; then
		echo -e "\n${YELLOW}⚠ One or more baseline schemas are missing. No validation performed.${NC}"
		echo -e "${BLUE}Run 'make update-schema-docs' to create baseline files.${NC}"
		exit 0
	# Check for schema drift (exit code 1)
	elif [[ $STASHDB_DRIFT -eq 1 || $TPDB_DRIFT -eq 1 ]]; then
		echo -e "\n${YELLOW}⚠ Schema drift detected. Review changes and update documentation.${NC}"
		exit 1
	# All schemas validated successfully (exit code 0)
	else
		echo -e "\n${GREEN}✅ All schemas are current. No action required.${NC}"
		exit 0
	fi
}

# Run main function
main "$@"
