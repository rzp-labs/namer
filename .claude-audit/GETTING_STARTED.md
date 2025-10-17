# Getting Started with Command Audit

This guide will walk you through auditing and optimizing your Claude Code slash commands.

## Prerequisites

- Claude Code with slash commands configured in `~/.claude/commands/`
- Bash shell (macOS/Linux)
- Basic command-line familiarity

## Step-by-Step Guide

### Step 1: Quick Overview

Get a quick snapshot of your command landscape:

```bash
# Make scripts executable
chmod +x .claude-audit/*.sh

# Run quick check
./.claude-audit/quick-check.sh
```

**What you'll see:**
- Total command count
- Commands grouped by common prefixes
- Potential overlaps based on shared words
- Commands grouped by first word

**Time:** ~30 seconds

### Step 2: Full Analysis

Generate complete inventory with metadata:

```bash
# Run full analysis
./.claude-audit/analyze-commands.sh
```

**This creates:**
- `COMMAND_INVENTORY.md` - Complete command list with metadata
- `COMMAND_CATEGORIES.json` - Categorization template

**Time:** ~1 minute

### Step 3: Review Inventory

Open the generated inventory:

```bash
# View in terminal
cat .claude-audit/COMMAND_INVENTORY.md

# Or open in your editor
code .claude-audit/COMMAND_INVENTORY.md  # VS Code
vim .claude-audit/COMMAND_INVENTORY.md   # Vim
subl .claude-audit/COMMAND_INVENTORY.md  # Sublime
```

**What to look for:**
- Total number of commands
- Commands without clear purpose
- Similar-sounding commands
- Very long or very short command names

**Time:** ~10 minutes

### Step 4: Categorize Commands

Manually assign each command to a category:

**Categories:**
1. **git-flow** - Git workflow (feature, release, hotfix)
2. **testing** - Test generation, execution, coverage
3. **ci-cd** - Build, deployment, automation
4. **code-quality** - Review, refactoring, analysis
5. **project-mgmt** - Planning, tracking, standup
6. **documentation** - PRD, JTBD, docs
7. **dev-tools** - Debugging, profiling
8. **ai-review** - AI-assisted review
9. **infrastructure** - Docker, deployment
10. **other** - Miscellaneous

**How to categorize:**
1. Read command description
2. Understand primary purpose
3. Assign to most relevant category
4. Update the category column in inventory

**Example:**
```markdown
| /generate-tests | Generate test suite | Yes | 150 | testing |
| /git-feature | Start feature branch | Yes | 120 | git-flow |
| /review-pr | Review pull request | Yes | 200 | code-quality |
```

**Time:** ~20-30 minutes

### Step 5: Identify Overlaps

Look for these patterns:

#### A. Exact Duplicates
Commands that do the same thing with different names:
```
/pr-review
/review-pr
→ Keep one, deprecate the other
```

#### B. Functional Subsets
One command is a subset of another:
```
/test
/test-quick
→ Consolidate: /test --quick
```

#### C. Similar Functionality
Commands that overlap but aren't identical:
```
/generate-tests
/write-tests
/create-test-suite
→ Consolidate or differentiate clearly
```

#### D. Naming Inconsistencies
Same concept, different verbs:
```
/create-feature
/generate-tests
/make-release
→ Standardize on create or generate
```

**Mark overlaps in your inventory:**
```markdown
## Overlaps Detected

1. **Test Commands** (3 commands)
   - /generate-tests
   - /write-tests
   - /test-create
   → Recommend: Consolidate to /test --generate

2. **PR Review** (2 commands)
   - /pr-review
   - /review-pr
   → Recommend: Keep /review-pr, deprecate /pr-review
```

**Time:** ~30 minutes

### Step 6: Create Optimization Proposal

Use the template to document recommendations:

```bash
# Copy template
cp .claude-audit/COMMAND_OPTIMIZATION_PROPOSAL_TEMPLATE.md \
   .claude-audit/COMMAND_OPTIMIZATION_PROPOSAL.md

# Edit with your findings
code .claude-audit/COMMAND_OPTIMIZATION_PROPOSAL.md
```

**Fill in:**
1. **Executive Summary** - High-level overview
2. **Detailed Findings** - Category breakdown, overlaps
3. **Specific Recommendations** - One section per consolidation/rename
4. **Naming Standards** - Conventions you'll adopt
5. **Implementation Plan** - Timeline and phases

**Time:** ~1-2 hours

### Step 7: Review & Refine

Before implementing:

1. **Self-review** - Read proposal end-to-end
2. **Check assumptions** - Verify you understand each command
3. **Test examples** - Try proposed new commands mentally
4. **Consider impact** - How will changes affect workflows?

