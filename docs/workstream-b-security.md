# Workstream B: Security & Dependencies

**Owner:** Security/Backend Engineer  
**Timeline:** Week 1-2  
**Total PRs:** 3 (B1, B2, B3)  
**Status:** Independent (minimal cross-workstream dependencies)

---

## Mission Statement

Enhance application security by introducing XML exploit protection, replacing weak randomness with cryptographic alternatives, and improving configuration management hygiene.

---

## Goals & Objectives

### Primary Goals

1. **Add `defusedxml` dependency** to protect against XML bomb/entity expansion attacks
2. **Replace `random` with `secrets`** for cryptographically secure temporary filename generation
3. **Extract hardcoded tokens** into named constants for better maintainability and security auditing

### Success Metrics

- ✅ All 3 PRs merged by end of Week 1
- ✅ Zero security regressions introduced
- ✅ `bandit` security scan passes with no new HIGH/CRITICAL findings
- ✅ All temporary files use cryptographically secure randomness

---

## First Day Checklist

**Complete before writing any code:**

- [ ] Read [migration-plan-fix-ambiguity-review.md](migration-plan-fix-ambiguity-review.md)
- [ ] Read [delivery-plan-fix-ambiguity-review.md](delivery-plan-fix-ambiguity-review.md)
- [ ] Read [migration-utilities.md](migration-utilities.md)
- [ ] Read this workstream doc completely
- [ ] Run pre-migration validation from migration plan
- [ ] Establish test coverage baseline: `poetry run pytest --cov=namer --cov-report=term | tee coverage-baseline.txt`
- [ ] Install migration utilities: `chmod +x scripts/*.sh`
- [ ] Join Slack channel: `#migration-ambiguity-review`
- [ ] Introduce yourself to team, identify backup reviewer
- [ ] Review source commits:
  ```bash
  git checkout fix/ambiguity-review
  git log --oneline main..fix/ambiguity-review | grep -E "(260e27d)"
  git show 260e27d  # All B-workstream changes
  ```

**Ready to start when all boxes checked.**

---

## PR Template

Use this template for all Workstream B PRs:

````markdown
## Migration PR: [Workstream B] - [PR ID]

### Source Information
- **Branch:** `fix/ambiguity-review`
- **Commit SHA:** `260e27d`
- **Cherry-pick command:** `git cherry-pick -n 260e27d`

### Changes
- List of files changed
- Brief description of what changed in each file

### Testing
- [ ] Unit tests pass: `poetry run pytest`
- [ ] Security scan passes: `poetry run bandit -r namer/`
- [ ] Linting passes: `poetry run ruff check .`
- [ ] Coverage maintained: `./scripts/compare-coverage.sh`
- [ ] Smoke test executed: `./scripts/smoke-test.sh B <PR-ID>`

### Dependencies
- **Blocks:** [PR IDs that depend on this]
- **Blocked by:** [PR IDs this depends on]

### Security Impact
- [ ] No new HIGH/CRITICAL bandit findings
- [ ] No hardcoded secrets introduced
- [ ] Dependencies scanned for known vulnerabilities

### Review Checklist
- [ ] Only relevant files from cherry-pick included
- [ ] No unintended changes
- [ ] All tests green
- [ ] Security best practices followed
````

---

## PR Breakdown

### **B1: Add defusedxml dependency**

**Priority:** High (blocks A3)  
**Complexity:** Low  
**Estimated Time:** 1-2 hours

#### What You're Adding

```toml
# pyproject.toml
[tool.poetry.dependencies]
defusedxml = "^0.7.1"
```

#### Why This Matters

**Vulnerability:** Standard `xml.etree.ElementTree` is vulnerable to:
- **Billion Laughs Attack:** Exponential entity expansion consumes memory
- **External Entity Injection:** Reads arbitrary files from server
- **DTD Retrieval:** Triggers SSRF attacks

**Solution:** `defusedxml` provides drop-in replacements that disable dangerous features by default.

#### Implementation Notes

**This PR only adds the dependency.** Actual usage will be implemented in future PRs outside this migration (not part of `fix/ambiguity-review`).

