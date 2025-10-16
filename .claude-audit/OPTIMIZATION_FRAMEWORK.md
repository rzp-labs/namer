# Command Optimization Framework

This framework provides structured guidance for optimizing Claude Code slash commands.

## Analysis Methodology

### Phase 1: Inventory & Categorization

**Objective:** Understand what commands exist and group them logically

**Steps:**
1. Run `./analyze-commands.sh` to generate inventory
2. Review each command's purpose and documentation
3. Assign categories based on primary function
4. Identify commands that span multiple categories

**Output:** Categorized command list with metadata

### Phase 2: Overlap Detection

**Objective:** Find redundancy and consolidation opportunities

#### A. Name-Based Analysis

Look for commands with similar names:

```
Pattern: PREFIX + ACTION
Examples:
- /create-* vs /generate-* vs /make-*
- /test vs /tests vs /testing
- /setup-* vs /init-* vs /start-*
```

**Red Flags:**
- Same prefix, different verbs (create vs generate)
- Same concept, different plurality (test vs tests)
- Same action, different prefixes (git-feature vs feature)

#### B. Function-Based Analysis

Look for commands that solve the same problem:

```
Example Overlaps:
- /generate-tests + /write-tests + /test-coverage
  → Could be: /test --generate, /test --coverage

- /pr-review + /code-review + /review-pr
  → Could be: /review [--type=pr|code]

- /standup + /daily-standup + /standup-report
  → Could be: /standup [--format=brief|detailed]
```

**Detection Method:**
1. Read command descriptions
2. Compare task/process sections
3. Check for shared dependencies
4. Identify functional subset relationships

#### C. Argument Pattern Analysis

Commands that accept similar arguments might be mergeable:

```
Pattern: Commands operating on same entities
- /analyze-code [file]
- /review-code [file]
- /refactor-code [file]
  → Could be: /code [--analyze|--review|--refactor] [file]
```

### Phase 3: Naming Standards

**Objective:** Establish consistent naming conventions

#### Recommended Patterns

**Action-Object Pattern:** `/[verb]-[noun]`
```
Good Examples:
- /generate-tests
- /review-code
- /create-feature

Avoid:
- /tests-generate (object-action)
- /testing-gen (unclear abbreviation)
```

**Namespace Pattern:** `/[category]:[action]`
```
Good Examples:
- /git:feature
- /test:generate
- /pr:review

Benefits:
- Clear categorization
- Easy to discover related commands
- Scales well with many commands
```

**Flag Pattern:** `/[command] --[modifier]`
```
Good Examples:
- /test --generate
- /test --coverage
- /test --watch

Benefits:
- Single entry point
- Discoverable options
- Follows CLI conventions
```

#### Naming Anti-Patterns

**Avoid:**
- Abbreviations: `/gen-tests` → Use `/generate-tests`
- Redundancy: `/git-git-flow` → Use `/git-flow`
- Ambiguity: `/do-thing` → Be specific about what/how
- Inconsistent verbs: Mix of create/make/generate for same concept

### Phase 4: Consolidation Strategy

**Objective:** Reduce command count while improving usability

#### Consolidation Decision Matrix

| Scenario | Action | Example |
|----------|--------|---------|
| **Exact duplicates** | Delete one, redirect to other | `/pr-review` → `/review-pr` |
| **Functional subsets** | Merge into parent with flag | `/quick-test` → `/test --quick` |
| **Related actions** | Create command family | `/git-feature`, `/git-release` → `/git:feature`, `/git:release` |
| **Different workflows** | Keep separate, improve naming | `/analyze-security` ≠ `/analyze-performance` |

#### Consolidation Template

For each consolidation:

```markdown
### Consolidation: [Topic]

**Current State:**
- `/command-a` - [Description]
- `/command-b` - [Description]
- `/command-c` - [Description]

**Analysis:**
- Overlap: [What functionality is shared?]
- Differences: [What's unique to each?]
- Usage: [How often is each used?]

**Proposed Solution:**
Option 1: Flag-based consolidation
- `/base-command --flag-a`
- `/base-command --flag-b`
- `/base-command --flag-c`

Option 2: Namespace consolidation
- `/topic:action-a`
- `/topic:action-b`
- `/topic:action-c`

**Recommendation:** [Which option and why]

**Migration Plan:**
1. Create new unified command
2. Mark old commands as deprecated
3. Add deprecation warnings (6 months)
4. Update documentation
5. Remove deprecated commands

**Benefits:**
- Reduced cognitive load: [How?]
- Easier discovery: [How?]
- Better maintainability: [How?]
```

### Phase 5: Discovery Improvements

**Objective:** Make commands easier to find and use

#### Directory Structure Options

**Option A: Flat with Namespacing**
```
.claude/commands/
├── git-feature.md
├── git-release.md
├── git-hotfix.md
├── test-generate.md
├── test-coverage.md
└── review-pr.md
```

**Pros:**
- Simple file structure
- Easy to list all commands
- No directory navigation

**Cons:**
- Harder to browse by category
- Name collisions possible
- Cluttered with many commands

