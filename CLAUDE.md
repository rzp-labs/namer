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

**GraphQL Schema Management:**

- `make check-schema-drift` - Detect API changes (requires STASHDB_TOKEN, TPDB_TOKEN)
- `make update-schema-docs` - Refresh schema documentation
- See `docs/api/SCHEMA_MAINTENANCE.md` for complete guide

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

```plaintext
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
```

```bash
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

```plaintext
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

## External API Integration

### Metadata Providers

Namer integrates with two external GraphQL APIs for video metadata:

**StashDB (stashdb.org)**

- Endpoint: `https://stashdb.org/graphql`
- Authentication: `APIKey` header (non-standard)
- Schema: 181 types, 35+ queries, full CRUD + voting
- Implementation: `namer/metadata_providers/stashdb_provider.py`

**ThePornDB (theporndb.net)**

- Endpoint: `https://theporndb.net/graphql`
- Authentication: `Authorization: Bearer` header (standard)
- Schema: 30 types, 7 queries, streamlined design
- Implementation: `namer/metadata_providers/theporndb_provider.py`

### Schema Drift Detection

**Automated Monitoring:**

- Weekly CI checks every Monday at 9 AM UTC
- PR validation when provider code changes
- Automatic GitHub issue creation on drift
- Detailed diff artifacts stored for 30 days

**Manual Operations:**

```bash
# Check for schema changes
export STASHDB_TOKEN="your_token"
export TPDB_TOKEN="your_token"
make check-schema-drift

# Update documentation after drift
make update-schema-docs
git add docs/api/ && git commit -m "docs: update GraphQL schemas"
```

**Documentation:**

- `docs/api/stashdb_schema.json` - Complete StashDB schema
- `docs/api/tpdb_schema.json` - Complete ThePornDB schema
- `docs/api/graphql_schema_documentation.md` - Human-readable guide
- `docs/api/SCHEMA_MAINTENANCE.md` - Operations manual

**Key Differences:**

| Feature | StashDB | ThePornDB |
|---------|---------|-----------|
| Auth Header | `APIKey` | `Authorization: Bearer` |
| Field: Studio/Site | `studio` | `site` |
| Field: URLs | `urls[].url` | `urls[].view` |
| Field: Date | `release_date` | `date` |
| Schema Size | 181 types | 30 types |

See `docs/api/SCHEMA_MAINTENANCE.md` for complete operational guide.

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

**Pre-push Hooks: Deep Validation (~2 minutes)**

- **Purpose:** Full quality gate before team review - "production ready" validation
- **Philosophy:** Ready to push = ready for team review = high confidence in quality
- **Checks:**
  - Full pytest suite with coverage - All tests including watchdog, web, videophash, and slow tests
  - Docker smoke test - Quick build validation to catch Dockerfile/build errors

**Note:** CodeRabbit AI review can be run manually via `make review`. Codacy security analysis runs in CI only (requires CODACY_PROJECT_TOKEN).

**Why this approach:**

1. **Type safety shift-left** - Catch type errors at commit time before they pile up
2. **Fast pytest in pre-commit** - 78 tests in 4 seconds provides excellent functional coverage
3. **CI-based security** - Codacy runs in CI where tokens are configured
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

## Hook Optimization Best Practices

### Philosophy: Skip When Files Don't Affect Outcomes

**Core Principle**: Git hooks should ONLY run when files that could affect their outcome are modified.

**Why This Matters:**

- Documentation-only changes shouldn't trigger test suites
- Config-only changes shouldn't rebuild Docker images
- Zero changes between commit and push means re-linting is redundant
- 70%+ time savings on docs-only workflows

### File Type Filter Implementation

**Configuration Pattern** (`.pre-commit-config.yaml`):

```yaml
# Single file type
- id: pytest-fast
  types: [python]          # Only Python files trigger

# Single file type
- id: hadolint
  types: [dockerfile]      # Only Dockerfiles trigger

# Multiple file types
- id: docker-smoke-test
  types_or: [dockerfile, python, javascript, json, toml, shell]
  # Only build-related files trigger
```

### When to Use Each Filter Type