#### Validation Steps

```bash
# Add dependency
poetry add defusedxml

# Verify installation
poetry show defusedxml

# Run tests to ensure no regressions
poetry run pytest

# Check for security issues
poetry run bandit -r namer/
```

**Expected Output:**
- `defusedxml` appears in `poetry.lock`
- All tests pass
- No new bandit warnings

#### Coordination with A3

**⚠️ CRITICAL:** A3 also modifies `poetry.lock` and `pyproject.toml`

**Merge Order:** B1 → A3

**After B1 merges:**
- Notify DevOps engineer in `#migration-ambiguity-review`
- DevOps engineer rebases A3 on updated `main`
- Verify both dependency sets present after rebase

---

### **B2: Replace random with secrets for temp filenames**

**Priority:** High  
**Complexity:** Low  
**Estimated Time:** 2-3 hours

#### What You're Changing

**Files:** `namer/ffmpeg.py`, `namer/ffmpeg_enhanced.py`

**Before:**
```python
import random
import string

temp_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
```

**After:**
```python
import secrets
import string

temp_filename = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
```

#### Why This Matters

**Security Issue:** `random.choices()` uses a Mersenne Twister PRNG, which is:
- **Predictable:** State can be recovered from 624 consecutive outputs
- **Not cryptographically secure:** Unsuitable for security-sensitive operations

**Impact:** Temporary filenames could be guessed by attackers, leading to:
- Race condition exploits (TOCTOU)
- Unauthorized file access
- Denial of service via filename collisions

**Solution:** `secrets.choice()` uses OS-provided randomness (e.g., `/dev/urandom`), which is:
- **Unpredictable:** Cryptographically secure random number generator
- **Suitable for security:** Designed for tokens, passwords, and sensitive data

#### Implementation Strategy

1. **Find all usages of `random.choices()` in ffmpeg files:**
   ```bash
   grep -n "random.choices" namer/ffmpeg*.py
   ```

2. **Replace with `secrets.choice()` pattern:**
   ```python
   # Old pattern
   random.choices(charset, k=length)
   
   # New pattern
   ''.join(secrets.choice(charset) for _ in range(length))
   ```

3. **Update imports:**
   ```python
   # Remove
   import random
   
   # Add
   import secrets
   ```

#### Testing

**Unit Tests:**
```python
# Verify randomness distribution (statistical test)
def test_temp_filename_randomness():
    filenames = [generate_temp_filename() for _ in range(1000)]
    unique_filenames = set(filenames)
    
    # Should have high uniqueness (>99%)
    assert len(unique_filenames) / len(filenames) > 0.99
    
    # Should be 16 characters
    assert all(len(f) == 16 for f in filenames)
```

**Manual Verification:**
```bash
# Generate temp files and inspect
poetry run python -c "
from namer.ffmpeg import generate_temp_filename
for _ in range(10):
    print(generate_temp_filename())
"
```

**Expected Output:** 10 unique 16-character alphanumeric strings

#### Security Validation

```bash
# Run bandit to confirm no weak randomness warnings
poetry run bandit -r namer/ffmpeg*.py | grep -i random

# Should output: No issues found
```

---

### **B3: Replace hardcoded token placeholders with constants**

**Priority:** Medium  
**Complexity:** Low  
**Estimated Time:** 2-3 hours

#### What You're Changing

**Files:**
- `namer/configuration.py`
- `namer/configuration_utils.py`
- `namer/videophash/videophashstash.py`

**Before:**
```python
if token == "YOUR_TOKEN_HERE":
    raise ValueError("Please set your API token")
```

**After:**
```python
# At module level
PLACEHOLDER_TOKEN = "YOUR_TOKEN_HERE"

# In validation logic
if token == PLACEHOLDER_TOKEN:
    raise ValueError("Please set your API token")
```

#### Why This Matters

**Maintainability:**
- **Single source of truth:** Change placeholder format in one place
- **Easier auditing:** Grep for `PLACEHOLDER_TOKEN` to find all validation points
- **Reduced typos:** No risk of mistyping the placeholder string

