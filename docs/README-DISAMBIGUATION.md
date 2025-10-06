# Scene Disambiguation

This feature helps avoid incorrect matches when multiple candidate scenes are close by perceptual hash (pHash). When enabled, the decision engine applies threshold rules to accept, reject, or mark a result as ambiguous. Ambiguous results can be routed to a separate folder for manual review.

- Provider-agnostic: works with both StashDB and ThePornDB providers
- Opt‑in: default is disabled (preserves current behavior)

## Enabling

In your `namer.cfg` under the `[namer]` section:

```ini
[namer]
# Feature flag to enable scene disambiguation logic (off by default)
enable_disambiguation = True
```

When disabled, behavior is unchanged.

## Ambiguous routing directory

Optionally configure a destination directory for ambiguous results in the `[watchdog]` section:

```ini
[watchdog]
# Directory to route files to when disambiguation determines results are ambiguous
ambiguous_dir = ./ambiguous
```

Notes:
- Must exist and be writable before startup.
- Must not be nested inside `watch_dir`, `work_dir`, `failed_dir`, or `dest_dir`.
  Create it ahead of time:
  
  ```bash
  mkdir -p ./ambiguous
  ```
- Files are routed here only when `enable_disambiguation = True` and the decision engine concludes the result is ambiguous.

### Artifacts created for ambiguous files

When a file is routed to `ambiguous_dir`, the following artifacts are written alongside the moved media (relative to the ambiguous directory):

- `<stem>_namer_summary.json`: Structured summary produced by `_build_summary()` containing the top-ranked `results`, parsed `fileinfo`, and ambiguity metadata.
  - `ambiguous_reason`: String key describing why the result was ambiguous (for example `phash_decision_ambiguous`, `phash_consensus_not_met`, or `phash_missing_guids`).
  - `candidate_guids`: Ordered list of GUIDs (or scene names when GUIDs are unavailable) that should be reviewed manually.
- `<stem>.ambiguous.json`: Lightweight note containing:
  - `ambiguous_reason`: Same reason string as above
  - `candidate_guids`: Simple array of GUID strings for programmatic access
  - `candidates`: Array of objects with `{guid, name}` pairs for rich UI display
- `<stem>_namer.json.gz`: Gzipped `ComparisonResults` dump used by legacy tooling. The encoded object now includes the same `ambiguous_reason` and `candidate_guids` attributes for completeness.

These outputs help downstream automation, UIs, or operators understand why the scene required disambiguation and which candidates to check. All artifacts use the consistent field name `candidate_guids` to match the `ComparisonResults.candidate_guids` attribute.

## Thresholds (provider‑agnostic)

Fine‑tune the decision thresholds under the `[Phash]` section:

```ini
[Phash]
# Maximum Hamming distance to accept directly when other conditions are met
phash_accept_distance = 6

# Ambiguous band (inclusive): results within this range are considered weak signals
phash_ambiguous_min = 7
phash_ambiguous_max = 12

# Accept the best candidate if it is at least this much closer than the second‑best
phash_distance_margin_accept = 3

# Accept the best candidate if the majority of fingerprints point to its GUID
# even when the distance margin is small (range: 0.0 – 1.0)
phash_majority_accept_fraction = 0.7
```

Decision summary:
- Accept if best distance ≤ `phash_accept_distance` and either:
  - Best is ahead of second‑best by ≥ `phash_distance_margin_accept`, or
  - The best GUID holds a fraction ≥ `phash_majority_accept_fraction` of the pHash hits.
- Ambiguous if best falls inside the ambiguous band [`phash_ambiguous_min`, `phash_ambiguous_max`] or the above accept conditions are not met and there are conflicting close candidates.
- Reject when the best distance is beyond `phash_ambiguous_max`.

Defaults are tuned conservatively; adjust based on your library and quality goals.

Misconfigurations (e.g., invalid ranges) are reported by the config verifier at startup.

## Hardware acceleration and performance (optional)

If you use the alternative pHash tool, hardware acceleration can speed extraction. See:

- `docs/README-GPU-ACCELERATION.md`
- `docs/README-INTEL-GPU.md`

Relevant keys (under `[Phash]`):

- `use_alt_phash_tool`
- `max_ffmpeg_workers`
- `use_gpu`
- `ffmpeg_hwaccel_backend`
- `ffmpeg_hwaccel_device`
- `ffmpeg_hwaccel_decoder`

Leave them empty to use automatic detection or see the GPU docs for examples.

## Minimal example

```ini
[namer]
metadata_provider = stashdb
enable_disambiguation = True

[Phash]
phash_accept_distance = 6
phash_ambiguous_min = 7
phash_ambiguous_max = 12
phash_distance_margin_accept = 3
phash_majority_accept_fraction = 0.7

[watchdog]
watch_dir = ./watch
work_dir = ./work
failed_dir = ./failed
ambiguous_dir = ./ambiguous
dest_dir = ./dest
```

## FAQ

- Q: Do I have to configure `ambiguous_dir`?
  
  A: No. If you don’t set it, ambiguous results are not routed and standard flow continues. If you do set it, ensure it exists and is writable.

- Q: Does this change existing behavior?
  
  A: Not unless you enable the feature flag. With `enable_disambiguation = False`, behavior is unchanged.

- Q: Is this tied to a specific provider?
  
  A: No, thresholds are provider‑agnostic and operate on the pHash distance and majority metrics.
