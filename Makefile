# Namer Docker Build Makefile - Clean & Atomic
#
# Uses scripts in ./scripts/ for all complex operations
# This Makefile focuses on simple composition and user interface

# Configuration
IMAGE_NAME ?= rzp-labs/namer
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo 'latest')
SCRIPT_DIR = ./scripts

.PHONY: help build build-fast build-full build-dev test test-basic test-integration validate clean clean-deep config

.PHONY: help build build-fast build-full build-dev test test-basic test-integration validate clean clean-deep config
.PHONY: build-local build-remote build-multi push build-test build-dev-arm64 build-orbstack build-orbstack-fast build-orbstack-full test-orbstack clean-orbstack

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

# Build targets (composable)
build: ## Build Docker image (auto-detects platform)
	@echo "🔍 Detecting build platform..."
	@if [ "$$(uname -s)" = "Darwin" ] && [ "$$(uname -m)" = "arm64" ]; then \
		echo "🍎 Detected: macOS ARM64 - Using OrbStack build (avoids Ubuntu dev repo issues)"; \
		echo "📋 Intel GPU hardware acceleration disabled (not applicable on macOS)"; \
		$(MAKE) build-orbstack; \
	elif [ "$$(uname -m)" = "x86_64" ] && [ -d "/dev/dri" ]; then \
		echo "🖥️  Detected: x86_64 with Intel GPU support - Using standard build"; \
		echo "🏗️  Building $(IMAGE_NAME):$(VERSION) with Intel GPU support..."; \
		docker build $(DOCKER_BUILD_ARGS) -t $(IMAGE_NAME):$(VERSION) -t $(IMAGE_NAME):latest .; \
	else \
		echo "🖥️  Detected: Standard build environment"; \
		echo "⚠️  Intel GPU hardware acceleration may not be available"; \
		echo "🏗️  Building $(IMAGE_NAME):$(VERSION)..."; \
		docker build $(DOCKER_BUILD_ARGS) -t $(IMAGE_NAME):$(VERSION) -t $(IMAGE_NAME):latest .; \
	fi

build-fast: ## Fast Docker build (skips tests, ~5 minutes)
	@$(SCRIPT_DIR)/build-orbstack.sh fast $(IMAGE_NAME) $(VERSION)

build-local: ## Force local Docker build (ignores platform detection)
	@echo "🏗️  Force building $(IMAGE_NAME):$(VERSION) locally (ignoring platform)..."
	@echo "⚠️  Warning: This may fail on macOS ARM64 due to Ubuntu dev repository issues"
	docker build $(DOCKER_BUILD_ARGS) -t $(IMAGE_NAME):$(VERSION) -t $(IMAGE_NAME):latest .

build-full: ## Complete build with all tests (~20 minutes)  
	@$(SCRIPT_DIR)/build-orbstack.sh full $(IMAGE_NAME) $(VERSION)

build-dev: ## Development build (build stage only, no export)
	@$(SCRIPT_DIR)/build-orbstack.sh dev $(IMAGE_NAME) $(VERSION)

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

build-staging: ## Build for staging deployment
	@$(MAKE) build-remote REMOTE_HOST=staging-build-server.com VERSION=staging-$(VERSION)

# Development helpers
dev-build: ## Quick development build without tests
	@echo "🚀 Quick development build..."
	docker build --target build $(DOCKER_BUILD_ARGS) -t $(IMAGE_NAME):dev .

build-dev-arm64: ## Fast ARM64 development build (no Intel GPU, stable repos)
	@echo "🍎 Fast ARM64 development build for local testing..."
	@echo "⚠️  Note: Intel GPU acceleration disabled for ARM64 compatibility"
	docker build -f Dockerfile.dev-arm64 $(DOCKER_BUILD_ARGS) -t $(IMAGE_NAME):dev-arm64 -t $(IMAGE_NAME):dev .

# OrbStack build targets (for macOS ARM64 compatibility)
build-orbstack: build-orbstack-fast ## Build Docker image using OrbStack Ubuntu VM (default: fast)

build-orbstack-fast: ## Fast OrbStack build (skips tests, ~5 minutes)
	@echo "🚀 Building $(IMAGE_NAME):$(VERSION) via OrbStack (fast mode)..."
	@./scripts/build-orbstack.sh fast $(IMAGE_NAME) $(VERSION)

build-orbstack-full: ## Complete OrbStack build with tests (~20 minutes)
	@echo "🚀 Building $(IMAGE_NAME):$(VERSION) via OrbStack (full mode)..."
	@./scripts/build-orbstack.sh full $(IMAGE_NAME) $(VERSION)

test-orbstack: ## Test OrbStack-built image with file ownership fix
	@echo "🧪 Testing file ownership fix with OrbStack-built image..."
	@./scripts/test-docker.sh $(IMAGE_NAME) $(VERSION) ownership

clean-orbstack: ## Clean up OrbStack VM and test files
	@echo "🧹 Cleaning up OrbStack resources..."
	@./scripts/cleanup.sh orbstack

# Show current configuration
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

# Docker operations (using native commands)
push: ## Push built image to registry
	@echo "📤 Pushing $(IMAGE_NAME):$(VERSION)..."
	@docker push $(IMAGE_NAME):$(VERSION)
	@docker push $(IMAGE_NAME):latest

pull: ## Pull image from registry
	@echo "📥 Pulling $(IMAGE_NAME):$(VERSION)..."
	@docker pull $(IMAGE_NAME):$(VERSION)