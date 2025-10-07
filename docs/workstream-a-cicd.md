# Workstream A: CI/CD Infrastructure

**Owner:** DevOps/Platform Engineer
**Timeline:** Week 1-2
**Total PRs:** 4 (A1, A2, A3, A4)
**Status:** Independent (no cross-workstream dependencies)

---

## Mission Statement

Modernize and harden the CI/CD pipeline by introducing static analysis, security scanning, and improved workflow organization while maintaining zero downtime and backward compatibility.

---

## Goals & Objectives

### Primary Goals

1. **Pin critical CI dependencies** to specific commits for reproducibility
2. **Introduce static analysis** (mypy, bandit, shfmt, shellcheck) without blocking existing workflows
3. **Add security scanning** (Trivy, Hadolint) to catch vulnerabilities early
4. **Streamline workflow** by removing redundant steps and improving readability

### Success Metrics

- ✅ All 4 PRs merged by end of Week 2
- ✅ CI runtime remains ≤5 minutes per run
- ✅ Zero false positives from new static analysis tools
- ✅ Security scans integrated without breaking existing jobs

---

## First Day Checklist

**Complete before writing any code:**

- [ ] Read [migration-plan-fix-ambiguity-review.md](migration-plan-fix-ambiguity-review.md)
- [ ] Read [delivery-plan-fix-ambiguity-review.md](delivery-plan-fix-ambiguity-review.md)
- [ ] Read this workstream doc completely
- [ ] Run pre-migration validation from migration plan
- [ ] Establish CI baseline metrics (see below)
- [ ] Install migration utilities: `chmod +x scripts/*.sh`
- [ ] Join Slack channel: `#migration-ambiguity-review`
- [ ] Introduce yourself to team, identify backup reviewer
- [ ] Review source commits:
  ```bash
  git checkout fix/ambiguity-review
  git log --oneline main..fix/ambiguity-review | grep -E "(091cc71|8e90cc3|f4361a2|5960020)"
  git show 5960020  # A1
  git show f4361a2  # A2
  git show 091cc71  # A3
  git show 8e90cc3  # A4
  ```

**Ready to start when all boxes checked.**

---

## Pre-Work: Establish CI Baseline

**Before starting A1, establish baseline metrics:**

```bash
# Record current CI performance
gh run list --workflow=pr-validate.yml --limit=10 --json conclusion,startedAt,updatedAt > ci-baseline.json

# Calculate average runtime (manual for now, or use jq)
gh run list --workflow=pr-validate.yml --limit=5

# Note average runtime for comparison
# Expected: ~3-4 minutes
```

**Success Criteria Updates:**

- **A1:** Runtime ±10 seconds from baseline
- **A2:** Runtime ≤ baseline + 1 minute (new tools add overhead)
- **A3:** Runtime ≤ baseline + 2 minutes (Trivy scan adds time)
- **A4:** Runtime ≤ baseline (simplification should not increase time)

**Record baseline in `ci-baseline.txt`:**

```bash
echo "Baseline CI runtime: 3m 42s" > ci-baseline.txt
echo "Measured at: $(date -Iseconds)" >> ci-baseline.txt
git add ci-baseline.txt
git commit -m "docs: record CI baseline for A-workstream"
```

---

## PR Template

Use this template for all Workstream A PRs:

````markdown
## Migration PR: [Workstream A] - [PR ID]

### Source Information
- **Branch:** `fix/ambiguity-review`
- **Commit SHA:** `<sha>`
- **Cherry-pick command:** `git cherry-pick -n <sha>`

### Changes
- List of files changed
- Brief description of what changed in each file

### Testing
- [ ] Unit tests pass: `poetry run pytest`
- [ ] Linting passes: `poetry run ruff check .`
- [ ] Coverage maintained: `./scripts/compare-coverage.sh`
- [ ] CI passes on PR branch
- [ ] Smoke test executed: `./scripts/smoke-test.sh A <PR-ID>`

### Dependencies
- **Blocks:** [PR IDs that depend on this]
- **Blocked by:** [PR IDs this depends on]

### CI Performance
- **Baseline runtime:** 3m 42s
- **This PR runtime:** [fill in after first CI run]
- **Δ from baseline:** [+/- seconds]

### Review Checklist
- [ ] Only relevant files from cherry-pick included
- [ ] No unintended changes
- [ ] All tests green
- [ ] Workflow YAML is valid
- [ ] New tools install successfully (A2/A3)
````