**Security:**
- **Clearer intent:** Constants signal "this is a sentinel value, not a real token"
- **Easier scanning:** Security tools can flag hardcoded strings more easily

#### Implementation Strategy

1. **Define constants in `configuration.py`:**
   ```python
   # Sentinel values for configuration validation
   PLACEHOLDER_TOKEN = "YOUR_TOKEN_HERE"
   PLACEHOLDER_API_KEY = "YOUR_API_KEY_HERE"
   ```

2. **Import and use in validation logic:**
   ```python
   from namer.configuration import PLACEHOLDER_TOKEN
   
   if stash_token == PLACEHOLDER_TOKEN:
       logger.error("Stash token not configured")
   ```

3. **Update error messages to reference constants:**
   ```python
   raise ValueError(
       f"API token is still set to placeholder: {PLACEHOLDER_TOKEN}. "
       "Please configure a real token."
   )
   ```

#### Files to Update

**`namer/configuration.py`:**
- Define `PLACEHOLDER_TOKEN` constant
- Replace hardcoded "YOUR_TOKEN_HERE" in validation

**`namer/configuration_utils.py`:**
- Import `PLACEHOLDER_TOKEN`
- Replace hardcoded placeholders in config loading

**`namer/videophash/videophashstash.py`:**
- Import `PLACEHOLDER_TOKEN`
- Replace hardcoded placeholders in Stash API client initialization

#### Testing

**Unit Tests:**
```python
def test_placeholder_token_validation():
    from namer.configuration import PLACEHOLDER_TOKEN
    
    # Should reject placeholder
    with pytest.raises(ValueError, match="Please set your API token"):
        validate_token(PLACEHOLDER_TOKEN)
    
    # Should accept real token
    validate_token("real_token_abc123")  # Should not raise
```

**Integration Test:**
```bash
# Verify error messages are clear
poetry run namer --config /tmp/test-config.cfg 2>&1 | grep "PLACEHOLDER"

# Should output helpful error message
```

#### Security Validation

```bash
# Ensure no hardcoded secrets remain
poetry run bandit -r namer/ | grep -i "hardcoded"

# Should only flag the new constants (which are intentional placeholders)
```

---

## Workflow Tips

### Daily Routine

1. **Morning:** Check for security advisories
   ```bash
   poetry show --outdated | grep -i security
   ```

2. **Before starting PR:** Run security scan baseline
   ```bash
   poetry run bandit -r namer/ -f json -o bandit-baseline.json
   ```

3. **After changes:** Compare security scan results
   ```bash
   poetry run bandit -r namer/ -f json -o bandit-current.json
   diff bandit-baseline.json bandit-current.json
   ```

### Common Pitfalls

#### 1. **Import Order Issues**

**Symptom:** `ruff` complains about import order after adding `secrets`

**Solution:** Follow PEP 8 import order:
```python
# Standard library
import secrets
import string

# Third-party
import requests

# Local
from namer.configuration import PLACEHOLDER_TOKEN
```

#### 2. **Performance Concerns with `secrets.choice()`**

**Symptom:** Slower temp filename generation

**Reality:** Negligible impact for 16-character strings
```python
# Benchmark (run 10,000 iterations)
import timeit

# random.choices (old)
timeit.timeit(
    "random.choices(string.ascii_letters, k=16)",
    setup="import random, string",
    number=10000
)  # ~0.05 seconds

# secrets.choice (new)
timeit.timeit(
    "''.join(secrets.choice(string.ascii_letters) for _ in range(16))",
    setup="import secrets, string",
    number=10000
)  # ~0.08 seconds
```

**Verdict:** 0.03s difference for 10,000 filenames is acceptable for security gain.

#### 3. **Constant Naming Conflicts**

**Symptom:** `PLACEHOLDER_TOKEN` already exists in another module

**Solution:** Use module-qualified imports:
```python
from namer.configuration import PLACEHOLDER_TOKEN as CONFIG_PLACEHOLDER
```

### Communication Protocol

**When to post in `#migration-ambiguity-review`:**

