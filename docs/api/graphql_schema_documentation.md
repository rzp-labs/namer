# GraphQL Schema Documentation: StashDB & ThePornDB

## Executive Summary

Both StashDB and ThePornDB provide GraphQL APIs for querying adult content metadata. This document provides comprehensive schema documentation for both services, including endpoint URLs, authentication methods, available queries/mutations, and key differences.

---

## 1. Service Endpoints & Authentication

### StashDB (stashdb.org)

**Endpoint URL:**
```
https://stashdb.org/graphql
```

**Authentication Method:**
- Header: `APIKey: <your-token>`
- Additional headers:
  - `Content-Type: application/json`
  - `Accept: application/json`
  - `User-Agent: namer-1`

**Configuration in Namer:**
- Environment variable: `STASHDB_ENDPOINT` (optional override)
- Config field: `config.stashdb_endpoint` (optional override)
- Token: `config.stashdb_token`

**Example Request:**
```bash
curl -X POST https://stashdb.org/graphql \
  -H "Content-Type: application/json" \
  -H "APIKey: $STASHDB_TOKEN" \
  -H "User-Agent: namer-1" \
  -d '{"query": "query { me { id name roles } }"}'
```

---

### ThePornDB (theporndb.net)

**Endpoint URL:**
```
https://theporndb.net/graphql
```

**Authentication Method:**
- Header: `Authorization: Bearer <your-token>`
- Additional headers:
  - `Content-Type: application/json`
  - `Accept: application/json`
  - `User-Agent: namer-1`

**Configuration in Namer:**
- Environment variable: `TPDB_ENDPOINT` (optional override)
- Config field: `config.override_tpdb_address` (optional override)
- Token: `config.porndb_token`

**Example Request:**
```bash
curl -X POST https://theporndb.net/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TPDB_TOKEN" \
  -H "User-Agent: namer-1" \
  -d '{"query": "query { me { id name } }"}'
```

---

## 2. Schema Complexity Comparison

| Metric | ThePornDB | StashDB |
|--------|-----------|---------|
| **Total Types** | 30 | 181 |
| **Object Types** | 18 | 59 |
| **Input Types** | 6 | 78 |
| **Enum Types** | 0 | 28 |
| **Scalar Types** | 6 | 9 |
| **Union Types** | 0 | 7 |
| **Queries** | 7 | 35 |
| **Mutations** | 5 | 70+ |

**Analysis:**
- **StashDB** has a significantly more complex schema with extensive CRUD operations, draft/edit workflows, and user management
- **ThePornDB** has a simpler, more streamlined schema focused on querying and basic submissions
- Both support the core functionality needed by the namer application: scene search, fingerprint matching, and metadata retrieval

---

## 3. Key Queries Used by Namer

### 3.1 Scene Search by Text

**ThePornDB:**
```graphql
query SearchScene($term: String!) {
    searchScene(term: $term) {
        id
        title
        date
        duration
        urls { view }
        site {
            name
            parent { name }
            network { name }
        }
        performers {
            performer {
                name
                image
            }
        }
        tags { name }
    }
}
```

**StashDB:**
```graphql
query SearchScenes($term: String!) {
    searchScene(term: $term) {
        id
        title
        date
        urls { url }
        details
        duration
        images { url }
        studio {
            name
            parent { name }
        }
        performers {
            performer {
                name
                aliases
                images { url }
                gender
            }
        }
        tags { name }
        fingerprints {
            hash
            algorithm
            duration
        }
    }
}
```

---

### 3.2 Scene Lookup by ID

**ThePornDB:**
```graphql
query GetScene($id: ID!) {
    findScene(id: $id) {
        id
        title
        date
        duration
        urls { view }
        isCollected
        site {
            name
            parent { name }
            network { name }
        }
        performers {
            performer {
                name
                image
            }
        }
        tags { name }
    }
}
```

