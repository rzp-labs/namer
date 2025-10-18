# GitHub Issues Created: Knowledge Management System Overhaul

**Date**: 2025-10-18
**Feature Branch**: `feature/dx-replace-memory-storage-with-supermemory`
**Repository**: rzp-labs/namer

---

## ✅ All 16 Issues Created Successfully

### Phase 0: Critical Prompt Engineering (BLOCKING) - 4.5 hours

**Must complete before ANY other work begins**

- #164 - Create mandatory knowledge check prompt template (2h)
- #165 - Reduce lesson retrieval from 5 to 3 maximum (30m)
- #166 - Implement lesson citation validation (1h)
- #167 - Add fallback to memory.json when Supermemory unavailable (1h)

**Impact**: Raises confidence from 6/10 → 8/10 (85% success probability)

### Phase 1: Quick Wins - 4 hours

**Immediate relief from CLAUDE.md bloat**

- #168 - Trim CLAUDE.md from 5000 to 2500 lines (2h)
- #169 - Create /query-memory command for jq-based bridge (1h)
- #170 - Document Supermemory integration plan in CLAUDE.md (1h)

### Phase 2: Supermemory Migration - 8 hours

**Migrate knowledge to searchable format**

- #171 - Create migration script with optimal lesson format (3h)
- #172 - Test search patterns with hybrid search (2h)
- #173 - Update /session-learning-capture to write to Supermemory (2h)
- #174 - Create /export-learnings command for optional git export (1h)

### Phase 3: Workflow Automation - 6 hours

**Automatic knowledge queries at session start**

- #175 - Implement session init auto-query with mandatory 5-step process (2h)
- #176 - Create /query command with hybrid search and 3-lesson limit (2h)
- #177 - Final CLAUDE.md trim to ~1500 lines with Supermemory references (2h)

### Phase 4: Validation - 4 hours

**Measure success and prevent regressions**

- #178 - Create utilization tracking dashboard (2h)
- #179 - Test validation scenarios (2h)

---

## 📊 Summary Statistics

- **Total Issues**: 16
- **Total Estimated Effort**: 26.5 hours
- **Timeline**: 4 weeks (1 phase per week)
- **Success Metrics**:
  - 80%+ sessions query knowledge
  - 90%+ agents cite lessons when applicable
  - <5% violation of documented patterns
  - CLAUDE.md stable at ~1500 lines

---

## 🔗 Issue Dependencies

### Critical Path
```
Phase 0 (#164-167) → BLOCKS ALL OTHER PHASES
  ↓
Phase 1 (#168-170) → Can start after Phase 0
  ↓
Phase 2 (#171-174) → Depends on Phase 1
  ↓
Phase 3 (#175-177) → Depends on Phase 2
  ↓
Phase 4 (#178-179) → Depends on Phase 3
```

### Specific Dependencies
- #165 (reduce lessons) → Used by #169, #176
- #166 (citation validation) → Required for #178
- #167 (fallback) → Required for all phases (reliability)
- #171 (migration) → Blocks #172, #173
- #172 (search patterns) → Blocks #176
- #175 (session init) → Blocks #178

---

## 🎯 Next Steps

1. **Start Phase 0** immediately (blocking work)
2. **Do NOT proceed** to Phase 1 until Phase 0 complete
3. **Track progress** with utilization metrics from #178
4. **Validate success** with scenarios from #179

---

## 📚 Planning Documents

- `docs/dx-knowledge-management-overhaul.md` - Full architecture plan
- `docs/dx-knowledge-management-prompt-review.md` - Critical improvements analysis
- `CLAUDE.md` - Will document migration as it progresses

---

**Status**: All issues created ✅  
**Ready to begin**: Phase 0 implementation
