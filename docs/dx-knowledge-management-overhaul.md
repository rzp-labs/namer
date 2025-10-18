# DX Optimization: Agent Knowledge Management System Overhaul

**Date**: 2025-10-18
**Status**: Planning Phase
**Feature Branch**: `feature/dx-replace-memory-storage-with-supermemory`

---

## Executive Summary

The current knowledge management system is **failing on all three critical dimensions**: (1) agents ignore `.agent/memory.json` because it's not in their prompt context and has no query mechanism, (2) CLAUDE.md has bloated to 5000+ lines causing warnings and unsustainable growth, and (3) capturing learnings post-PR requires another commit→PR→merge cycle, creating friction that discourages documentation. This plan proposes a **three-tiered knowledge architecture**: (Tier 1) trimmed CLAUDE.md (~1500 lines) with core rules and current project state, (Tier 2) Supermemory MCP for semantic search of historical patterns, and (Tier 3) memory.json as export/backup. The solution includes **automated session-start querying** of Supermemory for relevant context, **inline capture** during sessions without blocking PRs, and a **validation framework** to measure agent knowledge utilization and prevent repeated mistakes.

---

## Root Cause Analysis

### Problem 1: Agents Don't Reference memory.json

**Evidence from investigation:**
- Memory.json contains 28 lessons with rich patterns, anti-patterns, code examples, and historical context
- File is well-structured with categories, tags, and searchable metadata
- **But:** File is NOT loaded into agent session context (only CLAUDE.md is)
- **Result:** Agents have no awareness memory.json exists

**Root causes:**
1. **No retrieval mechanism** - No tooling to query memory.json when agent needs context
2. **Not in prompt** - System prompt loads CLAUDE.md via `claudeMd` context, but NOT memory.json
3. **Format mismatch** - Agents expect natural language guidance (CLAUDE.md style), not structured JSON
4. **Duplication** - Lessons ARE in CLAUDE.md (sections 19-28), so agents technically have access... but buried in 5000 lines

**Why this is critical:**
- Agents repeat mistakes documented 6 months ago (e.g., cherry-picking without investigation - lesson 19)
- No ability to search "have we solved this before?"
- Knowledge exists but is functionally invisible

### Problem 2: CLAUDE.md Size Bloat

**Current state:**
- CLAUDE.md: 5000+ lines
- Triggering system warnings about context size
- Contains: Project overview, commands, tech stack, Git Flow, shell patterns, lessons learned (duplicated from memory.json)

**Growth pattern:**
- `/session-learning-capture` appends new lessons to CLAUDE.md
- Each lesson adds 50-150 lines
- Historical context never removed (permanent accumulation)
- Sections duplicated between "Lessons Learned" and narrative documentation

**Why unsustainable:**
- Token limits approaching (5000 lines ≈ 15-20k tokens)
- Slower session init (large file parsing)
- Harder to maintain (find relevant sections)
- Warning messages every session

### Problem 3: Post-PR Capture Friction

**Current workflow:**
```
1. Work on feature → create PR → address reviews
2. Agent uses /finish to merge PR
3. **Context lost** - agent session ends or moves on
4. User manually runs /session-learning-capture
5. Writes to CLAUDE.md and memory.json
6. **Now need ANOTHER commit** → push → PR → merge cycle
7. Requires separate PR just to persist learnings
```

**Why this is broken:**
- **Blocking** - Learning capture becomes blocking work
- **Discourages documentation** - "Do I really want to create another PR?"
- **Context loss** - User must manually trigger, often forgotten
- **Workflow disruption** - Breaks flow state, requires separate PR review

**Ideal workflow:**
- Agent captures learnings during session (inline)
- Writes to non-blocking storage (Supermemory, not git)
- No additional PR required
- User can optionally export to git later

---

## Proposed Architecture

### Tier 1: Core, Always-Loaded Knowledge (CLAUDE.md - Trimmed to ~1500 lines)

**What stays:**
- Project overview (technology stack, structure)
- Development commands (Make, Poetry, testing)
- **Critical "rules of engagement"** (what agents MUST NOT do)
  - Git Flow discipline (never push to develop directly)
  - Hook bypass policy (NEVER --no-verify except meta-changes)
  - PR size guidelines (200-500 lines)
  - Version bump criteria (PATCH vs MINOR vs MAJOR)
