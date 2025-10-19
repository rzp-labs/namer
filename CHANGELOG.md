# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.23.8] - 2025-10-19 - HOTFIX

### 🔥 Critical Fixes
- Fix StashDB GraphQL validation errors (#TBD)
  - **Root cause**: Missing subfield selections for `images` field in performer queries
  - **Impact**: All StashDB file processing was failing with 422 validation errors
  - **Resolution**: Added required `url` subfield selection to performer `images` in all GraphQL queries (findScene, searchScene, findSceneByFingerprint)
  - **Error**: `Field "images" of type "[Image!]!" must have a selection of subfields`

## [1.23.7] - 2025-10-18

### Added
- Maintain original filename in file metadata (#160)
  - Preserves `source_file_name` for all files regardless of parsing success
  - Ensures original filename is available for reference and debugging
  - Comprehensive test coverage for full match, partial match, and no match scenarios

### Fixed
- Resolve subshell file I/O breaking deduplication in quick-check.sh
  - Fixed file descriptor handling in process substitution
  - Improved reliability of duplicate detection script
  - Better error handling for edge cases

### Changed
- Resolve merge conflict in quick-check.sh following backmerge/v1.23.6

### Documentation
- Fix git log flag typo in zsh compatibility example
  - Corrected command syntax for cross-shell compatibility

## [1.23.6] - 2025-10-17

### Changed
- Fail-safe exclusion pattern for docker-smoke-test hook (#157)
  - Uses exclusion pattern instead of inclusion for better reliability
  - Case-insensitive matching for robust file detection
  - Prevents silent skips when new build file types are added
- Standardized Poetry installation using pipx in CI workflows (#156)
- Git Flow process improvements and documentation enhancements

### Fixed
- Release PR target now correctly points to main branch (not develop)
- Git tag fetching in release workflow
- Multiple code review feedback items addressed

### Infrastructure
- Added git-push-wrapper.sh for handling longer pre-push hook timeouts
- Command audit framework and slash command design patterns
- Improved branch lifecycle management documentation
- Enhanced CI/CD alignment with repository standards

### Dependencies
- Bumped peter-evans/create-pull-request from 6.1.0 to 7.0.8
- Updated minor and patch Python dev dependencies
- Updated minor and patch GitHub Actions versions

## [1.23.3] - 2025-10-13

### Added
- Comprehensive session notes and learning documentation for 2025-10-13
- Automated release tag creation on PR merge (#115)
- Test video optimization script for creating optimized test fixtures
- Enhanced metadata provider data handling (#112)

### Changed
- Stratified git hooks with timeout enforcement (#121)
  - Pre-commit hooks (~15-20s): Fast quality + functional validation
  - Pre-push hooks (~2min): Comprehensive quality gate
- File type filtering for git hooks to skip unnecessary work
  - 70%+ time savings on documentation-only changes
  - Instant commit/push for docs and config-only changes
- Removed CodeRabbit from pre-push pipeline (#126)
- Removed Codacy from local pre-push hooks (CI only)
- Streamlined videohashes dependency management (#110)

### Fixed
- Critical CodeRabbit findings in hook system (#123)
- Dict key mismatch and misleading docstring (P1 issues) (#122)
- Mypy type errors in test files (#120)
- Command queue logic improvements (#116)
- Ambiguous routing enhancements and code quality improvements (#104)

### Performance
- Skip Docker smoke test when build files unchanged
- Skip pytest hooks when no Python files modified
- Optimized hook execution based on file type changes

### Infrastructure
- Use docker buildx for multi-platform image builds
- Enforce pnpm as the sole package manager
- Node.js version check and validation
- Pre-commit framework for git hooks (Python-native)

## [1.23.0] - 2024-XX-XX

### Added
- Initial release with improved metadata provider handling

## [1.22.0] - Previous Release

- Previous version baseline

[1.23.3]: https://github.com/nehpz/namer/compare/v1.22.0...v1.23.3
[1.23.0]: https://github.com/nehpz/namer/compare/v1.22.0...v1.23.0
[1.22.0]: https://github.com/nehpz/namer/releases/tag/v1.22.0
