# Claude Code Command Audit

This directory contains tools and documentation for auditing and optimizing Claude Code slash commands.

## Quick Start

### 1. Generate Command Inventory

```bash
# Make script executable
chmod +x .claude-audit/analyze-commands.sh

# Run analysis
./.claude-audit/analyze-commands.sh
```

This will:
- Scan `~/.claude/commands/` directory
- Generate command inventory with metadata
- Create categorization template
- Identify potential overlaps

### 2. Review Output

```bash
# View inventory
cat .claude-audit/COMMAND_INVENTORY.md

# Open in editor for categorization
code .claude-audit/COMMAND_INVENTORY.md  # VS Code
vim .claude-audit/COMMAND_INVENTORY.md   # Vim
```

### 3. Categorize Commands

Manually review each command and assign appropriate category:

- **git-flow** - Git Flow workflow commands
- **testing** - Test generation, execution, coverage
- **ci-cd** - Build, deployment, automation
- **code-quality** - Code review, refactoring, analysis
- **project-mgmt** - Planning, tracking, coordination
- **documentation** - PRD, JTBD, API docs
- **dev-tools** - Debugging, profiling, optimization
- **ai-review** - AI-assisted review integration
- **infrastructure** - Docker, deployment, environment
- **other** - Miscellaneous utilities

### 4. Identify Overlaps

Look for:
- Commands with similar names but different purposes
- Commands with similar purposes but different names
- Commands that could be merged with flags
- Duplicate or redundant commands

### 5. Generate Optimization Proposal

Based on findings, document recommendations:

```bash
# Copy template
cp .claude-audit/OPTIMIZATION_FRAMEWORK.md .claude-audit/COMMAND_OPTIMIZATION_PROPOSAL.md

# Edit with specific recommendations
code .claude-audit/COMMAND_OPTIMIZATION_PROPOSAL.md
```

## Files in This Directory

### Generated Files (by script)

- **COMMAND_INVENTORY.md** - Complete command list with metadata
- **COMMAND_CATEGORIES.json** - Machine-readable categorization

### Templates & Guides

- **README.md** - This file
- **OPTIMIZATION_FRAMEWORK.md** - Comprehensive optimization methodology
- **analyze-commands.sh** - Inventory generation script

## Common Patterns to Look For

### Naming Inconsistencies

```
Problem: Inconsistent verbs for similar actions
- /create-feature
- /generate-tests
- /make-release

Solution: Standardize on one verb
- /create-feature
- /create-tests
- /create-release
```

### Functional Overlaps

```
Problem: Multiple commands for same task
- /generate-tests
- /write-tests
- /create-test-suite

Solution: Consolidate with flags
- /test --generate [file]
```

### Category Sprawl

```
Problem: Unclear command organization
- /git-feature
- /feature-start
- /start-feature

Solution: Use namespace pattern
- /git:feature start
- /git:feature finish
```

## Optimization Goals

1. **Reduce Duplication** - Eliminate redundant commands
2. **Improve Discoverability** - Easier to find the right command
3. **Standardize Naming** - Consistent patterns and conventions
4. **Enhance Usability** - Clear, intuitive command structure
5. **Maintain Compatibility** - Graceful migration path

## Best Practices

### Before Consolidating

- Document current usage patterns
- Understand why duplicates exist
- Check for subtle functional differences
- Plan migration for users

### When Renaming

- Keep old command as deprecated alias (6 months)
- Add clear deprecation warnings
- Update all documentation
- Test thoroughly

### For New Commands

- Follow established naming conventions
- Check for existing similar commands
- Document purpose and arguments
- Assign to appropriate category

## Next Steps After Audit

1. **Share findings** - Review with team/stakeholders
2. **Prioritize changes** - Focus on high-impact optimizations
3. **Create migration plan** - Define timeline and steps
4. **Implement incrementally** - Don't change everything at once
5. **Monitor usage** - Track which commands are actually used
6. **Iterate** - Continuously improve based on feedback

## Support & Questions

For questions about:
- **Command structure** - See OPTIMIZATION_FRAMEWORK.md
- **Analysis methodology** - See Phase 1 in framework
- **Consolidation strategies** - See Phase 4 in framework
- **Naming standards** - See Phase 3 in framework

## Integration with Namer Project

This audit aligns with project practices documented in:
- **CLAUDE.md** - Development guidelines and patterns
- **Makefile** - Command-line interface patterns
- **pyproject.toml** - Tool configuration and standards

**Key Principle:** Commands should be as discoverable and consistent as Make targets and poe tasks.