- **Current project state** (active workflows, recent changes)
- **High-level pattern summaries** (links to Supermemory for details)

**What moves OUT:**
- Detailed lesson narratives (move to Supermemory)
- Historical debugging journeys (move to Supermemory)
- Code examples (move to Supermemory, keep only critical ones)
- Session summaries (move to Supermemory)
- Duplicate content from memory.json

**Target size:** ~1500 lines (~5k tokens, safe margin)

### Tier 2: Searchable Historical Context (Supermemory MCP)

**What goes here:**
- All 28 existing lessons from memory.json
- Future session learnings captured inline
- Debugging journeys with resolution paths
- Code examples with explanations
- Anti-patterns with "why not to do this"
- PR-specific context (metrics, decisions, ROI)

**Tagging schema:**
```json
{
  "category": "pr-workflow | git-hooks | shell-scripting | ci-cd | code-review",
  "tags": ["atomic-pr", "cherry-pick", "file-type-filtering", "performance"],
  "lesson_number": 19,
  "date": "2025-10-14",
  "severity": "critical | high | medium | low",
  "pattern_type": "best-practice | anti-pattern | gotcha | optimization"
}
```

**Search query patterns:**
```bash
# Agent queries Supermemory at session start based on task
Task: "Create PR" → Query: "category:pr-workflow AND (atomic OR splitting)"
Task: "Fix git hooks" → Query: "category:git-hooks AND (file-type-filtering OR performance)"
Task: "Branch cleanup" → Query: "branch-cleanup OR obsolescence"
```

### Tier 3: Archive/Export (memory.json)

**Purpose:**
- Backup/export format for Supermemory data
- Version-controlled historical record
- Searchable via jq for manual queries
- **Not actively used by agents** (Supermemory is source of truth)

**Maintenance:**
- Export from Supermemory monthly
- Commit to git for version control
- Provides audit trail and disaster recovery

---

## Workflow Redesign

### Pre-Session: Context Query (NEW)

**When:** Agent session starts
**How:** Automatic Supermemory query based on task/context

```python
# Agent initialization flow
def session_init(task_description):
    # 1. Load CLAUDE.md (core knowledge)
    core_knowledge = load_claude_md()

    # 2. Query Supermemory for relevant context
    relevant_lessons = query_supermemory(
        query=extract_keywords(task_description),
        filters={"category": detect_category(task_description)},
        limit=5
    )

    # 3. Inject into prompt context
    prompt = f"""
    {core_knowledge}

    ## Relevant Historical Context
    {format_lessons(relevant_lessons)}

    ## Current Task
    {task_description}
    """

    return prompt
```

**Example queries:**
- User says: "Create PR for git hook improvements"
- Agent queries: `category:git-hooks AND (optimization OR file-type-filtering)`
- Returns: Lessons 9, 11 (file type filtering patterns)
- Agent has context BEFORE making mistakes

### During Session: Inline Capture (NON-BLOCKING)

**Current problem:**
- `/session-learning-capture` writes to CLAUDE.md → requires git commit

**New approach:**
- Write to Supermemory during session
- No git operations required
- Knowledge immediately searchable

```bash
# Modified /session-learning-capture command
/session-learning-capture

# Workflow:
# 1. Agent drafts learning summary (interactive or auto)
# 2. Categorize and tag
# 3. Write to Supermemory via MCP
# 4. Confirm success
# 5. NO git commit required

# Optional: User can export to memory.json later
/export-learnings --since 2025-10-01
```

**Benefits:**
- **Non-blocking** - No PR cycle required
- **Immediate availability** - Next agent can query immediately
- **Lower friction** - Encourages regular capture

### Post-PR: Optional Export (ASYNC)

**When:** User wants to version-control learnings
**How:** Export from Supermemory to memory.json, commit separately

```bash
# Optional workflow (not required for knowledge to persist)
/export-learnings --since 2025-10-01 --output .agent/memory.json

# Creates git commit:
git add .agent/memory.json
git commit -m "docs: export learnings from Oct 2025 sessions"
git push

# Benefits:
# - Async (not blocking feature work)
# - Batched (monthly exports vs per-session commits)
# - Version controlled (audit trail)
```

---

## Supermemory Integration Strategy

### Migration Plan for Existing 28 Lessons

