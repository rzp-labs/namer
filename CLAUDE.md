# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Namer** is a Python-based video file naming application that uses metadata from porndb. It's built with:
- **Flask** web framework for the UI
- **Poetry** for dependency management
- **Ruff** for linting and formatting
- **pytest** for testing
- **mypy** for type checking
- **pnpm** for frontend asset management
- **Docker** for containerization

## Development Commands

### Primary Interface (Make)
Always prefer Make commands - they provide a stable interface and allow implementation changes without doc updates.

**Setup & Validation:**
- `make setup-dev` - Bootstrap Poetry, install dependencies, and git hooks
- `make validate` - Run comprehensive pre-push validation
- `make config` - Show current build configuration

**Docker Builds:**
- `make build` - Fast Docker build (recommended for development)
- `make build-full` - Complete build with all tests (~20 min)
- `make build-validated` - Validate then fast build
- `make build-amd64` / `make build-arm64` - Platform-specific builds

**Testing:**
- `make test` - Test Docker container (basic functionality)
- `make test-integration` - Run integration tests

**Workflows:**
- `make dev-cycle` - Quick development cycle (build + test)
- `make release-prep` - Full release preparation (validate + build + test)

**Cleanup:**
- `make clean` - Clean temporary files and containers
- `make clean-deep` - Deep clean (removes everything including VM)

### Direct Poetry/Poe Commands (for local dev)
Use these when working directly with Python code (not Docker):
- `poetry install` - Install/update dependencies
- `poetry shell` - Activate virtual environment
- `poe test` - Run linting and fast tests locally
- `poe test_format` - Run Ruff linting checks
- `poe test_namer` - Run pytest (excluding slow tests)
- `poe precommit` - Pre-commit checks (format + unit tests)

### Testing Commands
- `poetry run pytest` - Run all tests
- `poetry run pytest -v` - Run tests with verbose output
- `poetry run pytest --cov=namer` - Run tests with coverage report
- `poetry run pytest -x` - Stop on first failure
- `poetry run pytest -k "test_name"` - Run specific test by name
- `poetry run pytest -m "not slow"` - Skip slow tests
- `poetry run pytest -m "slow"` - Run only slow tests

### Code Quality Commands
- `poetry run ruff check .` - Run Ruff linter
- `poetry run ruff check --fix .` - Run Ruff and auto-fix issues
- `poetry run ruff format .` - Format code with Ruff
- `poetry run ruff format --check .` - Check formatting without changes
- `poetry run mypy namer/` - Run type checking with MyPy
- `poetry run bandit -r namer/` - Run security checks

### Additional Make Commands
See all available targets:
- `make help` - Show all available Make targets with descriptions
- `make review` - Run CodeRabbit branch review
- `make lint` / `make format` - Code quality checks
- `make test-local` - Fast local testing without Docker
- `make quick` - Quick feedback loop (lint-fix + fast tests)

**Note:** Docker image builds/pushes to GHCR are **always** done through CI/CD (GitHub Actions), never locally.

## Technology Stack

### Core Technologies
- **Python 3.11+** - Primary programming language
- **Poetry** - Dependency management and packaging
- **Flask 3.1+** - Web framework
- **Waitress** - Production WSGI server
- **Pony ORM** - Database ORM

### Frontend
- **Bootstrap 5** - UI framework
- **jQuery** - DOM manipulation
- **DataTables** - Table management
- **Webpack** - Asset bundling
- **pnpm** - Node package manager

### Processing & Utilities
- **ffmpeg-python** - Video processing
- **watchdog** - File system monitoring
- **requests-cache** - HTTP caching
- **Pillow** - Image processing
- **numpy/scipy** - Numerical processing

### Testing & Quality Tools
- **pytest 8.4+** - Testing framework
- **pytest-cov** - Coverage plugin
- **assertpy** - Fluent assertions
- **selenium** - Browser automation for web tests
- **Ruff 0.13+** - Fast linter and formatter (replaces black/flake8/isort)
- **mypy 1.11+** - Static type checker
- **bandit** - Security linter
- **pre-commit** - Git hooks framework
- **poethepoet** - Task runner

## Project Structure

