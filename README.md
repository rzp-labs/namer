# Namer

Automatically renames and tags adult video files using metadata from ThePornDB and StashDB.

**Core functionality:**

- **Watchdog mode**: Monitors directories, automatically processes new files
- **Web UI**: Browser interface for manual matching and queue management (port 6980)
- **CLI tool**: Batch rename, single file processing, dry-run suggestions
- **Metadata embedding**: Tags MP4 files with performers, studio, ratings, cover art
- **Perceptual hashing**: Identifies videos without parsable filenames
- **Dual provider**: Queries both StashDB and ThePornDB APIs

## Important Rules

### Critical Don'ts

1. **NEVER bypass git hooks** - No `--no-verify` on commits/pushes, hooks are mandatory
2. **NEVER force push to `main`** - Protected branch, will reject the push
3. **NEVER create files in `src/`** - Main package is `namer/`, tests in `test/`
4. **NEVER use `from typing import Callable`** - Use `from collections.abc import Callable` (Python 3.11+)
5. **NEVER use `print()`** - Use `loguru` logger instead

### Project Structure

```
namer/                   # Main package (NOT src/)
├── __main__.py          # Application entry point
├── configuration.py     # Config file parsing
├── database.py          # Pony ORM models
├── watchdog.py          # File monitoring
├── metadata_providers/  # StashDB/ThePornDB API clients
├── models/              # Data models
└── web/                 # Flask application
    ├── routes/api.py    # REST endpoints
    ├── routes/web.py    # Page routes
    ├── templates/       # Jinja2 templates
    └── public/          # Webpack bundled assets

test/                    # Tests (NOT tests/)
├── *_test.py            # Test modules (pytest)
└── integration/         # Integration tests
```

### Git Workflow (Git Flow)

- **Branch from**: `develop` (NOT `main`)
- **PR target**: `develop` (NOT `main`)
- **Branch naming**: `feature/description`, `fix/description`, `docs/description`
- **Protected branches**: `main` (no force push), `develop` (no force push)
- **Commit format**: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)
- **Pre-commit hooks** (~15-20s): Ruff, mypy, fast tests, shellcheck
- **Pre-push hooks** (~2min): Full test suite, Docker smoke test
- **Test coverage**: 90%+ required for new code

### Code Standards

- **Python**: 3.11+ required
- **Line length**: 320 characters (NOT 88)
- **Quotes**: Single quotes (enforced by Ruff)
- **Type hints**: Required for all function signatures
- **Imports**: `from pathlib import Path`, `from collections.abc import Callable`
- **Logging**: Use `loguru`, NOT `print()`
- **Testing**: pytest with assertpy assertions

## Local Environment Setup

### Prerequisites you must install first

- **Python 3.11+**
- **Poetry** - `pipx install poetry` or `pip install --user poetry`
- **Node.js v22+** - `corepack enable`
- **pnpm** - `corepack prepare pnpm@10 --activate`
- **FFmpeg** - `brew install ffmpeg` or `apt install ffmpeg`

### Setup steps

```bash
# 1. Install Python dependencies + git hooks
make setup-dev

# 2. Build frontend assets + submodules + videohashes
poetry run poe build_deps

# 3. Verify everything works
make validate
```

### Manual setup (if make fails)

```bash
# Python dependencies + git hooks
poetry install
poetry run pre-commit install
poetry run pre-commit install --hook-type pre-push

# Frontend + build assets
pnpm install
pnpm run build

# Videohashes submodule (optional, for perceptual hashing)
git submodule update --init --recursive
make -C ./videohashes macos-arm64  # or linux-amd64, etc.
```

## Development Workflow

### Fast Feedback Loop

```bash
# Quick validation during development (~11s)
make quick
```

### Before Pushing

```bash
# Full validation - REQUIRED before git push (~2-3min)
make validate
```

### Common Commands

