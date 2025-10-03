# Tracking: DRY ffmpeg suffix helper, phash flag API, and toast UX

Title: Polish items from PR #95 reviews
Labels: enhancement, refactor, frontend, tech-debt

Summary
- Extract a helper in FFMpeg to generate cryptographically secure random suffixes used for temp filenames, and use it in both ffmpeg.py and ffmpeg_enhanced.py to remove duplication.
- Decide on API surface for phash-origin flag in ComparisonResults: either expose as public field found_via_phash (and keep in as_dict), or keep private and rely on getter; align dictionary output accordingly. Remove extra blank lines in dataclass fields for consistent style.
- Frontend: replace blocking alert() calls with Bootstrap toasts (or inline, non-blocking notifications) in src/js/helpers.js for better UX.

Acceptance criteria
- A private method FFMpeg._generate_random_suffix(length: int = 10) -> str exists and is used at both call sites in ffmpeg.py and ffmpeg_enhanced.py.
- ComparisonResults: one of the following is implemented:
  - Public attribute found_via_phash consistently documented and present in as_dict
  - OR keep _found_via_phash private; remove it from as_dict and ensure callers use found_via_phash() getter
  Document the decision in CHANGELOG/UPGRADE notes if API changes.
- helpers.js: error presentation uses Bootstrap toasts (or similar) instead of alert(), with graceful fallback when Bootstrap is unavailable.

Notes
- Keep changes minimal and aligned with existing project patterns. Avoid introducing new error-handling frameworks; reuse existing logging and UX conventions.
- Ensure tests still pass; add or update unit tests where feasible (e.g., for ComparisonResults as_dict behavior).
- Coordinate changes with the “dual-file maintenance” rule for ffmpeg modules.