---

## PR Breakdown

### **A1: Update hadolint-action to pinned commit**

**Priority:** High (foundation for A2)
**Complexity:** Low
**Estimated Time:** 1-2 hours

#### What You're Changing

```yaml
# Before
- uses: hadolint/hadolint-action@latest

# After
- uses: hadolint/hadolint-action@54c9adbab1582c2ef04b2016b760714a4bfde3cf
```

#### Why This Matters

- **Reproducibility:** Pinning to a specific SHA ensures the same linter version runs across all environments
- **Security:** Prevents supply chain attacks via compromised `latest` tags
- **Stability:** Avoids unexpected breaking changes from upstream updates

#### Definition of Done

**Code Complete:**
- [ ] Cherry-pick applied cleanly
- [ ] Only `.github/workflows/pr-validate.yml` modified (1 line)
- [ ] Hadolint SHA matches: `54c9adbab1582c2ef04b2016b760714a4bfde3cf`

**Testing Complete:**
- [ ] CI passes on PR branch
- [ ] Hadolint step executes successfully
- [ ] No change in workflow runtime (±10 seconds from baseline)
- [ ] Smoke test passes: `./scripts/smoke-test.sh A A1`

**Review Complete:**
- [ ] 1 DevOps + 1 Backend approval
- [ ] No unresolved comments
- [ ] All conversations resolved

**Documentation Complete:**
- [ ] PR description includes commit SHA `5960020`
- [ ] Related PRs linked (blocks A2)

**Ready to Merge:**
- [ ] Rebased on latest `main`
- [ ] All CI checks green
- [ ] Approved by required reviewers

#### Post-Merge Smoke Test

**Immediately after A1 merges:**

```bash
# Run smoke test
./scripts/smoke-test.sh A A1

# Expected output:
# ✅ Hadolint SHA verified
# ✅ Smoke test passed for A-A1
```

**If smoke test fails:** Immediate rollback and root cause analysis.

---

### **A2: Add static analysis workflow foundation**

**Priority:** High (enables A3)
**Complexity:** Medium
**Estimated Time:** 4-6 hours

#### What You're Adding

New workflow steps for:

- **mypy:** Type checking for `namer/watchdog.py` and `namer/metadata_providers`
- **bandit:** Security scanning for Python code
- **shfmt:** Shell script formatting validation
- **shellcheck:** Shell script linting

#### Implementation Strategy

1. **Start with non-blocking checks:**

   ```yaml
   - name: Run mypy check
     continue-on-error: true # Initially permissive
     run: poetry run mypy namer/ | tee mypy.log
   ```

2. **Use `continue-on-error: true`** for all new static analysis steps in this initial PR. This allows us to merge the new tooling and address existing code issues in separate, focused PRs.

3. **Gradually tighten enforcement** in follow-up PRs (post-migration) by removing `continue-on-error`.

4. **Capture logs for all tools:**

   ```yaml
   - name: Upload static analysis results
     uses: actions/upload-artifact@v4
     with:
       name: static-analysis-logs
       path: |
         mypy.log
         bandit.txt
         shfmt.log
         shellcheck.log
   ```

#### Unique Considerations

**⚠️ Shell Tooling Installation:**
The workflow installs `shfmt` and `shellcheck` via a dedicated step:

```yaml
- name: Install shell tooling
  run: |
    # shfmt
    wget -qO- https://github.com/mvdan/sh/releases/download/v3.8.0/shfmt_v3.8.0_linux_amd64 > /usr/local/bin/shfmt
    chmod +x /usr/local/bin/shfmt

    # shellcheck
    sudo apt-get update && sudo apt-get install -y shellcheck
```

**Why not use pre-built actions?**

- More control over versions
- Faster than Docker-based actions
- Consistent with existing workflow patterns

#### Testing Locally

Before pushing:

```bash
# Test mypy
poetry run mypy namer/watchdog.py namer/metadata_providers

# Test bandit
poetry run bandit -q -r namer -x namer/web,tests

# Test shfmt (requires Docker)
docker run --rm -v "$PWD":/work -w /work mvdan/shfmt -d scripts

# Test shellcheck
shellcheck scripts/*.sh
```

**Expected Results:**

- mypy: May report existing issues (acceptable for initial PR)
- bandit: Should pass with no high-severity findings
- shfmt/shellcheck: Should pass (scripts already formatted in previous work)