- ✅ B1 merged (notify DevOps for A3 rebase)
- ✅ B2 merged (security improvement live)
- ✅ B3 merged (workstream complete)

**When to escalate:**

- `bandit` reports new HIGH/CRITICAL findings after changes
- `secrets` module not available (Python <3.6)
- Constant naming conflicts with existing code

---

## Testing Checklist

Before merging each PR:

### B1
- [ ] `defusedxml` in `poetry.lock`
- [ ] `poetry install` succeeds
- [ ] All tests pass
- [ ] No new bandit warnings
- [ ] DevOps engineer notified for A3 coordination

### B2
- [ ] All `random.choices()` replaced with `secrets.choice()`
- [ ] Imports updated (`import secrets` added, `import random` removed)
- [ ] Temp filenames still 16 characters alphanumeric
- [ ] No bandit warnings about weak randomness
- [ ] Performance impact <10% (if measured)

### B3
- [ ] Constants defined in `configuration.py`
- [ ] All hardcoded placeholders replaced
- [ ] Error messages reference constants
- [ ] No hardcoded secrets flagged by bandit (except intentional placeholders)
- [ ] Config validation tests pass

---

## Rollback Procedures

### Individual PR Rollback

```bash
# Identify merge commit
git log --oneline --merges main | grep "B[1-3]"

# Revert
git revert -m 1 <merge-commit-sha>
git push origin main
```

### Coordinated Rollback (B1+A3)

If A3 merge fails due to dependency conflicts:

1. **Revert A3 first:**
   ```bash
   git revert -m 1 <a3-merge-sha>
   ```

2. **Optionally revert B1** (if defusedxml causes issues):
   ```bash
   git revert -m 1 <b1-merge-sha>
   ```

3. **Notify team and reschedule B1→A3 merge**

---

## Success Criteria

- ✅ All 3 PRs merged by end of Week 1
- ✅ `defusedxml` available for future XML parsing
- ✅ All temporary filenames use cryptographically secure randomness
- ✅ Configuration constants improve code maintainability
- ✅ Zero security regressions (bandit clean)

---

## Security Best Practices

### Code Review Focus

When reviewing security PRs, check for:

1. **No new hardcoded secrets:**
   ```bash
   grep -ri "password\|token\|api_key" namer/ | grep -v PLACEHOLDER
   ```

2. **Proper error handling:**
   ```python
   # Bad: Leaks sensitive info
   except Exception as e:
       logger.error(f"Failed with token: {token}")
   
   # Good: Generic error
   except Exception as e:
       logger.error("Authentication failed")
   ```

3. **Input validation:**
   ```python
   # Always validate before using
   if not token or token == PLACEHOLDER_TOKEN:
       raise ValueError("Invalid token")
   ```

### Post-Merge Monitoring

After each PR merges, monitor for:

- **Error rate spikes** (indicates validation too strict)
- **Performance degradation** (unlikely but check)
- **Security scan failures** in subsequent PRs

---

## Post-Migration: defusedxml Usage Tracking

**After all PRs merge, ensure defusedxml gets used:**

### Follow-Up Issue

Create issue: `Replace xml.etree with defusedxml in production code`

**Tracking:**
```bash
# Identify vulnerable XML usage
grep -rn "xml.etree.ElementTree" namer/

# Should be replaced with:
# from defusedxml.ElementTree import parse
```

**Assign to:** Security engineer
**Target:** Within 1 sprint of migration completion
**Priority:** High

---

## Resources

- **Migration Plan:** [migration-plan-fix-ambiguity-review.md](migration-plan-fix-ambiguity-review.md)
- **Delivery Plan:** [delivery-plan-fix-ambiguity-review.md](delivery-plan-fix-ambiguity-review.md)
- **Migration Utilities:** [migration-utilities.md](migration-utilities.md) - Cherry-pick helper, time tracking, coverage comparison
- **Source Commits:** `fix/ambiguity-review` branch (commit `260e27d`)
- **Security Tools:** `bandit`, `trivy` (via Workstream A)

---

**Workstream Owner:** Security/Backend Engineer  
**Last Updated:** 2025-10-06  
**Status:** Ready to Start
