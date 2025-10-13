# Suggested Makefile Additions

This document contains suggested Make targets to add for a more complete developer interface.

## Rationale

Currently, some common operations require direct Poetry/poe commands or remembering script paths. Adding Make targets provides a consistent, discoverable interface.

## Suggested Additions

### Code Quality Targets

```makefile
# Linting and formatting
lint: ## Run Ruff linting checks
	@poetry run ruff check .

lint-fix: ## Run Ruff linting with auto-fix
	@poetry run ruff check --fix .

format: ## Format code with Ruff
	@poetry run ruff format .

format-check: ## Check formatting without changes
	@poetry run ruff format --check .

typecheck: ## Run mypy type checking
	@poetry run mypy namer/

security-scan: ## Run bandit security checks
	@poetry run bandit -r namer/
```

### Local Testing Targets

```makefile
# Local Python testing (not Docker)
test-local: ## Run local pytest (fast tests only)
	@poetry run pytest -m "not slow"

test-local-all: ## Run all local pytest tests (including slow)
	@poetry run pytest

test-local-coverage: ## Run local tests with coverage report
	@poetry run pytest --cov=namer --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@poetry run pytest-watch -m "not slow"
```

### Pre-commit/Pre-push Shortcuts

```makefile
precommit: ## Quick pre-commit checks (format + fast tests)
	@poetry run poe precommit

pre-push: validate ## Alias for validate (comprehensive pre-push checks)
```

### Dependency Management

```makefile
deps-install: ## Install/update all dependencies
	@poetry install

deps-update: ## Update all dependencies
	@poetry update

deps-show: ## Show installed dependencies
	@poetry show

deps-outdated: ## Check for outdated dependencies
	@poetry show --outdated

deps-lock: ## Regenerate poetry.lock
	@poetry lock --no-update
```

### Local Build Targets (Non-Docker)

```makefile
build-local: ## Build Python package locally (non-Docker)
	@poetry run poe build_namer

build-local-deps: ## Build dependencies (npm + videohashes)
	@poetry run poe build_deps

build-local-full: ## Full local build with all deps
	@poetry run poe build_all
```

### Run Targets

```makefile
run: ## Run namer locally (development mode)
	@poetry run python -m namer

run-port: ## Run namer on custom port (use PORT=8080)
	@poetry run python -m namer --port $(PORT)
```

### Documentation

```makefile
docs: ## Open project documentation
	@echo "Documentation locations:"
	@echo "  - Main README: readme.rst"
	@echo "  - Claude guide: CLAUDE.md"
	@echo "  - Project docs: docs/"

docs-serve: ## Serve documentation (if using mkdocs/sphinx)
	@echo "No doc server configured yet"
```

### Git Helpers

```makefile
branch: ## Show current branch and status
	@git branch --show-current
	@echo ""
	@git status --short

diff: ## Show git diff
	@git diff

commits: ## Show recent commits
	@git log --oneline -10
```

### Shortcuts for Common Workflows

```makefile
quick: lint-fix test-local ## Quick feedback (fix lint + fast tests)

ci: lint format-check typecheck test-local-all ## Simulate CI checks locally

fix: lint-fix format ## Fix all auto-fixable issues
```

## Usage After Adding

Once added to Makefile, developers can:

```bash
# Quick local validation
make quick

# Fix formatting issues
make fix

# Run specific check
make lint
make typecheck
make test-local

# Update dependencies
make deps-update

# Comprehensive pre-push validation
make validate  # (already exists)
```

## Implementation Priority

**High Priority (most commonly needed):**
1. `make lint` / `make format` - Quick code quality checks
2. `make test-local` - Fast local testing without Docker
3. `make precommit` - Quick pre-commit validation
4. `make deps-install` - Dependency management

**Medium Priority (nice to have):**
5. `make run` - Quick local execution
6. `make quick` - Fast feedback loop
7. `make typecheck` - Type checking

**Low Priority (convenience):**
8. Documentation helpers
9. Git helpers
10. Watch mode

## Notes

- All targets should be `.PHONY` since they don't create files
- Keep targets focused and single-purpose
- Use `@` prefix to suppress command echo (cleaner output)
- Add `## Description` for auto-documentation in `make help`
- Prefer calling existing poe tasks over duplicating logic