**Phase 1: Extract and Prepare**
```bash
# Read memory.json
lessons = jq '.sessions[]' .agent/memory.json

# For each lesson:
for lesson in lessons:
    # Extract structured data
    content = format_lesson_for_supermemory(lesson)
    tags = lesson["tags"] + [lesson["category"]]
    metadata = {
        "lesson_number": lesson["id"],
        "date": lesson["date"],
        "category": lesson["category"],
        "severity": classify_severity(lesson)
    }
```

**Phase 2: Batch Upload to Supermemory**
```python
# Use mcp__api-supermemory-ai__addMemory tool
for lesson in lessons:
    add_memory(
        content=lesson["formatted_content"],
        tags=lesson["tags"],
        metadata=lesson["metadata"]
    )
```

**Phase 3: Validation**
```python
# Test search queries
test_queries = [
    "atomic PR splitting strategy",
    "git hook file type filtering",
    "CHANGELOG reference links",
    "branch cleanup patterns"
]

for query in test_queries:
    results = search_supermemory(query)
    validate_relevance(results, expected_lessons)
```

### Tagging Schema Design

**Category hierarchy:**
```
pr-workflow
  ├── atomic-pr
  ├── cherry-pick
  ├── sequential-vs-parallel
  └── code-review

git-hooks
  ├── file-type-filtering
  ├── performance
  ├── timeout-configuration
  └── bypass-policy

shell-scripting
  ├── shellcheck
  ├── heredoc
  ├── platform-compatibility
  └── filename-sanitization

ci-cd
  ├── artifact-paths
  ├── exit-codes
  ├── schema-drift
  └── github-actions

git-flow
  ├── release-workflow
  ├── hotfix-workflow
  ├── branch-cleanup
  └── version-bumping
```

**Severity levels:**
- **critical** - Security, data integrity, production blockers
- **high** - Quality gates, workflow discipline
- **medium** - Best practices, optimizations
- **low** - Style, preferences

### Search Query Patterns

**Common agent scenarios:**

| Agent Task | Search Query | Expected Lessons |
|------------|--------------|------------------|
| Create PR | `category:pr-workflow AND atomic` | Lessons 1, 5, 6, 10 |
| Fix git hooks | `category:git-hooks AND (file-type OR performance)` | Lessons 9, 11 |
| Branch cleanup | `branch-cleanup OR obsolescence` | Lessons 19-23 |
| Release workflow | `category:git-flow AND release` | Lessons 25, 27, 28 |
| Shell script | `category:shell-scripting AND (heredoc OR shellcheck)` | Lessons 7, 15 |

---

## CLAUDE.md Trimming Strategy

### What MUST Stay (~1500 lines target)

**Section 1: Project Identity (200 lines)**
- Project overview (technology stack)
- File structure
- Development commands (Make, Poetry)

**Section 2: Critical Rules (~300 lines)**
- **Git Flow discipline** (never push directly to develop)
- **Hook bypass policy** (NEVER --no-verify except meta-changes)
- **PR size guidelines** (200-500 lines, atomic concerns)
- **Version bump criteria** (PATCH vs MINOR vs MAJOR)
- **Testing standards** (90%+ coverage, TDD)
- **Type checking requirements** (mypy, Callable imports)

**Section 3: Workflow Summaries (~500 lines)**
- Git Flow process (feature → release → hotfix)
- PR workflow (create → review → finish)
- Release workflow (bump → tag → back-merge)
- Hook configuration (stratified approach)

**Section 4: Quick Reference (~300 lines)**
- Common commands (compact reference)
- Troubleshooting checklist (brief)
- External API endpoints (StashDB, ThePornDB)

**Section 5: Learning Index (~200 lines)**
- **Summary table** of lessons (NOT full content)
- Links to Supermemory queries
- "See Supermemory for details" references

**Example Learning Index:**
```markdown
## Lessons Learned (Summary)

For detailed patterns, code examples, and historical context, query Supermemory:

| # | Title | Category | Query |
|---|-------|----------|-------|
| 19 | Investigation Before Cherry-Picking | pr-workflow | `lesson:19 OR cherry-pick investigation` |
| 20 | Respect Architectural Decisions | git-workflow | `lesson:20 OR architectural-decisions` |
| 21-23 | Branch Obsolescence Patterns | git-workflow | `branch-cleanup OR obsolescence` |
| 25 | GitHub PR Terminology | git-flow | `lesson:25 OR pr-terminology` |

**Quick Query Examples:**
- Atomic PR splitting: `/query category:pr-workflow AND atomic`
- Git hook optimization: `/query category:git-hooks AND performance`
- Release workflow: `/query category:git-flow AND release`
```