**`types: [single-type]`** - Use when hook validates/processes ONE file type:

- `types: [python]` → pytest, mypy, ruff
- `types: [dockerfile]` → hadolint
- `types: [shell]` → shellcheck
- `types: [yaml]` → actionlint

**`types_or: [type1, type2, ...]`** - Use when hook depends on MULTIPLE file types:

- Docker builds depend on: Dockerfile, Python code, JavaScript, configs (JSON/TOML), shell scripts
- Bundle operations depend on: JavaScript, CSS, HTML
- Integration tests depend on: Multiple source file types

**Files that should NEVER trigger hooks:**

- Markdown files (`.md`) - Documentation only
- Text files (`.txt`) - Notes and logs
- Image files (`.png`, `.jpg`) - Assets
- Non-executable configs that don't affect builds

### Performance Impact Measurement

**Before Optimization (all hooks run on all changes):**

- Docs-only commit: ~15-20s (unnecessary pytest, mypy, etc.)
- Docs-only push: ~2min (unnecessary full test suite, Docker build)
- **Total for docs PR:** ~2min+ per commit

**After Optimization (file type filters):**

- Docs-only commit: ~0s (all hooks skipped)
- Docs-only push: ~0s (all hooks skipped)
- **Total for docs PR:** Instant commit + instant push

**Savings:**

- 70%+ time saved on documentation workflows
- 50%+ time saved on config-only changes
- No impact on code changes (hooks still run when needed)

### Implementation Checklist

When adding new pre-commit hooks:

1. ☑️ **Identify file dependencies** - What files does this hook process?
2. ☑️ **Add appropriate filter** - Use `types` or `types_or` to limit scope
3. ☑️ **Test with different file types** - Verify hooks skip when expected
4. ☑️ **Measure impact** - Time hooks with various file type changes
5. ☑️ **Document in CLAUDE.md** - Update performance tables and examples

### Real-World Example: Docker Smoke Test Optimization

**Problem**: Docker smoke test ran on EVERY push, even docs-only changes
**Analysis**: Docker build only cares about: Dockerfile, Python, JS, configs, scripts
**Solution**: Added `types_or: [dockerfile, python, javascript, json, toml, shell]`
**Result**: 30-60s saved on docs-only pushes (instant instead of waiting for Docker build)

### User Feedback That Led to This

**User observation**: "There should be zero changes between commit and push, so re-linting doesn't make sense"

**Insight**: If pre-commit hooks do their job (format, type check, fast tests), pre-push should only add:

1. **Comprehensive testing** (full test suite vs fast tests)
2. **Build validation** (Docker, bundles)
3. **Not re-run** what pre-commit already validated

**Result**: All hooks now have file type filters to skip unnecessary work

## Troubleshooting & Best Practices

### Hook Performance & Timing

**Pre-commit Hook Performance (~15-20 seconds):**

```plaintext
Breakdown:
- Ruff linting + format: ~2-3s
- mypy type checking: ~2-3s
- pytest fast tests (78 tests): ~4-5s
- Shellcheck: ~1s
- Actionlint: ~1s
- Hadolint: ~1s
Total: ~15-20s
```

**Pre-push Hook Performance (~2 minutes):**

```plaintext
Breakdown:
- Full pytest with coverage: ~90s (timeout: 10min - generous for slow systems)
- Docker smoke test: ~30-60s (timeout: 10min - generous for cold builds)
Total: ~2 minutes typical

Note: Timeouts are generous to handle network delays, cold builds, and slow systems.
      CodeRabbit AI review: 'make review' (manual)
      Codacy security: Runs in CI only
```

**Hook Optimization via File Type Filtering:**

All hooks use `types` or `types_or` filters to skip when irrelevant files change:

| Hook | Filter | Files That Trigger |
|------|--------|-------------------|
| pytest-fast | `types: [python]` | Python files only |
| pytest-full | `types: [python]` | Python files only |
| mypy | `types: [python]` | Python files only |
| hadolint | `types: [dockerfile]` | Dockerfiles only |
| docker-smoke-test | `types_or: [dockerfile, python, javascript, json, toml, shell]` | Build-related files |
| shellcheck | `types: [shell]` | Shell scripts only |
| actionlint | `types: [yaml]` | Workflow files only |

