# ThePornDB GraphQL Migration

This document describes the migration from ThePornDB's REST API to their GraphQL API.

## Overview

The namer application has been updated to use ThePornDB's GraphQL endpoint (`https://theporndb.net/graphql`) instead of the legacy REST API (`https://api.theporndb.net`). This change provides:

- **Cleaner queries**: GraphQL allows requesting only the data we need
- **Better error handling**: GraphQL provides structured error responses
- **Improved performance**: Fewer round trips and more efficient data fetching
- **Future-proof**: GraphQL is ThePornDB's preferred API going forward

## What Changed

### Configuration
- **Default endpoint**: Changed from `https://api.theporndb.net` to `https://theporndb.net/graphql`
- **Config key**: `override_tpdb_address` now points to GraphQL endpoint by default
- **Backward compatibility**: Existing config files will continue to work

### Core Functionality
All major features have been migrated to GraphQL:

1. **Scene searching** - Uses `searchScenes` GraphQL query
2. **Scene details** - Uses `findScene` GraphQL query  
3. **Hash-based search** - Uses `searchScenesByHash` GraphQL query
4. **User information** - Uses `me` GraphQL query
5. **Collection management** - Uses `markSceneCollected` GraphQL mutation
6. **Hash sharing** - Uses `shareSceneHash` GraphQL mutation

### File Structure Changes

#### New Files
- `namer/metadata_providers/theporndb_provider.py` - Complete GraphQL implementation
- Enhanced provider factory in `namer/metadata_providers/factory.py`

#### Modified Files
- `namer/configuration.py` - Updated default GraphQL endpoint
- `namer/namer.cfg.default` - Updated configuration comments
- `namer/metadataapi.py` - Routes to GraphQL provider by default

## Migration Process

The migration followed the "nail it before we scale it" principle:

### Phase 1: Infrastructure ✅
- [x] Updated configuration to use GraphQL endpoint
- [x] Implemented GraphQL HTTP request handling
- [x] Created GraphQL response to data structure mapping

### Phase 2: Core Features ✅
- [x] Implemented GraphQL scene search functionality
- [x] Implemented GraphQL scene detail lookup
- [x] Migrated user info and collection management
- [x] Updated all routing to use GraphQL by default

### Phase 3: Safety & Testing ✅
- [x] Validated GraphQL implementation with test suite
- [x] Maintained legacy REST code as fallback
- [x] Added deprecation notices to legacy functions

## Usage

### For End Users
No changes required! The application automatically uses GraphQL with existing configurations.

### For Developers

#### Using the GraphQL Provider Directly
```python
from namer.metadata_providers.theporndb_provider import ThePornDBProvider
from namer.configuration_utils import default_config

provider = ThePornDBProvider()
config = default_config()

# Search for scenes
results = provider.match(parsed_filename, config, phash)

# Get complete scene info
scene_info = provider.get_complete_info(parsed_filename, "scenes/123456", config)

# Get user information
user_info = provider.get_user_info(config)
```

#### GraphQL Queries Used

**Scene Search:**
```graphql
query SearchScenes($query: String!, $page: Int) {
  searchScenes(input: {query: $query, page: $page}) {
    data {
      id, title, date, url, description, duration
      site { name, parent { name }, network { name } }
      performers { name, parent { name, image, extras { gender } } }
      tags { name }
      hashes { hash, type, duration }
    }
  }
}
```

**Scene Details:**
```graphql
query GetScene($id: ID!) {
  findScene(id: $id) {
    id, title, date, url, description, duration, isCollected
    site { name, parent { name }, network { name } }
    performers { name, parent { name, image, extras { gender } } }
    tags { name }
    hashes { hash, type, duration }
  }
}
```

## Backward Compatibility

### Legacy REST Support
The legacy REST API implementation remains available in `metadataapi.py` as `_match_legacy_theporndb()` for backward compatibility, but is marked as deprecated.

### Configuration Migration
- Existing config files continue to work
- `override_tpdb_address` can still point to REST endpoints for testing
- No user action required for migration

## Testing

The migration includes comprehensive testing:

```bash
# Run existing test suite (validates GraphQL integration)
poetry run pytest

# Run specific GraphQL-related tests  
poetry run pytest test/namer_metadataapi_test.py -v
```

## Performance Considerations

### Improvements
- **Reduced API calls**: GraphQL allows fetching complete scene data in single request
- **Bandwidth efficiency**: Only requested fields are returned
- **Better caching**: HTTP caching works seamlessly with GraphQL POST requests

### Considerations
- **Query complexity**: More complex GraphQL queries may have higher server cost
- **Error handling**: GraphQL errors are handled gracefully with fallback behavior

## Troubleshooting

### Common Issues

**Configuration Problems:**
```
Error: Invalid GraphQL endpoint
```
Solution: Check `override_tpdb_address` points to valid GraphQL endpoint

**Authentication Errors:**
```
GraphQL error: Invalid token
```
Solution: Verify `porndb_token` is valid and has required permissions

**Network Issues:**
```
HTTP error 500: Internal server error  
```
Solution: Check ThePornDB service status or fallback to legacy implementation

### Debugging

Enable debug logging to see GraphQL queries and responses:
```python
config.debug = True
config.diagnose_errors = True  # Be careful - may log tokens
```

## Future Considerations

### Planned Improvements
- [ ] GraphQL subscription support for real-time updates
- [ ] Query optimization based on usage patterns  
- [ ] Batch operations for processing multiple files
- [ ] Enhanced error recovery and retry logic

### Migration to Other Providers
The provider pattern makes it easy to add other GraphQL-based metadata providers following the same structure.

## References

- [ThePornDB GraphQL Documentation](https://theporndb.net/graphql) 
- [GraphQL Specification](https://graphql.org/learn/)
- [Namer Provider Architecture](namer/metadata_providers/README.md)

---

*This migration maintains full backward compatibility while enabling future GraphQL-based enhancements.*
