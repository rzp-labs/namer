# Agent Memory Store

Historical learning data from development sessions. This structured archive preserves rich context and debugging journeys while keeping CLAUDE.md focused on actionable patterns.

## Structure

```json
{
  "metadata": {
    "version": "1.0.0",
    "last_updated": "2025-10-13T00:00:00Z",
    "total_sessions": 17,
    "description": "..."
  },
  "sessions": [
    {
      "id": "lesson-001",
      "date": "2025-10-13",
      "title": "...",
      "category": "pr-workflow",
      "tags": ["tag1", "tag2", ...],
      "problem": "...",
      "solution": "...",
      "pattern": "...",
      "impact": {
        "roi": "...",
        "performance": "...",
        "quality": "..."
      },
      "related_files": [...],
      "related_prs": [...],
      "code_examples": [...]
    }
  ]
}
```

## Categories

- **pr-workflow**: Pull request strategies, code review, atomic PRs
- **git-hooks**: Pre-commit, pre-push optimization, file type filtering
- **shell-scripting**: Bash patterns, shellcheck compliance, heredocs
- **ci-cd**: CI/CD automation, workflows, exit codes, artifact paths
- **code-review**: Review response, issue management, AI feedback
- **code-quality**: Formatting, linting, consistency
- **cross-platform**: macOS/Linux compatibility patterns

## Querying Examples

### Search by category

```bash
jq '.sessions[] | select(.category == "pr-workflow")' .agent/memory.json
```

### Search by tag

```bash
jq '.sessions[] | select(.tags[] | contains("performance"))' .agent/memory.json
```

### Find by date range

```bash
jq '.sessions[] | select(.date >= "2025-10-01" and .date <= "2025-10-31")' .agent/memory.json
```

### Get all patterns for a topic

```bash
jq '.sessions[] | select(.tags[] | contains("git-hooks")) | {title, pattern}' .agent/memory.json
```

### List all lessons by category

```bash
jq '.sessions | group_by(.category) | map({category: .[0].category, count: length, lessons: map(.title)})' .agent/memory.json
```

### Find lessons with specific PR references

```bash
jq '.sessions[] | select(.related_prs[] | contains("#141"))' .agent/memory.json
```

### Extract code examples for a specific language

```bash
jq '.sessions[].code_examples[] | select(.language == "bash")' .agent/memory.json
```

## Usage in Development

### Finding Patterns

When working on a specific feature or debugging an issue:

1. **Search by category** - Find all lessons in relevant domain
2. **Search by tags** - Narrow to specific technique or tool
3. **Review pattern** - Get actionable implementation guidance
4. **Check code examples** - See working examples for copy-paste

### Adding New Lessons

When capturing new learnings:

1. Assign next sequential ID (lesson-018, lesson-019, etc.)
2. Use consistent category names (see Categories section)
3. Add 3-5 searchable tags
4. Structure problem/solution/pattern/impact clearly
5. Include code examples where applicable
6. Reference related PRs and files
7. Update `metadata.total_sessions` count
8. Update `metadata.last_updated` timestamp

## Maintenance

### Periodic Review

- **Monthly**: Review and consolidate similar patterns
- **Quarterly**: Update cross-references between lessons
- **Yearly**: Archive obsolete patterns to separate file

### Quality Checks

```bash
# Validate JSON structure
jq empty .agent/memory.json && echo "Valid JSON"

# Count lessons by category
jq '.sessions | group_by(.category) | map({category: .[0].category, count: length})' .agent/memory.json

# Find lessons without code examples
jq '.sessions[] | select(.code_examples | length == 0) | .title' .agent/memory.json

# List all unique tags
jq '[.sessions[].tags[]] | unique | sort' .agent/memory.json
```

## Integration with CLAUDE.md

The distilled "Lessons Learned" section in CLAUDE.md references this archive:

- **CLAUDE.md**: Actionable patterns (~100 lines)
- **memory.json**: Complete historical context (full details)
- **Workflow**: Scan CLAUDE.md for patterns → Dive into memory.json for details

Pattern references in CLAUDE.md:
```markdown
_Reference: `.agent/memory.json` (lesson-001, lesson-005, lesson-006) for detailed ROI metrics_
```

## Benefits

1. **Reduced CLAUDE.md size**: From 1,460 lines → ~1,250 lines (~200 line reduction)
2. **Preserved context**: No knowledge lost, rich details archived
3. **Structured querying**: Find patterns by category, tags, dates
4. **Actionable patterns**: CLAUDE.md stays focused on "what to do"
5. **Historical insight**: memory.json preserves "why and how we learned"
6. **Searchable archive**: jq queries enable powerful filtering
7. **Maintainable**: Clear separation makes updates easier

## Version History

- **v1.0.0** (2025-10-13): Initial distillation of 17 lessons from CLAUDE.md