**Performance Impact by Change Type:**

| Change Type | Pre-Commit | Pre-Push | Total | Savings |
|------------|-----------|----------|-------|---------|
| **Docs/Markdown** | ~0s | ~0s | Instant | ~2min saved |
| **Config files (non-build)** | ~0s | ~0s | Instant | ~2min saved |
| **Python code** | ~15-20s | ~90s | ~2min | Baseline |
| **Dockerfile** | ~15-20s | ~60s | ~1.5min | ~30s saved |
| **Shell scripts** | ~5s | ~0s | ~5s | ~2min saved |

**Why stratified hooks work:**

- Pre-commit is fast enough not to disrupt flow (< 20s for code, instant for docs)
- Pre-commit catches 90% of issues early (types, tests, style)
- Pre-push provides deep validation before team review
- File type filtering prevents unnecessary work (70%+ time savings on docs-only changes)
- Clear separation prevents frustration and bypass temptation

### Git Hooks Best Practices

**NEVER bypass pre-push hooks:**

- ❌ **`git push --no-verify`** - STRICTLY PROHIBITED
- ❌ Bypassing skips security scans, tests, and quality gates
- ❌ Puts broken code into shared branches
- ✅ If hooks are slow, **break work into smaller commits**
- ✅ Small commits = faster reviews = quicker delivery

**Why this policy:**

1. **Quality gates** - Full test suite ensures functionality before sharing
2. **CI validation** - Security checks run in CI where tokens are configured
3. **Team protection** - Don't break others' workflows
4. **Better practices** - Small, focused commits are better engineering

**If pre-push hooks seem slow:**

- Review your commit size - are you committing too much at once?
- Break large changes into smaller, logical commits
- Smaller commits review faster and are easier to understand
- Example: Instead of one 2000-line commit, create 5 focused 400-line commits

**Hook timeout guidelines:**

- pytest full suite: 10 minutes max (typically completes in ~90s)
- Docker smoke test: 10 minutes max (typically completes in ~30-60s, generous for cold builds)

**Common hook issues:**

1. **Timeout** - Commit too large? Break it into smaller pieces
2. **Type errors** - Run `poetry run mypy .` locally first (caught in pre-commit)
3. **Test failures** - Fix tests before pushing (caught in pre-commit fast tests)
4. **Docker build failures** - Test locally with `docker build .`
5. **Hooks running unnecessarily** - Check file type filters in `.pre-commit-config.yaml`

**Branch cleanup strategy:**
When features complete and PRs merge, clean up systematically:

```bash
# 1. Find local branches tracking deleted remotes
git branch -vv | grep ": gone]"

# 2. Verify branches from closed PRs
gh pr list --state closed --author @me

# 3. Delete obsolete local branches
git branch -D feature/old-branch

# 4. Clean up stale remote tracking branches
git remote prune origin

# 5. Verify cleanup
git branch -a
```

**Pattern**: Always verify before deleting - check PR status, merge status, and ensure no uncommitted work.

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
- **Pre-push (~2min):** Comprehensive quality gate
  - Full test suite with coverage (all tests, no filtering)
  - Docker build validation
- **Manual:** `make validate` for full CI simulation, `make review` for CodeRabbit AI review
- **CI only:** Codacy security analysis (requires token configuration)

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

**Systematic PR Review Response**:

1. **Create comprehensive todo list** from all review comments (CodeRabbit, Gemini, manual)
2. **Prioritize systematically:** CRITICAL > HIGH > MAJOR > Minor
3. **Address in priority order**, marking items completed immediately after finishing
4. **When blocked, reassess approach** - don't brute-force the same solution
5. **User intervention helpful** for fundamental design issues (e.g., parser incompatibilities)
6. **Document deferred items** with clear rationale for follow-up PRs

**Example Priority Breakdown:**