**StashDB:**
```graphql
query FindScene($id: ID!) {
    findScene(id: $id) {
        id
        title
        date
        urls { url }
        details
        duration
        images { url }
        studio {
            name
            parent { name }
        }
        performers {
            performer {
                name
                aliases
                images { url }
                gender
            }
        }
        tags { name }
        fingerprints {
            hash
            algorithm
            duration
        }
    }
}
```

---

### 3.3 Scene Search by Fingerprint/Hash

**ThePornDB:**
```graphql
query FindByFingerprints($fingerprints: [[FingerprintQueryInput]]) {
    findScenesBySceneFingerprints(fingerprints: $fingerprints) {
        # Returns [[Scene]] - nested arrays
        id
        title
        date
        # ... scene fields
    }
}
```

**StashDB:**
```graphql
query SearchByFingerprint($hash: String!) {
    findSceneByFingerprint(fingerprint: {hash: $hash, algorithm: PHASH}) {
        id
        title
        date
        urls { url }
        details
        duration
        images { url }
        studio {
            name
            parent { name }
        }
        performers {
            performer {
                name
                aliases
                images { url }
                gender
            }
        }
        tags { name }
        fingerprints {
            hash
            algorithm
            duration
        }
    }
}
```

---

### 3.4 User Information

**Both Services:**
```graphql
query Me {
    me {
        id
        name
        roles  # StashDB returns enum array, ThePornDB returns string array
    }
}
```

---

## 4. Key Mutations Used by Namer

### 4.1 Submit Fingerprint/Hash

**ThePornDB:**
```graphql
mutation SubmitFingerprint($input: FingerprintSubmission) {
    submitFingerprint(input: $input)
}

# Input type:
input FingerprintSubmission {
    scene_id: ID!
    fingerprint: FingerprintInput!
    unmatch: Boolean
}

input FingerprintInput {
    user_ids: [Int]
    hash: String!
    algorithm: String!
    duration: Int!
}
```

**StashDB:**
```graphql
mutation SubmitFingerprint($input: FingerprintSubmission!) {
    submitFingerprint(input: $input)
}

# Input type:
input FingerprintSubmission {
    scene_id: ID!
    fingerprint: FingerprintInput!
    unmatch: Boolean
}

input FingerprintInput {
    user_ids: [Int]
    hash: String!
    algorithm: String!
    duration: Int!
}
```

---

### 4.2 Mark Scene as Collected (ThePornDB only)

**ThePornDB:**
```graphql
# Note: This mutation is not visible in the introspection schema
# but is referenced in the namer codebase. It may be a custom
# extension or part of a different API endpoint.
```

---

### 4.3 Favorite Performer/Studio

**Both Services:**
```graphql
mutation FavoritePerformer($id: ID!, $favorite: Boolean!) {
    favoritePerformer(id: $id, favorite: $favorite)
}

mutation FavoriteStudio($id: ID!, $favorite: Boolean!) {
    favoriteStudio(id: $id, favorite: $favorite)
}
```

---

## 5. Core Object Types

### 5.1 Scene Type

**Common Fields (Both Services):**
- `id: ID!` - Unique identifier
- `title: String!` - Scene title
- `date: String` - Release date (YYYY-MM-DD)
- `duration: Int` - Duration in seconds
- `studio: Studio` - Production studio
- `performers: [PerformerAppearance]` - Cast
- `tags: [Tag]` - Content tags
- `images: [Image]` - Poster/screenshot URLs
- `fingerprints: [Fingerprint]` - Hash data
- `deleted: Boolean` - Soft delete flag
- `created: DateTime/Time` - Creation timestamp
- `updated: DateTime/Time` - Last update timestamp

**ThePornDB-Specific Fields:**
- `urls: [URL]` with `view` field
- `site: Studio` - Alias for studio
- `details: String` - Description
- `director: String`
- `code: String` - Scene code/identifier

**StashDB-Specific Fields:**
- `urls: [URL!]!` with `url` field (non-null)
- `release_date: String` - Explicit release date
- `production_date: String` - Explicit production date
- `details: String` - Description
- `director: String`
- `code: String` - Scene code/identifier

