# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