- **CRITICAL:** Artifact path mismatch causing CI failures → Must fix now
- **HIGH:** Hardcoded data becoming stale → Must fix now
- **MAJOR:** Formatting issues, graceful error handling → Should fix now
- **Minor:** Style improvements, documentation formatting → Can defer

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

**Heredoc with Non-Shell Code** (Critical for documentation generation):

```bash
# Problem: Heredocs containing non-shell code (GraphQL, JSON, YAML) break shfmt parsing
# When content has shell-like syntax (braces, brackets), parser gets confused

# ❌ WRONG: Unquoted heredoc with GraphQL code breaks shfmt
cat >"$file" <<EOF
## Schema
- **Types:** $TYPE_COUNT

```graphql
type Scene {
  id: ID!
}
```

EOF

# ✅ RIGHT: Quoted heredoc + sed replacement

cat >"$file" <<'TEMPLATE_EOF'

## Schema

- **Types:** TYPE_COUNT_PLACEHOLDER

```graphql
type Scene {
  id: ID!
}
```

TEMPLATE_EOF

# Replace placeholders with actual values

sed -i.bak "s/TYPE_COUNT_PLACEHOLDER/$TYPE_COUNT/g" "$file"
rm -f "${file}.bak"

```

**Why quoted heredoc works:**
- `<<'DELIMITER'` prevents shell interpretation (no variable expansion, no parsing)
- Content can contain any syntax without breaking shell parser
- Sed performs safe text replacement on complete file
- shfmt can parse correctly because no shell interpretation happens in heredoc

**Pattern summary:**
1. Use **quoted delimiter** (`<<'DELIMITER'`) for literal content
2. Use **placeholder tokens** for variables (e.g., `VARIABLE_PLACEHOLDER`)
3. Use **sed replacements** after heredoc to substitute actual values
4. Remove backup files created by sed (`-i.bak`)

### CI/CD and Automation Patterns

**Artifact Path Consistency** (Critical for CI workflows):
```bash
# Problem: Workflow uploads from one path, script writes to another

# ✅ In shell scripts - use RUNNER_TEMP with fallback
ARTIFACT_DIR="${RUNNER_TEMP:-/tmp}"
DIFF_FILE="${ARTIFACT_DIR}/diff.txt"
REPORT_FILE="${ARTIFACT_DIR}/report.json"

# ✅ In GitHub Actions workflows - use runner.temp
- name: Upload artifacts
  uses: actions/upload-artifact@v4
  with:
    path: |
      ${{ runner.temp }}/diff.txt
      ${{ runner.temp }}/report.json
```

**Pattern:** Always use `${RUNNER_TEMP:-/tmp}` in scripts and `${{ runner.temp }}` in workflows for consistent, discoverable paths across CI and local execution.

**Exit Code Semantics** (Critical for automation):

```bash
# Use distinct exit codes for different failure types
exit 0  # Success
exit 1  # Actionable failure (e.g., drift detected)
exit 2  # Informational state (e.g., missing baseline)

# Check exit codes explicitly in workflows
if [ $EXIT_CODE -eq 1 ]; then
    echo "actionable_failure=true" >> "$GITHUB_OUTPUT"
elif [ $EXIT_CODE -eq 2 ]; then
    echo "informational=true" >> "$GITHUB_OUTPUT"
fi

# ❌ WRONG: Implicit check treats all non-zero the same
if [ $EXIT_CODE -ne 0 ]; then
    echo "Something failed but don't know what"
fi
```

**Pattern:** Use semantic exit codes (0, 1, 2, etc.) and check explicitly (`-eq`) instead of implicitly (`-ne 0`) to differentiate actionable failures from informational states.

**Dynamic Documentation Generation** (Best practice):

