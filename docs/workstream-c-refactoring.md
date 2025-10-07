# Workstream C: Code Quality & Refactoring

**Owner:** Backend Engineer  
**Timeline:** Week 1-2  
**Total PRs:** 3 (C1, C2, C3)  
**Status:** Semi-Independent (C2 depends on C1; C3 is parallel)

---

## Mission Statement

Improve code maintainability and error diagnostics by consolidating directory creation logic, enhancing error context, and adding defensive path validation.

---

## Goals & Objectives

### Primary Goals

1. **Improve error logging** to provide actionable context when directory creation fails
2. **Refactor directory creation** into a shared utility function to reduce code duplication
3. **Add path validation** in watchdog to prevent processing invalid/missing files

### Success Metrics

- ✅ All 3 PRs merged by end of Week 2
- ✅ Directory creation logic consolidated into single function
- ✅ Error messages include full context (paths, permissions, disk space)
- ✅ Watchdog rejects invalid paths before processing

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
  git log --oneline main..fix/ambiguity-review | grep -E "(260e27d|34200fc|8d1fcd9)"
  git show 260e27d  # C1 changes
  git show 34200fc  # C2 changes
  git show 8d1fcd9  # C3 changes
  ```

**Ready to start when all boxes checked.**

---

## PR Template

Use this template for all Workstream C PRs:

````markdown
## Migration PR: [Workstream C] - [PR ID]

### Source Information
- **Branch:** `fix/ambiguity-review`
- **Commit SHA:** `[260e27d|34200fc|8d1fcd9]`
- **Cherry-pick command:** `git cherry-pick -n [SHA]`

### Changes
- List of files changed
- Brief description of what changed in each file

### Testing
- [ ] Unit tests pass: `poetry run pytest`
- [ ] Security scan passes: `poetry run bandit -r namer/`
- [ ] Linting passes: `poetry run ruff check .`
- [ ] Coverage maintained: `./scripts/compare-coverage.sh`
- [ ] Smoke test executed: `./scripts/smoke-test.sh C <PR-ID>`

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

### **C1: Improve error context in directory creation**

**Priority:** High (foundation for C2)  
**Complexity:** Low  
**Estimated Time:** 2-3 hours

#### What You're Changing

**Files:** `namer/command.py`, `namer/namer.py`

**Before:**
```python
try:
    os.makedirs(target_dir, exist_ok=True)
except OSError:
    logger.error("Failed to create directory")
```

**After:**
```python
try:
    os.makedirs(target_dir, exist_ok=True)
except OSError as e:
    logger.error(
        "Failed to create directory: %s (error: %s, errno: %s)",
        target_dir,
        e.strerror,
        e.errno
    )
    raise
```

#### Why This Matters

**Current Problem:** Generic error messages make debugging difficult:
- "Failed to create directory" → Which directory? Why did it fail?

**Improved Diagnostics:**
- "Failed to create directory: /media/ambiguous (error: Permission denied, errno: 13)"
- "Failed to create directory: /media/failed (error: No space left on device, errno: 28)"

#### Implementation Strategy

1. **Identify all `os.makedirs()` calls:**
   ```bash
   grep -n "os.makedirs" namer/command.py namer/namer.py
   ```

2. **Wrap each in try/except with enhanced logging:**
   ```python
   try:
       os.makedirs(directory, exist_ok=True)
   except OSError as e:
       logger.error(
           "Failed to create directory: %s (error: %s, errno: %s)",
           directory, e.strerror, e.errno
       )
       # Re-raise to preserve original behavior
       raise
   ```

3. **Add context for common errno values:**
   ```python
   import errno
   
   except OSError as e:
       if e.errno == errno.EACCES:
           logger.error("Permission denied creating %s", directory)
       elif e.errno == errno.ENOSPC:
           logger.error("No space left on device for %s", directory)
       else:
           logger.error("Failed to create %s: %s", directory, e)
       raise
   ```

#### Testing

**Unit Tests:**
```python
def test_directory_creation_error_logging(tmp_path, caplog):
    # Create read-only parent directory
    parent = tmp_path / "readonly"
    parent.mkdir()
    parent.chmod(0o444)
    
    # Attempt to create subdirectory
    with pytest.raises(OSError):
        create_directory(parent / "subdir")
    
    # Verify error message includes path and errno
    assert "Permission denied" in caplog.text
    assert str(parent / "subdir") in caplog.text