### Actual File Organization
```
namer/                   # Main package (NOT src/)
├── __init__.py
├── __main__.py          # Application entry point
├── command.py           # CLI commands
├── configuration.py     # Config management
├── database.py          # Pony ORM models
├── ffmpeg*.py           # Video processing
├── metadata_providers/  # Data source integrations
├── models/              # Data models
├── web/                 # Flask web application
│   ├── routes/          # API & page routes
│   ├── templates/       # Jinja2 templates
│   └── public/          # Static assets (built by webpack)
└── tools/               # Binary tools (videohashes)

test/                    # Test directory (NOT tests/)
├── __init__.py
├── *_test.py            # Test modules
├── integration/         # Integration tests
└── *.mp4, *.json        # Test fixtures

config/                  # Configuration examples
scripts/                 # Build and utility scripts
docs/                    # Documentation
```

### Naming Conventions
- **Files/Modules**: Use snake_case (`user_profile.py`)
- **Classes**: Use PascalCase (`UserProfile`)
- **Functions/Variables**: Use snake_case (`get_user_data`)
- **Constants**: Use UPPER_SNAKE_CASE (`API_BASE_URL`)
- **Private methods**: Prefix with underscore (`_private_method`)

## Python Guidelines

### Type Hints
- Use type hints for function parameters and return values
- Import types from `typing` module when needed
- Use `Optional` for nullable values
- Use `Union` for multiple possible types
- Document complex types with comments

### Code Style
- Follow PEP 8 style guide (enforced by Ruff)
- Use meaningful variable and function names
- Keep functions focused and single-purpose
- Use docstrings for modules, classes, and functions
- Line length: 320 characters (project standard, not 88)
- Quote style: single quotes (configured in ruff)

### Best Practices
- Use list comprehensions for simple transformations
- Prefer `pathlib` over `os.path` for file operations
- Use context managers (`with` statements) for resource management
- Handle exceptions appropriately with try/except blocks
- Use `logging` module instead of print statements

## Testing Standards

### Test Structure
- Organize tests to mirror source code structure
- Use descriptive test names that explain the behavior
- Follow AAA pattern (Arrange, Act, Assert)
- Use fixtures for common test data
- Group related tests in classes

### Coverage Goals
- Aim for 90%+ test coverage
- Write unit tests for business logic
- Use integration tests for external dependencies
- Mock external services in tests
- Test error conditions and edge cases

### pytest Configuration
```ini
# pytest.ini (actual project config)
[pytest]
markers =
    slow: marks tests as slow

# Run fast tests only (default):
poetry run pytest -m "not slow"

# Run all tests:
poetry run pytest

# Test with coverage:
poetry run pytest --cov=namer --cov-report=html
```

## Development Environment Setup

### Poetry-Based Workflow
```bash
# One-time setup (installs Poetry, deps, and git hooks)
make setup-dev

# Or manually:
poetry install                    # Install all dependencies
poetry shell                      # Activate virtual environment

# Add dependencies
poetry add requests               # Production dependency
poetry add --group dev pytest     # Dev dependency

# Update dependencies
poetry update                     # Update all
poetry update requests            # Update specific package
```

### Dependency Management
- All dependencies managed in `pyproject.toml`
- Use `[tool.poetry.dependencies]` for production
- Use `[tool.poetry.group.dev.dependencies]` for development
- Poetry automatically manages `poetry.lock` for reproducibility

## Flask-Specific Guidelines (This Project)

### Flask Application Structure
```
namer/web/
├── __init__.py          # Flask app factory
├── server.py            # Server configuration
├── routes/
│   ├── api.py           # API endpoints
│   └── pages.py         # Page routes
├── templates/           # Jinja2 templates
│   └── *.html
└── public/              # Static assets (webpack output)
    └── assets/
```

### Running the Application
```bash
# Development mode
poetry run python -m namer

# Production mode (using Waitress)
poetry run python -m namer --port 8080

# Docker
docker run -p 6980:6980 nehpz/namer:latest
```

### Configuration
- Configuration file: `namer.cfg` (based on `namer.cfg.default`)
- Environment variables supported via `.env`
- Database: Pony ORM with SQLite (default) or PostgreSQL

## Security Guidelines

### Dependencies
- Update dependencies: `poetry update`
- Check outdated: `poetry show --outdated`
- Security scanning: `poetry run bandit -r namer/`
- Dependencies are pinned in `poetry.lock`
- Sensitive packages pinned: attrs<25, cattrs<25 (see pyproject.toml)

### Code Security
- Validate input data with Pydantic or similar
- Use environment variables for sensitive configuration
- Implement proper authentication and authorization
- Sanitize data before database operations
- Use HTTPS for production deployments