```bash
# ❌ WRONG: Hardcoded statistics become stale
cat >"$doc" <<EOF
Schema has 181 types and 35 queries
EOF

# ✅ RIGHT: Extract statistics from source data
TYPE_COUNT=$(jq '[.data.__schema.types[] | select(.name | startswith("__") | not)] | length' "$schema")
QUERY_COUNT=$(jq '.data.__schema.queryType.name as $qt | .data.__schema.types[] | select(.name == $qt) | .fields | length' "$schema")

cat >"$doc" <<'TEMPLATE_EOF'
Schema has TYPE_COUNT_PLACEHOLDER types and QUERY_COUNT_PLACEHOLDER queries
TEMPLATE_EOF

sed -i.bak \
    -e "s/TYPE_COUNT_PLACEHOLDER/$TYPE_COUNT/g" \
    -e "s/QUERY_COUNT_PLACEHOLDER/$QUERY_COUNT/g" \
    "$doc"
rm -f "${doc}.bak"
```

**Pattern:** Never hardcode statistics that can be derived from data sources. Extract dynamically → Template with placeholders → Sed replacement. Documentation stays synchronized automatically.

---

## Lessons Learned (Distilled Patterns)

### PR Workflow Patterns

**Atomic PRs**: 200-500 lines per PR, single focused concern.

- Investment: ~1 hour to split
- Return: 20x faster review time
- Pattern: Sequential PRs for evolving docs/config, parallel for independent changes

**Splitting Strategy**:

