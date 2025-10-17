# Claude Code Command Audit - File Index

Quick reference for all files in this directory.

## Start Here

🚀 **[GETTING_STARTED.md](GETTING_STARTED.md)** - Step-by-step guide to running the audit

📊 **[ANALYSIS_SUMMARY.md](ANALYSIS_SUMMARY.md)** - Overview of what's been created and why

## Tools (Executable Scripts)

🔧 **[quick-check.sh](quick-check.sh)** - Fast overview of command landscape (~30 seconds)
```bash
chmod +x .claude-audit/quick-check.sh
./.claude-audit/quick-check.sh
```

🔧 **[analyze-commands.sh](analyze-commands.sh)** - Generate full inventory (~1 minute)
```bash
chmod +x .claude-audit/analyze-commands.sh
./.claude-audit/analyze-commands.sh
```

## Reference Documentation

📖 **[README.md](README.md)** - Quick reference and overview

📖 **[OPTIMIZATION_FRAMEWORK.md](OPTIMIZATION_FRAMEWORK.md)** - Comprehensive methodology
- Phase 1: Inventory & Categorization
- Phase 2: Overlap Detection
- Phase 3: Naming Standards
- Phase 4: Consolidation Strategy
- Phase 5: Discovery Improvements
- Phase 6: Implementation Plan

## Templates

📝 **[COMMAND_OPTIMIZATION_PROPOSAL_TEMPLATE.md](COMMAND_OPTIMIZATION_PROPOSAL_TEMPLATE.md)**
- Copy and fill in with your findings
- Complete proposal structure
- Implementation plan included

📝 **[COMMAND_INVENTORY_TEMPLATE.md](COMMAND_INVENTORY_TEMPLATE.md)**
- Manual inventory template
- Use if scripts don't work
- Categorization guidelines

## Generated Files (Created by Scripts)

🔄 **COMMAND_INVENTORY.md** (created by analyze-commands.sh)
- Complete command list with metadata
- Ready for categorization
- Overlap detection checklist

🔄 **COMMAND_CATEGORIES.json** (created by analyze-commands.sh)
- Machine-readable categorization
- Template structure
- For tooling/automation

## Configuration

⚙️ **[.gitignore](.gitignore)** - Prevents committing generated files

## Workflow

### Quick Audit (10 minutes)

```bash
1. Read: GETTING_STARTED.md (2 min)
2. Run: quick-check.sh (30 sec)
3. Review: Quick check output (5 min)
4. Run: analyze-commands.sh (1 min)
5. Scan: COMMAND_INVENTORY.md (2 min)
```

### Full Audit (3-5 hours)

```bash
1. Read: GETTING_STARTED.md (10 min)
2. Run: analyze-commands.sh (1 min)
3. Review: COMMAND_INVENTORY.md (10 min)
4. Categorize: Each command (30 min)
5. Identify: Overlaps and duplicates (30 min)
6. Read: OPTIMIZATION_FRAMEWORK.md (30 min)
7. Create: COMMAND_OPTIMIZATION_PROPOSAL.md (2 hours)
8. Review: Proposal and refine (30 min)
```

### Implementation (4-6 weeks)

```bash
Week 1-2: High-priority changes
Week 3-4: Medium-priority changes
Week 5-6: Polish and validation
After 6 months: Remove deprecated commands
```

## File Purposes

| File | Purpose | When to Use |
|------|---------|-------------|
| GETTING_STARTED.md | Learn how to audit | First time through |
| ANALYSIS_SUMMARY.md | Understand framework | Overview and context |
| README.md | Quick reference | When you need a reminder |
| OPTIMIZATION_FRAMEWORK.md | Deep dive methodology | Planning and decision-making |
| quick-check.sh | Fast overview | Initial assessment |
| analyze-commands.sh | Generate inventory | Start of audit process |
| COMMAND_OPTIMIZATION_PROPOSAL_TEMPLATE.md | Document findings | Creating proposal |
| COMMAND_INVENTORY_TEMPLATE.md | Manual tracking | If scripts fail |

## Reading Order

**For Beginners:**
1. GETTING_STARTED.md
2. Run quick-check.sh
3. Run analyze-commands.sh
4. OPTIMIZATION_FRAMEWORK.md
5. Create proposal from template

**For Quick Reference:**
1. ANALYSIS_SUMMARY.md
2. README.md
3. Run scripts
4. Reference framework as needed

**For Deep Understanding:**
1. OPTIMIZATION_FRAMEWORK.md (all phases)
2. ANALYSIS_SUMMARY.md
3. GETTING_STARTED.md
4. Experiment with scripts

## Key Concepts

### Categories
- git-flow, testing, ci-cd, code-quality, project-mgmt
- documentation, dev-tools, ai-review, infrastructure, other

### Naming Patterns
- **action-object:** `/generate-tests`
- **namespace:action:** `/git:feature`
- **command --flag:** `/test --generate`

### Consolidation Types
- Exact duplicates → Delete one
- Functional subsets → Merge with flags
- Related actions → Create command family
- Different workflows → Keep separate, improve naming

## Success Criteria

✅ Reduced command count (20-30%)
✅ Zero duplicates
✅ Consistent naming
✅ Clear categorization
✅ Faster discovery
✅ Better maintainability

## Common Questions

**Q: Where are my commands stored?**
A: `~/.claude/commands/` (gitignored, not in repo)

**Q: Which file do I start with?**
A: GETTING_STARTED.md

**Q: How long will this take?**
A: 3-5 hours for complete audit, 4-6 weeks for implementation

**Q: Can I skip the analysis?**
A: Not recommended - flying blind leads to suboptimal organization

**Q: What if I make a mistake?**
A: Keep old commands as deprecated aliases for 6 months - safe migration

## Quick Commands

```bash
# Make scripts executable
chmod +x .claude-audit/*.sh

# Quick check
./.claude-audit/quick-check.sh

# Full analysis
./.claude-audit/analyze-commands.sh

# View inventory
cat .claude-audit/COMMAND_INVENTORY.md

# Start proposal
cp .claude-audit/COMMAND_OPTIMIZATION_PROPOSAL_TEMPLATE.md \
   .claude-audit/COMMAND_OPTIMIZATION_PROPOSAL.md

# Edit proposal
code .claude-audit/COMMAND_OPTIMIZATION_PROPOSAL.md
```

## Support

Stuck? Check these in order:
1. GETTING_STARTED.md - Detailed instructions
2. OPTIMIZATION_FRAMEWORK.md - Methodology details
3. ANALYSIS_SUMMARY.md - Context and rationale
4. README.md - Quick tips

## Version

**Created:** 2025-10-14
**Framework Version:** 1.0.0
**Project:** Namer
**Purpose:** Command audit and optimization

---

**Next Step:** Read [GETTING_STARTED.md](GETTING_STARTED.md) and run [quick-check.sh](quick-check.sh)
