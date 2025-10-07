# Migration Plan: `fix/ambiguity-review` → `main`

## Executive Summary

This document outlines the migration strategy for incorporating 9 commits from the `fix/ambiguity-review` branch into `main`. The plan prioritizes **atomic PRs**, **parallel development**, and **minimal merge conflicts** by organizing work into independent workstreams.

**Key Metrics:**

- **Total PRs:** 16
- **Parallel Workstreams:** 4
- **Max PR Size:** ~100 lines, ≤5 files
- **Estimated Timeline:** 2-3 weeks with 2-4 concurrent engineers

---

## Pre-Migration Validation

**⚠️ Complete these steps before creating any PRs:**

### 1. Verify Branch State

```bash
# Confirm branch exists and has expected commits
git checkout fix/ambiguity-review
git log --oneline main..fix/ambiguity-review | wc -l  # Should output: 9

# Record common ancestor
git merge-base fix/ambiguity-review main

# Validate expected changes
git diff main...fix/ambiguity-review --stat
```

**Expected Output:** ~15-20 files changed across the 9 commits listed below.

### 2. Check for Overlapping Changes

```bash
# Verify no conflicts with current main
git checkout main
git pull origin main
git checkout fix/ambiguity-review

# Compare high-risk files
git diff main...fix/ambiguity-review -- namer/namer.py
git diff main...fix/ambiguity-review -- namer/comparison_results.py
git diff main...fix/ambiguity-review -- .github/workflows/pr-validate.yml
```

**Action:** If `main` has divergent changes in these files since branch creation, document them and adjust PR specifications accordingly.

### 3. Dry-Run Cherry-Picks for High-Risk PRs

Test cherry-picks without committing to identify potential conflicts:

```bash
# Test C2 (refactor directory creation)
git checkout -b test-c2 main
git cherry-pick -n 34200fc
git status  # Check for conflicts
git reset --hard HEAD
git checkout main
git branch -D test-c2

# Test E1 (ambiguous file handling)
git checkout -b test-e1 main
git cherry-pick -n fa96678
git status  # Check for conflicts
git reset --hard HEAD
git checkout main
git branch -D test-e1

# Test D1-D3 sequence (phash handling)
git checkout -b test-phash main
git cherry-pick -n 8d1fcd9 0381399 65b8c44
git status  # Check for conflicts
git reset --hard HEAD
git checkout main
git branch -D test-phash
```

**Escalation Criteria:** If ≥2 dry-runs fail, schedule a 30-minute planning session before starting Week 1.

### 4. Validate Test Suite Baseline

```bash
# Record current test coverage
git checkout main
poetry install
poetry run pytest --cov=namer --cov-report=term | tee coverage-baseline.txt

# Note current coverage percentage for comparison
```

**Baseline:** All PRs must maintain or improve upon this coverage percentage.

---

## Source Commits

The following commits from `fix/ambiguity-review` require migration:

| Commit    | Description                                  | Files Changed       |
| --------- | -------------------------------------------- | ------------------- |
| `091cc71` | Enhances CI validation and static analysis   | 5 files, +322/-17   |
| `8e90cc3` | Simplifies CI workflow                       | 1 file, -81         |
| `f4361a2` | Adds static analysis workflow                | 3 files, +130/-18   |
| `65b8c44` | Improves phash result handling               | 2 files, +12/-7     |
| `0381399` | Adds setter method for phash flag            | 2 files, +11/-2     |
| `8d1fcd9` | Improves file path handling and validation   | 3 files, +36/-26    |
| `5960020` | Updates hadolint-action to specific commit   | 1 file, +1/-1       |
| `260e27d` | Improves error handling and security         | 10 files, +115/-132 |
| `34200fc` | Refactors directory creation into a function | 3 files, +14/-16    |
| `fa96678` | Improves ambiguous file handling             | 3 files, +38/-3     |

---

## Workstream Organization

### **Workstream A: CI/CD Infrastructure** (Independent)

**Owner:** DevOps/Platform Engineer
**Files:** `.github/workflows/pr-validate.yml`, `Dockerfile`

