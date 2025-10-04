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
        setup-dev review local-dev

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
	@echo "  make local-dev       # One-command setup for local development environment"
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

# Docker operations (using native commands)
push: ## Push built image to registry
	@docker push $(IMAGE_NAME):$(VERSION)
	@docker push $(IMAGE_NAME):latest
pull: ## Pull image from registry
	@echo "Pulling $(IMAGE_NAME):$(VERSION)..."
	@docker pull $(IMAGE_NAME):$(VERSION)

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

local-dev: ## One-command setup for local development environment
	@echo "🚀 Setting up local development environment..."
	@echo "Step 1/4: Initializing git submodules..."
	@git submodule update --init --recursive
	@echo "Step 2/4: Installing Node dependencies with pnpm..."
	@if ! command -v pnpm >/dev/null 2>&1; then \
		echo "⚠️  pnpm not found. Please install pnpm first (https://pnpm.io/installation)"; \
		exit 1; \
	fi
	@pnpm install
	@echo "Step 3/4: Installing Python dependencies with Poetry..."
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "⚠️  Poetry not found. Please install Poetry first (https://python-poetry.org/docs/#installation)"; \
		exit 1; \
	fi
	@poetry install
	@echo "Step 4/4: Installing pre-commit hooks..."
	@chmod +x scripts/install-hooks.sh || true
	@./scripts/install-hooks.sh
	@echo "✅ Local development environment setup complete!"
	@echo "🔍 You can now start developing. Try 'poetry run namer --help' to get started."
