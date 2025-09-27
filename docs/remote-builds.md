# Remote Docker Build Guide

This guide covers different approaches for building Docker images on remote build servers instead of locally.

## 🚀 Quick Start

```bash
# Show available build targets
make help

# Build locally (current behavior)
make build

# Build on remote Linux server  
make build-remote REMOTE_HOST=your-server.com

# Build multi-platform images
make build-multi
```

## 🏗️ Build Patterns

### 1. GitHub Actions (Recommended for CI/CD)

**Best for:** Automated builds, multi-platform images, team development

**Benefits:**
- ✅ Native Linux AMD64/ARM64 builders
- ✅ Built-in container registry (ghcr.io)
- ✅ Automatic builds on push/PR
- ✅ Free for public repos, generous limits for private
- ✅ Integrated caching and security scanning

**Setup:**
```bash
# The workflow is already configured in .github/workflows/docker-build.yml
# Just push to main/develop or create a tag:
git tag v1.19.16-stashdb
git push origin --tags
```

**Features:**
- Builds for both `linux/amd64` and `linux/arm64`
- Automatic versioning from git tags
- Caching between builds
- Automatic testing of built images

### 2. Remote Docker Context

**Best for:** One-off builds, development testing, specific server targeting

**Benefits:**  
- ✅ Direct SSH access to remote Docker daemon
- ✅ Uses remote server resources
- ✅ Simple setup with existing Docker installation

**Setup:**
```bash
# Configure your remote host
export DOCKER_REMOTE_HOST=build-server.example.com
export DOCKER_REMOTE_USER=docker

# Run the build
./scripts/remote-build.sh
```

**What it does:**
1. Creates Docker context pointing to remote host
2. Syncs source code via rsync
3. Builds image on remote Docker daemon
4. Tests the image
5. Cleans up build context

### 3. Docker Buildx (Multi-platform)

**Best for:** Building for multiple architectures, complex build requirements

**Benefits:**
- ✅ True multi-platform builds (ARM64 + AMD64)
- ✅ Advanced caching strategies  
- ✅ Can use remote builders
- ✅ Emulation support for cross-compilation

**Setup:**
```bash
# One-time setup of remote builder
./scripts/setup-remote-builder.sh

# Build for multiple platforms
./scripts/build-with-remote.sh
```

**Architectures supported:**
- `linux/amd64` - Intel/AMD 64-bit
- `linux/arm64` - ARM 64-bit (Apple Silicon, ARM servers)

### 4. Makefile Integration

**Best for:** Standardized development workflows

**Usage:**
```bash
make config              # Show current settings
make build              # Local build
make build-remote       # Remote build  
make build-multi        # Multi-platform remote build
make test              # Test built image
make push              # Push to registry
```

## 🎯 Architecture Solutions

### Problem: Building on Apple Silicon

**Issue:** Local builds create ARM64 binaries, but production needs AMD64

**Solutions:**

1. **GitHub Actions (Recommended):**
   ```yaml
   # Builds both architectures automatically
   platforms: linux/amd64,linux/arm64
   ```

2. **Remote Linux Builder:**
   ```bash
   make build-remote REMOTE_HOST=amd64-linux-server.com
   ```

3. **Multi-platform Buildx:**
   ```bash
   make build-multi  # Creates both AMD64 and ARM64
   ```

### Problem: Cross-compilation Issues

**Issue:** Go binary builds with wrong architecture

**Solution:** The build system automatically detects target platform:

```bash
# In pyproject.toml - this logic handles architecture detection:
build_videohashes = { shell = "mkdir -p ./videohashes/dist && if [[ \"$OSTYPE\" == \"darwin\"* ]]; then make macos-arm64 -C ./videohashes; else make linux-amd64 -C ./videohashes; fi" }
```

## 📊 Comparison Matrix

| Method | Multi-Platform | Setup | Cost | CI/CD | Caching |
|--------|----------------|-------|------|-------|---------|
| GitHub Actions | ✅ | Easy | Free* | ✅ | ✅ |
| Remote Context | ❌ | Medium | Server | ❌ | ❌ |
| Docker Buildx | ✅ | Medium | Server | Partial | ✅ |
| Local Build | ❌ | None | None | ❌ | ❌ |

*Free for public repos, paid tiers for private repos with high usage

## 🔧 Environment Configuration

### Required Environment Variables

```bash
# Remote build configuration
export DOCKER_REMOTE_HOST=your-build-server.com
export DOCKER_REMOTE_USER=docker

# Image configuration  
export IMAGE_NAME=nehpz/namer
export VERSION=1.19.16-stashdb

# Registry authentication (for pushes)
export DOCKER_REGISTRY=ghcr.io
export DOCKER_USERNAME=your-username
export DOCKER_PASSWORD=your-token
```

### SSH Key Setup (for remote builds)

```bash
# Generate SSH key if needed
ssh-keygen -t ed25519 -C "docker-build-key"

# Copy to remote host
ssh-copy-id -i ~/.ssh/id_ed25519 docker@your-build-server.com

# Test connection
ssh docker@your-build-server.com "docker version"
```

## 🎯 Production Deployment

### Recommended Workflow

1. **Development:** Use GitHub Actions for automated builds
2. **Staging:** Deploy from GitHub Container Registry
3. **Production:** Use tagged releases with multi-platform images

```bash
# Tag a release
git tag v1.19.16-stashdb
git push origin --tags

# GitHub Actions automatically builds and pushes:
# ghcr.io/your-org/namer:v1.19.16-stashdb
# ghcr.io/your-org/namer:latest
```

### Deployment Command

```bash
# Pull and run from registry
docker pull ghcr.io/your-org/namer:v1.19.16-stashdb
docker run -d \
  -v /path/to/config:/config \
  -v /path/to/media:/media \
  -p 6980:6980 \
  ghcr.io/your-org/namer:v1.19.16-stashdb
```

## 🐛 Troubleshooting

### Build Failures

1. **Architecture mismatch:**
   ```bash
   # Check what was built
   docker run --rm your-image uname -m
   
   # Force rebuild with correct platform
   docker buildx build --platform linux/amd64 .
   ```

2. **SSH connection issues:**
   ```bash
   # Test SSH connection
   ssh -v docker@your-build-server.com
   
   # Check Docker daemon
   ssh docker@your-build-server.com "docker version"
   ```

3. **Permission issues:**
   ```bash
   # Add user to docker group
   ssh your-server.com "sudo usermod -aG docker $USER"
   ```

## 🔍 Monitoring Builds

### GitHub Actions
- Check Actions tab in GitHub repository
- View logs and artifacts
- Monitor build times and success rates

### Remote Builds
```bash
# Monitor build progress
ssh docker@your-server.com "docker logs -f \$(docker ps -q --filter ancestor=buildx_buildkit)"

# Check builder resources
ssh docker@your-server.com "docker system df"
```

This approach solves your architecture mismatch issues while providing scalable, production-ready build infrastructure! 🚀
