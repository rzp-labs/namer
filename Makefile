# Namer Docker Build Makefile - Clean & Atomic
#
# Uses scripts in ./scripts/ for all complex operations
# This Makefile focuses on simple composition and user interface

# Configuration
IMAGE_NAME ?= nehpz/namer
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo 'latest')
SCRIPT_DIR = ./scripts

.PHONY: all help build build-fast build-full build-dev \
        build-amd64 build-arm64 build-multiarch ensure-builder \
        test test-basic test-integration validate clean clean-deep config \
        setup-dev review \
        lint lint-fix format format-check typecheck security-scan \
        test-local test-local-all test-local-coverage test-watch \
        precommit pre-push \
        deps-install deps-update deps-show deps-outdated deps-lock \
        build-local build-local-deps build-local-full \
        run run-port \
        docs branch diff commits \
        check-schema-drift update-schema-docs \
        quick ci fix

help: ## Show available targets
	@echo "🏗️  Namer Build System"
	@echo "====================="
	@echo ""
	@echo "Build targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Examples:"
	@echo "  make build           # Fast build (recommended for development)"
	@echo "  make build-validated # Full validation + fast build"
	@echo "  make build-full      # Complete build with all tests (slow)"
	@echo "  make test            # Test the built image"
	@echo ""

all: build ## Default 'all' target builds the project

build: build-fast ## Default: fast build for development iteration

build-fast: ## Fast Docker build (skips tests, ~5 minutes)
	@$(SCRIPT_DIR)/build-orbstack.sh fast $(IMAGE_NAME) $(VERSION)

build-full: ## Complete build with all tests (~20 minutes)
	@$(SCRIPT_DIR)/build-orbstack.sh full $(IMAGE_NAME) $(VERSION)

build-dev: ## Development build (build stage only, no export)
	@$(SCRIPT_DIR)/build-orbstack.sh dev $(IMAGE_NAME) $(VERSION)

# --- Cross-platform build targets (Docker Buildx) ---

ensure-builder: ## Ensure a docker buildx builder exists and is active
	@docker buildx inspect namer-builder >/dev/null 2>&1 || \
		docker buildx create --name namer-builder --driver docker-container --use >/dev/null 2>&1
	@docker buildx inspect namer-builder --bootstrap >/dev/null 2>&1
	@docker buildx use namer-builder >/dev/null 2>&1

build-amd64: ensure-builder ## Build for linux/amd64 (works on ARM64 hosts via emulation; loads into local Docker)
	@echo "🏗️  Building $(IMAGE_NAME):$(VERSION) for linux/amd64 (local load)"
	@docker buildx build \
		--platform linux/amd64 \
		-t $(IMAGE_NAME):$(VERSION) \
		-t $(IMAGE_NAME):latest \
		--load \
		.

build-arm64: ensure-builder ## Build for linux/arm64 (native on Apple Silicon; loads into local Docker)
	@echo "🏗️  Building $(IMAGE_NAME):$(VERSION) for linux/arm64 (local load)"
	@docker buildx build \
		--platform linux/arm64 \
		-t $(IMAGE_NAME):$(VERSION) \
		-t $(IMAGE_NAME):latest \
		-t $(IMAGE_NAME):$(VERSION)-arm64 \
		-t $(IMAGE_NAME):latest-arm64 \
		--load \
		.

build-multiarch: ensure-builder ## Build and push multi-arch (linux/amd64,linux/arm64) — requires registry auth
	@echo "🌐 Building and pushing multi-arch $(IMAGE_NAME):$(VERSION) (amd64,arm64)"
	@docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t $(IMAGE_NAME):$(VERSION) \
		-t $(IMAGE_NAME):latest \
		--push \
		.

# Quality gates (composable)
validate: ## Run comprehensive pre-push validation
	@if [ -f "validate.sh" ]; then \
		chmod +x validate.sh && ./validate.sh; \
	else \
		echo "❌ validate.sh not found"; \
		exit 1; \
	fi

build-validated: validate build-fast ## Validate then fast build
	@echo "✅ Validated build complete: $(IMAGE_NAME):$(VERSION)"

# Testing targets (composable)
test: test-basic ## Default: basic functionality tests