**Questions to ask:**
- Does this actually improve discoverability?
- Are the new names clearer than the old?
- Is the migration path obvious?
- Have I documented all edge cases?

**Time:** ~30 minutes

### Step 8: Implement Changes

Follow your implementation plan:

**Phase 1: High Priority (Week 1-2)**
```bash
# Example: Rename confusing command
mv ~/.claude/commands/old-name.md ~/.claude/commands/new-name.md

# Add deprecation notice to old location
cat > ~/.claude/commands/old-name.md << 'EOF'
# Old Command Name (DEPRECATED)

**This command has been renamed to `/new-name`**

Please use `/new-name` instead. This command will be removed on [DATE].

[Same content as new command]
EOF
```

**Phase 2: Consolidation (Week 3-4)**
```bash
# Example: Consolidate multiple commands
# 1. Create unified command with flag support
# 2. Add deprecation notices to old commands
# 3. Update documentation
```

**Phase 3: Cleanup (After grace period)**
```bash
# Remove deprecated commands (after 6 months)
rm ~/.claude/commands/deprecated-command.md
```

## Common Questions

### Q: How many commands is too many?

**A:** Guidelines:
- **< 15 commands:** Probably fine, focus on naming consistency
- **15-30 commands:** Good candidate for organization improvements
- **30-50 commands:** Definitely needs categorization and consolidation
- **> 50 commands:** High priority for major restructuring

### Q: Should I use subdirectories or flat structure?

**A:** For Namer project, **recommend flat structure** because:
- Consistent with Make targets and poe tasks
- Easier to grep/search
- Simple mental model
- Naming prefixes provide grouping (git-*, test-*)

### Q: What if I'm not sure about a consolidation?

**A:** When in doubt:
1. Keep commands separate initially
2. Mark as "potential consolidation" in notes
3. Use both for a while
4. Track which one you actually use
5. Decide after 2-4 weeks of real usage

### Q: How long should the migration period be?

**A:** Recommended timeline:
- **Minor renames:** 1 month grace period
- **Major consolidations:** 3-6 months grace period
- **Breaking changes:** 6 months minimum

### Q: What if users resist changes?

**A:** Best practices:
1. Clearly communicate benefits
2. Provide detailed migration guide
3. Keep old commands as aliases longer
4. Get feedback early in process
5. Be willing to adjust based on real usage

## Tips & Tricks

### Finding Similar Commands Quickly

```bash
# List all commands
ls -1 ~/.claude/commands/*.md | xargs -n1 basename | sed 's/.md$//'

# Find commands with specific prefix
ls -1 ~/.claude/commands/test-*.md

# Search command content
grep -r "specific term" ~/.claude/commands/
```

### Testing New Command Names

Before implementing, mentally test with real scenarios:

```
Scenario: "I want to generate tests for a Python file"
Old: Which command? /generate-tests or /write-tests or /test-create?
New: Obviously /test --generate [file]
✓ Clear improvement
```

### Measuring Success

Track these metrics:
1. **Time to find command** - Faster = better
2. **Wrong command attempts** - Fewer = better
3. **Questions about which command** - Fewer = better
4. **New user onboarding time** - Faster = better

### Avoiding Over-Optimization

Don't consolidate if:
- Commands serve genuinely different workflows
- Users have strong muscle memory
- Consolidation makes commands more complex
- Risk outweighs benefit

**Example of good separation:**
```
/test --unit      # Unit tests
/test --integration  # Integration tests
→ Keep separate if they have different:
  - Setup requirements
  - Argument patterns
  - Output formats
  - Use cases
```

## Recommended Reading Order

1. **This file (GETTING_STARTED.md)** - You are here
2. **README.md** - Overview and quick reference
3. **OPTIMIZATION_FRAMEWORK.md** - Deep dive into methodology
4. **Your generated COMMAND_INVENTORY.md** - Your actual data
5. **COMMAND_OPTIMIZATION_PROPOSAL_TEMPLATE.md** - For creating proposal

## Next Steps

Ready to begin? Here's your checklist:

- [ ] Run quick-check.sh for overview
- [ ] Run analyze-commands.sh for full inventory
- [ ] Review generated COMMAND_INVENTORY.md
- [ ] Categorize each command
- [ ] Identify overlaps and duplicates
- [ ] Create COMMAND_OPTIMIZATION_PROPOSAL.md
- [ ] Review and refine proposal
- [ ] Implement changes in phases
- [ ] Monitor results and adjust

**Estimated total time:** 3-5 hours for initial audit and proposal

**Good luck!** 🚀
