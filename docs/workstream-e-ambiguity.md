# Workstream E: Ambiguity Handling

**Owner:** Backend Engineer
**Timeline:** Week 2-3
**Total PRs:** 3 (E1, E2, E3)
**Status:** Depends on C2 (E1 blocked until C2 merges; E2 parallel)

---

## Mission Statement

Enhance the ambiguous file routing system to provide better user experience when multiple metadata matches are found, with improved directory handling and workflow validation.

---

## Goals & Objectives

### Primary Goals

1. **Improve ambiguous file directory handling** to use refactored directory creation utility
2. **Enhance watchdog event processing** for better file event filtering and logging
3. **Add workflow validation** to ensure ambiguous file handling works correctly in CI

### Success Metrics

- ✅ All 3 PRs merged by end of Week 3
- ✅ Ambiguous files route to correct directory 100% of the time
- ✅ Watchdog processes only valid file events
- ✅ CI validates ambiguous file workflow

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
  git log --oneline main..fix/ambiguity-review | grep -E "(fa96678|f4361a2)"
  git show fa96678  # E1 and E2 changes
  git show f4361a2  # E3 changes
  ```

**Ready to start when all boxes checked.**

---

## PR Template

Use this template for all Workstream E PRs:

````markdown
## Migration PR: [Workstream E] - [PR ID]

### Source Information
- **Branch:** `fix/ambiguity-review`
- **Commit SHA:** `[fa96678|f4361a2]`
- **Cherry-pick command:** `git cherry-pick -n [SHA]`

### Changes
- List of files changed
- Brief description of what changed in each file

### Testing
- [ ] Unit tests pass: `poetry run pytest`
- [ ] Security scan passes: `poetry run bandit -r namer/`
- [ ] Linting passes: `poetry run ruff check .`
- [ ] Coverage maintained: `./scripts/compare-coverage.sh`
- [ ] Smoke test executed: `./scripts/smoke-test.sh E <PR-ID>`

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

### **E1: Improve ambiguous file directory handling**

**Priority:** High
**Complexity:** Medium
**Estimated Time:** 4-6 hours
**⚠️ BLOCKED BY:** C2 (refactor directory creation)

#### What You're Changing

**Files:** `namer/namer.py`

**Before:**

```python
# Duplicated directory creation logic
ambiguous_dir = Path(config.ambiguous_dir)
try:
    os.makedirs(ambiguous_dir, exist_ok=True)
except OSError as e:
    logger.error("Failed to create ambiguous directory: %s", e)
    raise

# Move file to ambiguous directory
shutil.move(file_path, ambiguous_dir / file_path.name)
```

**After:**

```python
# Use shared utility from C2
from namer.utils import ensure_directory

ambiguous_dir = Path(config.ambiguous_dir)
ensure_directory(ambiguous_dir, "ambiguous files directory")

# Enhanced move logic with conflict resolution
target_path = ambiguous_dir / file_path.name

if target_path.exists():
    # Handle filename conflicts
    base_name = file_path.stem
    suffix = file_path.suffix
    counter = 1

    while target_path.exists():
        target_path = ambiguous_dir / f"{base_name}_{counter}{suffix}"
        counter += 1

    logger.info("Renamed to avoid conflict: %s", target_path.name)