test-basic: ## Test basic container functionality
	@$(SCRIPT_DIR)/test-docker.sh $(IMAGE_NAME) $(VERSION) basic

test-integration: ## Run integration tests
	@$(SCRIPT_DIR)/test-docker.sh $(IMAGE_NAME) $(VERSION) integration

# Utility targets
clean: ## Clean up temporary files and containers
	@$(SCRIPT_DIR)/cleanup.sh medium

clean-deep: ## Deep clean (removes everything including VM)
	@$(SCRIPT_DIR)/cleanup.sh deep

config: ## Show current build configuration
	@echo "Configuration:"
	@echo "  IMAGE_NAME: $(IMAGE_NAME)"
	@echo "  VERSION:    $(VERSION)"
	@echo "  SCRIPT_DIR: $(SCRIPT_DIR)"

# Workflow examples (combinations)
dev-cycle: build-fast test-basic ## Quick development cycle
	@echo "🚀 Development cycle complete"

release-prep: validate build-full test-integration ## Full release preparation
	@echo "🎉 Release preparation complete"

review: ## Run CodeRabbit branch review (optional)
	@./scripts/run-coderabbit.sh branch


# Developer setup
setup-dev: ## Bootstrap Poetry + deps, then install local hooks (pre-commit + pre-push)
	@bash -lc 'set -euo pipefail; \
	  echo "Checking Poetry availability..."; \
	  export PATH="$$HOME/.local/bin:$$PATH"; \
	  if ! command -v poetry >/dev/null 2>&1; then \
	    if command -v pipx >/dev/null 2>&1; then \
	      pipx install --include-deps poetry; \
	      hash -r; \
	    else \
	      echo "Poetry not found. Install pipx (brew install pipx && pipx ensurepath) or pip (pip install --user poetry)"; \
	      exit 1; \
	    fi; \
	  fi; \
	  poetry --version; \
	  echo "Installing project dependencies with Poetry..."; \
	  poetry install; \
	  chmod +x scripts/install-hooks.sh || true; \
	  ./scripts/install-hooks.sh'

# --- Code Quality Targets ---

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

# --- Local Testing Targets ---

test-local: ## Run local pytest (fast tests only)
	@poetry run pytest -m "not slow"

test-local-all: ## Run all local pytest tests (including slow)
	@poetry run pytest

test-local-coverage: ## Run local tests with coverage report
	@poetry run pytest --cov=namer --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@poetry run pytest-watch -m "not slow"

# --- Pre-commit/Pre-push Shortcuts ---

precommit: ## Quick pre-commit checks (format + fast tests)
	@poetry run poe precommit

pre-push: validate ## Alias for validate (comprehensive pre-push checks)

# --- Dependency Management ---

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

# --- Local Build Targets (Non-Docker) ---

build-local: ## Build Python package locally (non-Docker)
	@poetry run poe build_namer

build-local-deps: ## Build dependencies (npm + videohashes)
	@poetry run poe build_deps

build-local-full: ## Full local build with all deps
	@poetry run poe build_all

# --- Run Targets ---

run: ## Run namer locally (development mode)
	@poetry run python -m namer

run-port: ## Run namer on custom port (use PORT=8080)
	@poetry run python -m namer --port $(PORT)

# --- Documentation ---

docs: ## Open project documentation
	@echo "Documentation locations:"
	@echo "  - Main README: readme.rst"
	@echo "  - Claude guide: CLAUDE.md"
	@echo "  - Project docs: docs/"

# --- Git Helpers ---

branch: ## Show current branch and status
	@git branch --show-current
	@echo ""
	@git status --short

diff: ## Show git diff
	@git diff

commits: ## Show recent commits
	@git log --oneline -10

# --- Shortcuts for Common Workflows ---

quick: lint-fix test-local ## Quick feedback (fix lint + fast tests)

ci: lint format-check typecheck test-local-all ## Simulate CI checks locally

fix: lint-fix format ## Fix all auto-fixable issues

# --- GraphQL Schema Management ---

check-schema-drift: ## Check for GraphQL schema drift (requires STASHDB_TOKEN, TPDB_TOKEN)
	@./scripts/check-schema-drift.sh

update-schema-docs: ## Update GraphQL schema documentation (requires STASHDB_TOKEN, TPDB_TOKEN)
	@./scripts/update-schema-docs.sh