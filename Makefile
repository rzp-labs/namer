# Namer Docker Build Makefile

# Configuration
IMAGE_NAME ?= rzp-labs/namer
VERSION ?= $(shell git describe --tags --always --dirty)
BUILD_DATE = $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_HASH = $(shell git rev-parse --verify HEAD)
REMOTE_HOST ?= your-build-server.com
REMOTE_USER ?= docker

# Docker build arguments
DOCKER_BUILD_ARGS = \
	--build-arg BUILD_DATE=$(BUILD_DATE) \
	--build-arg GIT_HASH=$(GIT_HASH) \
	--build-arg PROJECT_VERSION=$(VERSION)

.PHONY: build build-remote build-multi push test clean help

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker image locally
	@echo "🏗️  Building $(IMAGE_NAME):$(VERSION) locally..."
	docker build $(DOCKER_BUILD_ARGS) -t $(IMAGE_NAME):$(VERSION) -t $(IMAGE_NAME):latest .

build-remote: ## Build Docker image on remote host
	@echo "🌐 Building $(IMAGE_NAME):$(VERSION) on remote host $(REMOTE_HOST)..."
	@./scripts/remote-build.sh

build-multi: setup-remote-builder ## Build multi-platform images using remote builder
	@echo "🚀 Building multi-platform $(IMAGE_NAME):$(VERSION)..."
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		$(DOCKER_BUILD_ARGS) \
		-t $(IMAGE_NAME):$(VERSION) \
		-t $(IMAGE_NAME):latest \
		--push \
		.

setup-remote-builder: ## Set up remote buildx builder
	@echo "⚙️  Setting up remote buildx builder..."
	@./scripts/setup-remote-builder.sh

test: ## Test the built Docker image
	@echo "🧪 Testing $(IMAGE_NAME):$(VERSION)..."
	docker run --rm $(IMAGE_NAME):$(VERSION) namer --help
	docker run --rm $(IMAGE_NAME):$(VERSION) namer suggest --help

push: ## Push image to registry
	@echo "📤 Pushing $(IMAGE_NAME):$(VERSION)..."
	docker push $(IMAGE_NAME):$(VERSION)
	docker push $(IMAGE_NAME):latest

clean: ## Clean up build artifacts and unused images
	@echo "🧹 Cleaning up..."
	docker image prune -f
	docker system prune -f

ci-build: ## GitHub Actions compatible build
	@echo "🤖 CI Build - $(IMAGE_NAME):$(VERSION)"
	docker build $(DOCKER_BUILD_ARGS) -t $(IMAGE_NAME):$(VERSION) .
	docker tag $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest

# Remote build with specific environment
build-production: ## Build for production deployment
	@$(MAKE) build-remote REMOTE_HOST=prod-build-server.com VERSION=$(VERSION)

build-staging: ## Build for staging deployment  
	@$(MAKE) build-remote REMOTE_HOST=staging-build-server.com VERSION=staging-$(VERSION)

# Development helpers
dev-build: ## Quick development build without tests
	@echo "🚀 Quick development build..."
	docker build --target build $(DOCKER_BUILD_ARGS) -t $(IMAGE_NAME):dev .

# Show current configuration
config: ## Show current build configuration
	@echo "Configuration:"
	@echo "  IMAGE_NAME: $(IMAGE_NAME)"
	@echo "  VERSION: $(VERSION)"
	@echo "  BUILD_DATE: $(BUILD_DATE)"
	@echo "  GIT_HASH: $(GIT_HASH)"
	@echo "  REMOTE_HOST: $(REMOTE_HOST)"
	@echo "  REMOTE_USER: $(REMOTE_USER)"