---

### 5.2 Performer Type

**Common Fields:**
- `id: ID!`
- `name: String` / `String!`
- `aliases: [String]`
- `gender: String` / `GenderEnum`
- `birthdate: String` / `FuzzyDate`
- `ethnicity: String` / `EthnicityEnum`
- `country: String`
- `eye_color: String` / `EyeColorEnum`
- `hair_color: String` / `HairColorEnum`
- `height: Int` - Height in cm
- `images: [Image]`

**StashDB Enhancements:**
- Typed enums for gender, ethnicity, eye color, hair color
- More detailed measurements (cup_size, band_size, waist_size, hip_size)
- Tattoos and piercings as structured data
- Career start/end years
- Scene count and scenes list
- Merge tracking (merged_ids, merged_into_id)

---

### 5.3 Fingerprint Type

**Common Fields:**
- `hash: String` / `String!` - Hash value (hex string)
- `algorithm: String` / `FingerprintAlgorithm!` - Algorithm used (PHASH, MD5, OSHASH, etc.)
- `duration: Int` / `Int!` - Video duration in seconds
- `submissions: Int` - Number of user submissions
- `created: DateTime/Time`
- `updated: DateTime/Time`
- `user_submitted: Boolean` - Whether current user submitted

**StashDB-Specific:**
- `reports: Int` - Number of mismatch reports
- `user_reported: Boolean` - Whether current user reported mismatch

---

### 5.4 Studio Type

**Common Fields:**
- `id: ID!`
- `name: String!`
- `parent: Studio` - Parent company
- `urls: [URL]`
- `images: [Image]`
- `aliases: [String]`
- `deleted: Boolean`
- `is_favorite: Boolean`

**StashDB-Specific:**
- `child_studios: [Studio!]!` - Network of child studios

---

### 5.6 Image Type

**Both Services (Identical):**
```graphql
type Image {
    id: ID!
    url: String!
    width: Int!
    height: Int!
}
```

---

## 6. Fingerprint Algorithms Supported

Based on the code and schema analysis:

**Supported Hash Types:**
- `PHASH` - Perceptual hash (primary for video matching)
- `MD5` - MD5 checksum
- `OSHASH` - OpenSubtitles hash
- `CRC32` - CRC32 checksum (ThePornDB)

**StashDB Enum Values (from schema):**
```graphql
enum FingerprintAlgorithm {
    MD5
    PHASH
    OSHASH
    # ... potentially more
}
```

---

## 7. Key Differences Between Services

### 7.1 Authentication
- **StashDB**: Uses `APIKey` header (not standard Bearer token)
- **ThePornDB**: Uses standard `Authorization: Bearer` header

### 7.2 Schema Complexity
- **StashDB**: Full CRUD operations, edit proposals, voting system, draft submissions
- **ThePornDB**: Simpler schema focused on queries and basic submissions

### 7.3 Field Naming
- **StashDB**: More explicit (e.g., `release_date` vs `date`)
- **ThePornDB**: More compact (e.g., `urls[].view` vs `urls[].url`)
- **StashDB**: Uses enums extensively (GenderEnum, EthnicityEnum, etc.)
- **ThePornDB**: Uses strings for most categorical data

### 7.4 URL Structure
- **StashDB**: Scene UUIDs are scene IDs directly
- **ThePornDB**: Scene UUIDs follow `scenes/{id}` format in namer code

### 7.5 Fingerprint Queries
- **StashDB**: 
  - `findSceneByFingerprint(fingerprint: FingerprintQueryInput!)` - Single hash
  - `findScenesByFingerprints(fingerprints: [String!]!)` - Multiple hashes (simple strings)
  - `findScenesByFullFingerprints(fingerprints: [FingerprintQueryInput!]!)` - Full fingerprint objects
  - `findScenesBySceneFingerprints(fingerprints: [[FingerprintQueryInput!]!]!)` - Nested arrays for batch scene matching

