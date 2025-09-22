# ThePornDB GraphQL API Schema

This document contains the complete GraphQL schema for ThePornDB API as of the introspection query run.

## Key Features for Namer Integration

1. **Scene Search**: Use `searchScene` for text-based matching
2. **Fingerprint Matching**: Use `findScenesBySceneFingerprints` with perceptual hashes
3. **Fingerprint Submission**: Use `submitFingerprint` to contribute hashes
4. **Complete Metadata**: Scenes include all necessary metadata (title, performers, studio, tags, dates)

## Authentication

All requests require Bearer token authentication:
```
Authorization: Bearer ${TPDB_TOKEN}
```

## Root Types

- **Query**: Read operations
- **Mutation**: Write operations  
- **No Subscription**: Subscriptions are not supported

## Core Data Types

### Scene
The main entity representing adult video content:

```graphql
type Scene {
  id: ID!
  title: String!
  details: String
  date: String
  release_date: String
  production_date: String
  urls: [URL]
  studio: Studio
  tags: [Tag]
  images: [Image]
  performers: [PerformerAppearance]
  fingerprints: [Fingerprint]
  duration: Int
  director: String
  code: String
  deleted: Boolean
  edits: [Edit]
  created: DateTime
  updated: DateTime
}
```

### Performer
Information about adult performers:

```graphql
type Performer {
  id: ID!
  name: String
  disambiguation: String
  aliases: [String]
  gender: String
  urls: [URL]
  birthdate: FuzzyDate
  birth_date: String
  death_date: String
  age: Int
  ethnicity: String
  country: String
  eye_color: String
  hair_color: String
  height: Int
  measurements: Measurements
  cup_size: String
  band_size: Int
  waist_size: Int
  hip_size: Int
  breast_type: String
  career_start_year: Int
  career_end_year: Int
  tattoos: [BodyModification]
  piercings: [BodyModification]
  images: [Image]
  deleted: Boolean
  edits: [Edit]
  scene_count: Int
  scenes: [Scene]
  merged_ids: [ID]
  merged_into_id: ID
  studios: [Studio]
  is_favorite: Boolean
  created: DateTime
  updated: DateTime
}
```

### Studio
Production studio information:

```graphql
type Studio {
  id: ID!
  name: String!
  urls: [URL]
  parent: Studio
  images: [Image]
  aliases: [String]!
  child_studios: [Studio]
  deleted: Boolean
  is_favorite: Boolean
  created: DateTime
  updated: DateTime
}
```

### Tag
Content categorization:

```graphql
type Tag {
  id: ID!
  name: String!
  description: String
  aliases: [String]
  deleted: Boolean
  edits: [Edit]
  category: TagCategory
  created: DateTime
  updated: DateTime
}
```

### Fingerprint
Perceptual hashes for video matching:

```graphql
type Fingerprint {
  hash: String
  algorithm: String
  duration: Int
  submissions: Int
  created: DateTime
  updated: DateTime
  user_submitted: Boolean
}
```

## Query Operations

### Find Operations
```graphql
# Find single scene by ID
findScene(id: ID): Scene

# Find single performer by ID  
findPerformer(id: ID!): Performer

# Find studio by ID or name
findStudio(id: ID, name: String): Studio
```

### Search Operations
```graphql
# Search scenes by text term
searchScene(term: String!, limit: Int): [Scene]

# Search performers by text term
searchPerformer(term: String!, limit: Int): [Performer]

# Find scenes by fingerprint hashes
findScenesBySceneFingerprints(fingerprints: [[FingerprintQueryInput]]): [[Scene]]
```

### User Information
```graphql
# Get current authenticated user
me: User
```

## Mutation Operations

### Fingerprint Submission
```graphql
# Submit fingerprint for scene matching
submitFingerprint(input: FingerprintSubmission): Boolean
```

### Content Submission
```graphql
# Submit new scene draft for review
submitSceneDraft(input: SceneDraftInput): DraftSubmissionStatus

# Submit new performer draft for review  
submitPerformerDraft(input: PerformerDraftInput): DraftSubmissionStatus
```

### Favorites
```graphql
# Mark performer as favorite
favoritePerformer(id: ID!, favorite: Boolean!): Boolean!

# Mark studio as favorite
favoriteStudio(id: ID!, favorite: Boolean!): Boolean!
```

## Input Types

### FingerprintInput
For submitting perceptual hashes:

```graphql
input FingerprintInput {
  user_ids: [Int]
  hash: String!
  algorithm: String!
  duration: Int!
}
```

### FingerprintQueryInput
For searching by fingerprint:

```graphql
input FingerprintQueryInput {
  hash: String!
  algorithm: String!
}
```

### FingerprintSubmission
For associating fingerprints with scenes:

```graphql
input FingerprintSubmission {
  scene_id: ID!
  fingerprint: FingerprintInput!
  unmatch: Boolean
}
```

## Supporting Types

### URL
External links with site information:

```graphql
type URL {
  url: String
  type: String @deprecated(reason: "Use the site field instead")
  site: Site
}
```

### Site
Website/platform information:

```graphql
type Site {
  id: ID
  name: String
}
```

### Image
Image metadata:

```graphql
type Image {
  id: ID!
  url: String!
  width: Int!
  height: Int!
}
```

### PerformerAppearance
Performer participation in scenes:

```graphql
type PerformerAppearance {
  performer: Performer!
  as: String  # stage name used in this scene
}
```

### User
Current user information:

```graphql
type User {
  id: ID
  name: String
  roles: [String]
  email: String
  api_key: String
}
```

## Deprecation Notes

- `URL.type` field is deprecated - use `URL.site` instead
- This aligns with the current codebase which should be updated accordingly

This schema shows ThePornDB has fully migrated from REST to GraphQL, providing more flexible queries and better type safety.

## How This Schema Was Generated

This schema documentation was generated using the following GraphQL introspection query. This introspection query retrieves the complete schema definition, including all types, fields, arguments, and deprecation information.

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TPDB_TOKEN}" \
  -d '{
    "query": "query IntrospectionQuery { __schema { queryType { name } mutationType { name } subscriptionType { name } types { kind name description fields(includeDeprecated: true) { name description args { name description type { name kind ofType { name kind } } defaultValue } type { name kind ofType { name kind } } isDeprecated deprecationReason } inputFields { name description type { name kind ofType { name kind } } defaultValue } enumValues(includeDeprecated: true) { name description isDeprecated deprecationReason } possibleTypes { name } } } }"
  }' \
  https://theporndb.net/graphql
```

Or as a formatted GraphQL query:

```graphql
query IntrospectionQuery {
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
          type {
            name
            kind
            ofType {
              name
              kind
            }
          }
          defaultValue
        }
        type {
          name
          kind
          ofType {
            name
            kind
          }
        }
        isDeprecated
        deprecationReason
      }
      inputFields {
        name
        description
        type {
          name
          kind
          ofType {
            name
            kind
          }
        }
        defaultValue
      }
      enumValues(includeDeprecated: true) {
        name
        description
        isDeprecated
        deprecationReason
      }
      possibleTypes {
        name
      }
    }
  }
}
```
