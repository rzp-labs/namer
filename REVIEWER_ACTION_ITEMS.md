# Code Review Action Items

## Status: Build Successfully Running ✅

The videohashes submodule build issue has been resolved. The Docker build is now working correctly.

---

## Before Merge (Critical)

### 1. Fix FFmpeg Initialization Logic (configuration.py:577) ⚠️

**Problem:** 
- Current code uses `'pytest' in sys.modules` which is brittle
- Can cause false positives/negatives in test detection

**Solution:**
- Replace with explicit environment variable control + conservative argv detection
- Primary: `NAMER_SKIP_FFMPEG_VALIDATION` environment variable
- Fallback: Detect pytest via `sys.argv[0]` (process name)

**Implementation:**
```python
_TRUTHY = {'1', 'true', 'yes', 'on'}

def _env_truthy(name: str, default: str = 'false') -> bool:
    return str(os.getenv(name, default)).strip().lower() in _TRUTHY

def _ffmpeg_should_skip_validation() -> bool:
    if _env_truthy('NAMER_SKIP_FFMPEG_VALIDATION'):
        return True
    argv0 = os.path.basename(sys.argv[0] or '')
    if argv0.startswith('pytest') or argv0.startswith('py.test'):
        return True
    return False

# Then replace line 577 with:
ffmpeg: FFMpeg = FFMpeg(skip_validation=_ffmpeg_should_skip_validation())
```

**Branch:** `fix/ffmpeg-skip-detection`

---

### 2. Verify FFProbeResults/FFProbeStream Imports ✅

**Status:** All imports verified as using canonical path

**Checked:**
```bash
grep -r "from ffmpeg_common import" namer/
grep -r "FFProbeResults\|FFProbeStream" namer/
```

**Result:** All imports correctly use:
```python
from namer.ffmpeg_common import FFProbeResults, FFProbeStream
```

---

### 3. Search for ValidationError Exception Handlers ✅

**Status:** Verified - No ValidationError handlers found

```bash
grep -r "except.*ValidationError" namer/
```

**Result:** No matches found ✅

---

## Post-Merge (Documentation & Tracking)

### 1. Add Submodule Commit Verification to Dockerfile

**Goal:** Ensure Docker image uses intended videohashes commit

**Implementation:**
```dockerfile
ARG VHASH_COMMIT

# After submodule initialization
RUN test "$(git -C videohashes rev-parse HEAD)" = "$VHASH_COMMIT" \
  || (echo "videohashes commit mismatch" && exit 1)
```

**Usage:**
```bash
docker build --build-arg VHASH_COMMIT=$(git -C videohashes rev-parse HEAD) -t namer:local .
```

**Documentation:** Add to `docs/BUILD.md`

---

### 2. Document Integration Test Config Setup

**Create:** `docs/testing.md` or update existing testing documentation

**Example config** (`tests/integration/config.test.yml`):
```yaml
metadata_provider: "theporndb"
porndb_token: "test-token"  # Use CI secret
enable_disambiguation: false
web: false
watch_dir: "./tmp/watch"
work_dir: "./tmp/work"
failed_dir: "./tmp/failed"
dest_dir: "./tmp/dest"
```

**pytest.ini recommendation:**
```ini
[pytest]
env =
    NAMER_SKIP_FFMPEG_VALIDATION=true
```

---

### 3. Create Issue to Upgrade attrs/cattrs

**GitHub Issue Template:**

**Title:** Upgrade attrs/cattrs to 25.x when feasible

**Body:**
```markdown
## Current State
- attrs pinned to <25.0.0
- cattrs pinned to <25.0.0
- Reason: Breaking changes in serialization behavior with jsonpickle

## Proposed Approach
1. Add CI matrix job testing with latest attrs/cattrs (allow failure)
2. Monitor for compatibility issues
3. Update code as needed
4. Remove pins when stable

## References
- https://github.com/python-attrs/attrs/releases/tag/25.0.0
- Internal jsonpickle usage audit needed
```

---

### 4. Monitor Pytest Detection Logic

**GitHub Issue Template:**

**Title:** Monitor FFmpeg skip detection after replacing pytest sys.modules heuristic

**Body:**
```markdown
## Context
Replaced `'pytest' in sys.modules` with more explicit detection:
- Primary: NAMER_SKIP_FFMPEG_VALIDATION env var
- Fallback: argv[0] starts with 'pytest'

## Monitoring Plan
- [ ] Verify CI logs for next 2 releases
- [ ] Check for unexpected FFmpeg validation failures
- [ ] Check for unexpected skips in non-test contexts
- [ ] Solicit contributor feedback

## Optional Enhancement
Add DEBUG-level logging to show why FFmpeg validation was skipped (if debug mode enabled)
```

---

## Summary

### Before Merge ✅
- [x] Videohashes submodule build working
- [x] FFProbeResults/FFProbeStream imports verified
- [x] ValidationError handlers checked
- [ ] **TODO:** Fix FFmpeg initialization logic (line 577)

### Post-Merge 📋
- [ ] Add submodule verification to Dockerfile
- [ ] Document integration test setup
- [ ] Create attrs/cattrs upgrade issue
- [ ] Create pytest detection monitoring issue

---

## Next Steps

1. **Create new branch:**
   ```bash
   git checkout -b fix/ffmpeg-skip-detection
   ```

2. **Implement FFmpeg detection fix** (see section 1 above)

3. **Add tests:**
   - Create `test/unit/test_ffmpeg_skip_detection.py`
   - Test env var control
   - Test argv detection
   - Test default behavior

4. **Verify:**
   ```bash
   NAMER_SKIP_FFMPEG_VALIDATION=true pytest -q
   pytest -q
   python -c "from namer.configuration import Configuration; print('ok')"
   ```

5. **Open PR** with all changes and post-merge action items documented