- **A1:** Update hadolint-action to pinned commit (`5960020`)
- **A2:** Add static analysis workflow foundation (`f4361a2` - workflow only)
- **A3:** Enhance CI validation with dependency scanning (`091cc71` - CI/Dockerfile)
- **A4:** Simplify CI workflow (if applicable after A2/A3 merge)

**Conflict Risk:** Low (single file owner)

---

### **Workstream B: Security & Dependencies** (Independent)

**Owner:** Security/Backend Engineer
**Files:** `pyproject.toml`, `poetry.lock`, `namer/ffmpeg*.py`, `namer/configuration*.py`

- **B1:** Add defusedxml dependency (`260e27d` - deps only)
- **B2:** Replace random with secrets for temp filenames (`260e27d` - ffmpeg only)
- **B3:** Replace hardcoded token placeholders with constants (`260e27d` - config only)

**Conflict Risk:** Low (B1 must merge first; B2/B3 are independent)

---

### **Workstream C: Code Quality & Refactoring** (Semi-Independent)

**Owner:** Backend Engineer
**Files:** `namer/command.py`, `namer/namer.py`, `namer/moviexml.py`, `namer/watchdog.py`

- **C1:** Improve error context in directory creation (`260e27d` - logging only)
- **C2:** Refactor directory creation into shared utility (`34200fc`)
- **C3:** Improve file path validation in watchdog (`8d1fcd9` - watchdog only)

**Dependencies:**

- C2 depends on C1 (both touch `namer/namer.py`)
- C3 is independent

**Conflict Risk:** Medium (C1→C2 sequential; C3 parallel)

---

### **Workstream D: Feature Enhancements** (Independent)

**Owner:** Backend Engineer
**Files:** `namer/comparison_results.py`, `namer/metadata_providers/theporndb_provider.py`

- **D1:** Improve comparison result path handling (`8d1fcd9` - comparison_results only)
- **D2:** Add setter method for phash flag (`0381399`)
- **D3:** Improve phash result handling (`65b8c44`)
- **D4:** Improve ThePornDB provider error handling (`f4361a2` - provider only)

**Dependencies:**

- D2 depends on D1 (both touch `comparison_results.py`)
- D3 depends on D2 (both touch `comparison_results.py`)
- D4 is independent

**Conflict Risk:** Medium (D1→D2→D3 sequential; D4 parallel)

---

### **Workstream E: Ambiguity Handling** (Depends on C2)

**Owner:** Backend Engineer
**Files:** `namer/namer.py`, `namer/watchdog.py`, `.github/workflows/pr-validate.yml`

- **E1:** Improve ambiguous file directory handling (`fa96678` - namer.py only)
- **E2:** Enhance watchdog event processing (`f4361a2` - watchdog only)
- **E3:** Add ambiguous file workflow validation (`fa96678` - CI + watchdog)

**Dependencies:**

