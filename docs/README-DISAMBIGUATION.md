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
- If set, ensure this directory is writable by the process. Depending on the version, config verification may expect the directory to already exist. To avoid verification failures, create it ahead of time (recommended):
  
  ```bash
  mkdir -p ./ambiguous
  ```
- Files are routed here only when `enable_disambiguation = True` and the decision engine concludes the result is ambiguous.

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