### What Moves to Supermemory (~3500 lines removed)

- **Detailed lesson narratives** (19-28, session-001)
- **Code examples** (keep only 2-3 critical ones)
- **Debugging journeys** (heredoc parser issues, exit code semantics)
- **PR-specific metrics** (time breakdowns, ROI calculations)
- **Historical context** (why decisions were made 6 months ago)
- **Duplicate content** (lessons in both narrative and structured sections)

---

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1 - 4 hours)

**Goal:** Immediate improvement without Supermemory migration

**Tasks:**
1. **Trim CLAUDE.md** (2 hours)
   - Remove duplicate lessons from narrative sections
   - Keep only summary table with links to memory.json
   - Move detailed code examples to comments
   - Target: Reduce from 5000 → 2500 lines

2. **Create `/query-memory` command** (1 hour)
   - Temporary bridge: jq-based search of memory.json
   - Enables manual queries until Supermemory ready
   - Example: `/query-memory tags:atomic-pr`

3. **Document Supermemory integration plan** (1 hour)
   - Add to CLAUDE.md as upcoming change
   - Prepare migration checklist
   - Validate MCP tools available

**Success criteria:**
- CLAUDE.md under 3000 lines (no warnings)
- Agent can manually query memory.json
- Team aware of upcoming changes

### Phase 2: Supermemory Migration (Week 2 - 8 hours)

**Goal:** Migrate all 28 lessons to Supermemory

**Tasks:**
1. **Migration script** (3 hours)
   - Read memory.json
   - Format lessons for Supermemory
   - Batch upload via MCP
   - Validation queries

2. **Test search patterns** (2 hours)
   - Define 10-15 common queries
   - Validate result relevance
   - Tune tagging if needed

3. **Update `/session-learning-capture`** (2 hours)
   - Change target from CLAUDE.md → Supermemory
   - Keep memory.json export as option
   - Test non-blocking workflow

4. **Create `/export-learnings` command** (1 hour)
   - Export from Supermemory to memory.json
   - Batch operation (monthly export)
   - Git commit automation

**Success criteria:**
- All 28 lessons searchable in Supermemory
- `/session-learning-capture` writes to Supermemory
- No git commits required for capture

### Phase 3: Workflow Automation (Week 3 - 6 hours)

**Goal:** Agents automatically query Supermemory at session start

**Tasks:**
1. **Session init prompt template** (2 hours)
   - Detect task category from user input
   - Auto-query Supermemory for relevant lessons
   - Inject into agent context

2. **Create `/query` command** (2 hours)
   - User-facing Supermemory search
   - Replace `/query-memory` temp command
   - Example: `/query atomic PR splitting`

3. **Update CLAUDE.md** (2 hours)
   - Final trim to ~1500 lines
   - Add "Query Supermemory for details" throughout
   - Document new workflow

**Success criteria:**
- Agents query Supermemory at session start
- User can manually query with `/query`
- CLAUDE.md stabilized at ~1500 lines

### Phase 4: Validation (Week 4 - 4 hours)

**Goal:** Verify agents use knowledge and stop repeating mistakes

**Tasks:**
1. **Audit framework** (2 hours)
   - Track queries made by agents
   - Measure knowledge utilization
   - Detect repeated mistakes

2. **Validation scenarios** (2 hours)
   - Test: Agent creating PR → should query atomic PR lessons
   - Test: Agent fixing hooks → should query file-type-filtering
   - Test: Agent doing release → should query release workflow
   - Document gaps and iterate

**Success criteria:**
- Agents query knowledge 80%+ of relevant sessions
- Zero repeated mistakes from documented lessons
- User reports improved agent context awareness

---

## Success Metrics

### Knowledge Utilization (Primary Metric)

**Measurement:**
- Track Supermemory queries per agent session
- Target: 70%+ of sessions query knowledge
- Breakdown by category (pr-workflow, git-hooks, etc.)

