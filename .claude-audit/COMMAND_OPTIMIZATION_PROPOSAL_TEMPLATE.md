# Command Optimization Proposal

**Date:** [DATE]
**Auditor:** [NAME]
**Total Commands Analyzed:** [NUMBER]

## Executive Summary

**Current State:**
- Total commands: [NUMBER]
- Identified duplicates: [NUMBER]
- Naming inconsistencies: [NUMBER]
- Consolidation opportunities: [NUMBER]

**Proposed State:**
- Optimized command count: [NUMBER] ([X]% reduction)
- Standardized naming: [YES/NO]
- Clear categorization: [NUMBER] categories
- Migration timeline: [X] weeks

**Expected Benefits:**
- [BENEFIT 1]
- [BENEFIT 2]
- [BENEFIT 3]

## Detailed Findings

### Command Categories

| Category | Current Count | Proposed Count | Change |
|----------|--------------|----------------|--------|
| git-flow | [#] | [#] | [+/-#] |
| testing | [#] | [#] | [+/-#] |
| ci-cd | [#] | [#] | [+/-#] |
| code-quality | [#] | [#] | [+/-#] |
| project-mgmt | [#] | [#] | [+/-#] |
| documentation | [#] | [#] | [+/-#] |
| dev-tools | [#] | [#] | [+/-#] |
| ai-review | [#] | [#] | [+/-#] |
| infrastructure | [#] | [#] | [+/-#] |
| other | [#] | [#] | [+/-#] |
| **Total** | **[#]** | **[#]** | **[+/-#]** |

### Identified Overlaps

#### High Priority (Must Fix)

**1. [Overlap Name]**
- Commands: `/cmd-a`, `/cmd-b`, `/cmd-c`
- Issue: [Description of overlap/duplication]
- Impact: [How it affects usability]
- Recommendation: [Specific solution]

**2. [Overlap Name]**
- Commands: `/cmd-a`, `/cmd-b`
- Issue: [Description]
- Impact: [Impact]
- Recommendation: [Solution]

#### Medium Priority (Should Fix)

**1. [Overlap Name]**
- Commands: [List]
- Issue: [Description]
- Impact: [Impact]
- Recommendation: [Solution]

#### Low Priority (Nice to Have)

**1. [Overlap Name]**
- Commands: [List]
- Issue: [Description]
- Impact: [Impact]
- Recommendation: [Solution]

### Naming Issues

#### Inconsistent Verbs

| Current Commands | Issue | Proposed Standard |
|-----------------|-------|-------------------|
| /create-*, /generate-*, /make-* | Mixed verbs for creation | Use /create-* or /generate-* |
| [List] | [Issue] | [Standard] |

#### Ambiguous Names

| Command | Issue | Proposed Rename |
|---------|-------|-----------------|
| /thing | Too vague | /specific-thing |
| [Command] | [Issue] | [Rename] |

#### Abbreviations

| Command | Issue | Proposed Full Name |
|---------|-------|-------------------|
| /gen-tests | Unclear abbreviation | /generate-tests |
| [Command] | [Issue] | [Full name] |

## Specific Recommendations

### Recommendation 1: [Title]

**Category:** [git-flow/testing/etc]
**Priority:** [High/Medium/Low]

**Current State:**
```
/command-a - [Description]
/command-b - [Description]
/command-c - [Description]
```

**Problem:**
- [Issue 1]
- [Issue 2]
- [Issue 3]

**Proposed Solution:**

**Option A: Flag-Based Consolidation**
```
/base-command --flag-a [args]
/base-command --flag-b [args]
/base-command --flag-c [args]
```

**Option B: Namespace Consolidation**
```
/category:action-a [args]
/category:action-b [args]
/category:action-c [args]
```

**Recommended Option:** [A/B] because [rationale]

**Migration Plan:**
1. Create new unified command
2. Mark old commands as deprecated (add warnings)
3. Update documentation
4. Grace period: 6 months
5. Remove deprecated commands

**Benefits:**
- [Benefit 1]
- [Benefit 2]
- [Benefit 3]

**Risks:**
- [Risk 1 and mitigation]
- [Risk 2 and mitigation]

---

### Recommendation 2: [Title]

**Category:** [Category]
**Priority:** [Priority]

[Follow same structure as Recommendation 1]

---

### Recommendation 3: [Title]

**Category:** [Category]
**Priority:** [Priority]

[Follow same structure as Recommendation 1]

## Naming Standards

### Adopted Conventions

**Primary Pattern:** [action-object / namespace:action / other]

**Rationale:** [Why this pattern works for Namer project]

### Naming Rules

1. **Use clear, descriptive verbs**
   - Preferred: create, generate, analyze, review
   - Avoid: make, do, run (too generic)

2. **Be specific with nouns**
   - Good: /generate-tests, /review-pr
   - Bad: /gen-thing, /check-stuff

3. **Avoid abbreviations**
   - Good: /generate-tests
   - Bad: /gen-tests, /gentests

4. **Use kebab-case**
   - Good: /create-feature-branch
   - Bad: /createFeatureBranch, /create_feature_branch

5. **Category prefixes (if using namespaces)**
   - Git: /git:*
   - Test: /test:*
   - Review: /review:*

### Examples

| Category | Good | Bad | Why |
|----------|------|-----|-----|
| git-flow | /git:feature start | /start-feat | Clear namespace, full words |
| testing | /test --generate | /gen-tests | Standard flag pattern |
| review | /review:pr [num] | /pr-rev | Clear namespace, full words |

## Directory Structure

### Current Structure
```
.claude/commands/
├── [command-a].md
├── [command-b].md
└── [etc]
```

### Proposed Structure

**Recommendation:** [Flat / Subdirectories / Hybrid]

**Structure:**
```
.claude/commands/
├── [structure details]
└── [etc]
```

**Rationale:** [Why this structure works for the project]

## Discovery Improvements

### Command Index

**Create:** `/commands` or `/help` command

**Purpose:** Make all commands discoverable

**Features:**
- List all commands by category
- Search by keyword
- Show recently used
- Display command descriptions

### Auto-Complete

**Enhance command metadata:**
```yaml
---
command: generate-tests
category: testing
args: <file-path>
description: Generate comprehensive test suite for Python file
examples:
  - /generate-tests namer/config.py
  - /generate-tests test/integration/
---
```

### Documentation

**Update:**
- Add command reference section to CLAUDE.md
- Create quick reference card
- Document naming conventions
- Provide migration guide

## Implementation Plan

### Phase 1: High Priority (Week 1-2)

**Tasks:**
1. [ ] Rename most confusing commands
2. [ ] Consolidate obvious duplicates
3. [ ] Fix critical naming issues
4. [ ] Add deprecation warnings

**Success Criteria:**
- No duplicate functionality
- Clear command names
- Deprecated commands marked

### Phase 2: Medium Priority (Week 3-4)

**Tasks:**
1. [ ] Implement command families
2. [ ] Standardize naming across categories
3. [ ] Create command index
4. [ ] Update documentation

**Success Criteria:**
- Consistent naming patterns
- Commands organized by category
- Discovery improvements in place

### Phase 3: Low Priority (Week 5-6)

**Tasks:**
1. [ ] Polish remaining issues
2. [ ] Create migration guide
3. [ ] Final documentation pass
4. [ ] User testing and feedback

**Success Criteria:**
- All recommendations implemented
- Complete documentation
- Positive user feedback

### Phase 4: Cleanup (Week 7-8)

**Tasks:**
1. [ ] Monitor usage of new commands
2. [ ] Gather feedback
3. [ ] Make adjustments as needed
4. [ ] Remove deprecated commands (after grace period)

**Success Criteria:**
- Smooth transition completed
- No confusion reported
- Improved productivity

## Migration Guide

### For Users

**What's Changing:**
- [Summary of major changes]

**Action Required:**
1. Review new command names in [DOCUMENT]
2. Update any saved workflows or scripts
3. Use new commands going forward

**Backwards Compatibility:**
- Old commands will work until [DATE]
- Deprecation warnings will guide you to new commands
- No functionality is being removed

### Command Mapping

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| /old-cmd | /new-cmd | [Migration notes] |
| /deprecated | /replacement --flag | [Notes] |

## Success Metrics

### Quantitative Goals

- [ ] Reduce command count by [X]%
- [ ] 100% of commands properly categorized
- [ ] 0 duplicate functionality
- [ ] Average command name length < 20 characters
- [ ] All commands follow naming standard

### Qualitative Goals

- [ ] Easier to find the right command first time
- [ ] Reduced confusion about which command to use
- [ ] Clearer command organization
- [ ] Improved new user onboarding
- [ ] Better alignment with project patterns (Make, poe)

### Measurement

**Track:**
- Time to complete common tasks
- Number of "wrong command" attempts
- User feedback/satisfaction
- Command usage patterns

**Review:**
- 2 weeks after Phase 1
- 1 month after full implementation
- 3 months for long-term assessment

## Risks & Mitigation

### Risk 1: User Confusion During Migration

**Mitigation:**
- Clear deprecation warnings
- Comprehensive documentation
- Gradual transition (6 month grace period)
- Migration guide with examples

### Risk 2: Breaking Existing Workflows

**Mitigation:**
- Keep old commands as aliases
- Provide mapping documentation
- Test thoroughly before removing
- Communicate changes clearly

### Risk 3: Over-Consolidation

**Mitigation:**
- Preserve distinct workflows as separate commands
- Use flags only for truly related actions
- Get user feedback before implementing
- Be willing to keep some "duplicates" if they serve different needs

## Appendix

### A. Complete Command Inventory

[Link to COMMAND_INVENTORY.md]

### B. Category Definitions

[Link to detailed category descriptions]

### C. Naming Convention Reference

[Link to naming standards document]

### D. Migration Scripts

[Any automation tools created]

---

**Approval:**

- [ ] Reviewed by: [NAME]
- [ ] Approved by: [NAME]
- [ ] Implementation start date: [DATE]
- [ ] Target completion date: [DATE]
