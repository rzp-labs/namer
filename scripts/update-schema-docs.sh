#!/usr/bin/env bash
# Update GraphQL Schema Documentation
# Fetches latest schemas and regenerates documentation

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

# Cleanup on exit
trap 'rm -rf "$TEMP_DIR"' EXIT

# GraphQL introspection query
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
          description
          type { name kind ofType { name kind } }
        }
        type { name kind ofType { name kind } }
        isDeprecated
        deprecationReason
      }
      inputFields {
        name
        description
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
        description
        type { name kind ofType { name kind } }
      }
    }
  }
}'

# Function to fetch and save schema
fetch_and_save_schema() {
    local service=$1
    local endpoint=$2
    local auth_header=$3
    local token=$4
    local output_file="$DOCS_DIR/${service}_schema.json"

    echo -e "${BLUE}Fetching schema for ${service}...${NC}"

    local response
    response=$(curl -s -X POST "$endpoint" \
        -H "$auth_header: $token" \
        -H "Content-Type: application/json" \
        -d "{\"query\":$(echo "$INTROSPECTION_QUERY" | jq -Rs .)}")

    if echo "$response" | jq -e '.errors' > /dev/null 2>&1; then
        echo -e "${RED}Error fetching ${service} schema:${NC}"
        echo "$response" | jq '.errors'
        return 1
    fi

    # Save formatted schema
    echo "$response" | jq '.data' > "$output_file"
    echo -e "${GREEN}✓ Schema saved to $output_file${NC}"
}