**Validation:**
```python
# Monthly report
sessions_total = count_sessions_last_month()
sessions_with_queries = count_sessions_with_supermemory_queries()
utilization_rate = sessions_with_queries / sessions_total

# Breakdown
queries_by_category = group_queries_by_category()
# Expected: pr-workflow (30%), git-hooks (20%), git-flow (25%), etc.
```

### Mistake Prevention (Impact Metric)

**Measurement:**
- Track instances where documented patterns are violated
- Example: Agent cherry-picks without investigation (lesson 19 violation)
- Example: Agent creates large PR >500 lines (lesson 1 violation)
- Target: <5% violation rate

**Detection:**
```python
# Code review patterns to detect
violations = [
    "PR >500 lines without split discussion",
    "Cherry-pick without git diff check",
    "Hook bypass without justification",
    "Release to develop instead of main",
    "Missing CHANGELOG reference links"
]

# Manual review monthly
review_recent_prs_for_violations()
```

### Knowledge Capture (Activity Metric)

**Measurement:**
- Sessions with learnings captured
- Target: 80%+ of feature/release sessions
- Time to capture: <5 minutes (non-blocking)

**Validation:**
```python
# Monthly capture rate
sessions_with_feature_work = count_feature_release_sessions()
sessions_with_capture = count_sessions_with_learning_capture()
capture_rate = sessions_with_capture / sessions_with_feature_work

# Friction measurement
avg_capture_time = measure_time_to_capture()  # Target <5min
```

### CLAUDE.md Size Stability (Health Metric)

**Measurement:**
- CLAUDE.md line count over time
- Target: Stable at ~1500 lines (±100 lines)
- No warnings from system

**Validation:**
```bash
# Monthly size check
wc -l CLAUDE.md
# Target: 1400-1600 lines

# Warning check
# No "large file" warnings in session init logs
```

---

## Risks and Mitigations

### Risk 1: Supermemory API Unavailable

**Scenario:** API down, rate limits, authentication issues

**Mitigation:**
- **Graceful degradation** - Fall back to memory.json search
- **Local caching** - Cache frequent queries
- **Offline mode** - Export critical lessons to CLAUDE.md appendix

**Implementation:**
```python
def query_knowledge(query):
    try:
        results = query_supermemory(query)
        return results
    except SupermemoryUnavailable:
        # Fallback to memory.json
        results = query_memory_json(query)
        return results
```

### Risk 2: Search Quality Issues

**Scenario:** Supermemory returns irrelevant results

**Mitigation:**
- **Tagging discipline** - Strict tagging schema
- **Query tuning** - Refine queries based on results
- **Hybrid search** - Combine semantic + tag filters
- **Feedback loop** - User feedback on result quality

**Implementation:**
```python
# Hybrid search pattern
def hybrid_search(query, category):
    # Semantic search
    semantic_results = supermemory.search(query)

    # Filter by tags
    filtered_results = [
        r for r in semantic_results
        if category in r["tags"]
    ]

    return filtered_results[:5]  # Top 5
```

### Risk 3: Migration Data Loss

**Scenario:** Lessons lost during migration from memory.json

**Mitigation:**
- **Backup first** - Copy memory.json before migration
- **Validation step** - Verify all lessons migrated
- **Rollback plan** - Keep memory.json as source of truth during transition
- **Audit trail** - Log all uploads

**Implementation:**
```bash
# Migration safety protocol
cp .agent/memory.json .agent/memory.json.backup
./migrate-to-supermemory.sh
./validate-migration.sh || rollback
```

### Risk 4: Agent Doesn't Use System

**Scenario:** Agents still don't query knowledge despite availability

**Mitigation:**
- **Prompt engineering** - Add "Always check knowledge before proceeding"
- **Workflow integration** - Auto-query at session start (not optional)
- **Validation prompts** - "Have you checked if this pattern exists?"
- **Success showcasing** - Document wins from knowledge use

**Implementation:**
```python
# Mandatory knowledge check in prompt
prompt_template = """
BEFORE proceeding with this task, you MUST:
1. Query Supermemory for relevant lessons: /query {task_keywords}
2. Review returned lessons for applicable patterns
3. Reference lesson numbers in your response

Task: {user_task}
"""
```

### Risk 5: Knowledge Fragmentation

**Scenario:** Knowledge split across Supermemory, memory.json, CLAUDE.md, git history

