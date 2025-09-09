# Stage 1: Build videohashes (Go binaries)
FROM golang:1.22-alpine AS videohashes-builder
RUN apk add --no-cache make git
WORKDIR /build
COPY videohashes/ ./
RUN make build || echo "Make build failed, but continuing..."

# Stage 2: Build frontend assets (Node.js)
FROM node:22-alpine AS frontend-builder
WORKDIR /build
# Copy package files first for better layer caching
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
# Copy frontend source and build
COPY namer/web/ namer/web/
COPY webpack.prod.js ./
RUN pnpm run build

# Stage 3: Build Python package
FROM python:3.11-slim AS python-builder
# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN --mount=type=cache,target=/root/.cache/pip pip install poetry

WORKDIR /build

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock ./
RUN --mount=type=cache,target=/root/.cache/pypi poetry config virtualenvs.create false \
    && poetry install --only=main --no-root --no-interaction --no-ansi

# Copy source code
COPY namer/ namer/
COPY README.md ./
# Copy built assets (create directories if they don't exist)
COPY --from=frontend-builder /build/namer/web/public/ namer/web/public/
RUN mkdir -p namer/tools
COPY --from=videohashes-builder /build/build/ namer/tools/ || echo "No videohashes build output found"

# Build the Python package
RUN poetry build

# Stage 4: Final runtime image
FROM python:3.11-slim

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pipx and the built package
RUN --mount=type=cache,target=/root/.cache/pip pip install pipx
COPY --from=python-builder /build/dist/*.tar.gz /tmp/
RUN pipx install /tmp/*.tar.gz && rm /tmp/*.tar.gz

ARG BUILD_DATE
ARG GIT_HASH
ARG PROJECT_VERSION

ENV PYTHONUNBUFFERED=1
ENV NAMER_CONFIG=/config/namer.cfg
ENV BUILD_DATE=$BUILD_DATE
ENV GIT_HASH=$GIT_HASH
ENV PROJECT_VERSION=$PROJECT_VERSION

EXPOSE 6980
HEALTHCHECK --interval=1m --timeout=30s CMD curl -s $(namer url)/api/healthcheck >/dev/null || exit 1
ENTRYPOINT ["namer", "watchdog"]
