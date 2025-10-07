# Workstream D: Feature Enhancements

**Owner:** Backend Engineer
**Timeline:** Week 1-2
**Total PRs:** 4 (D1, D2, D3, D4)
**Status:** Semi-Independent (D1→D2→D3 sequential; D4 parallel)

---

## Mission Statement

Improve perceptual hash (phash) matching reliability and metadata provider error handling by adding validation, encapsulation, and defensive programming patterns.

---

## Goals & Objectives

### Primary Goals

1. **Add path validation** to comparison results to prevent invalid file references
2. **Encapsulate phash flag** with setter method for better state management
3. **Improve phash result handling** to reduce false positives/negatives
4. **Enhance ThePornDB provider** error handling for network failures

### Success Metrics

- ✅ All 4 PRs merged by end of Week 2
- ✅ Phash matching accuracy improved (measured via test suite)
- ✅ Comparison result objects always have valid paths
- ✅ ThePornDB provider gracefully handles API errors

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
  git log --oneline main..fix/ambiguity-review | grep -E "(8d1fcd9|0381399|65b8c44|f4361a2)"
  git show 8d1fcd9  # D1 changes
  git show 0381399  # D2 changes
  git show 65b8c44  # D3 changes
  git show f4361a2  # D4 changes
  ```

**Ready to start when all boxes checked.**

---

## PR Template

Use this template for all Workstream D PRs:

````markdown
## Migration PR: [Workstream D] - [PR ID]

### Source Information
- **Branch:** `fix/ambiguity-review`
- **Commit SHA:** `[8d1fcd9|0381399|65b8c44|f4361a2]`
- **Cherry-pick command:** `git cherry-pick -n [SHA]`

### Changes
- List of files changed
- Brief description of what changed in each file

### Testing
- [ ] Unit tests pass: `poetry run pytest`
- [ ] Security scan passes: `poetry run bandit -r namer/`
- [ ] Linting passes: `poetry run ruff check .`
- [ ] Coverage maintained: `./scripts/compare-coverage.sh`
- [ ] Smoke test executed: `./scripts/smoke-test.sh D <PR-ID>`

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

### **D1: Improve comparison result path handling**

**Priority:** High (foundation for D2)
**Complexity:** Low
**Estimated Time:** 2-3 hours

#### What You're Changing

**Files:** `namer/comparison_results.py`

**Before:**

```python
class ComparisonResult:
    def __init__(self, file_path: str, ...):
        self.file_path = file_path  # No validation
```

**After:**

```python
class ComparisonResult:
    def __init__(self, file_path: str, ...):
        # Validate path exists and is a file
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise ValueError(f"File does not exist: {file_path}")
        if not path_obj.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        self.file_path = str(path_obj.resolve())  # Store absolute path
```

#### Why This Matters

**Current Problem:**

- Comparison results may reference deleted/moved files
- Relative paths cause issues when working directory changes
- No validation leads to downstream errors

**Benefits:**

- **Early failure:** Catch invalid paths at construction time
- **Absolute paths:** Consistent file references regardless of CWD
- **Better debugging:** Clear error messages for missing files

#### Implementation Strategy

1. **Add validation in `__init__`:**

   ```python
   from pathlib import Path

   def __init__(self, file_path: str, match_score: float, ...):
       # Convert to Path and validate
       path_obj = Path(file_path)

       if not path_obj.exists():
           logger.warning("File does not exist: %s", file_path)
           raise FileNotFoundError(f"File not found: {file_path}")

       if not path_obj.is_file():
           raise ValueError(f"Not a file: {file_path}")

       # Store absolute path
       self.file_path = str(path_obj.resolve())
       self.match_score = match_score
       ...
   ```

2. **Update all instantiation sites:**

   ```bash
   # Find all ComparisonResult() calls
   grep -rn "ComparisonResult(" namer/

   # Ensure file_path is valid before passing
   ```

3. **Add property for Path object:**

   ```python
   @property
   def path(self) -> Path:
       """Get file path as Path object."""
       return Path(self.file_path)
   ```

#### Testing

**Unit Tests:**

```python
def test_comparison_result_validates_path(tmp_path):
    valid_file = tmp_path / "video.mp4"
    valid_file.touch()

    # Should accept valid file
    result = ComparisonResult(str(valid_file), match_score=0.95)
    assert result.file_path == str(valid_file.resolve())