**Option B: Categorized Subdirectories**
```
.claude/commands/
├── git-flow/
│   ├── feature.md
│   ├── release.md
│   └── hotfix.md
├── testing/
│   ├── generate.md
│   └── coverage.md
└── review/
    └── pr.md
```

**Pros:**
- Clear categorization
- Easy to browse by topic
- Scales well

**Cons:**
- Deeper paths
- Need to remember categories
- Potential for miscategorization

**Option C: Hybrid Approach**
```
.claude/commands/
├── git-flow.md        (index/router command)
├── git/
│   ├── feature.md
│   ├── release.md
│   └── hotfix.md
└── test.md            (index/router command)
```

**Pros:**
- Top-level commands for common tasks
- Subcategories for specialized commands
- Best of both worlds

**Recommendation for Namer Project:**

Based on the project's characteristics:
- Medium-sized command set (estimated 15-30 commands)
- Mix of general and specialized commands
- Team familiarity with flat structures (Make targets, poe tasks)

**Recommended:** Option A (Flat with Namespacing)

**Rationale:**
- Consistent with existing patterns (Make, poe)
- Easy to grep/search
- Namespacing provides logical grouping
- Simpler mental model

### Phase 6: Implementation Plan

**Objective:** Execute optimizations systematically

#### Step-by-Step Process

**Week 1: Analysis & Planning**
1. Generate inventory with `analyze-commands.sh`
2. Categorize all commands
3. Identify top 5 consolidation opportunities
4. Document naming standards
5. Get user buy-in on approach

**Week 2: High-Priority Changes**
1. Rename most confusing commands
2. Consolidate obvious duplicates
3. Create command index/help system
4. Update documentation

**Week 3: Medium-Priority Changes**
1. Implement command families
2. Standardize naming across categories
3. Add deprecation warnings
4. Create migration guide

**Week 4: Polish & Validation**
1. Test all new commands
2. Update command descriptions
3. Create discovery tooling
4. Final documentation pass

#### Migration Best Practices

**For Renamed Commands:**
```markdown
# Old Command (Deprecated)

**DEPRECATED:** Use `/new-command` instead.

This command will be removed on [DATE].

See `/new-command` for the updated version.
```

**For Consolidated Commands:**
```markdown
# Old Command (Deprecated)

**DEPRECATED:** Use `/base-command --flag` instead.

This command has been consolidated into `/base-command`.

Migration:
- `/old-command arg` → `/base-command --flag arg`

This command will be removed on [DATE].
```

**For Deleted Commands:**
1. Mark as deprecated for 6 months minimum
2. Add clear migration path in command file
3. Update all documentation
4. Send notification if team-shared commands
5. Only delete after grace period

## Success Metrics

### Quantitative
- **Command count reduction:** Target 20-30% reduction
- **Average command name length:** Target < 20 characters
- **Commands per category:** Target 3-8 per category
- **Duplicate/overlap reduction:** Target 100% elimination

### Qualitative
- **Time to find command:** Should decrease
- **New user onboarding:** Easier to learn command set
- **Naming consistency:** No ambiguous or conflicting names
- **Maintenance burden:** Easier to add new commands

## Tools & Automation

### Command Discovery Helper

Create a helper command: `/commands` or `/help`

```markdown
# Command Discovery Helper

List and search available Claude Code commands.

## Usage

/commands [category]
/commands --search [keyword]
/commands --recent

## Examples

/commands git-flow
/commands --search test
/commands --recent
```

### Auto-Complete Hints

Add argument hints to command metadata:

```yaml
---
command: generate-tests
category: testing
args: file-path
description: Generate comprehensive test suite for file
---
```

## Appendix: Example Optimizations

### Example 1: Test Commands

**Before:**
- `/generate-tests` - Generate test files
- `/write-tests` - Write test cases
- `/test-coverage` - Analyze coverage
- `/run-tests` - Execute tests
- `/test-file` - Test specific file

**After:**
- `/test --generate [file]` - Generate tests
- `/test --coverage` - Analyze coverage
- `/test [file]` - Run tests
- `/test --watch [file]` - Watch mode

**Benefits:**
- 5 commands → 1 base command with flags
- Clearer mental model: "test" is the namespace
- Easier to discover related functionality

### Example 2: Git Flow Commands

**Before:**
- `/start-feature` - Start feature branch
- `/finish-feature` - Finish feature
- `/create-release` - Create release
- `/start-hotfix` - Start hotfix
- `/git-status` - Check git status

**After:**
- `/git:feature [action]` - Feature workflow
- `/git:release [action]` - Release workflow
- `/git:hotfix [action]` - Hotfix workflow
- `/git:status` - Repository status

**Benefits:**
- Clear namespace for git operations
- Consistent naming pattern
- Room for expansion

### Example 3: Review Commands

**Before:**
- `/pr-review` - Review pull request
- `/code-review` - Review code changes
- `/review-pr` - Review PR (duplicate?)
- `/gemini-review` - AI review

**After:**
- `/review:pr [number]` - Review pull request
- `/review:code [file]` - Review code file
- `/review:ai [pr]` - AI-assisted review

**Benefits:**
- Eliminated duplicate
- Clear review namespace
- Obvious AI vs manual distinction