1. Analyze commits: `git log develop..HEAD --oneline`
2. Create atomic branches from develop
3. Cherry-pick relevant commits: `git cherry-pick <hash>`
4. Apply fixes selectively (don't cherry-pick entire commits blindly)

**Strategic Decision Reassessment**: When upstream decisions change, reassess dependent features before merging.

_Reference: `.agent/memory.json` (lesson-001, lesson-005, lesson-006, lesson-010, lesson-013, lesson-014) for detailed ROI metrics, workflows, and separation strategies_

---

### Git Hook Patterns

**File Type Filtering**: Hooks ONLY run when relevant files change.

```yaml
# Single file type
- id: pytest-fast
  types: [python]

# Multiple file types
- id: docker-smoke-test
  types_or: [dockerfile, python, javascript, json, toml, shell]
```

**Impact**: 70%+ time savings on docs-only workflows (instant vs 2min).

**Timeout Configuration**: Generous timeouts (10min) with fast typical execution (~90s).

**Hook Bypass Guidelines**:

- ✅ Acceptable: When modifying hook system itself (chicken-egg problem)
- ❌ Never: To skip failing tests or security scans

_Reference: `.agent/memory.json` (lesson-002, lesson-003, lesson-004, lesson-009, lesson-011) for performance benchmarks, optimization philosophy, and bypass guidelines_

---

### Shell Scripting Patterns

**Shellcheck Compliance**: Remove unused variables during refactoring.

**Heredoc with Non-Shell Code**: Use quoted delimiter + sed replacement.

```bash
cat >"$file" <<'TEMPLATE_EOF'
Content with PLACEHOLDER
TEMPLATE_EOF
sed -i.bak "s/PLACEHOLDER/$value/g" "$file"
rm -f "${file}.bak"
```

**Filename Sanitization**: Use bash parameter expansion.

```bash
SAFE_BRANCH="${BRANCH//\//-}"  # shellcheck compliant
```

_Reference: `.agent/memory.json` (lesson-007, lesson-015) for parser issues, debugging journeys, and systematic review response_

---

### CI/CD Patterns

**Artifact Paths**: `${RUNNER_TEMP:-/tmp}` in scripts, `${{ runner.temp }}` in workflows.

**Exit Code Semantics**: Distinct codes for distinct states (0=success, 1=failure, 2=informational).

```bash
if [ $EXIT_CODE -eq 1 ]; then
    echo "actionable_failure=true"
elif [ $EXIT_CODE -eq 2 ]; then
    echo "informational=true"
fi
```

**Dynamic Documentation**: Extract statistics from source data, never hardcode.

**Schema Drift Detection**: Automated introspection + CI monitoring.

- `make check-schema-drift` - Manual detection
- `make update-schema-docs` - Refresh documentation
- Weekly CI checks + PR validation
- Auto-create GitHub issues on drift

_Reference: `.agent/memory.json` (lesson-012, lesson-015, lesson-017) for implementation patterns, architecture details, emergency response workflows, and iterative PR review resolution_

---

### Code Review Patterns

**Systematic Response**: Create todo list → Prioritize (CRITICAL > HIGH > MAJOR > Minor) → Address systematically.

**Issue Management**: Convert AI feedback to GitHub issues with priority labels.

```bash
gh issue create \
  --title "🔴 [Urgent] Issue title" \
  --label urgent,bug \
  --body "## Problem\n...\n\n## Impact\n...\n\n## Solution\n..."
```

**JSON Extraction**: Use GraphQL queries for nested data structures.

```bash
jq '.data.repository.pullRequest.reviews[] | select(.author.login == "gemini-code-assist")'
```

_Reference: `.agent/memory.json` (lesson-008, lesson-016) for tools, workflows, issue structure best practices, and label management_

---

**Complete Historical Context**: See `.agent/memory.json` for full session details, ROI analysis, debugging journeys, and 17 structured lessons with code examples.

**Query Examples**:

```bash
# Search by category
jq '.sessions[] | select(.category == "pr-workflow")' .agent/memory.json

# Search by tag
jq '.sessions[] | select(.tags[] | contains("performance"))' .agent/memory.json

# Get all patterns for a topic
jq '.sessions[] | select(.tags[] | contains("git-hooks")) | {title, pattern}' .agent/memory.json
```

### 18. Stratified Hooks Validation in Real Release Cycle

- **Evidence from Release/1.23.3:**
  - Pre-commit caught: Type errors, formatting issues, test failures
  - Pre-push caught: Full test suite coverage, Docker build validation
  - File type filtering: Only relevant hooks ran (Python hooks skipped for shell changes)
- **Confirmed Benefits:**
  - Fast feedback loop (~15-20s) prevents iteration delays
  - Comprehensive gate (~2min) ensures quality before push
  - 70%+ time savings on docs/config-only changes
- **Validation:** System working as designed through full release workflow
- **Future:** Continue measuring and optimizing hook performance

---

### Branch Lifecycle and Cleanup

### 19. Thorough Investigation Before Cherry-Picking

- **Context:** Attempted to extract "security improvements" from 12-day-old branch (chore/urgent-ci-hardening)
- **Initial Assessment:** Branch appeared to have valuable changes (secrets.choice, defusedxml, path sanitization)
- **Discovery Process:**
  1. Checked if improvements were in develop
  2. Found secrets.choice in namer/ffmpeg_impl.py (lines 247, 287)
  3. Found defusedxml already in pyproject.toml
  4. Realized code had been refactored, incorporating all improvements
- **Lesson:** Always diff current code against "improvements" - refactoring may have already incorporated them
- **Pattern:** Old branches may appear to have value, but subsequent development often supersedes them
- **Workflow:**
  ```bash
  # Before cherry-picking from old branch:
  git diff develop old-branch -- path/to/file.py
  grep -r "suspected_improvement" namer/
  git log --all --grep="improvement_keyword"
  ```
- **Time Investment:** Spent ~30 minutes investigating only to find nothing was needed
- **Benefit:** Prevented duplicate code and unnecessary merge conflicts

### 20. Respect Intentional Architectural Decisions

- **Context:** Attempted to "improve security" by replacing corepack with npm --ignore-scripts
- **User Challenge:** "I thought we used corepack for a specific reason"
- **Investigation:** Found PR #108 (commit c6d12b6c) established corepack intentionally
- **Rationale for Corepack:**
  - Official Node.js way to manage package managers
  - Ensures everyone uses exactly pnpm@10.0.0
  - Part of deliberate pnpm enforcement strategy
  - Consistency > hypothetical security benefit
- **Mistake:** Traded hypothetical security for breaking intentional design
- **Lesson:** Before "improving" something, research WHY it was done that way
- **Pattern:** Use `git log --grep="keyword"` to understand rationale behind decisions
- **Workflow:**
  ```bash
  # Research architectural decisions:
  git log --all --grep="corepack"
  git log --all -S "corepack" --source --all
  gh pr list --search "corepack" --state all
  ```
- **Recovery:** Abandoned change, closed PR, deleted branches
- **Best Practice:** Document significant architectural decisions in commit messages or ADRs

### 21. Branch Obsolescence Patterns

- **Pattern 1 - Squash Merged:** Branches with content in main but different commit SHAs
  - Example: hotfix/graphql-schema-fixes (commit 9af0765 vs main's bea5bbf)
  - Identification: Content is in target branch but `git branch --contains` returns false
  - Solution: Use `git branch -D` after verifying content is in main
- **Pattern 2 - Superseded Dependabot:** Old PRs replaced by newer versions
  - Example: dependabot/npm_and_yarn/minor-and-patch (10 updates) → (13 updates)
  - Identification: Check `git branch -vv | grep ": gone]"`
  - Solution: Delete local branch, close old PR
- **Pattern 3 - Working Branches:** Staging area for atomic PRs, never meant to merge
  - Example: feature/improve-dev-tooling → split into PRs #120, #123, #126
  - Identification: No PR exists, but commits appear in other PRs
  - Solution: Delete after all atomic PRs merge
- **Pattern 4 - Regressive Branches:** Outdated bases that would remove newer work
  - Example: fire-16/fire-17 from Oct 4, would delete 24k+ lines added since
  - Identification: Large negative line count in `git diff develop branch --stat`
  - Solution: Close with clear explanation, delete branch
- **Pattern 5 - Incorporated Branches:** Content cherry-picked into other work
  - Example: chore/urgent-ci-hardening improvements in develop via refactoring
  - Identification: Compare actual code, not just commit history
  - Solution: Verify with `git diff`, then delete if truly incorporated

### 22. Efficient Obsolescence Detection Workflow

Systematic approach to identifying and cleaning up obsolete branches:

```bash
# 1. Check PR status first
gh pr list --state all --head branch-name

# 2. Verify content location
# If closed without merge:
git diff develop branch -- path/to/files

# If merged (squashed):
git log --all --grep="PR #123"  # Find merge commit

# 3. Compare line counts
git diff develop branch --stat | tail -1
# Large negative numbers = regressive/outdated

# 4. Check commit dates
git log branch --format="%ci" -1
# >2 weeks old + closed PR = likely stale

# 5. Verify no unique value
# Compare actual code changes:
git diff develop branch | grep "^+" | head -20
```

**Decision Matrix:**

| Branch Age | PR Status | Line Delta | Action |
|------------|-----------|------------|--------|
| <1 week | Open | Positive | Keep (active development) |
| <1 week | Closed | Any | Investigate (may have value) |
| >2 weeks | Open | Positive | Review with author |
| >2 weeks | Closed/None | Negative | Delete (regressive) |
| >2 weeks | Closed/None | Small positive | Verify incorporated |
| Any | Merged | Any | Delete local after verification |

**Cleanup Commands:**

```bash
# Safe deletion workflow:
# 1. Find local branches tracking deleted remotes
git branch -vv | grep ": gone]"

# 2. Verify branches from closed PRs
gh pr list --state closed --author @me

# 3. Delete obsolete local branches
git branch -D feature/old-branch

# 4. Clean up stale remote tracking branches
git remote prune origin

# 5. Verify cleanup
git branch -a
```

### 23. PR Closure Communication

When closing obsolete PRs, provide clear rationale for future reference:

**Good Closure Comment Structure:**
```markdown
Closing as [reason: obsolete/regressive/incorporated]

Investigation reveals:
✅ [What's already done]
✅ [What's been incorporated]

Branch issues:
- [Specific problem 1]
- [Specific problem 2]

Conclusion: [Clear statement of why closing]
```

**Real Example from PR #93:**
```markdown
Closing as regressive - branch is outdated and would remove significant work

Investigation reveals:
✅ All FIRE-16 goals already implemented in develop
✅ GraphQL schema improvements incorporated via PRs #120-126

Branch issues:
- Based on develop from October 4 (6 weeks outdated)
- Would remove 24,000+ lines of recent improvements
- Contains superseded code patterns

Conclusion: Safe to close and delete branch
```

**Benefits:**
- Future readers understand decision without re-investigation
- Prevents accidental re-opening of obsolete work
- Documents project history and evolution
- Shows due diligence in cleanup decisions

**Template Variables:**
- **obsolete** - Functionality replaced by better implementation
- **regressive** - Would remove newer work if merged
- **incorporated** - Changes already merged via other PRs
- **superseded** - Newer version of same work exists

### 24. Slash Command Design Patterns

- **Context:** Session on 2025-10-14 focused on improving Git Flow commands and command organization
- **Key Learnings:**

#### A. Automatic Version Detection
- **Problem:** Requiring users to manually specify versions creates cognitive overhead
- **Solution:** Make version arguments optional and auto-detect based on commit analysis
- **Pattern:**
  ```bash
  # Auto-detect version from commits
  /release                    # Analyzes commits → suggests v1.24.0
  /release v1.25.0           # Override if needed

  # Hotfix auto-calculation
  /hotfix critical-bug       # Auto-calculates v1.23.6 from v1.23.5
  ```
- **Benefits:**
  - Eliminates guessing game
  - Applies semantic versioning correctly
  - Transparent reasoning shown to user
  - Still allows manual override
- **Implementation:** Commands analyze git history and suggest versions, then ask for confirmation

#### B. zsh Compatibility in Slash Commands
- **Problem:** Command substitution `$(...)` inside backticks breaks in zsh
- **Solution:** Use xargs with sh -c for portable command execution
- **Pattern:**
  ```bash
  # ❌ Breaks in zsh:
  !`git log $(git describe --tags --abbrev=0)..HEAD --oneline | wc -l`

  # ✅ Works in both bash and zsh:
  !`git describe --tags --abbrev=0 2>/dev/null | xargs -I {} sh -c 'git log {}..HEAD --oneline 2>/dev/null | wc -l | tr -d " "' || echo "N/A"`
  ```
- **Why:** macOS default shell is zsh; commands must be portable
- **Testing:** Always test commands in both bash and zsh before deploying

#### C. Git Flow Configuration Management
- **Problem:** No explicit configuration for Git Flow preferences
- **Solution:** Created `/git-flow-init` command to capture explicit preferences
- **Pattern:**
  - Ask user questions (never assume!)
  - Store in `.claude/git-flow-config.json`
  - Commands check initialization before running
  - Configuration includes: branch names, versioning system, release automation, tag creation
- **Benefits:**
  - No assumptions about user workflows
  - Configuration is explicit and documented
  - Commands adapt to project conventions
  - Team members inherit configuration

#### D. Command Audit Framework
- **Problem:** Large number of commands (60+) difficult to discover and maintain
- **Solution:** Created comprehensive audit framework with analysis tools
- **Deliverables:**
  - Analysis scripts (analyze-commands.sh, quick-check.sh)
  - Documentation (GETTING_STARTED.md, OPTIMIZATION_FRAMEWORK.md)
  - Templates for optimization proposals
- **Recommendations:**
  - Keep flat directory structure (aligns with Make/poe patterns)
  - Use action-object naming consistently
  - Target 20-30% reduction through consolidation
  - 6-month deprecation period for merged commands
- **Process:** 6-phase framework taking 3-5 hours for comprehensive optimization

#### E. User-Centric Command Design
- **Insight:** "Why do I need to define the version number when the agent already analyzes commits?"
- **Principle:** If the command already has the information, don't make the user provide it
- **Application:**
  - Version detection in `/release` and `/hotfix`
  - Configuration analysis in `/git-flow-init`
  - Commit analysis for changelog generation
- **Result:** Commands become assistants, not data collectors

**Files Created:**
- `.claude/commands/git-flow-init.md` - Interactive Git Flow configuration
- `.claude/git-flow-config.json.example` - Example configuration
- `.claude-audit/` directory - Complete command audit framework (9 files)

**Files Modified:**
- `.claude/commands/release.md` - Added automatic version detection
- `.claude/commands/hotfix.md` - Added automatic version calculation
- Both commands now have zsh-compatible command substitution

**Recommendation:** When designing new commands, ask "Does the user really need to provide this, or can we detect it?"

_Reference: Session 2025-10-14 for complete implementation details, command audit framework, and user feedback that drove design decisions_