---

### **A3: Enhance CI validation with dependency scanning**

**Priority:** High
**Complexity:** High
**Estimated Time:** 6-8 hours

#### What You're Adding

1. **Trivy vulnerability scanning** for Docker images and dependencies
2. **Hadolint** for Dockerfile linting
3. **Updated test dependencies** in `pyproject.toml`

#### Files Modified

- `.github/workflows/pr-validate.yml` (new Trivy/Hadolint steps)
- `Dockerfile` (minor improvements for Hadolint compliance)
- `poetry.lock`, `pyproject.toml` (test dependency updates)

#### Dependency File Coordination

**⚠️ CRITICAL:** This PR conflicts with **B1** (Add defusedxml dependency)

**Resolution Protocol:**

1. **Merge Order:** B1 must merge first
2. **After B1 merges:**

   ```bash
   git checkout chore/enhance-ci-validation
   git fetch origin
   git rebase origin/main

   # Regenerate lock file if conflicts occur
   poetry lock --no-update
   poetry install

   # Verify both dependency sets are present
   poetry show | grep -E "(trivy|hadolint|defusedxml)"
   ```

3. **If `pyproject.toml` conflicts:**
   - Preserve both dependency additions (B1's `defusedxml` + A3's CI tools)
   - Run `poetry lock` to regenerate lock file
   - Verify `poetry install` completes successfully

#### Trivy Configuration

Add Trivy scan to workflow with SARIF upload:

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: "namer:test"
    format: "sarif"
    output: "trivy-results.sarif"
    severity: "CRITICAL,HIGH"
  env:
    TRIVY_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

- name: Upload Trivy results to GitHub Security
  uses: github/codeql-action/upload-sarif@v2
  if: always()  # Upload even if Trivy finds issues
  with:
    sarif_file: "trivy-results.sarif"
```

**Why upload SARIF:**
- Vulnerabilities appear in GitHub Security tab
- Easier tracking and remediation
- Historical vulnerability tracking
- Integration with Dependabot alerts

**Severity Thresholds:**

- **CRITICAL:** Block merge
- **HIGH:** Block merge
- **MEDIUM:** Warn only (visible in Security tab)
- **LOW:** Ignore

#### Dockerfile Improvements

Hadolint may flag issues in the existing Dockerfile. Common fixes:

```dockerfile
# Before
RUN apt-get update && apt-get install -y python3