```bash
# Run application
poetry run python -m namer watchdog          # Start watchdog + web UI (port 6980)
poetry run python -m namer rename -f file.mp4 # Rename single file
poetry run python -m namer suggest -f file.mp4 # Dry run

# Testing
poetry run pytest                             # All tests
poetry run pytest -m "not slow"               # Fast tests only
poetry run pytest --cov=namer                 # With coverage report
poetry run pytest -v -s test/namer_test.py::test_name # Single test

# Code quality
poetry run ruff check .                       # Lint
poetry run ruff check --fix .                 # Auto-fix issues
poetry run ruff format .                      # Format code
poetry run mypy namer/                        # Type checking
poetry run bandit -r namer/                   # Security scan

# Make targets
make help                                     # Show all available commands
make quick                                    # Fast validation
make validate                                 # Full validation
make test-local                               # Tests without Docker
make build                                    # Build Docker image
make clean                                    # Clean temporary files
```

### Configuration

Application config file: `namer.cfg` (copy from `namer/namer.cfg.default`)

Key sections:

- `[namer]`: CLI behavior, naming templates, file parsing
- `[Phash]`: Perceptual hash settings, GPU acceleration
- `[metadata]`: MP4 tagging, cover art downloads
- `[watchdog]`: Folder monitoring, web UI settings, retry logic

### Common Issues

**"Module not found" errors:**

```bash
poetry install  # Reinstall dependencies
```

**Type checking errors:**

```python
# WRONG
from typing import Callable

# CORRECT (Python 3.11+)
from collections.abc import Callable
from pathlib import Path
```

**Test failures:**

```bash
# Run with verbose output and no capture
poetry run pytest -v -s test/namer_test.py::test_name

# Check if you're on develop branch
git status
```

**Pre-commit hooks seem slow:**

- Hooks use file type filters - docs-only changes = instant
- Python changes trigger full validation
- If truly slow, commit smaller chunks

**Git hooks failing:**

- Run `make validate` to see what's failing
- Fix issues, don't bypass with `--no-verify`
- Check `.pre-commit-config.yaml` for hook config

## Technology Stack

**Backend:**

- Python 3.11+ with Poetry dependency management
- Flask 3.1+ web framework
- Pony ORM for database (SQLite default, PostgreSQL supported)
- FFmpeg for video processing
- requests-cache for HTTP caching

**Frontend:**

- Bootstrap 5 UI framework
- jQuery for DOM manipulation
- DataTables for table management
- Webpack for asset bundling
- pnpm package manager (enforced)

**Testing & Quality:**

- pytest 8.4+ with assertpy assertions
- Selenium for web testing
- Ruff 0.13+ for linting/formatting (replaces black/flake8/isort)
- mypy 1.11+ for static type checking
- bandit for security scanning
- pre-commit framework for git hooks

## Key Files for AI Agents

**Must read before making changes:**

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive development guide, patterns, lessons learned
- **[pyproject.toml](pyproject.toml)** - Dependencies, versions, build config, poe tasks
- **[Makefile](Makefile)** - All available commands with descriptions
- **[.pre-commit-config.yaml](.pre-commit-config.yaml)** - Git hook definitions

**Reference when needed:**

- **[namer/namer.cfg.default](namer/namer.cfg.default)** - Configuration reference
- **[docs/api/](docs/api/)** - GraphQL schema documentation
- **[CHANGELOG.md](CHANGELOG.md)** - Recent changes

## API Integration

**Metadata providers:**

- **StashDB** (`stashdb.org/graphql`) - Auth: `APIKey` header
- **ThePornDB** (`theporndb.net/graphql`) - Auth: `Authorization: Bearer` header

**Schema drift detection:**

```bash
# Check for API changes (requires tokens in env)
export STASHDB_TOKEN="your_token"
export TPDB_TOKEN="your_token"
make check-schema-drift

# Update schema documentation
make update-schema-docs
```

See `docs/api/SCHEMA_MAINTENANCE.md` for complete guide.