## Git Flow Workflow

This project uses **Git Flow** branching model.

### Branch Structure
- **main** - Production-ready code, tagged releases only
- **develop** - Integration branch for features
- **feature/** - New features (branch from develop)
- **release/** - Release preparation (branch from develop)
- **hotfix/** - Emergency fixes (branch from main)

### Common Operations

**Start new feature:**
```bash
git flow feature start my-feature
# or manually: git checkout -b feature/my-feature develop
```

**Finish feature (merge to develop):**
```bash
git flow feature finish my-feature
# or manually: merge to develop and delete branch
```

**Start release:**
Use GitHub Actions "Bump Version and Open Release PR" workflow instead of manual git-flow release.

**Hotfix:**
```bash
git flow hotfix start hotfix-name
git flow hotfix finish hotfix-name
```

### Development Workflow

### Before Starting
1. Ensure Python 3.11+ is installed
2. Run `make setup-dev` for complete environment setup
3. Ensure you're on `develop` branch for new features

### During Development (Docker workflow)
1. Create feature branch from `develop`
2. Make code changes
3. Run `make dev-cycle` to build and test quickly
4. Use meaningful commit messages (conventional commits)
5. Let pre-commit hooks auto-format code (installed by setup-dev)

### During Development (Local Python workflow)
1. Create feature branch from `develop`
2. Activate Poetry shell: `poetry shell`
3. Make code changes
4. Run `poe test` for quick validation
5. Use meaningful commit messages

### Git Hooks (pre-commit framework)

This project uses Python's **pre-commit** framework for git hooks (NOT Husky).

#### Stratified Hook Philosophy

We use a **stratified approach** that separates fast commit-time validation from thorough push-time quality gates:

**Pre-commit Hooks: Fast Quality + Functional Validation (~15-20 seconds)**
- **Purpose:** Immediate feedback on code quality AND functionality
- **Philosophy:** Fast enough not to disrupt flow, thorough enough to catch real issues
- **Checks:**
  - Ruff linting with auto-fix (`--fix`) - Style consistency
  - Ruff formatting - Code formatting
  - mypy type checking - Catch type errors early before they accumulate
  - pytest fast tests - 78 tests in ~4 seconds for comprehensive functional validation
  - Shellcheck - Bash script validation
  - Actionlint - GitHub Actions workflow validation
  - Hadolint - Dockerfile linting (optional)

**Pre-push Hooks: Deep Validation + Security (~3-5 minutes)**
- **Purpose:** Full quality gate before team review - "production ready" validation
- **Philosophy:** Ready to push = ready for team review = high confidence in quality and security
- **Checks:**
  - Full pytest suite with coverage - All tests including watchdog, web, videophash, and slow tests
  - Codacy security analysis - Security vulnerabilities, code quality, complexity analysis
  - CodeRabbit AI review - Design patterns, best practices, security concerns
  - Docker smoke test - Quick build validation to catch Dockerfile/build errors

**Why this approach:**
1. **Type safety shift-left** - Catch type errors at commit time before they pile up
2. **Fast pytest in pre-commit** - 78 tests in 4 seconds provides excellent functional coverage
3. **Security built-in** - Codacy catches vulnerabilities before push
4. **No skipped tests on push** - Full test suite including watchdog (core functionality)
5. **Docker validation** - Catch build errors locally before CI
6. **Clear separation** - Commit (fast iteration) vs Push (comprehensive gate)

**Manual execution:**
- `pre-commit run --all-files` - Run all pre-commit hooks manually
- `pre-commit run --hook-stage pre-push --all-files` - Run all pre-push hooks manually
- `poe precommit` - Alternative: format checking + fast tests

**Hook management:**
- Hooks are installed automatically by `make setup-dev`
- Configuration: `.pre-commit-config.yaml`
- Update hooks: `pre-commit autoupdate`
- Skip hooks (not recommended): `git commit --no-verify` or `git push --no-verify`

### Before Pushing
**Comprehensive validation:**
- `make validate` - Full validation suite (required before PR)

### Creating Pull Requests
- Feature branches → merge to `develop`
- Release branches → merge to `main` (via automated workflow)
- Hotfix branches → merge to both `main` and `develop`

### Release Process
**Do not use `git flow release`** - instead use the automated GitHub Actions workflow (see `/release` command or release.md)

## Troubleshooting & Best Practices

### Hook Performance & Timing

**Pre-commit Hook Performance (~15-20 seconds):**
```
Breakdown:
- Ruff linting + format: ~2-3s
- mypy type checking: ~2-3s
- pytest fast tests (78 tests): ~4-5s
- Shellcheck: ~1s
- Actionlint: ~1s
- Hadolint: ~1s
Total: ~15-20s
```

**Pre-push Hook Performance (~3-5 minutes):**
```
Breakdown:
- Full pytest with coverage: ~90s (timeout: 10min - generous for slow systems)
- Codacy security analysis: ~60-90s (timeout: 5min)
- CodeRabbit AI review: ~60-120s (timeout: 10min - faster for small commits!)
- Docker smoke test: ~30-60s (timeout: 10min - generous for cold builds)
Total: ~3-5 minutes typical, up to 10min for comprehensive runs

Note: Timeouts are generous to handle network delays, cold builds, and complex reviews.
      Smaller commits complete much faster than the timeout limits.
```

**Why stratified hooks work:**
- Pre-commit is fast enough not to disrupt flow (< 20s)
- Pre-commit catches 90% of issues early (types, tests, style)
- Pre-push provides deep validation before team review
- Clear separation prevents frustration and bypass temptation

### Git Hooks Best Practices

**NEVER bypass pre-push hooks:**
- ❌ **`git push --no-verify`** - STRICTLY PROHIBITED
- ❌ Bypassing skips security scans, tests, and quality gates
- ❌ Puts broken code into shared branches
- ✅ If hooks are slow, **break work into smaller commits**
- ✅ Small commits = faster CodeRabbit reviews = quicker delivery

**Why this policy:**
1. **Security first** - Codacy catches vulnerabilities before they're shared
2. **Quality gates** - Full test suite ensures functionality
3. **Team protection** - Don't break others' workflows
4. **Better practices** - Small, focused commits are better engineering

**If pre-push hooks seem slow:**
- Review your commit size - are you committing too much at once?
- Break large changes into smaller, logical commits
- Smaller commits review faster and are easier to understand
- Example: Instead of one 2000-line commit, create 5 focused 400-line commits

**Hook timeout guidelines:**
- pytest full suite: 10 minutes max (typically completes in ~90s)
- Codacy analysis: 5 minutes max (typically completes in ~60-90s)
- CodeRabbit review: 10 minutes max (typically completes in ~60-120s, faster for small commits!)
- Docker smoke test: 10 minutes max (typically completes in ~30-60s, generous for cold builds)

**Common hook issues:**
1. **Timeout** - Commit too large? Break it into smaller pieces
2. **Type errors** - Run `poetry run mypy .` locally first (caught in pre-commit)
3. **Test failures** - Fix tests before pushing (caught in pre-commit fast tests)
4. **Security issues** - Address Codacy findings
5. **CodeRabbit feedback** - Address design/quality issues

### Type Checking Tips

**Common mypy issues and fixes:**

1. **Callable import error:**
   ```python
   # ❌ Wrong
   from typing import Callable

   # ✅ Correct (Python 3.11+)
   from collections.abc import Callable
   ```

2. **Redundant type annotations after unpacking:**
   ```python
   # ❌ Redundant
   with environment() as (temp_dir, fake_tpdb, config):
       temp_dir: Path
       fake_tpdb: FakeTPDB
       config: NamerConfig

   # ✅ Correct - types inferred from tuple unpacking
   with environment() as (temp_dir, fake_tpdb, config):
       # No redundant annotations needed
   ```

3. **Optional Path attributes:**
   ```python
   # ❌ Assumes Path is never None
   files = list(config.watch_dir.iterdir())

   # ✅ Check for None first
   watch_dir = config.watch_dir
   if watch_dir:
       files = list(watch_dir.iterdir())
   ```

### Development Workflow Insights

**Make targets usage:**
- `make quick` - Fast feedback during development (~11s)
- `make validate` - Full validation before push (~2-3 min)
- `make test-local` - Local tests without Docker
- `make ci` - Simulate CI environment locally

**Git hooks workflow (stratified approach):**
- **Pre-commit (~15-20s):** Fast quality + functional validation
  - Auto-formats code with Ruff
  - Catches type errors with mypy
  - Runs 78 fast tests for functional coverage
  - Validates scripts and configs
- **Pre-push (~3-5min):** Comprehensive quality gate
  - Full test suite with coverage (all tests, no filtering)
  - Codacy security analysis
  - CodeRabbit AI review
  - Docker build validation
- **Manual:** `make validate` for full CI simulation with Docker integration

### Dependency Management

**Adding type stubs:**
```bash
# When mypy complains about missing stubs
poetry add --group dev types-requests
poetry add --group dev types-<package-name>
```

**Python-native tooling preference:**
- ✅ Use pre-commit (Python) over Husky (Node.js)
- ✅ Use Ruff (Python) over ESLint (Node.js) for Python
- ✅ Keep tooling consistent with project language

---

## Pull Request Strategy

### Atomic PR Guidelines

**Goal**: Create focused, reviewable PRs that respect reviewer time and project quality standards.

**Optimal Size**: 200-500 lines per PR, single focused concern

**When to Split Large Branches**:
- Branch exceeds 500 lines across multiple files
- Multiple distinct concerns mixed together
- Review cycles becoming slow (>1 day for initial feedback)
- Changes can be logically separated

**Splitting Strategy**:

**Sequential PRs** (use when documentation/config evolves):
1. Analyze commits: `git log develop..HEAD --oneline`
2. Create atomic branches from develop
3. Cherry-pick commits: `git cherry-pick <hash>`
4. Handle conflicts strategically (`git checkout --ours` for complete implementations)
5. Push and create PR with context

**Parallel PRs** (use when changes are independent):
- Split by feature/concern
- No shared files modified
- Can be reviewed/merged independently

**Real-World Example**:
- **Original**: 1 PR, 12 commits, 1,445 lines → 10+ min review time
- **Split**: 5 PRs averaging 300 lines → <5 min review time each
- **Result**: Faster reviews, parallel progress, lower merge risk

**PR Series Template**:
```markdown
## Part of Series
This is **PR #X of N** from `feature/large-branch`:
1. PR #1: Foundation (type safety, dependencies)
2. **This PR**: Core functionality
3. PR #3: Integration (depends on this)
4. PR #4: Bug fixes
5. PR #5: Documentation
```

---

## AI Code Review Integration

### Gemini Code Assist Workflow

This project uses Gemini Code Assist for automated PR reviews. Use the `/gemini-review` command to analyze and action feedback.

**Workflow**:
```bash
1. Create PR → Gemini reviews automatically
2. Run: /gemini-review [pr-number]
3. Analyze suggestions by category
4. Implement high-priority items
5. Document decisions in PR comments
6. Reference in commit messages
```

**Decision Framework**:

| Priority | Criteria | Action |
|----------|----------|--------|
| **Must-Fix** | Security vulnerabilities, data integrity issues, breaking changes, critical performance (>100ms) | Implement immediately |
| **Should-Fix** | Maintainability issues, moderate performance (10-100ms), important best practices | Implement in same PR |
| **Nice-to-Have** | Style improvements, minor optimizations (<10ms), optional refactoring | Consider for follow-up PR |
| **Skip** | Conflicts with project standards, out of scope, low ROI | Document why skipped |

**Not All AI Feedback Requires Action**:
- Formatting suggestions that conflict with Ruff configuration → Skip
- Style preferences vs project standards → Skip (maintain consistency)
- Out-of-scope suggestions → Defer to separate PR
- Technical debt observations → Evaluate ROI vs effort

**PR Comment Template**:
```markdown
## Addressed Gemini Code Assist Feedback

### Implemented (commit abc123):
- **Suggestion**: [What Gemini suggested]
- **Action**: [What you did]
- **Benefit**: [Why it improves the code]

### Deferred:
- **Suggestion**: [What Gemini suggested]
- **Reason**: [Why deferring - separate PR, out of scope, etc.]

### Declined:
- **Suggestion**: [What Gemini suggested]
- **Reason**: [Why declining - conflicts with project config, etc.]
```

---

## Cross-Platform Development

### Platform Compatibility Patterns

**Timeout Commands** (macOS vs Linux):
- macOS: `gtimeout` (via `brew install coreutils`)
- Linux: `timeout` (built-in)

**Detection Pattern**:
```bash
TIMEOUT_CMD=$(command -v gtimeout || command -v timeout || echo "")
if [ -n "$TIMEOUT_CMD" ]; then
    exec "$TIMEOUT_CMD" "$SECONDS" "$@"
else
    warn "No timeout available, running without limit"
    exec "$@"
fi
```

**Project Implementation**: `scripts/timeout-wrapper.sh`
- Usage: `./scripts/timeout-wrapper.sh <seconds> <command> [args...]`
- Handles platform detection automatically
- Provides helpful warnings when timeout unavailable
- Used by all pre-push git hooks

**Best Practices**:
- Always use **feature detection**, not platform detection
- Provide **graceful fallbacks** with warnings
- Centralize platform-specific logic in reusable scripts
- Test on both macOS and Linux before merging

**Filename Sanitization Patterns** (Critical for scripts):
```bash
# ❌ Wrong - triggers shellcheck warnings
SAFE_BRANCH=$(echo "$BRANCH" | sed 's|/|-|g')

# ✅ Correct - bash parameter expansion (shellcheck compliant)
SAFE_BRANCH="${BRANCH//\//-}"

# Use case: Branch names with slashes (feature/name) break filename construction
FEEDBACK_FILE="${TIMESTAMP}_${SAFE_BRANCH}_${COMMIT}.txt"
```

**Robust Filename Parsing** (Critical for structured filenames):
```bash
# Problem: Simple cut breaks with underscores in branch names
# Bad: BRANCH=$(echo "$FILENAME" | cut -d'_' -f2)  # Fragile!

# ✅ Extract from edges inward
FILENAME=$(basename "$FILE" .txt)
COMMIT=$(echo "$FILENAME" | rev | cut -d'_' -f1 | rev)  # Last field
BRANCH=$(echo "$FILENAME" | sed "s/^[^_]*_//; s/_${COMMIT}$//")  # Middle

# Handles: 2025-10-13-06-11-39_feat-my_feature_name_abc123.txt correctly
```

**Race Condition Prevention**:
```bash
# ❌ Wrong - hardcoded temp file causes race conditions
gh issue create ... > /tmp/issue_url.txt

# ✅ Correct - unique temp file with cleanup
local temp_file
temp_file=$(mktemp)
trap 'rm -f "$temp_file"' RETURN
gh issue create ... > "$temp_file"
```

---

## Lessons Learned

### Key Insights from Practice

**1. Atomic PRs Deliver Measurable ROI**
- Investment: ~1 hour to split large branch
- Return: 20x faster review time (30s vs 10min)
- Benefit: Parallel progress, lower risk, easier rollback
- Pattern: 200-500 lines per PR = optimal reviewer experience

**2. Respect Auto-Formatting Configuration**
- Don't make manual changes that conflict with Ruff
- If formatting is problematic, update Ruff config project-wide
- Consistency across codebase > isolated "readability" improvements
- Pre-commit hooks will revert manual formatting changes

**3. Generous Timeouts Prevent False Failures**
- 10min timeout with ~90s typical execution = best UX
- Accommodates: slow systems, network delays, first-time package downloads
- Prevents frustration from timeout failures on edge cases
- Pattern: Generous safety margin + fast typical execution

**4. Context-Appropriate Hook Bypass**
- ✅ Acceptable: When modifying hook system itself (chicken-egg problem)
- ✅ Acceptable: Atomic PRs missing build scripts (focused scope)
- ❌ Never: To skip failing tests or security scans
- ❌ Never: To bypass hooks before pushing to shared branches

**5. Sequential > Parallel for Evolving Documentation**
- When CLAUDE.md or configs evolve across commits, expect conflicts
- Sequential PRs (building on each other) easier than parallel splits
- Resolve conflicts by keeping more complete implementation
- Document resolution rationale in merge commit message

**6. Selective Fix Application (Atomic PR Extraction)**
- Cherry-picking entire commits can include unrelated changes
- **Better approach:** Manually apply only relevant fixes per feature area
- **Process:** Review `git show <sha>`, identify target files, apply selectively
- **Example:** Commit had 5 fixes, but PR only needed 3 (other 2 belonged elsewhere)
- **Benefit:** Maintains true atomic PRs, prevents scope creep

**7. Shellcheck Compliance During Refactoring**
- Unused variables block commits when shellcheck is enabled
- **Pattern:** Remove unused code when refactoring - don't leave dead variables
- **Example:** Removed `MAX_CRF` variable and `--max-crf` option after loop refactor
- **Impact:** Keeps codebase clean, prevents confusion

**8. Data Extraction from Nested JSON**
- AI review comments often nested deep in GraphQL responses
- **Pattern:** Use `.reviews[] | select(.author.login == "gemini-code-assist")`
- **Challenge:** Comments may be in `.reviews[].comments.nodes[]` requiring graph traversal
- **Solution:** GraphQL queries more reliable than parsing comment HTML