```

**Manual Testing:**
```bash
# Test permission denied
mkdir /tmp/test-readonly
chmod 444 /tmp/test-readonly
poetry run namer --target /tmp/test-readonly/subdir

# Expected: Error log with "Permission denied" and full path
```

---

### **C2: Refactor directory creation into shared utility**

**Priority:** High (blocks E1)  
**Complexity:** Medium  
**Estimated Time:** 4-6 hours

#### What You're Changing

**Files:** `namer/command.py`, `namer/moviexml.py`, `namer/namer.py`

**Before (duplicated across 3 files):**
```python
# namer/command.py
try:
    os.makedirs(target_dir, exist_ok=True)
except OSError as e:
    logger.error("Failed to create directory: %s", e)
    raise

# namer/namer.py
try:
    os.makedirs(failed_dir, exist_ok=True)
except OSError as e:
    logger.error("Failed to create directory: %s", e)
    raise

# namer/moviexml.py
try:
    os.makedirs(output_dir, exist_ok=True)
except OSError as e:
    logger.error("Failed to create directory: %s", e)
    raise
```

**After (single shared function):**
```python
# namer/utils.py (new file)
def ensure_directory(path: Path, description: str = "directory") -> None:
    """
    Create directory if it doesn't exist, with enhanced error logging.
    
    Args:
        path: Directory path to create
        description: Human-readable description for error messages
        
    Raises:
        OSError: If directory creation fails
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(
            "Failed to create %s: %s (error: %s, errno: %s)",
            description, path, e.strerror, e.errno
        )
        raise

# Usage in all files
from namer.utils import ensure_directory

ensure_directory(target_dir, "target directory")
ensure_directory(failed_dir, "failed files directory")
ensure_directory(output_dir, "XML output directory")
```

#### Why This Matters

**Code Duplication:** Same logic repeated 8+ times across codebase
**Inconsistent Error Handling:** Some locations log errors, others don't
**Maintenance Burden:** Bug fixes require updating multiple locations

**Benefits:**
- **DRY principle:** Single source of truth for directory creation
- **Consistent logging:** All directory creation uses same error format
- **Easier testing:** Test once, applies everywhere

#### Implementation Strategy

1. **Create `namer/utils.py`:**
   ```python
   """Shared utility functions for namer package."""
   import logging
   from pathlib import Path
   
   logger = logging.getLogger(__name__)
   
   def ensure_directory(path: Path, description: str = "directory") -> None:
       """Create directory with enhanced error logging."""
       try:
           path.mkdir(parents=True, exist_ok=True)
           logger.debug("Ensured %s exists: %s", description, path)
       except OSError as e:
           logger.error(
               "Failed to create %s: %s (error: %s, errno: %s)",
               description, path, e.strerror, e.errno
           )
           raise
   ```

2. **Replace all `os.makedirs()` calls:**
   ```bash
   # Find all occurrences
   grep -rn "os.makedirs\|Path.*mkdir" namer/command.py namer/moviexml.py namer/namer.py
   
   # Replace each with ensure_directory()
   ```

3. **Update imports:**
   ```python
   # Remove
   import os
   
   # Add
   from pathlib import Path
   from namer.utils import ensure_directory
   ```

#### Testing

**Unit Tests:**
```python
def test_ensure_directory_creates_path(tmp_path):
    target = tmp_path / "new" / "nested" / "dir"
    ensure_directory(target, "test directory")
    assert target.exists()
    assert target.is_dir()

def test_ensure_directory_idempotent(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    
    # Should not raise on existing directory
    ensure_directory(target, "test directory")
    assert target.exists()

def test_ensure_directory_logs_on_failure(tmp_path, caplog):
    readonly = tmp_path / "readonly"
    readonly.mkdir()
    readonly.chmod(0o444)
    
    with pytest.raises(OSError):
        ensure_directory(readonly / "subdir", "test directory")
    
    assert "Failed to create test directory" in caplog.text
```

**Integration Test:**
```bash
# Verify all directory creation uses new utility
grep -r "os.makedirs\|\.mkdir(" namer/ --exclude-dir=__pycache__

# Should only find:
# - namer/utils.py (the implementation)
# - Test files (allowed)
```

#### Migration Checklist

- [ ] Create `namer/utils.py` with `ensure_directory()`
- [ ] Replace `os.makedirs()` in `namer/command.py`
- [ ] Replace `os.makedirs()` in `namer/namer.py`
- [ ] Replace `os.makedirs()` in `namer/moviexml.py`
- [ ] Update imports in all 3 files
- [ ] Run tests: `poetry run pytest test/namer_test.py test/command_test.py`
- [ ] Verify no `os.makedirs()` remain (except in utils.py)

---

### **C3: Improve file path validation in watchdog**

**Priority:** Medium  
**Complexity:** Low  
**Estimated Time:** 2-3 hours

#### What You're Changing

**Files:** `namer/watchdog.py`

**Before:**
```python
def on_created(self, event):
    file_path = Path(event.src_path)
    # Immediately process without validation
    self.process_file(file_path)
```

**After:**
```python
def on_created(self, event):
    file_path = Path(event.src_path)
    
    # Validate path before processing
    if not file_path.exists():
        logger.warning("Skipping non-existent file: %s", file_path)
        return
    
    if not file_path.is_file():
        logger.debug("Skipping non-file path: %s", file_path)
        return
    
    self.process_file(file_path)
```

#### Why This Matters

**Race Conditions:** File may be deleted between event trigger and processing
**Invalid Events:** Watchdog may trigger on directories, symlinks, etc.
**Error Propagation:** Processing invalid paths causes cascading failures

**Benefits:**
- **Defensive programming:** Fail fast on invalid inputs
- **Better logging:** Clear messages for skipped files
- **Reduced errors:** Prevents downstream exceptions

#### Implementation Strategy

1. **Add validation helper:**
   ```python
   def _is_valid_video_file(self, path: Path) -> bool:
       """Check if path is a valid video file for processing."""
       if not path.exists():
           logger.warning("Path does not exist: %s", path)
           return False
       
       if not path.is_file():
           logger.debug("Path is not a file: %s", path)
           return False
       
       if path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
           logger.debug("Unsupported file type: %s", path)
           return False
       
       return True
   ```

2. **Use in event handlers:**
   ```python
   def on_created(self, event):
       file_path = Path(event.src_path)
       if self._is_valid_video_file(file_path):
           self.process_file(file_path)
   
   def on_modified(self, event):
       file_path = Path(event.src_path)
       if self._is_valid_video_file(file_path):
           self.process_file(file_path)
   ```

#### Testing

**Unit Tests:**
```python
def test_watchdog_skips_nonexistent_file(tmp_path, caplog):
    watchdog = FileWatchdog(tmp_path)
    fake_event = FileCreatedEvent(str(tmp_path / "missing.mp4"))
    
    watchdog.on_created(fake_event)
    
    assert "Path does not exist" in caplog.text
    assert not watchdog.processed_files  # Nothing processed

def test_watchdog_skips_directory(tmp_path, caplog):
    subdir = tmp_path / "videos"
    subdir.mkdir()
    
    watchdog = FileWatchdog(tmp_path)
    fake_event = FileCreatedEvent(str(subdir))
    
    watchdog.on_created(fake_event)
    
    assert "Path is not a file" in caplog.text
```

**Integration Test:**
```bash
# Start watchdog in test mode
poetry run namer --watch /tmp/test-watch &
NAMER_PID=$!

# Create invalid paths
mkdir /tmp/test-watch/subdir
touch /tmp/test-watch/invalid.txt

# Create valid video
cp test/fixtures/sample.mp4 /tmp/test-watch/

# Check logs
kill $NAMER_PID
grep "Skipping" /tmp/namer.log

# Should skip directory and .txt file, process .mp4
```

---

## Workflow Tips

### Daily Routine

1. **Morning:** Check for C1 merge status
   ```bash
   gh pr view <c1-pr-number> --json state,mergedAt
   ```

2. **After C1 merges:** Immediately start C2
   ```bash
   git checkout main
   git pull origin main
   git checkout -b refactor/consolidate-directory-creation
   ```

3. **C3 can start anytime** (parallel with C1/C2)

### Common Pitfalls

#### 1. **Circular Import with `namer.utils`**

**Symptom:** `ImportError: cannot import name 'ensure_directory' from partially initialized module`

**Solution:** Keep `utils.py` dependency-free:
```python
# namer/utils.py - NO imports from namer.* modules
import logging
from pathlib import Path

# OK
logger = logging.getLogger(__name__)
```

**Why Circular Imports Happen:**

Circular imports occur when two or more modules depend on each other, creating a cycle in the import graph. Python imports modules by executing them top-to-bottom, so if Module A tries to import Module B while Module B is trying to import Module A, one of them will be only partially initialized.

**Example of a Circular Import:**

```python
# namer/utils.py (BAD - creates circular import)
from namer.configuration import get_config  # Imports configuration

def ensure_directory(path: Path, description: str = "directory") -> None:
    config = get_config()  # Uses configuration
    # ... directory creation logic

# namer/configuration.py (BAD - creates circular import)
from namer.utils import ensure_directory  # Imports utils

def get_config():
    ensure_directory(CONFIG_DIR, "config directory")  # Uses utils
    # ... config loading logic
```

**Result:** `ImportError` because:
1. `utils.py` starts importing `configuration.py`
2. `configuration.py` tries to import `utils.py` (but it's not finished yet)
3. Python finds `utils.py` only partially initialized
4. Import fails

**How to Avoid Circular Imports:**

1. **Keep utility modules dependency-free:**
   ```python
   # namer/utils.py (GOOD - no namer.* imports)
   import logging
   from pathlib import Path

   def ensure_directory(path: Path, description: str = "directory") -> None:
       """Pure utility - no dependencies on other namer modules."""
       try:
           path.mkdir(parents=True, exist_ok=True)
           logger.debug("Ensured %s exists: %s", description, path)
       except OSError as e:
           logger.error("Failed to create %s: %s", description, e)
           raise
   ```

2. **Use dependency injection instead of imports:**
   ```python
   # namer/configuration.py (GOOD - pass directory creator as argument)
   def get_config(ensure_dir_func=None):
       if ensure_dir_func:
           ensure_dir_func(CONFIG_DIR, "config directory")
       # ... config loading logic

   # Usage in namer/command.py
   from namer.utils import ensure_directory
   from namer.configuration import get_config

   config = get_config(ensure_dir_func=ensure_directory)
   ```

3. **Move imports inside functions (lazy import):**
   ```python
   # namer/configuration.py (GOOD - import only when needed)
   def get_config():
       from namer.utils import ensure_directory  # Import inside function
       ensure_directory(CONFIG_DIR, "config directory")
       # ... config loading logic
   ```

4. **Restructure code to break the cycle:**
   ```python
   # namer/constants.py (NEW - shared constants, no imports)
   from pathlib import Path

   CONFIG_DIR = Path.home() / ".namer"

   # namer/utils.py (GOOD - no imports from namer.configuration)
   def ensure_directory(path: Path, description: str = "directory") -> None:
       # ... directory creation logic

   # namer/configuration.py (GOOD - no imports from namer.utils)
   from namer.constants import CONFIG_DIR

   def get_config():
       # Create directory directly here, or use lazy import
       # ... config loading logic
   ```

**Testing for Circular Imports:**

```bash
# Check import graph for cycles
poetry run python -c "import namer.utils"  # Should succeed immediately
poetry run python -c "import namer.configuration"  # Should succeed immediately

# Use pydeps to visualize dependencies
pip install pydeps
pydeps namer/ --max-bacon=2 --cluster
# Look for cycles in the generated graph
```

#### 2. **Path vs. String Confusion**

**Symptom:** `TypeError: expected str, bytes or os.PathLike object, not Path`

**Solution:** Ensure consistent Path usage:
```python
# Convert strings to Path early
file_path = Path(event.src_path)

# Use Path methods
if file_path.exists() and file_path.is_file():
    ...
```

#### 3. **Overly Aggressive Validation**

**Symptom:** Watchdog skips valid files due to strict checks

**Solution:** Log at appropriate levels:
```python
# DEBUG for expected skips (directories, temp files)
logger.debug("Skipping directory: %s", path)

# WARNING for unexpected skips (missing files)
logger.warning("File disappeared before processing: %s", path)
```

### Communication Protocol

**When to post in `#migration-ambiguity-review`:**

- ✅ C1 merged (start C2)
- ✅ C2 merged (notify E1 engineer - blocker removed)
- ✅ C3 merged (workstream complete)

**When to escalate:**

- C2 introduces circular imports
- Tests fail after refactoring (logic changed unintentionally)
- E1 engineer blocked >1 day waiting for C2

---

## Testing Checklist

Before merging each PR:

### C1
- [ ] All `os.makedirs()` wrapped in try/except
- [ ] Error messages include path, strerror, and errno
- [ ] Tests verify enhanced error logging
- [ ] No change in behavior (only logging improved)

### C2
- [ ] `namer/utils.py` created with `ensure_directory()`
- [ ] All directory creation uses `ensure_directory()`
- [ ] No `os.makedirs()` remain (except in utils.py and tests)
- [ ] No circular imports
- [ ] All tests pass (especially `test/namer_test.py`)

### C3
- [ ] Watchdog validates paths before processing
- [ ] Invalid paths logged appropriately
- [ ] No valid files skipped incorrectly
- [ ] Tests cover race conditions (file deleted mid-processing)

---

## Rollback Procedures

### Individual PR Rollback

```bash
git revert -m 1 <merge-commit-sha>
git push origin main
```

### Coordinated Rollback (C1+C2)

If C2 introduces bugs:

```bash
# Revert C2 first
git revert -m 1 <c2-merge-sha>

# Optionally revert C1 if error logging causes issues
git revert -m 1 <c1-merge-sha>

git push origin main
```

**Post-Rollback:**
- Notify E1 engineer (C2 rollback unblocks them)
- Document root cause
- Fix and re-submit

---

## Success Criteria

- ✅ All 3 PRs merged by end of Week 2
- ✅ Directory creation logic consolidated (C2)
- ✅ Error messages include actionable context (C1)
- ✅ Watchdog rejects invalid paths gracefully (C3)
- ✅ Zero regressions in directory creation behavior

---

## Resources

- **Migration Plan:** [migration-plan-fix-ambiguity-review.md](migration-plan-fix-ambiguity-review.md)
- **Delivery Plan:** [delivery-plan-fix-ambiguity-review.md](delivery-plan-fix-ambiguity-review.md)
- **Migration Utilities:** [migration-utilities.md](migration-utilities.md) - Cherry-pick helper, time tracking, coverage comparison
- **Source Commits:** `fix/ambiguity-review` (commits `260e27d`, `34200fc`, `8d1fcd9`)
- **Related Workstreams:** E (depends on C2)

---

**Workstream Owner:** Backend Engineer 2  
**Last Updated:** 2025-10-06  
**Status:** Ready to Start