def test_comparison_result_rejects_missing_file():
    with pytest.raises(ValueError, match="File not found"):
        ComparisonResult("/nonexistent/file.mp4", match_score=0.95)

def test_comparison_result_rejects_directory(tmp_path):
    directory = tmp_path / "videos"
    directory.mkdir()

    with pytest.raises(ValueError, match="Not a file"):
        ComparisonResult(str(directory), match_score=0.95)

def test_comparison_result_stores_absolute_path(tmp_path):
    os.chdir(tmp_path)
    video = tmp_path / "video.mp4"
    video.touch()

    # Pass relative path
    result = ComparisonResult("video.mp4", match_score=0.95)

    # Should store absolute path
    assert result.file_path == str(video.resolve())
```

---

### **D2: Add setter method for phash flag**

**Priority:** High (foundation for D3)
**Complexity:** Low
**Estimated Time:** 2-3 hours

#### What You're Changing

**Files:** `namer/comparison_results.py`, `namer/metadata_providers/theporndb_provider.py`

**Before:**

```python
class ComparisonResult:
    def __init__(self, ...):
        self.phash_matched = False  # Direct attribute access

# Usage
result.phash_matched = True  # No validation or logging
```

**After:**

```python
class ComparisonResult:
    def __init__(self, ...):
        self._phash_matched = False  # Private attribute

    @property
    def phash_matched(self) -> bool:
        """Whether this result matched via perceptual hash."""
        return self._phash_matched

    @phash_matched.setter
    def phash_matched(self, value: bool) -> None:
        """Set phash match status with validation."""
        if not isinstance(value, bool):
            raise TypeError(f"phash_matched must be bool, got {type(value)}")

        if value and not self._phash_matched:
            logger.debug("Marking result as phash-matched: %s", self.file_path)

        self._phash_matched = value
```

#### Why This Matters

**Encapsulation Benefits:**

- **Type safety:** Prevent accidental assignment of non-boolean values
- **Observability:** Log when phash matching is used
- **Future extensibility:** Easy to add validation/side effects later

**Example Bug Prevented:**

```python
# Before: Silent bug
result.phash_matched = "yes"  # String instead of bool
if result.phash_matched:  # Always truthy!
    ...

# After: Immediate error
result.phash_matched = "yes"  # TypeError: phash_matched must be bool
```

#### Implementation Strategy

1. **Add property and setter:**

   ```python
   class ComparisonResult:
       def __init__(self, ...):
           self._phash_matched = False

       @property
       def phash_matched(self) -> bool:
           return self._phash_matched

       @phash_matched.setter
       def phash_matched(self, value: bool) -> None:
           if not isinstance(value, bool):
               raise TypeError(
                   f"phash_matched must be bool, got {type(value).__name__}"
               )
           self._phash_matched = value
   ```

2. **Update all direct assignments:**

   ```bash
   # Find all assignments
   grep -rn "\.phash_matched\s*=" namer/

   # Ensure they use the setter (no code changes needed)
   ```

3. **Add logging for debugging:**

   ```python
   @phash_matched.setter
   def phash_matched(self, value: bool) -> None:
       if not isinstance(value, bool):
           raise TypeError(...)

       if value != self._phash_matched:
           logger.debug(
               "Phash match status changed: %s -> %s for %s",
               self._phash_matched, value, self.file_path
           )

       self._phash_matched = value
   ```

#### Testing

**Unit Tests:**

```python
def test_phash_matched_getter(tmp_path):
    video = tmp_path / "video.mp4"
    video.touch()
    result = ComparisonResult(str(video), match_score=0.95)

    assert result.phash_matched is False

