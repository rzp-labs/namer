# GraphQL Schema Maintenance Guide

This guide explains how to maintain and monitor GraphQL schema documentation for Namer's metadata provider integrations.

## Overview

Namer integrates with two external GraphQL APIs:
- **StashDB** (stashdb.org)
- **ThePornDB** (theporndb.net)

Since these APIs can change without notice, we use **automated schema introspection** and **drift detection** to ensure our documentation and integration code stay current.

---

## Quick Reference

| Task | Command | When |
|------|---------|------|
| **Check for drift** | `make check-schema-drift` | Before updating integration code |
| **Update docs** | `make update-schema-docs` | After API changes detected |
| **View schemas** | View `docs/api/*_schema.json` | Any time |
| **Test locally** | `scripts/check-schema-drift.sh` | Development workflow |

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     External APIs                            │
│  ┌──────────────────┐          ┌──────────────────┐         │
│  │  StashDB API     │          │  ThePornDB API   │         │
│  │  (stashdb.org)   │          │ (theporndb.net)  │         │
│  └────────┬─────────┘          └────────┬─────────┘         │
└───────────┼──────────────────────────────┼───────────────────┘
            │                              │
            │ GraphQL Introspection        │
            │                              │
┌───────────▼──────────────────────────────▼───────────────────┐
│              Schema Drift Detection                           │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  scripts/check-schema-drift.sh                       │    │
│  │  • Fetches current schemas                           │    │
│  │  • Compares with baseline                            │    │
│  │  • Generates diff reports                            │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────┬───────────────────────────────────────────────────┘
            │
            │ Drift detected?
            ├─────────── YES ──────────┐
            │                          │
            │                          ▼
            │              ┌───────────────────────┐
            │              │  Create GitHub Issue  │
            │              │  Alert maintainers    │
            │              └───────────────────────┘
            │
            │
┌───────────▼───────────────────────────────────────────────────┐
│               Documentation Update                            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  scripts/update-schema-docs.sh                       │    │
│  │  • Fetches latest schemas                            │    │
│  │  • Saves to docs/api/                                │    │
│  │  • Regenerates markdown docs                         │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

### Files

```
docs/api/
├── stashdb_schema.json          # Complete StashDB schema (baseline)
├── tpdb_schema.json             # Complete ThePornDB schema (baseline)
├── graphql_schema_documentation.md  # Human-readable docs
├── graphql_schemas_report.json  # Technical comparison report
└── SCHEMA_MAINTENANCE.md        # This file

scripts/
├── check-schema-drift.sh        # Drift detection script
└── update-schema-docs.sh        # Documentation update script

.github/workflows/
└── schema-drift-check.yml       # CI automation
```

---

## How It Works

### 1. Schema Introspection

Both scripts use GraphQL introspection queries to fetch complete schema metadata:

```graphql
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      name
      kind
      description
      fields { ... }
      inputFields { ... }
      enumValues { ... }
    }
  }
}
```

This returns the **entire schema structure** including:
- All types (objects, enums, interfaces, unions)
- All queries and mutations
- Field definitions and arguments
- Type relationships

### 2. Drift Detection

The drift detection process:

1. **Fetch** current schemas from live APIs
2. **Normalize** both current and baseline schemas (sort, format)
3. **Compare** using `diff` to detect changes
4. **Report** findings with detailed diffs

**Exit codes:**
- `0` = No drift (schemas match)
- `1` = Drift detected (schemas differ)
- `2` = No baseline found

### 3. Automated Monitoring

GitHub Actions workflow runs:

**Weekly Schedule:**
- Every Monday at 9 AM UTC
- Checks for drift automatically
- Creates GitHub issue if drift detected

**On Pull Requests:**
- When metadata provider code changes
- When schema docs change
- Fails PR if drift detected without doc updates

**Manual Trigger:**
- Via GitHub Actions UI
- For on-demand checks

---

## Usage

### Local Development

#### Check for Schema Drift

```bash
# Using Make (recommended)
make check-schema-drift

# Or directly
export STASHDB_TOKEN="your_token"
export TPDB_TOKEN="your_token"
./scripts/check-schema-drift.sh
```

**Output:**
```
=== GraphQL Schema Drift Detection ===

Step 1: Fetching current schemas
✓ Successfully fetched stashdb schema
✓ Successfully fetched tpdb schema

Step 2: Comparing with baseline
✓ stashdb: No schema drift detected
⚠ tpdb: Schema drift detected!

Summary of changes:
  • Fields changed: 12

Full diff saved to: /tmp/tpdb_drift.diff

⚠ Schema drift detected. Review changes and update documentation.
```

#### Update Documentation

After drift is detected and reviewed:

```bash
# Using Make (recommended)
make update-schema-docs

# Or directly
export STASHDB_TOKEN="your_token"
export TPDB_TOKEN="your_token"
./scripts/update-schema-docs.sh
```

This will:
1. Fetch latest schemas
2. Save to `docs/api/`
3. Regenerate markdown documentation
4. Display next steps

**Next steps after update:**
```bash
# 1. Review changes
git diff docs/api/

# 2. Test integration code
poetry run pytest test/

# 3. Commit updates
git add docs/api/
git commit -m "docs: update GraphQL schemas"
```

### CI/CD Integration

#### Workflow Triggers

The schema drift check workflow runs automatically:

**1. Weekly Schedule (Monday 9 AM UTC)**
- Checks both APIs for changes
- Creates GitHub issue if drift detected
- Uploads diff artifacts

**2. Pull Request Changes**
- Runs on changes to:
  - `namer/metadata_providers/**`
  - `docs/api/**`
  - Drift detection scripts
- Fails PR if schemas outdated

**3. Manual Dispatch**
- Run via Actions UI
- Useful for ad-hoc checks

#### GitHub Issue Creation

When drift is detected on schedule, an issue is automatically created:

**Title:** `⚠️ GraphQL Schema Drift Detected - YYYY-MM-DD`

**Labels:** `schema-drift`, `documentation`, `maintenance`

**Content:**
- Summary of changes
- Link to workflow run
- Detailed action items
- Artifact links

If an open drift issue already exists, a comment is added instead.

#### Artifacts

Workflow uploads:
- `*_drift.diff` - Detailed schema diffs
- `schema_drift_report.md` - Summary report

**Retention:** 30 days

---

## Authentication

### Required Secrets

Add to GitHub repository secrets:

```
STASHDB_TOKEN    # StashDB API key
TPDB_TOKEN       # ThePornDB Bearer token
```

**Local development:**
```bash
export STASHDB_TOKEN="your_stashdb_key"
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

**Expected response:**
```json
{
  "data": {
    "me": {
      "id": "...",
      "name": "...",
      "roles": [...]
    }
  }
}
```

---

## Interpreting Drift

### Types of Changes

#### 1. **Breaking Changes** (High Priority)

**Indicators:**
- Removed types or fields
- Changed field types
- Removed enum values
- Required fields added

**Action Required:**
- Update integration code immediately
- Add compatibility layer if needed
- Update tests
- Document breaking change

**Example:**
```diff
- "name": "studio"
+ "name": "site"
```

#### 2. **Additions** (Medium Priority)

**Indicators:**
- New types added
- New fields added
- New enum values

**Action Required:**
- Review for useful new features
- Consider integrating new fields
- Update documentation
- Optional: enhance integration

**Example:**
```diff
  fields: [
    { name: "title" },
    { name: "date" },
+   { name: "director" }
  ]
```

#### 3. **Deprecations** (Medium Priority)

**Indicators:**
- Fields marked deprecated
- Deprecation reason provided

**Action Required:**
- Plan migration to new fields
- Test with deprecated fields
- Schedule update work

**Example:**
```diff
  fields: [
    {
      name: "release_date",
-     isDeprecated: false
+     isDeprecated: true,
+     deprecationReason: "Use 'date' instead"
    }
  ]
```

#### 4. **Documentation Changes** (Low Priority)

**Indicators:**
- Description text changes
- Comment updates
- No structural changes

**Action Required:**
- Update documentation
- Review for clarifications

---

## Best Practices

### 1. Regular Checks

Run drift detection:
- **Before** starting integration work
- **After** API announcements
- **Weekly** via CI automation

### 2. Version Control

Always commit schema updates with:
- Clear commit message
- Link to API changelog if available
- Summary of breaking changes

**Example commit:**
```bash
git commit -m "docs: update ThePornDB schema - add director field

- Added Scene.director field (optional)
- Deprecated Scene.release_date in favor of Scene.date
- No breaking changes to existing integration

Ref: https://theporndb.net/changelog/2024-01
"
```

### 3. Testing Strategy

After schema updates:

```bash
# 1. Run full test suite
poetry run pytest

# 2. Specifically test affected providers
poetry run pytest test/metadata_provider_test.py -k theporndb

# 3. Integration test with real API (if tokens available)
STASHDB_TOKEN=$STASHDB_TOKEN TPDB_TOKEN=$TPDB_TOKEN \
  poetry run pytest test/integration/