- **ThePornDB**:
  - `findScenesBySceneFingerprints(fingerprints: [[FingerprintQueryInput]])` - Nested arrays for batch scene matching

### 7.6 Collection Management
- **ThePornDB**: Has `isCollected` field and mutation to mark scenes as collected
- **StashDB**: No collection tracking in public schema

---

## 8. Usage Patterns in Namer Application

### 8.1 Scene Matching Flow

1. **Text Search**: Use `searchScene(term: $term)` to find candidates by title/site/date
2. **Hash Search**: Use fingerprint queries to find exact matches
3. **Consensus Logic**: 
   - If PHASH results have >threshold consensus on one scene ID, return that scene
   - Otherwise, treat as ambiguous and present all candidates
4. **Complete Info**: Use `findScene(id: $id)` to fetch full metadata for selected scene

### 8.2 Fingerprint Submission

When namer processes a video:
1. Calculate PHASH using videophash tool
2. Search for matches using hash
3. If confident match found, submit fingerprint to help community
4. Use `submitFingerprint` mutation with scene ID and hash data

### 8.3 Error Handling

**GraphQL Errors**:
Both services return errors in standard GraphQL format:
```json
{
  "errors": [
    {
      "message": "Error description",
      "locations": [...],
      "path": [...]
    }
  ],
  "data": null
}
```

**HTTP Errors**:
- 401: Invalid or missing API key/token
- 403: Insufficient permissions
- 429: Rate limiting
- 500: Server error

---

## 9. Rate Limiting & Best Practices

### Rate Limiting
- **Both services** implement rate limiting
- **StashDB**: User object includes `api_calls: Int!` field for tracking
- **Best practice**: Cache responses when possible (namer uses `requests-cache`)

### Caching Strategy
```python
# Namer uses cache_session from config
http = Http.request(
    RequestType.POST, 
    endpoint, 
    cache_session=config.cache_session,  # Enable caching
    headers=headers, 
    data=data
)
```

### Query Optimization
- Request only needed fields (GraphQL advantage)
- Use batch queries when searching multiple scenes
- Implement exponential backoff for retries

---

## 10. Implementation Recommendations

### 10.1 For Scene Search Applications

**Recommended Query Fields (Minimum):**
```graphql
{
    id
    title
    date
    site { name }
    performers {
        performer { name }
    }
    fingerprints {
        hash
        algorithm
        duration
    }
}
```

**For Complete Metadata:**
```graphql
{
    id
    title
    date
    duration
    details
    urls { url }  # or { view } for ThePornDB
    site { 
        name 
        parent { name }
    }
    performers {
        performer {
            name
            aliases
            gender
            image
        }
    }
    tags { name }
    images { url width height }
    fingerprints {
        hash
        algorithm
        duration
        submissions
    }
}
```

### 10.2 Fingerprint Matching Logic

**Best Practices:**
1. Always include duration with PHASH submissions
2. Use consensus threshold (e.g., 70%+) for ambiguous results
3. Verify PHASH distance is within acceptable range (e.g., <8 for confident match)
4. Fall back to text search if no hash matches found

### 10.3 Error Recovery

```python
def execute_graphql_query(query, variables, config):
    """Execute GraphQL query with error handling"""
    try:
        response = make_request(query, variables, config)
        
        # Check for GraphQL errors
        if 'errors' in response:
            logger.error(f"GraphQL errors: {response['errors']}")
            return None
            
        return response.get('data')
        
    except HTTPError as e:
        if e.status_code == 401:
            logger.error("Authentication failed - check API token")
        elif e.status_code == 429:
            logger.warning("Rate limited - backing off")
            time.sleep(60)
            return execute_graphql_query(query, variables, config)  # Retry
        else:
            logger.error(f"HTTP error {e.status_code}: {e.response.text}")
        return None
```

---

## 11. Testing Queries

### 11.1 Validate Authentication

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

### 11.2 Search Test

