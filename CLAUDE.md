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

**Automatic checks on commit:**
- Ruff linting with auto-fix (`--fix`)
- Ruff formatting
- Shellcheck for bash scripts
- Actionlint for GitHub Actions workflows
- CodeRabbit pre-commit review (optional)
- Dockerfile linting with hadolint

**Automatic checks on push:**
- `validate.sh --fast` - Quick validation before push

**Manual execution:**
- `pre-commit run --all-files` - Run all hooks manually
- `poe precommit` - Alternative: format checking + fast tests

**Hook management:**
- Hooks are installed automatically by `make setup-dev`
- Configuration: `.pre-commit-config.yaml`
- Update hooks: `pre-commit autoupdate`
- Skip hooks (not recommended): `git commit --no-verify`

### Before Pushing
**Comprehensive validation:**
- `make validate` - Full validation suite (required before PR)

### Creating Pull Requests
- Feature branches → merge to `develop`
- Release branches → merge to `main` (via automated workflow)
- Hotfix branches → merge to both `main` and `develop`

### Release Process
**Do not use `git flow release`** - instead use the automated GitHub Actions workflow (see `/release` command or release.md)