def test_phash_matched_setter(tmp_path):
    video = tmp_path / "video.mp4"
    video.touch()
    result = ComparisonResult(str(video), match_score=0.95)

    result.phash_matched = True
    assert result.phash_matched is True

def test_phash_matched_type_validation(tmp_path):
    video = tmp_path / "video.mp4"
    video.touch()
    result = ComparisonResult(str(video), match_score=0.95)

    with pytest.raises(TypeError, match="must be bool"):
        result.phash_matched = "yes"

    with pytest.raises(TypeError, match="must be bool"):
        result.phash_matched = 1

def test_phash_matched_logging(tmp_path, caplog):
    video = tmp_path / "video.mp4"
    video.touch()
    result = ComparisonResult(str(video), match_score=0.95)

    result.phash_matched = True

    assert "Phash match status changed" in caplog.text
```

---

### **D3: Improve phash result handling**

**Priority:** High
**Complexity:** Medium
**Estimated Time:** 4-6 hours

#### What You're Changing

**Files:** `namer/comparison_results.py`, `namer/metadata_providers/theporndb_provider.py`

**Before:**

```python
# Simple boolean check
if phash_distance < threshold:
    result.phash_matched = True
```

**After:**

```python
# Enhanced logic with confidence scoring
phash_confidence = calculate_phash_confidence(phash_distance, threshold)

if phash_confidence >= MIN_CONFIDENCE:
    result.phash_matched = True
    result.phash_confidence = phash_confidence
    logger.info(
        "Phash match found: distance=%d, confidence=%.2f",
        phash_distance, phash_confidence
    )
```

#### Why This Matters

**Current Problem:**

- Binary phash matching (yes/no) loses nuance
- No confidence scoring for borderline matches
- Difficult to tune threshold without feedback

**Improvements:**

- **Confidence scores:** Quantify match quality
- **Better logging:** Track phash performance over time
- **Tunable thresholds:** Data-driven threshold optimization

#### Implementation Strategy

1. **Add confidence calculation:**

   ```python
   def calculate_phash_confidence(distance: int, threshold: int) -> float:
       """
       Calculate confidence score for phash match.

       Returns:
           0.0 (no match) to 1.0 (perfect match)
       """
       if distance > threshold:
           return 0.0

       # Linear interpolation: threshold -> 0.5, 0 -> 1.0
       return 1.0 - (distance / (threshold * 2))
   ```

2. **Add confidence field to ComparisonResult:**

   ```python
   class ComparisonResult:
       def __init__(self, ...):
           ...
           self.phash_confidence: Optional[float] = None
   ```

3. **Update phash matching logic:**

   ```python
   # In theporndb_provider.py
   phash_distance = calculate_hamming_distance(file_phash, scene_phash)
   confidence = calculate_phash_confidence(phash_distance, PHASH_THRESHOLD)

   if confidence >= MIN_PHASH_CONFIDENCE:
       result.phash_matched = True
       result.phash_confidence = confidence
       logger.info(
           "Phash match: %s (distance=%d, confidence=%.2f)",
           scene.title, phash_distance, confidence
       )
   ```

#### Testing

**Unit Tests:**

```python
def test_phash_confidence_perfect_match():
    # Distance 0 = perfect match
    confidence = calculate_phash_confidence(distance=0, threshold=10)
    assert confidence == 1.0

def test_phash_confidence_threshold_match():
    # At threshold = 50% confidence
    confidence = calculate_phash_confidence(distance=10, threshold=10)
    assert 0.4 <= confidence <= 0.6

def test_phash_confidence_no_match():
    # Above threshold = no match
    confidence = calculate_phash_confidence(distance=15, threshold=10)
    assert confidence == 0.0