shutil.move(file_path, target_path)
logger.info("Moved ambiguous file to: %s", target_path)
```

#### Why This Matters

**Current Problem:**

- Duplicated directory creation logic (fixed by C2 dependency)
- No handling of filename conflicts in ambiguous directory
- Minimal logging makes troubleshooting difficult

**Improvements:**

- **Reuses C2 utility:** Consistent error handling across codebase
- **Conflict resolution:** Prevents overwriting existing ambiguous files
- **Better logging:** Track all ambiguous file movements

#### Implementation Strategy

1. **Wait for C2 to merge:**

   ```bash
   # Monitor C2 PR status
   gh pr view <c2-pr-number> --json state,mergedAt

   # After C2 merges, start E1
   git checkout main
   git pull origin main
   git checkout -b feat/improve-ambiguous-handling
   ```

2. **Import and use `ensure_directory`:**

   ```python
   from namer.utils import ensure_directory

   # Replace all ambiguous directory creation
   ensure_directory(ambiguous_dir, "ambiguous files directory")
   ```

3. **Add conflict resolution logic:**

   ```python
   def move_to_ambiguous_directory(
       file_path: Path,
       ambiguous_dir: Path,
       timeout: int = 30
   ) -> Path:
       """
       Move file to ambiguous directory with conflict resolution.

       Args:
           file_path: Path to file to move
           ambiguous_dir: Target directory for ambiguous files
           timeout: Maximum seconds to wait for file operations (default: 30)

       Returns:
           Final path where file was moved

       Raises:
           TimeoutError: If operation exceeds timeout
           FileExistsError: If cannot resolve filename conflict
       """
       import time
       start_time = time.time()

       def check_timeout():
           """Check if operation has exceeded timeout."""
           if time.time() - start_time > timeout:
               raise TimeoutError(
                   f"Operation timed out after {timeout}s moving {file_path.name}"
               )

       ensure_directory(ambiguous_dir, "ambiguous files directory")
       check_timeout()

       target_path = ambiguous_dir / file_path.name

       # Handle filename conflicts
       if target_path.exists():
           base_name = file_path.stem
           suffix = file_path.suffix
           counter = 1
           max_attempts = 1000

           while target_path.exists() and counter < max_attempts:
               check_timeout()  # Check timeout during conflict resolution
               target_path = ambiguous_dir / f"{base_name}_{counter}{suffix}"
               counter += 1

           if target_path.exists():
               raise FileExistsError(
                   f"Could not resolve filename conflict for {file_path.name} "
                   f"after {max_attempts} attempts."
               )

           logger.info(
               "Renamed to avoid conflict: %s -> %s",
               file_path.name, target_path.name
           )

       check_timeout()
       shutil.move(str(file_path), str(target_path))
       logger.info(
           "Moved ambiguous file to: %s (took %.2fs)",
           target_path, time.time() - start_time
       )

       return target_path
   ```

4. **Update all ambiguous file routing:**

   ```bash
   # Find all ambiguous file handling
   grep -rn "ambiguous" namer/namer.py

   # Replace with new function
   ```

#### Testing

**Unit Tests:**

```python
def test_move_to_ambiguous_directory(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_text("test content")

    ambiguous_dir = tmp_path / "ambiguous"

    result = move_to_ambiguous_directory(video, ambiguous_dir)

    assert result.exists()
    assert result.parent == ambiguous_dir
    assert result.name == "video.mp4"

def test_move_to_ambiguous_handles_conflicts(tmp_path):
    # Create original file
    video1 = tmp_path / "video.mp4"
    video1.write_text("content 1")

    # Create conflicting file in ambiguous dir
    ambiguous_dir = tmp_path / "ambiguous"
    ambiguous_dir.mkdir()
    (ambiguous_dir / "video.mp4").write_text("existing")

    # Move should rename to avoid conflict
    result = move_to_ambiguous_directory(video1, ambiguous_dir)

    assert result.name == "video_1.mp4"
    assert (ambiguous_dir / "video.mp4").exists()  # Original preserved
    assert result.exists()

def test_move_to_ambiguous_creates_directory(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_text("test content")

    ambiguous_dir = tmp_path / "nonexistent" / "ambiguous"

    # Should create nested directories
    result = move_to_ambiguous_directory(video, ambiguous_dir)

    assert ambiguous_dir.exists()
    assert result.exists()
```

**Integration Test:**

```bash
# Create test scenario
mkdir -p /tmp/namer-test-e1/watch
mkdir -p /tmp/namer-test-e1/ambiguous

# Create ambiguous match scenario
# (requires setting up test database with duplicate scenes)

# Run namer
poetry run namer --watch /tmp/namer-test-e1/watch \
                 --ambiguous /tmp/namer-test-e1/ambiguous

# Verify file moved to ambiguous directory
ls -la /tmp/namer-test-e1/ambiguous/
```

#### Coordination with C2

**⚠️ CRITICAL:** E1 cannot start until C2 merges

**After C2 merges:**

1. Pull latest `main`
2. Verify `namer/utils.py` exists with `ensure_directory()`
3. Start E1 implementation
4. Rebase frequently to avoid conflicts

**If C2 is delayed:**

- Switch to E2 (parallel work)
- Assist with C2 review/testing
- Prepare E1 code in draft PR (mark as blocked)

---

### **E2: Enhance watchdog event processing**

**Priority:** Medium
**Complexity:** Low
**Estimated Time:** 2-3 hours
**Status:** Independent (can start anytime)

#### What You're Changing

**Files:** `namer/watchdog.py`

**Before:**

```python
def on_created(self, event):
    # Minimal filtering
    if event.is_directory:
        return

    self.process_file(event.src_path)
```

**After:**

```python
def on_created(self, event):
    # Enhanced filtering and logging
    if event.is_directory:
        logger.debug("Ignoring directory event: %s", event.src_path)
        return

    file_path = Path(event.src_path)

    # Filter by extension
    if file_path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        logger.debug("Ignoring non-video file: %s", file_path)
        return

    # Filter temporary files
    if file_path.name.startswith('.') or file_path.name.endswith('.tmp'):
        logger.debug("Ignoring temporary file: %s", file_path)
        return

    logger.info("Processing new file: %s", file_path)
    self.process_file(file_path)
```

#### Why This Matters

**Current Problem:**

- Watchdog processes all file events, including non-video files
- Temporary files trigger unnecessary processing
- Minimal logging makes debugging difficult

**Improvements:**

- **Extension filtering:** Only process supported video formats
- **Temp file filtering:** Ignore `.tmp`, `.part`, hidden files
- **Better logging:** Track what's processed and what's ignored

#### Implementation Strategy

1. **Define supported extensions:**

   ```python
   SUPPORTED_VIDEO_EXTENSIONS = {
       '.mp4', '.mkv', '.avi', '.mov', '.wmv',
       '.flv', '.webm', '.m4v', '.mpg', '.mpeg'
   }
   ```

2. **Add filtering logic:**

   ```python
   def _should_process_file(self, file_path: Path) -> bool:
       """Check if file should be processed."""
       # Ignore directories
       if file_path.is_dir():
           logger.debug("Ignoring directory: %s", file_path)
           return False

       # Check extension
       if file_path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
           logger.debug("Unsupported extension: %s", file_path)
           return False

       # Ignore hidden files
       if file_path.name.startswith('.'):
           logger.debug("Ignoring hidden file: %s", file_path)
           return False

       # Ignore temporary files
       if file_path.suffix in {'.tmp', '.part', '.download'}:
           logger.debug("Ignoring temporary file: %s", file_path)
           return False

       return True
   ```

3. **Use in event handlers:**

   ```python
   def on_created(self, event):
       file_path = Path(event.src_path)

       if self._should_process_file(file_path):
           logger.info("Processing new file: %s", file_path)
           self.process_file(file_path)

   def on_modified(self, event):
       file_path = Path(event.src_path)

       if self._should_process_file(file_path):
           logger.info("Processing modified file: %s", file_path)
           self.process_file(file_path)
   ```

#### Testing

**Unit Tests:**

```python
def test_should_process_video_file(tmp_path):
    video = tmp_path / "movie.mp4"
    video.touch()

    watchdog = FileWatchdog(tmp_path)
    assert watchdog._should_process_file(video) is True

def test_should_not_process_directory(tmp_path):
    directory = tmp_path / "videos"
    directory.mkdir()

    watchdog = FileWatchdog(tmp_path)
    assert watchdog._should_process_file(directory) is False

def test_should_not_process_unsupported_extension(tmp_path):
    text_file = tmp_path / "readme.txt"
    text_file.touch()

    watchdog = FileWatchdog(tmp_path)
    assert watchdog._should_process_file(text_file) is False

def test_should_not_process_hidden_file(tmp_path):
    hidden = tmp_path / ".hidden.mp4"
    hidden.touch()

    watchdog = FileWatchdog(tmp_path)
    assert watchdog._should_process_file(hidden) is False

def test_should_not_process_temp_file(tmp_path):
    temp = tmp_path / "video.mp4.tmp"
    temp.touch()

    watchdog = FileWatchdog(tmp_path)
    assert watchdog._should_process_file(temp) is False
```

**Integration Test:**

```bash
# Start watchdog
poetry run namer --watch /tmp/test-watchdog &
NAMER_PID=$!

# Create various files
touch /tmp/test-watchdog/video.mp4       # Should process
touch /tmp/test-watchdog/readme.txt      # Should ignore
touch /tmp/test-watchdog/.hidden.mp4     # Should ignore
touch /tmp/test-watchdog/video.tmp       # Should ignore
mkdir /tmp/test-watchdog/subdir          # Should ignore

# Check logs
kill $NAMER_PID
grep "Processing new file" /tmp/namer.log  # Should only show video.mp4
grep "Ignoring" /tmp/namer.log             # Should show others
```

---

### **E3: Add ambiguous file workflow validation**

**Priority:** Medium
**Complexity:** Low
**Estimated Time:** 2-3 hours
**⚠️ BLOCKED BY:** E1 (ambiguous handling logic)

#### What You're Changing

**Files:** `.github/workflows/pr-validate.yml`, `namer/watchdog.py`

**Before:**

- No CI validation of ambiguous file handling

**After:**

```yaml
# .github/workflows/pr-validate.yml
- name: Test ambiguous file handling
  run: |
    # Create test directories
    mkdir -p /tmp/test-ambiguous/{watch,ambiguous}

    # Create test video
    cp test/fixtures/sample.mp4 /tmp/test-ambiguous/watch/

    # Run namer with ambiguous directory configured
    poetry run namer \
      --watch /tmp/test-ambiguous/watch \
      --ambiguous /tmp/test-ambiguous/ambiguous \
      --dry-run

    # Verify ambiguous directory created
    test -d /tmp/test-ambiguous/ambiguous

    echo "Ambiguous file handling validated"
```

#### Why This Matters

**Current Problem:**

- Ambiguous file handling only tested manually
- Regressions not caught until production
- No automated validation of directory creation

**Improvements:**

- **Automated testing:** CI validates ambiguous workflow
- **Early detection:** Catch regressions before merge
- **Documentation:** Workflow serves as example usage

#### Implementation Strategy

1. **Add CI test step:**

   ```yaml
   - name: Validate ambiguous file workflow
     shell: bash
     run: |
       set -e

       # Setup test environment
       TEST_DIR="/tmp/namer-ambiguous-test"
       mkdir -p "$TEST_DIR"/{watch,ambiguous,target}

       # Create test fixture
       cp test/fixtures/sample.mp4 "$TEST_DIR/watch/test-video.mp4"

       # Run namer (dry-run mode)
       poetry run namer \
         --config test/fixtures/test-config.cfg \
         --watch "$TEST_DIR/watch" \
         --ambiguous "$TEST_DIR/ambiguous" \
         --target "$TEST_DIR/target" \
         --dry-run || true

       # Verify directories created
       if [ ! -d "$TEST_DIR/ambiguous" ]; then
         echo "ERROR: Ambiguous directory not created"
         exit 1
       fi

       echo "✓ Ambiguous file workflow validated"
   ```

2. **Add watchdog test:**

   ```python
   # In namer/watchdog.py or test file
   def test_ambiguous_file_routing():
       """Integration test for ambiguous file handling."""
       # Setup test directories
       test_dir = Path("/tmp/namer-test")
       watch_dir = test_dir / "watch"
       ambiguous_dir = test_dir / "ambiguous"

       watch_dir.mkdir(parents=True, exist_ok=True)

       # Create test video
       test_video = watch_dir / "test.mp4"
       shutil.copy("test/fixtures/sample.mp4", test_video)

       # Process with ambiguous result
       # (mock metadata provider to return multiple matches)

       # Verify file moved to ambiguous directory
       assert not test_video.exists()
       assert (ambiguous_dir / "test.mp4").exists()
   ```

3. **Update workflow documentation:**

   ```yaml
   # Add comment explaining the test
   # This validates that:
   # 1. Ambiguous directory is created automatically
   # 2. Files with multiple matches route correctly
   # 3. Directory creation uses shared utility (from C2)
   # 4. Watchdog processes ambiguous files (from E2)
   ```

#### Testing

**Local Validation:**

```bash
# Run the same test locally
TEST_DIR="/tmp/namer-ambiguous-test"
mkdir -p "$TEST_DIR"/{watch,ambiguous,target}

cp test/fixtures/sample.mp4 "$TEST_DIR/watch/test-video.mp4"

poetry run namer \
  --watch "$TEST_DIR/watch" \
  --ambiguous "$TEST_DIR/ambiguous" \
  --target "$TEST_DIR/target" \
  --dry-run

# Verify
ls -la "$TEST_DIR/ambiguous/"
```

**CI Validation:**

```bash
# After PR created, check CI logs
gh run view <run-id> --log | grep "ambiguous"

# Should show:
# ✓ Ambiguous file workflow validated
```

---

## Workflow Tips

### Daily Routine

1. **Morning:** Check C2 merge status (for E1)

   ```bash
   gh pr view <c2-pr-number> --json state,mergedAt
   ```

2. **If C2 not merged:** Work on E2 (parallel)

   ```bash
   git checkout -b fix/enhance-watchdog-events
   ```

3. **After E1 merges:** Start E3 immediately

   ```bash
   git checkout -b test/validate-ambiguous-workflow
   ```

### Common Pitfalls

#### 1. **Filename Conflict Loop**

**Symptom:** Infinite loop when resolving conflicts

**Solution:** Add safety limit:

```python
counter = 1
max_attempts = 1000

while target_path.exists() and counter < max_attempts:
    target_path = ambiguous_dir / f"{base_name}_{counter}{suffix}"
    counter += 1

if counter >= max_attempts:
    raise RuntimeError(f"Could not resolve filename conflict: {file_path.name}")
```

#### 2. **Watchdog Event Storm**

**Symptom:** Same file processed multiple times

**Solution:** Add debouncing with cleanup:

```python
from collections import defaultdict
import time

class FileWatchdog:
    def __init__(self, ...):
        self._last_processed = defaultdict(float)
        self._debounce_seconds = 2.0
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

    def _cleanup_debounce_cache(self):
        """Remove old entries from debounce cache to prevent memory leak."""
        now = time.time()

        # Only cleanup every N seconds
        if now - self._last_cleanup < self._cleanup_interval:
            return

        # Remove entries older than debounce window
        cutoff_time = now - (self._debounce_seconds * 10)  # Keep 10x debounce window
        old_entries = [
            path for path, timestamp in self._last_processed.items()
            if timestamp < cutoff_time
        ]

        for path in old_entries:
            del self._last_processed[path]

        if old_entries:
            logger.debug(
                "Cleaned up %d old debounce entries",
                len(old_entries)
            )

        self._last_cleanup = now

    def on_created(self, event):
        file_path = Path(event.src_path)

        # Periodic cleanup to prevent memory leak
        self._cleanup_debounce_cache()

        # Debounce: ignore if processed recently
        now = time.time()
        if now - self._last_processed[file_path] < self._debounce_seconds:
            logger.debug("Debouncing: %s", file_path)
            return

        self._last_processed[file_path] = now
        self.process_file(file_path)

    def on_modified(self, event):
        """Handle file modification events with debouncing."""
        file_path = Path(event.src_path)

        # Periodic cleanup
        self._cleanup_debounce_cache()

        # Debounce
        now = time.time()
        if now - self._last_processed[file_path] < self._debounce_seconds:
            logger.debug("Debouncing modified event: %s", file_path)
            return

        self._last_processed[file_path] = now
        self.process_file(file_path)
```

**Testing Debounce Cleanup:**

```python
def test_debounce_cleanup_prevents_memory_leak():
    """Verify debounce cache doesn't grow indefinitely."""
    watchdog = FileWatchdog(tmp_path)

    # Process many different files
    for i in range(1000):
        fake_event = FileCreatedEvent(str(tmp_path / f"file_{i}.mp4"))
        watchdog.on_created(fake_event)

    # Trigger cleanup
    watchdog._last_cleanup = 0  # Force cleanup on next call
    watchdog.on_created(FileCreatedEvent(str(tmp_path / "trigger.mp4")))

    # Cache should be pruned (only recent files kept)
    assert len(watchdog._last_processed) < 100, \
        f"Cache not cleaned up: {len(watchdog._last_processed)} entries"

def test_debounce_cleanup_preserves_recent_entries():
    """Verify cleanup doesn't remove recent entries."""
    watchdog = FileWatchdog(tmp_path)

    # Process a file
    recent_file = tmp_path / "recent.mp4"
    watchdog.on_created(FileCreatedEvent(str(recent_file)))

    # Trigger cleanup immediately
    watchdog._last_cleanup = 0
    watchdog.on_created(FileCreatedEvent(str(tmp_path / "trigger.mp4")))

    # Recent file should still be in cache
    assert recent_file in watchdog._last_processed, \
        "Recent entry removed by cleanup"
```

#### 3. **CI Test Flakiness**

**Symptom:** Ambiguous workflow test fails intermittently

**Solution:** Add retries and better cleanup:

```yaml
- name: Validate ambiguous file workflow
  run: |
    set -e

    # Cleanup from previous runs
    rm -rf /tmp/namer-ambiguous-test

    # Run test with timeout
    timeout 30s bash -c '
      # Test logic here
    '

    # Cleanup after test
    rm -rf /tmp/namer-ambiguous-test
```

### Communication Protocol

**When to post in `#migration-ambiguity-review`:**

- ✅ C2 merged (start E1)
- ✅ E1 merged (start E3)
- ✅ E2 merged (watchdog improvements live)
- ✅ E3 merged (workstream complete, migration done!)

**When to escalate:**

- C2 delayed >2 days (blocks E1)
- E1 introduces regressions in file routing
- CI test fails consistently

---

## Testing Checklist

Before merging each PR:

### E1

- [ ] Uses `ensure_directory()` from C2
- [ ] Handles filename conflicts
- [ ] Logs all ambiguous file movements
- [ ] Tests cover conflicts, nested directories
- [ ] No regressions in file routing

### E2

- [ ] Filters by video extension
- [ ] Ignores temporary files
- [ ] Logs ignored files at DEBUG level
- [ ] Tests cover all filter cases
- [ ] No valid files skipped

### E3

- [ ] CI test validates ambiguous workflow
- [ ] Test creates directories automatically
- [ ] Test runs in <30 seconds
- [ ] Cleanup happens after test
- [ ] Documentation updated

---

## Rollback Procedures

### Individual PR Rollback

```bash
git revert -m 1 <merge-commit-sha>
git push origin main
```

### Coordinated Rollback (E1+E3)

If E3 test fails due to E1 bug:

```bash
# Revert E3 first (test)
git revert -m 1 <e3-merge-sha>

# Revert E1 (implementation)
git revert -m 1 <e1-merge-sha>

git push origin main
```

**Post-Rollback:**

- Notify team in `#migration-ambiguity-review`
- Fix E1 bug
- Re-submit E1 → E3 sequence

---

## Success Criteria

- ✅ All 3 PRs merged by end of Week 3
- ✅ Ambiguous files route correctly 100% of the time
- ✅ Filename conflicts handled gracefully
- ✅ Watchdog filters non-video files
- ✅ CI validates ambiguous workflow
- ✅ **Migration complete!**

---

## Post-Migration Tasks

After E3 merges:

1. **Archive `fix/ambiguity-review` branch:**

   ```bash
   git branch -D fix/ambiguity-review
   git push origin --delete fix/ambiguity-review
   ```

2. **Update documentation:**

   - Add ambiguous file handling to user guide
   - Document filename conflict resolution
   - Update troubleshooting guide

3. **Monitor production:**

   - Track ambiguous file routing metrics
   - Monitor error rates for 1 week
   - Validate no regressions

4. **Retrospective:**
   - Schedule team meeting
   - Document lessons learned
   - Update migration process for future use

---

## Resources

- **Migration Plan:** [migration-plan-fix-ambiguity-review.md](migration-plan-fix-ambiguity-review.md)
- **Delivery Plan:** [delivery-plan-fix-ambiguity-review.md](delivery-plan-fix-ambiguity-review.md)
- **Migration Utilities:** [migration-utilities.md](migration-utilities.md) - Cherry-pick helper, time tracking, coverage comparison
- **Source Commits:** `fix/ambiguity-review` (commits `fa96678`, `f4361a2`)
- **Related Workstreams:** C (C2 blocks E1)
- **Test Fixtures:** `test/fixtures/sample.mp4`

---

**Workstream Owner:** Backend Engineer 2
**Last Updated:** 2025-10-06
**Status:** Waiting for C2 (E1 blocked), E2 ready to start