**Mitigation:**
- **Single source of truth** - Supermemory is canonical
- **Clear hierarchy** - CLAUDE.md = rules, Supermemory = patterns, memory.json = backup
- **Documentation** - Explicitly state what lives where
- **Consolidation cadence** - Monthly review to prevent drift

**Implementation:**
```markdown
## Knowledge Hierarchy

**CLAUDE.md (Core Rules):**
- Critical "must not do" policies
- Current project state
- Workflow summaries

**Supermemory (Searchable Patterns):**
- Lessons learned (all 28+)
- Code examples
- Debugging journeys
- Historical context

**memory.json (Archive):**
- Monthly export from Supermemory
- Version-controlled backup
- Disaster recovery

**WHERE TO LOOK:**
- Need to know "never do X"? → CLAUDE.md
- Need to know "how to solve Y"? → Supermemory
- Need to audit history? → memory.json
```

---

## Validation Plan

### Phase 1: Unit Validation (Week 1)

**Goal:** Verify each component works in isolation

**Tests:**
1. **Supermemory connectivity**
   - Upload test memory
   - Search and retrieve
   - Verify metadata preserved

2. **Search quality**
   - Test 10 known queries
   - Validate relevance of top 5 results
   - Tune if needed

3. **Command functionality**
   - `/session-learning-capture` writes to Supermemory
   - `/export-learnings` exports to memory.json
   - `/query` searches Supermemory

**Success criteria:**
- All MCP tools working
- Search returns relevant results >80%
- Commands execute without errors

### Phase 2: Integration Validation (Week 2)

**Goal:** Verify components work together in workflow

**Scenarios:**
1. **Feature PR workflow**
   - User: "Create PR for hook improvements"
   - Agent: Queries Supermemory for git-hooks lessons
   - Agent: References lesson 9 (file-type-filtering)
   - Agent: Creates PR following documented pattern

2. **Release workflow**
   - User: "Create release v1.24.0"
   - Agent: Queries Supermemory for release patterns
   - Agent: References lesson 27 (version bump criteria)
   - Agent: Follows PATCH vs MINOR guidelines

3. **Post-session capture**
   - Agent: Completes feature work
   - User: `/session-learning-capture`
   - Agent: Drafts learning, writes to Supermemory
   - Verify: No git commit required

**Success criteria:**
- Agents query knowledge before proceeding
- Agents reference lesson numbers in responses
- Knowledge capture non-blocking

### Phase 3: Behavioral Validation (Week 3-4)

**Goal:** Verify agents stop repeating documented mistakes

**Test cases:**

| Mistake (Lesson) | Test Scenario | Expected Behavior |
|------------------|---------------|-------------------|
| Cherry-pick without investigation (19) | "Extract security improvements from old branch" | Agent queries lesson 19 → diffs code first |
| Large PR without splitting (1) | "Create PR with 800 lines" | Agent suggests splitting → references lesson 1 |
| Release to develop (25) | "Create release PR" | Agent targets main → references lesson 25 |
| Missing CHANGELOG links (28) | "Complete release" | Agent adds reference links → lesson 28 |

**Success criteria:**
- Zero violations of documented patterns
- Agents proactively reference lessons
- User feedback: "Agent knew what to do without me explaining"

---

## Next Steps

### Immediate Actions (This Session)

1. **Validate Supermemory MCP** availability
2. **Create migration script** for 28 lessons
3. **Test one lesson** upload/search cycle

### This Week (Phase 1)

1. Trim CLAUDE.md to 2500 lines (50% reduction)
2. Create `/query-memory` temporary command
3. Document Supermemory integration plan

### Next Week (Phase 2)

1. Complete Supermemory migration
2. Update `/session-learning-capture`
3. Test search patterns

### Month 1 Complete (Phase 3-4)

1. Auto-query at session start
2. Final CLAUDE.md trim to 1500 lines
3. Validation framework deployed
4. Monthly metrics dashboard

---

## Timeline Summary

- **Phase 1** (Week 1): 4 hours - Quick wins, CLAUDE.md trim
- **Phase 2** (Week 2): 8 hours - Supermemory migration, command updates
- **Phase 3** (Week 3): 6 hours - Workflow automation, auto-query
- **Phase 4** (Week 4): 4 hours - Validation framework, testing

**Total estimated effort**: 22 hours over 4 weeks

---

**Status**: Ready to proceed with Phase 1 (CLAUDE.md trim + temp query command) for immediate relief from size warnings.