```

### 4. Communication

When drift detected:
- **Internal:** Update team via issue/PR comments
- **Documentation:** Update CHANGELOG.md
- **Users:** Mention in release notes if user-facing

---

## Troubleshooting

### Common Issues

#### 1. Authentication Failures

**Symptom:**
```
Error fetching stashdb schema:
[{"message": "Unauthorized"}]
```

**Solutions:**
- Verify token is set: `echo $STASHDB_TOKEN`
- Test auth manually (see Authentication section)
- Check token hasn't expired
- Verify correct header format

#### 2. Rate Limiting

**Symptom:**
```
Error: 429 Too Many Requests
```

**Solutions:**
- Wait before retrying
- Reduce check frequency
- Contact API provider for rate limit increase

#### 3. False Positives

**Symptom:**
Schema diff shows changes but API didn't change.

**Causes:**
- Field order differences (normalized by script)
- Whitespace differences (normalized by script)
- JSON formatting differences (normalized by script)

**Solutions:**
- Check if changes are structural or cosmetic
- Review normalized diffs in `/tmp/`
- Manually inspect schema files

#### 4. Network Issues

**Symptom:**
```
curl: (6) Could not resolve host
```

**Solutions:**
- Check internet connectivity
- Verify endpoint URLs
- Check for DNS issues
- Try different network

---

## Maintenance Schedule

### Weekly Tasks (Automated)

- ✅ Run drift detection via CI
- ✅ Create issues for detected drift
- ✅ Upload artifacts for review

### Monthly Tasks (Manual)

- Review and close resolved drift issues
- Update integration tests with new API features
- Review API changelogs for upcoming changes
- Update this maintenance guide if needed

### Quarterly Tasks (Manual)

- Audit token permissions and security
- Review CI workflow performance
- Update dependencies (jq, curl, etc.)
- Test disaster recovery (schema baseline restoration)

---

## Emergency Procedures

### Breaking API Change Without Notice

**Symptoms:**
- Integration tests suddenly fail
- Production errors from metadata providers
- Unexpected API responses

**Immediate Actions:**

1. **Identify scope:**
   ```bash
   make check-schema-drift
   ```

2. **Review diff:**
   ```bash
   cat /tmp/*_drift.diff
   ```

3. **Quick fix options:**
   - **Option A:** Revert to last working integration
   - **Option B:** Add compatibility shim
   - **Option C:** Update integration code

4. **Update documentation:**
   ```bash
   make update-schema-docs
   git add docs/api/
   git commit -m "docs: emergency schema update - [description]"
   ```

5. **Test thoroughly:**
   ```bash
   poetry run pytest
   ```

6. **Deploy fix:**
   - Create hotfix branch if production affected
   - Follow release process
   - Monitor for errors

### Schema File Corruption

**Symptoms:**
- `jq` errors when reading schema files
- Invalid JSON in baseline files

**Recovery:**

1. **Fetch fresh schemas:**
   ```bash
   make update-schema-docs
   ```

2. **Verify JSON validity:**
   ```bash
   jq empty docs/api/stashdb_schema.json
   jq empty docs/api/tpdb_schema.json
   ```

3. **If still corrupted, restore from git:**
   ```bash
   git checkout HEAD -- docs/api/stashdb_schema.json
   git checkout HEAD -- docs/api/tpdb_schema.json
   ```

---

## Contributing

### Adding New Metadata Providers

When adding a new GraphQL provider:

1. **Add endpoint configuration:**
   ```python
   # namer/metadata_providers/new_provider.py
   ENDPOINT = "https://api.example.com/graphql"
   ```

2. **Fetch initial schema:**
   ```bash
   # Manually fetch and save baseline
   curl -X POST "$ENDPOINT" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"query":"...introspection query..."}' \
     | jq '.data' > docs/api/newprovider_schema.json
   ```

3. **Update drift detection script:**
   ```bash
   # Add to scripts/check-schema-drift.sh
   fetch_schema "newprovider" "$ENDPOINT" "Authorization" "Bearer $TOKEN"
   compare_schemas "newprovider"
   ```

4. **Update CI workflow:**
   ```yaml
   # Add secret requirement in .github/workflows/schema-drift-check.yml
   env:
     NEW_PROVIDER_TOKEN: ${{ secrets.NEW_PROVIDER_TOKEN }}
   ```

5. **Document:**
   - Add to `graphql_schema_documentation.md`
   - Update this maintenance guide

---

## References

- [GraphQL Introspection Specification](https://spec.graphql.org/October2021/#sec-Introspection)
- [StashDB API Documentation](https://stashdb.org/docs) (namer/metadata_providers/stashdb_provider.py:543)
- [ThePornDB API Documentation](https://theporndb.net/docs) (namer/metadata_providers/theporndb_provider.py:57)
- [Project CLAUDE.md](../../CLAUDE.md) - Development workflow
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-10-13 | Initial schema maintenance system created | System |

---

**Questions or Issues?**

- Open a GitHub issue with label `schema-drift`
- Check existing drift detection issues
- Review [CLAUDE.md](../../CLAUDE.md) for development guidelines