def test_phash_result_includes_confidence(tmp_path):
    video = tmp_path / "video.mp4"
    video.touch()
    result = ComparisonResult(str(video), match_score=0.95)

    result.phash_matched = True
    result.phash_confidence = 0.87

    assert result.phash_confidence == 0.87
```

**Integration Test:**

```bash
# Run phash ambiguity tests
poetry run pytest test/stashdb_phash_ambiguity_test.py -v

# Verify confidence scores logged
grep "phash_confidence" test-output.log
```

#### Confidence Formula Validation

The confidence calculation formula must satisfy specific mathematical properties to ensure reliable phash matching:

**Required Properties:**

1. **Monotonic Decreasing:** Confidence decreases as distance increases
2. **Bounded:** Confidence is always in range [0.0, 1.0]
3. **Perfect Match:** Distance 0 yields confidence 1.0
4. **Threshold Boundary:** Distance at threshold yields confidence ~0.5
5. **No Match:** Distance above threshold yields confidence 0.0

**Mathematical Verification:**

```python
def test_confidence_formula_properties():
    """Verify confidence formula satisfies required mathematical properties."""
    threshold = 10

    # Property 1: Monotonic decreasing
    distances = [0, 2, 5, 8, 10, 15]
    confidences = [calculate_phash_confidence(d, threshold) for d in distances]

    for i in range(len(confidences) - 1):
        assert confidences[i] >= confidences[i + 1], \
            f"Not monotonic: {confidences[i]} < {confidences[i + 1]}"

    # Property 2: Bounded
    for d in range(0, threshold * 2):
        confidence = calculate_phash_confidence(d, threshold)
        assert 0.0 <= confidence <= 1.0, \
            f"Out of bounds: {confidence} for distance {d}"

    # Property 3: Perfect match
    assert calculate_phash_confidence(0, threshold) == 1.0, \
        "Perfect match should yield 1.0 confidence"

    # Property 4: Threshold boundary (~0.5)
    threshold_confidence = calculate_phash_confidence(threshold, threshold)
    assert 0.4 <= threshold_confidence <= 0.6, \
        f"Threshold confidence {threshold_confidence} not near 0.5"

    # Property 5: No match
    assert calculate_phash_confidence(threshold + 1, threshold) == 0.0, \
        "Above threshold should yield 0.0 confidence"

def test_confidence_formula_edge_cases():
    """Test edge cases and boundary conditions."""
    # Zero threshold (degenerate case)
    assert calculate_phash_confidence(0, 0) == 1.0
    assert calculate_phash_confidence(1, 0) == 0.0

    # Very large threshold
    large_threshold = 1000
    assert calculate_phash_confidence(0, large_threshold) == 1.0
    assert calculate_phash_confidence(large_threshold, large_threshold) >= 0.4

    # Negative distance (should not happen, but handle gracefully)
    with pytest.raises(ValueError, match="Distance cannot be negative"):
        calculate_phash_confidence(-1, 10)

    # Negative threshold (invalid)
    with pytest.raises(ValueError, match="Threshold must be positive"):
        calculate_phash_confidence(5, -1)

def test_confidence_distribution():
    """Verify confidence distribution has good spread."""
    threshold = 10

    # Generate confidence values for all distances
    distances = list(range(0, threshold + 1))
    confidences = [calculate_phash_confidence(d, threshold) for d in distances]

    # Should have good spread (not all clustered at extremes)
    middle_range_count = sum(1 for c in confidences if 0.3 <= c <= 0.7)
    assert middle_range_count >= 3, \
        "Formula should have good spread, not just extremes"

    # Standard deviation should be reasonable
    import statistics
    std_dev = statistics.stdev(confidences)
    assert std_dev > 0.2, \
        f"Confidence distribution too narrow: σ={std_dev}"