# Function to generate markdown documentation
generate_markdown_docs() {
    local output_file="$DOCS_DIR/graphql_schema_documentation.md"

    cat > "$output_file" <<'EOF'
# GraphQL Schema Documentation

This document provides comprehensive documentation for the GraphQL APIs used by Namer.

**Last Updated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")

---

## Table of Contents

1. [Overview](#overview)
2. [StashDB API](#stashdb-api)
3. [ThePornDB API](#theporndb-api)
4. [Authentication](#authentication)
5. [Common Queries](#common-queries)
6. [Schema Comparison](#schema-comparison)
7. [Code Examples](#code-examples)

---

## Overview

Namer integrates with two GraphQL APIs to fetch video metadata:

- **StashDB** (stashdb.org) - Community-maintained adult content database
- **ThePornDB** (theporndb.net) - Comprehensive adult content metadata provider

Both services use GraphQL for flexible, efficient data retrieval.

---

## StashDB API

### Endpoint
```
https://stashdb.org/graphql
```

### Authentication
```bash
curl -X POST https://stashdb.org/graphql \
  -H "APIKey: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"..."}'
```

**Note:** StashDB uses a non-standard `APIKey` header (not `Authorization: Bearer`).

### Key Features
- 181 GraphQL types
- 35+ queries
- 70+ mutations
- Full edit workflow with voting
- CRUD operations on all entities

### Important Types

#### Scene
```graphql
type Scene {
  id: ID!
  title: String
  details: String
  date: String
  urls: [URL!]!
  studio: Studio
  performers: [PerformerAppearance!]!
  tags: [Tag!]!
  images: [Image!]!
  fingerprints: [Fingerprint!]!
  duration: Int
}
```

#### Fingerprint
```graphql
type Fingerprint {
  hash: String!
  algorithm: FingerprintAlgorithm!
  duration: Int!
  submissions: Int!
}
```

---

## ThePornDB API

### Endpoint
```
https://theporndb.net/graphql
```

### Authentication
```bash
curl -X POST https://theporndb.net/graphql \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"..."}'
```

**Note:** ThePornDB uses standard `Authorization: Bearer` header.

### Key Features
- 30 GraphQL types
- 7 queries
- 5 mutations
- Streamlined API design
- Focus on content retrieval

### Important Types

#### Scene
```graphql
type Scene {
  id: ID!
  title: String
  description: String
  date: String
  urls: [SceneURL!]!
  site: Site
  performers: [Performance!]!
  tags: [Tag!]!
  posters: [Image!]!
  background_images: [Image!]!
  duration: Int
}
```

---

## Authentication

### Environment Variables

```bash
export STASHDB_TOKEN="your_stashdb_api_key"
export TPDB_TOKEN="your_theporndb_token"
```

### Testing Authentication

**StashDB:**
```bash
curl -X POST https://stashdb.org/graphql \
  -H "APIKey: $STASHDB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"query{me{id name roles}}"}'
```

**ThePornDB:**
```bash
curl -X POST https://theporndb.net/graphql \
  -H "Authorization: Bearer $TPDB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"query{me{id name}}"}'
```

---

## Common Queries

### Search Scenes by Text

**StashDB:**
```graphql
query SearchScenes($term: String!) {
  searchScene(term: $term) {
    id
    title
    date
    studio { name }
    urls { url }
    images { url }
  }
}
```

**ThePornDB:**
```graphql
query SearchScenes($term: String!) {
  searchScene(term: $term) {
    id
    title
    date
    site { name }
    urls { url }
    posters { url }
  }
}
```

### Find Scene by ID

**Both services:**
```graphql
query FindScene($id: ID!) {
  findScene(id: $id) {
    id
    title
    date
    duration
    performers {
      performer {
        name
      }
    }
    tags {
      name
    }
  }
}
```

### Search by Perceptual Hash (PHASH)

**StashDB:**
```graphql
query FindByPHASH($fingerprint: FingerprintQueryInput!) {
  findSceneByFingerprint(fingerprint: $fingerprint) {
    id
    title
    fingerprints {
      hash
      algorithm
      duration
    }
  }
}
```

**ThePornDB:**
```graphql
query FindByPHASH($fingerprints: [[FingerprintQueryInput]]!) {
  findScenesBySceneFingerprints(fingerprints: $fingerprints) {
    id
    title
    fingerprints {
      hash
      algorithm
      duration
    }
  }
}
```

---

## Schema Comparison

| Feature | StashDB | ThePornDB |
|---------|---------|-----------|
| **Auth Header** | `APIKey` | `Authorization: Bearer` |
| **Total Types** | 181 | 30 |
| **Queries** | 35+ | 7 |
| **Mutations** | 70+ | 5 |
| **Edit System** | Full workflow with voting | Draft submissions |
| **Scene Date Field** | `release_date` | `date` |
| **Scene URL Field** | `urls[].url` | `urls[].view` |
| **Studio/Site** | `studio` | `site` |
| **Images Field** | `images` | `posters`, `background_images` |

---

## Code Examples

### Python (using requests)

```python
import requests
import os

def query_stashdb(query: str, variables: dict = None):
    """Query StashDB GraphQL API"""
    response = requests.post(
        "https://stashdb.org/graphql",
        headers={
            "APIKey": os.environ["STASHDB_TOKEN"],
            "Content-Type": "application/json"
        },
        json={"query": query, "variables": variables}
    )
    response.raise_for_status()
    return response.json()

def query_theporndb(query: str, variables: dict = None):
    """Query ThePornDB GraphQL API"""
    response = requests.post(
        "https://theporndb.net/graphql",
        headers={
            "Authorization": f"Bearer {os.environ['TPDB_TOKEN']}",
            "Content-Type": "application/json"
        },
        json={"query": query, "variables": variables}
    )
    response.raise_for_status()
    return response.json()

# Example: Search for a scene
query = """
query SearchScenes($term: String!) {
  searchScene(term: $term) {
    id
    title
    date
  }
}
"""

result = query_stashdb(query, {"term": "scene title"})
print(result["data"]["searchScene"])
```

---

## Troubleshooting

### Common Issues

**1. Authentication Errors**
- Verify token is set: `echo $STASHDB_TOKEN`
- Check header format: `APIKey` vs `Authorization: Bearer`
- Test with `me` query to validate credentials

**2. Rate Limiting**
- Implement exponential backoff
- Cache responses when possible
- Batch requests where API supports it

**3. Schema Changes**
- Run `make check-schema-drift` regularly
- Subscribe to API changelog/notifications
- Test integration after schema updates

---

## Maintenance

### Check for Schema Drift
```bash
make check-schema-drift
```

### Update Documentation
```bash
make update-schema-docs
```

### View Full Schemas
- StashDB: `docs/api/stashdb_schema.json`
- ThePornDB: `docs/api/tpdb_schema.json`

---

## References

- [StashDB Documentation](https://stashdb.org/docs)
- [ThePornDB Documentation](https://theporndb.net/docs)
- [GraphQL Specification](https://spec.graphql.org/)
- [Namer Implementation](../../namer/metadata_providers/)
EOF

    # Replace $(date...) with actual date
    local current_date
    current_date=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
    sed -i.bak "s/\$(date -u +\"%Y-%m-%d %H:%M:%S UTC\")/$current_date/" "$output_file"
    rm "${output_file}.bak"

    echo -e "${GREEN}✓ Markdown documentation generated: $output_file${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}=== Updating GraphQL Schema Documentation ===${NC}\n"

    # Check for required environment variables
    if [[ -z "${STASHDB_TOKEN:-}" ]]; then
        echo -e "${RED}Error: STASHDB_TOKEN environment variable not set${NC}"
        exit 1
    fi

    if [[ -z "${TPDB_TOKEN:-}" ]]; then
        echo -e "${RED}Error: TPDB_TOKEN environment variable not set${NC}"
        exit 1
    fi

    # Fetch and save schemas
    echo -e "${BLUE}Step 1: Fetching schemas${NC}"
    fetch_and_save_schema "stashdb" "https://stashdb.org/graphql" "APIKey" "$STASHDB_TOKEN"
    fetch_and_save_schema "tpdb" "https://theporndb.net/graphql" "Authorization" "Bearer $TPDB_TOKEN"

    # Generate markdown documentation
    echo -e "\n${BLUE}Step 2: Generating documentation${NC}"
    generate_markdown_docs

    echo -e "\n${GREEN}✅ Schema documentation updated successfully!${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo -e "  1. Review changes: git diff $DOCS_DIR"
    echo -e "  2. Test integration code with updated schemas"
    echo -e "  3. Commit changes: git add $DOCS_DIR && git commit -m 'docs: update GraphQL schemas'"
}

# Run main function
main "$@"