```bash
# Search for "vixen" scenes
curl -X POST <ENDPOINT> \
  -H "<AUTH_HEADER>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query SearchScene($term: String!) { searchScene(term: $term) { id title date } }",
    "variables": {"term": "vixen"}
  }'
```

---

## 12. Schema Evolution & Deprecations

### Deprecated Fields (StashDB)

**Scene:**
- `date: String` → Use `release_date` instead

**Performer:**
- `birthdate: FuzzyDate` → Use `birth_date: String`
- `measurements: Measurements!` → Use individual fields (cup_size, band_size, etc.)

**User:**
- `active_invite_codes: [String!]` → Use `invite_codes: [InviteKey!]`

**URL:**
- `type: String` → Use `site: Site` instead

**Best Practice:** Monitor deprecation warnings in GraphQL responses and update queries accordingly.

---

## 13. Security Considerations

### API Token Storage
- **Never commit tokens** to version control
- Use environment variables: `$STASHDB_TOKEN`, `$TPDB_TOKEN`
- Rotate tokens periodically
- Use separate tokens for dev/prod environments

### Input Validation
- Sanitize user input before including in GraphQL queries
- Use parameterized queries (variables) instead of string concatenation
- Validate scene IDs match expected format before querying

### Error Message Handling
- Don't expose raw error messages to end users
- Log detailed errors server-side
- Return generic "Unable to fetch data" messages to users

---

## 14. Appendix: Full Schema Files

The complete introspection schema responses have been saved to:
- **StashDB**: `/tmp/stashdb_schema.json` (217 KB)
- **ThePornDB**: `/tmp/tpdb_schema.json` (50 KB)

These files contain the full type definitions, input types, enums, and field descriptions for both services.

---

## 15. Quick Reference

| Feature | StashDB | ThePornDB |
|---------|---------|-----------|
| **Endpoint** | `https://stashdb.org/graphql` | `https://theporndb.net/graphql` |
| **Auth Header** | `APIKey: <token>` | `Authorization: Bearer <token>` |
| **Token Env Var** | `$STASHDB_TOKEN` | `$TPDB_TOKEN` |
| **Scene Search** | `searchScene(term: String!)` | `searchScene(term: String!)` |
| **Scene by ID** | `findScene(id: ID!)` | `findScene(id: ID!)` |
| **Hash Search** | `findSceneByFingerprint(...)` | `findScenesBySceneFingerprints(...)` |
| **User Info** | `me { id name roles }` | `me { id name }` |
| **Submit Hash** | `submitFingerprint(...)` | `submitFingerprint(...)` |
| **Schema Complexity** | Very complex (181 types) | Simple (30 types) |
| **Edit System** | Full edit/vote/draft workflow | Draft submissions only |

---

## 16. Common Issues & Solutions

### Issue: "APIKey header missing" (StashDB)
**Solution:** Use `APIKey` header, not `Authorization: Bearer`

### Issue: "Unauthorized" (ThePornDB)
**Solution:** Use `Authorization: Bearer <token>` header format

### Issue: No fingerprint matches found
**Solution:** 
1. Verify PHASH calculation is correct
2. Check hash format (hex string)
3. Ensure duration matches video length
4. Fall back to text search

### Issue: Ambiguous scene matches
**Solution:**
1. Implement disambiguation UI
2. Use additional metadata (date, performers) to refine
3. Allow user to manually select correct match

### Issue: Rate limiting errors
**Solution:**
1. Implement exponential backoff
2. Use caching for repeated queries
3. Batch requests when possible
4. Consider requesting rate limit increase from service

---

## Document Information

**Created:** 2025-10-13  
**Author:** Technical Research Agent (Claude Code)  
**Sources:**
- StashDB GraphQL Introspection (https://stashdb.org/graphql)
- ThePornDB GraphQL Introspection (https://theporndb.net/graphql)
- Namer codebase analysis (stashdb_provider.py, theporndb_provider.py)

**Maintenance:** This document should be updated when schemas change or new features are added to either service.