```

**Implementation with Validation:**

```python
def calculate_phash_confidence(distance: int, threshold: int) -> float:
    """
    Calculate confidence score for phash match.

    Args:
        distance: Hamming distance between phash values
        threshold: Maximum distance for a match

    Returns:
        Confidence in range [0.0, 1.0]

    Raises:
        ValueError: If distance is negative or threshold is non-positive
    """
    # Input validation
    if distance < 0:
        raise ValueError(f"Distance cannot be negative: {distance}")
    if threshold <= 0:
        raise ValueError(f"Threshold must be positive: {threshold}")

    # No match if beyond threshold
    if distance > threshold:
        return 0.0

    # Perfect match
    if distance == 0:
        return 1.0

    # Linear interpolation: threshold -> 0.5, 0 -> 1.0
    confidence = 1.0 - (distance / (threshold * 2))

    # Clamp to ensure [0, 1] range (defensive programming)
    return max(0.0, min(1.0, confidence))
```

---

### **D4: Improve ThePornDB provider error handling**

**Priority:** Medium
**Complexity:** Low
**Estimated Time:** 2-3 hours

#### What You're Changing

**Files:** `namer/metadata_providers/theporndb_provider.py`

**Before:**

```python
def fetch_scene_metadata(scene_id):
    response = requests.get(f"{API_BASE}/scenes/{scene_id}")
    return response.json()  # Crashes on network error
```

**After:**

```python
def fetch_scene_metadata(scene_id):
    try:
        response = requests.get(
            f"{API_BASE}/scenes/{scene_id}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        logger.error("Timeout fetching scene %s", scene_id)
        return None
    except requests.HTTPError as e:
        logger.error("HTTP error fetching scene %s: %s", scene_id, e)
        return None
    except requests.RequestException as e:
        logger.error("Network error fetching scene %s: %s", scene_id, e)
        return None
```

#### Why This Matters

**Current Problem:**

- Network errors crash the entire processing pipeline
- No timeout leads to indefinite hangs
- Users see generic exceptions instead of helpful errors

**Improvements:**

- **Graceful degradation:** Continue processing other files on API failure
- **Timeout protection:** Prevent indefinite hangs
- **Better logging:** Clear error messages for troubleshooting

#### Implementation Strategy

1. **Wrap all API calls in try/except:**

   ```python
   def _api_request(self, endpoint: str, **kwargs) -> Optional[dict]:
       """Make API request with error handling."""
       try:
           response = requests.get(
               f"{self.api_base}/{endpoint}",
               timeout=kwargs.pop('timeout', 10),
               **kwargs
           )
           response.raise_for_status()
           return response.json()
       except requests.Timeout:
           logger.error("API timeout: %s", endpoint)
           return None
       except requests.HTTPError as e:
           if e.response.status_code == 404:
               logger.debug("Not found: %s", endpoint)
           else:
               logger.error("HTTP %d: %s", e.response.status_code, endpoint)
           return None
       except requests.RequestException as e:
           logger.error("Network error: %s (%s)", endpoint, e)
           return None
   ```

2. **Add retry logic for transient failures:**

   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=10)
   )
   def _api_request_with_retry(self, endpoint: str, **kwargs):
       return self._api_request(endpoint, **kwargs)
   ```

3. **Update callers to handle None:**

   ```python
   metadata = self.fetch_scene_metadata(scene_id)
   if metadata is None:
       logger.warning("Failed to fetch metadata for scene %s", scene_id)
       return None  # Skip this scene
   ```

#### Testing

**Unit Tests:**

```python
def test_api_request_handles_timeout(mocker):
    mocker.patch('requests.get', side_effect=requests.Timeout)

    provider = ThePornDBProvider()
    result = provider._api_request("scenes/123")

    assert result is None

def test_api_request_handles_404(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
    mocker.patch('requests.get', return_value=mock_response)

    provider = ThePornDBProvider()
    result = provider._api_request("scenes/999")

    assert result is None

def test_api_request_retries_on_failure(mocker):
    # First two calls fail, third succeeds
    mocker.patch('requests.get', side_effect=[
        requests.Timeout,
        requests.Timeout,
        mocker.Mock(json=lambda: {"id": 123})
    ])

    provider = ThePornDBProvider()
    result = provider._api_request_with_retry("scenes/123")

    assert result == {"id": 123}
```

---

## Workflow Tips

### Daily Routine

1. **Morning:** Check phash test results

   ```bash
   poetry run pytest test/stashdb_phash_ambiguity_test.py -v
   ```

2. **After each PR:** Run full comparison test suite

   ```bash
   poetry run pytest test/comparison_results_test.py -v
   ```

3. **Monitor phash accuracy** via logs

   ```bash
   grep "phash_confidence" logs/namer.log | awk '{print $NF}' | sort -n
   ```

### Common Pitfalls

#### 1. **Path Validation Too Strict**

**Symptom:** Valid files rejected during processing

**Solution:** Allow temporary non-existence during file creation:

```python
def __init__(self, file_path: str, allow_missing: bool = False, ...):
    path_obj = Path(file_path)

    if not allow_missing and not path_obj.exists():
        raise ValueError(f"File not found: {file_path}")
```

#### 2. **Phash Confidence Calculation Errors**

**Symptom:** Confidence scores >1.0 or <0.0

**Solution:** Clamp values:

```python
def calculate_phash_confidence(distance: int, threshold: int) -> float:
    if distance > threshold:
        return 0.0

    confidence = 1.0 - (distance / (threshold * 2))
    return max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
```

#### 3. **API Retry Storms**

**Symptom:** Excessive retries overwhelm API

**Solution:** Add exponential backoff:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30)
)
```

### Communication Protocol

**When to post in `#migration-ambiguity-review`:**