# After (pin versions, use --no-install-recommends)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3=3.11.* && \
    rm -rf /var/lib/apt/lists/*
```

#### Testing Strategy

1. **Local Trivy scan:**

   ```bash
   docker build -t namer:test .
   trivy image namer:test
   ```

2. **Local Hadolint:**

   ```bash
   docker run --rm -i hadolint/hadolint < Dockerfile
   ```

3. **Verify dependency updates:**

   ```bash
   poetry install
   poetry run pytest
   ```

**Expected Results:**

- Trivy: No CRITICAL/HIGH vulnerabilities in base image
- Hadolint: All warnings addressed or suppressed with inline comments
- Tests: All pass with updated dependencies

---

### **A4: Simplify CI workflow** (OPTIONAL)

**Priority:** Low
**Complexity:** Medium
**Estimated Time:** 2-4 hours

#### Decision Point

**SKIP A4 if:**

- [ ] A2 and A3 already removed the exact lines A4 would delete
- [ ] Workflow file is <200 lines after A3 merge
- [ ] No duplicate job definitions exist in workflow

**PROCEED with A4 if:**

- [ ] Lines from commit `8e90cc3` still present in `.github/workflows/pr-validate.yml`
- [ ] Duplicate job steps identified (e.g., multiple lint/test definitions)
- [ ] Workflow file >250 lines after A3 merge

#### What You're Removing

Commit `8e90cc3` removes 81 lines of redundant workflow configuration. Common candidates:

- Duplicate `poetry install` steps
- Redundant cache configurations
- Unused environment variables

#### Validation

Before starting A4:

```bash
# Check current workflow line count
wc -l .github/workflows/pr-validate.yml

# Identify duplicate steps
grep -n "poetry install" .github/workflows/pr-validate.yml
grep -n "actions/cache" .github/workflows/pr-validate.yml
```

**If duplicates found:** Proceed with A4
**If workflow is clean:** Skip A4 and document decision in GitHub discussion

---

## Workflow Tips

### Daily Routine

1. **Morning:** Check CI status on `main`

   ```bash
   gh run list --workflow=pr-validate.yml --branch=main --limit=5
   ```

2. **Before starting PR:** Sync with latest `main`

   ```bash
   git checkout main
   git pull origin main
   git checkout -b <branch-name>
   ```

3. **After PR creation:** Monitor CI closely for first run
   - Watch for new tool installation failures
   - Check artifact uploads succeed
   - Verify logs are readable

### Common Pitfalls

#### 1. **Shell Tooling Installation Failures**

**Symptom:** `shfmt` or `shellcheck` not found in CI

**Solution:**

```yaml
- name: Install shell tooling
  run: |
    set -e  # Fail fast on errors
    wget -qO /usr/local/bin/shfmt https://github.com/mvdan/sh/releases/download/v3.8.0/shfmt_v3.8.0_linux_amd64
    chmod +x /usr/local/bin/shfmt
    shfmt --version  # Verify installation
```

#### 2. **Trivy Rate Limiting**

**Symptom:** Trivy fails with "API rate limit exceeded"

**Solution:**

```yaml
env:
  TRIVY_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### 3. **Artifact Upload Failures**

**Symptom:** "Artifact path not found" errors

**Solution:** Always create log files even if tools pass:

```yaml
- name: mypy check
  run: |
    poetry run mypy namer/ | tee mypy.log || echo "mypy failed" >> mypy.log
```

### Communication Protocol

**When to post in `#migration-ambiguity-review`:**

- ✅ A1 merged (foundation complete)
- ✅ A2 merged (static analysis live)
- ✅ A3 blocked by B1 (coordinate with Backend-1)
- ✅ A4 decision made (skip or proceed)

**When to escalate:**

- CI runtime exceeds 7 minutes after A2/A3
- Trivy finds CRITICAL vulnerabilities in base image
- Hadolint requires Dockerfile changes >20 lines

---

## Testing Checklist

Before merging each PR:

### A1

- [ ] Hadolint action runs with pinned SHA
- [ ] No change in Dockerfile linting results
- [ ] CI completes in same time as before

### A2

- [ ] All 4 static analysis tools install successfully
- [ ] Logs uploaded as artifacts
- [ ] `continue-on-error: true` prevents blocking
- [ ] Workflow file passes YAML validation

### A3

- [ ] Trivy scans Docker image
- [ ] Hadolint lints Dockerfile
- [ ] Dependencies install cleanly after rebase on B1
- [ ] No new CRITICAL/HIGH vulnerabilities introduced

### A4 (if applicable)

- [ ] Workflow line count reduced by ~80 lines
- [ ] No duplicate steps remain
- [ ] All jobs still execute correctly
- [ ] CI runtime unchanged or improved

---

## Rollback Procedures

### Individual PR Rollback

```bash
# Identify merge commit
git log --oneline --merges main | grep "A[1-4]"

# Revert
git revert -m 1 <merge-commit-sha>
git push origin main
```

### Coordinated Rollback (A2+A3)

If A3 introduces breaking changes that require reverting A2:

```bash
git revert -m 1 <a3-merge-sha>
git revert -m 1 <a2-merge-sha>
git push origin main
```

**Post-Rollback:**

- Notify team in `#migration-ambiguity-review`
- Document root cause in GitHub issue
- Update migration timeline

---

## Success Criteria

- ✅ All 4 PRs merged by end of Week 2
- ✅ CI pipeline includes static analysis and security scanning
- ✅ Zero production incidents from CI changes
- ✅ Workflow file is maintainable (<250 lines)
- ✅ New tools catch at least 1 real issue in future PRs

---

## Resources

- **Migration Plan:** [migration-plan-fix-ambiguity-review.md](migration-plan-fix-ambiguity-review.md)
- **Delivery Plan:** [delivery-plan-fix-ambiguity-review.md](delivery-plan-fix-ambiguity-review.md)
- **Migration Utilities:** [migration-utilities.md](migration-utilities.md) - Cherry-pick helper, time tracking, coverage comparison
- **Source Commits:** `fix/ambiguity-review` branch
- **CI Workflow:** `.github/workflows/pr-validate.yml`

---

**Workstream Owner:** DevOps Engineer
**Last Updated:** 2025-10-06
**Status:** Ready to Start