- E1 depends on C2 (both refactor `namer.py` directory logic)
- E2 is independent
- E3 depends on E1 (validates E1's logic)

**Conflict Risk:** High (E1 must wait for C2; E3 must wait for E1)

---

## Parallel Execution Matrix

| Week  | Workstream A | Workstream B | Workstream C | Workstream D | Workstream E |
| ----- | ------------ | ------------ | ------------ | ------------ | ------------ |
| **1** | A1 → A2      | B1 → B2      | C1 → C2      | D1 → D2      | ⏸️ (waiting) |
| **2** | A3 → A4      | B3           | C3           | D3 → D4      | E2           |
| **3** | ✅ Complete  | ✅ Complete  | ✅ Complete  | ✅ Complete  | E1 → E3      |

**Concurrency:** Up to 4 engineers can work simultaneously without conflicts.

---

## PR Specifications

### **A1: Update hadolint-action to pinned commit**

- **Branch:** `chore/pin-hadolint-action`
- **Files:** `.github/workflows/pr-validate.yml` (1 line)
- **Cherry-pick:** `git cherry-pick -n 5960020`
- **Tests:** CI must pass
- **Merge Order:** 1

### **A2: Add static analysis workflow foundation**

- **Branch:** `chore/add-static-analysis-workflow`
- **Files:** `.github/workflows/pr-validate.yml` (+81 lines)
- **Cherry-pick:** `git cherry-pick -n f4361a2` (stage workflow only)
- **Tests:** Verify mypy/bandit/shfmt/shellcheck steps run
- **Merge Order:** 2 (after A1)

### **A3: Enhance CI validation with dependency scanning**

- **Branch:** `chore/enhance-ci-validation`
- **Files:** `.github/workflows/pr-validate.yml`, `Dockerfile`, `poetry.lock`, `pyproject.toml`
- **Cherry-pick:** `git cherry-pick -n 091cc71` (exclude test file changes)
- **Tests:** Trivy/Hadolint must run successfully
- **Merge Order:** 3 (after A2, coordinate with B1 for dependency files)

**⚠️ Dependency File Coordination (A3 ↔ B1):**

Since both A3 and B1 modify `poetry.lock` and `pyproject.toml`, follow this protocol:

1. **Merge Order:** B1 → A3 (security dependencies first)
2. **After B1 merges:**
   ```bash
   # On A3 branch
   git checkout chore/enhance-ci-validation
   git fetch origin
   git rebase origin/main

   # Regenerate lock file if conflicts occur
   poetry lock --no-update
   poetry install

   # Verify both dependency sets are present
   poetry show | grep -E "(trivy|hadolint|defusedxml)"

   # Push rebased branch
   git push --force-with-lease
   ```
3. **If conflicts in `pyproject.toml`:**
   - Preserve both dependency additions (B1's defusedxml + A3's CI tools)
   - Run `poetry lock` to regenerate lock file
   - Verify `poetry install` completes successfully

### **A4: Simplify CI workflow**

- **Branch:** `chore/simplify-ci-workflow`
- **Files:** `.github/workflows/pr-validate.yml` (-81 lines)
- **Cherry-pick:** `git cherry-pick -n 8e90cc3`
- **Tests:** CI must pass with simplified workflow
- **Merge Order:** 4 (after A3). **Decision Point:** Before starting, the DevOps engineer will confirm if the refactoring in `8e90cc3` is still applicable after A2 and A3 are merged. If the changes are entirely superseded, this PR will be skipped.

---

### **B1: Add defusedxml dependency**

- **Branch:** `chore/add-defusedxml`
- **Files:** `poetry.lock`, `pyproject.toml`
- **Cherry-pick:** `git cherry-pick -n 260e27d` (stage deps only)
- **Tests:** `poetry install` must succeed
- **Merge Order:** 1 (independent)

### **B2: Replace random with secrets for temp filenames**

- **Branch:** `fix/use-secrets-for-temp-files`
- **Files:** `namer/ffmpeg.py`, `namer/ffmpeg_enhanced.py`
- **Cherry-pick:** `git cherry-pick -n 260e27d` (stage ffmpeg files only)
- **Tests:** `pytest test/namer_ffmpeg_test.py`
- **Merge Order:** 2 (after B1)

### **B3: Replace hardcoded token placeholders with constants**

- **Branch:** `refactor/extract-token-constants`
- **Files:** `namer/configuration.py`, `namer/configuration_utils.py`, `namer/videophash/videophashstash.py`
- **Cherry-pick:** `git cherry-pick -n 260e27d` (stage config files only)
- **Tests:** `pytest test/configuration_test.py`
- **Merge Order:** 3 (parallel with B2)

---

### **C1: Improve error context in directory creation**

- **Branch:** `fix/improve-directory-error-logging`
- **Files:** `namer/command.py`, `namer/namer.py`
- **Cherry-pick:** `git cherry-pick -n 260e27d` (stage logging changes only)
- **Tests:** `pytest test/namer_test.py`
- **Merge Order:** 1 (independent)

### **C2: Refactor directory creation into shared utility**

- **Branch:** `refactor/consolidate-directory-creation`
- **Files:** `namer/command.py`, `namer/moviexml.py`, `namer/namer.py`
- **Cherry-pick:** `git cherry-pick -n 34200fc`
- **Tests:** `pytest test/namer_test.py test/command_test.py`
- **Merge Order:** 2 (after C1)

### **C3: Improve file path validation in watchdog**

- **Branch:** `fix/validate-watchdog-paths`
- **Files:** `namer/watchdog.py`
- **Cherry-pick:** `git cherry-pick -n 8d1fcd9` (stage watchdog only)
- **Tests:** `pytest test/watchdog_test.py`
- **Merge Order:** 3 (parallel with C2)

---

### **D1: Improve comparison result path handling**

- **Branch:** `fix/validate-comparison-paths`
- **Files:** `namer/comparison_results.py`
- **Cherry-pick:** `git cherry-pick -n 8d1fcd9` (stage comparison_results only)
- **Tests:** `pytest test/comparison_results_test.py`
- **Merge Order:** 1 (independent)

### **D2: Add setter method for phash flag**

- **Branch:** `refactor/add-phash-setter`
- **Files:** `namer/comparison_results.py`, `namer/metadata_providers/theporndb_provider.py`
- **Cherry-pick:** `git cherry-pick -n 0381399`
- **Tests:** `pytest test/comparison_results_test.py`
- **Merge Order:** 2 (after D1)

### **D3: Improve phash result handling**

- **Branch:** `fix/improve-phash-handling`
- **Files:** `namer/comparison_results.py`, `namer/metadata_providers/theporndb_provider.py`
- **Cherry-pick:** `git cherry-pick -n 65b8c44`
- **Tests:** `pytest test/stashdb_phash_ambiguity_test.py`
- **Merge Order:** 3 (after D2)

### **D4: Improve ThePornDB provider error handling**

- **Branch:** `fix/theporndb-error-handling`
- **Files:** `namer/metadata_providers/theporndb_provider.py`
- **Cherry-pick:** `git cherry-pick -n f4361a2` (stage provider only)
- **Tests:** `pytest test/metadata_providers_test.py`
- **Merge Order:** 4 (parallel with D1-D3)

---

### **E1: Improve ambiguous file directory handling**

- **Branch:** `feat/improve-ambiguous-handling`
- **Files:** `namer/namer.py`
- **Cherry-pick:** `git cherry-pick -n fa96678` (stage namer.py only)
- **Tests:** `pytest test/namer_test.py`
- **Merge Order:** 1 (after C2)

### **E2: Enhance watchdog event processing**

- **Branch:** `fix/enhance-watchdog-events`
- **Files:** `namer/watchdog.py`
- **Cherry-pick:** `git cherry-pick -n f4361a2` (stage watchdog only)
- **Tests:** `pytest test/watchdog_test.py`
- **Merge Order:** 2 (parallel with E1)

### **E3: Add ambiguous file workflow validation**

- **Branch:** `test/validate-ambiguous-workflow`
- **Files:** `.github/workflows/pr-validate.yml`, `namer/watchdog.py`
- **Cherry-pick:** `git cherry-pick -n fa96678` (stage CI + watchdog)
- **Tests:** CI must validate ambiguous file handling
- **Merge Order:** 3 (after E1)

---

## Conflict Resolution Strategy

### **High-Risk Conflicts**

1. **`namer/namer.py`** (touched by C1, C2, E1)

   - **Mitigation:** C1 → C2 → E1 strict sequence
   - **Validation:** Rebase E1 on latest `main` after C2 merges

2. **`namer/comparison_results.py`** (touched by D1, D2, D3)

   - **Mitigation:** D1 → D2 → D3 strict sequence
   - **Validation:** Each PR rebases on previous

3. **`.github/workflows/pr-validate.yml`** (touched by A1, A2, A3, A4, E3)
   - **Mitigation:** A-series sequential; E3 waits for A4
   - **Validation:** Rebase E3 on latest `main` after A4 merges

### **Low-Risk Conflicts**

- **Workstream B:** All files are independent or dependency-ordered
- **Workstream C3:** `watchdog.py` isolated from C1/C2
- **Workstream D4:** `theporndb_provider.py` isolated from D1-D3

---

## Validation Checklist (Per PR)

- [ ] Cherry-pick commit and stage only relevant files
- [ ] Run `poetry run ruff check .`
- [ ] Run `poetry run pytest` (full suite)
- [ ] Run `poetry run mypy namer/` (if applicable)
- [ ] **Verify test coverage is maintained:**
  ```bash
  poetry run pytest --cov=namer --cov-report=term
  # Compare to baseline from Pre-Migration Validation step 4
  # If coverage drops, add tests before merging
  ```
- [ ] Verify CI passes on PR branch
- [ ] Confirm no merge conflicts with `main`
- [ ] Update PR description with:
  - Source commit SHA
  - Files changed
  - Test coverage percentage
  - Related PRs (dependencies)

---

## Rollback Plan

Each PR is independently revertible:

```bash
git revert <merge-commit-sha>
git push origin main
```

**Critical PRs requiring coordinated rollback:**

- C1 + C2 (directory refactor)
- D1 + D2 + D3 (phash handling)
- E1 + E3 (ambiguous file logic + validation)

---

## Cherry-Pick Conflict Resolution

**If cherry-pick fails with conflicts:**

### Step 1: Identify Conflicting Files

```bash
git status
# Look for files marked as "both modified"
```

### Step 2: Resolve Each Conflict

```bash
# Compare source commit vs main
git diff main...fix/ambiguity-review -- <conflicting-file>

# Open file in editor and manually apply changes
# Look for conflict markers: <<<<<<<, =======, >>>>>>>

# After resolving, stage the file
git add <conflicting-file>
```

### Step 3: Complete Cherry-Pick

```bash
git cherry-pick --continue
```

### Step 4: Verify Changes

**⚠️ CRITICAL:** Ensure only intended changes are staged:

```bash
# Review all staged changes
git diff --staged

# Compare to original commit
git show <original-commit-sha>

# If unexpected changes are present, reset and retry
git cherry-pick --abort
```

### Common Conflict Scenarios

| Scenario | Resolution Strategy |
|----------|---------------------|
| `poetry.lock` conflict | Run `poetry lock --no-update` and stage the result |
| Import statement order changed | Preserve main's order, add new imports alphabetically |
| Function signature modified in main | Apply original commit's logic to new signature |
| File deleted in main | Skip changes to that file: `git rm <file>` |

### Escalation

If conflict resolution is unclear or involves >50 lines:
1. Post in migration channel with conflict details
2. Schedule 15-minute sync with original commit author
3. Document resolution in PR description

---

## Success Metrics

- **Zero merge conflicts** during concurrent development
- **All PRs ≤100 lines** (excluding lock files)
- **CI green** on every PR before merge
- **No test coverage regression** (maintain ≥80%)
- **Complete migration** within 3 weeks

---

## Appendix: File Ownership Matrix

| File                                             | Workstreams | Conflict Risk |
| ------------------------------------------------ | ----------- | ------------- |
| `.github/workflows/pr-validate.yml`              | A, E3       | High          |
| `namer/namer.py`                                 | C1, C2, E1  | High          |
| `namer/comparison_results.py`                    | D1, D2, D3  | Medium        |
| `namer/watchdog.py`                              | C3, E2, E3  | Medium        |
| `namer/ffmpeg*.py`                               | B2          | Low           |
| `namer/configuration*.py`                        | B3          | Low           |
| `namer/command.py`                               | C1, C2      | Low           |
| `namer/moviexml.py`                              | C2          | Low           |
| `namer/metadata_providers/theporndb_provider.py` | D2, D3, D4  | Low           |
| `poetry.lock`, `pyproject.toml`                  | A3, B1      | Low           |
| `Dockerfile`                                     | A3          | Low           |

---

**Document Version:** 1.0
**Last Updated:** 2025-10-06
**Maintained By:** Engineering Team