- ✅ D1 merged (start D2)
- ✅ D2 merged (start D3)
- ✅ D3 merged (phash improvements live)
- ✅ D4 merged (workstream complete)

**When to escalate:**

- Phash tests fail after D3 changes
- API error handling breaks existing integrations
- Path validation rejects valid files

---

## Testing Checklist

Before merging each PR:

### D1

- [ ] ComparisonResult validates file paths
- [ ] Absolute paths stored
- [ ] Tests cover missing files, directories, relative paths

### D2

- [ ] Phash flag uses property/setter
- [ ] Type validation prevents non-boolean assignments
- [ ] Logging tracks phash match status changes

### D3

- [ ] Confidence calculation implemented
- [ ] ComparisonResult includes confidence field
- [ ] Phash tests pass with new logic
- [ ] Confidence scores in range [0.0, 1.0]

### D4

- [ ] All API calls wrapped in try/except
- [ ] Timeout protection added
- [ ] Retry logic implemented
- [ ] Tests cover timeout, 404, network errors

---

## Success Criteria

- ✅ All 4 PRs merged by end of Week 2
- ✅ Comparison results always have valid paths
- ✅ Phash matching includes confidence scores
- ✅ ThePornDB provider handles network errors gracefully
- ✅ Phash test suite passes with ≥95% accuracy

---

## Resources

- **Migration Plan:** [migration-plan-fix-ambiguity-review.md](migration-plan-fix-ambiguity-review.md)
- **Delivery Plan:** [delivery-plan-fix-ambiguity-review.md](delivery-plan-fix-ambiguity-review.md)
- **Migration Utilities:** [migration-utilities.md](migration-utilities.md) - Cherry-pick helper, time tracking, coverage comparison
- **Source Commits:** `fix/ambiguity-review` (commits `8d1fcd9`, `0381399`, `65b8c44`, `f4361a2`)
- **Test Suite:** `test/stashdb_phash_ambiguity_test.py`, `test/comparison_results_test.py`

---

**Workstream Owner:** Backend Engineer 3
**Last Updated:** 2025-10-06
**Status:** Ready to Start
