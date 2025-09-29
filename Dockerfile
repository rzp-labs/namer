FROM ubuntu:24.04 AS base

# Automatically provided by Docker BuildKit
ARG TARGETARCH

ENV PATH="/usr/local/bin:/root/.local/bin:$PATH"
ENV TZ=Europe/London
ARG DEBIAN_FRONTEND=noninteractive

# Use standard Ubuntu repositories (avoid "devel" channels)


# Install dependencies with Intel GPU hardware acceleration support (Intel packages only on amd64)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3-pip \
       python3 \
       pipx \
       ffmpeg \
       tzdata \
       curl \
       wget \
       gnupg2 \
       vainfo \
       bc \
       gosu \
    && if [ "$TARGETARCH" = "amd64" ]; then \
         apt-get install -y --no-install-recommends \
           intel-media-va-driver \
           libmfx-gen1.2 \
         ; \
       fi \
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean

FROM base AS build
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       libffi-dev \
       libssl-dev \
       systemd \
       systemd-sysv \
       python3-dev \
       python3-venv \
       golang \
       git \
       xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean

ENV DISPLAY=:99
ARG CHROME_VERSION="google-chrome-stable"
ARG TARGETARCH
RUN set -eux; \
  if [ "${TARGETARCH}" = "amd64" ]; then \
    ARCH=$(dpkg --print-architecture); \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux.gpg; \
    echo "deb [arch=${ARCH} signed-by=/usr/share/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends google-chrome-stable; \
  else \
    echo "Skipping Google Chrome installation on ${TARGETARCH}"; \
  fi; \
  rm -rf /var/lib/apt/lists/* /var/cache/apt/*

RUN pipx install poetry
# Install Node.js (v22) from NodeSource with GPG verification, then pin PNPM 10
RUN set -eux; \
    ARCH=$(dpkg --print-architecture); \
    # Add NodeSource GPG key and repository for Node 22
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg; \
    echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends nodejs; \
    # Verify node version is >= 22
    node -v; \
    # Install pnpm with scripts disabled to avoid executing arbitrary lifecycle scripts
    npm i -g pnpm@10.0.0 --ignore-scripts; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

RUN mkdir /work/
COPY . /work
WORKDIR /work

# ⚠️  CRITICAL: Replace base ffmpeg.py with enhanced version for container builds
# This OVERWRITES namer/ffmpeg.py with the enhanced version that includes:
#   - Intel GPU hardware acceleration (QSV)
#   - Advanced codec detection and mapping  
#   - Robust fallback chains for different hardware configurations
#
# 🔧 MAINTENANCE WARNING:
# When making changes to FFmpeg functionality, you MUST update BOTH files:
#   - namer/ffmpeg.py (base/development version)
#   - namer/ffmpeg_enhanced.py (production/container version - used here)
#
# Failure to sync both files will cause inconsistent behavior!
COPY namer/ffmpeg_enhanced.py /work/namer/ffmpeg.py

RUN rm -rf /work/namer/__pycache__/ || true \
    && rm -rf /work/test/__pycache__/ || true \
    && poetry lock \
    && poetry install
RUN bash -lc "( Xvfb :99 & cd /work/ && poetry run poe build_deps && poetry run poe build_namer )"

FROM base

# Install the built namer package globally
COPY --from=build /work/dist/namer-*.tar.gz /
RUN pip3 install --break-system-packages /namer-*.tar.gz \
    && rm /namer-*.tar.gz

# Install Intel GPU firmware from host if available, otherwise use a fallback
# This step installs firmware to support Intel Arc, UHD Graphics, and other Intel GPUs
RUN mkdir -p /lib/firmware/i915 /tmp/firmware-backup
COPY scripts/install-intel-firmware-fast.sh /tmp/install-intel-firmware-fast.sh
RUN timeout 300 bash -c "chmod +x /tmp/install-intel-firmware-fast.sh && /tmp/install-intel-firmware-fast.sh"

# Copy Intel GPU detection script
COPY scripts/detect-intel-gpu.sh /usr/local/bin/detect-gpu.sh
RUN chmod +x /usr/local/bin/detect-gpu.sh

# Create non-root user and secure directories
# Align defaults with docker-compose (PUID=99, PGID=100), but allow overrides at build time
ARG PUID=99
ARG PGID=100
RUN set -eux; \
    if getent group "$PGID" >/dev/null; then \
      grpname="$(getent group "$PGID" | cut -d: -f1)"; \
      groupmod -n namer "$grpname" 2>/dev/null || true; \
    else \
      groupadd -g "$PGID" namer; \
    fi; \
    if getent passwd "$PUID" >/dev/null; then \
      usrname="$(getent passwd "$PUID" | cut -d: -f1)"; \
      usermod -l namer "$usrname" 2>/dev/null || true; \
      usermod -g "$PGID" namer 2>/dev/null || true; \
    else \
      useradd -m -u "$PUID" -g "$PGID" namer; \
    fi; \
    mkdir -p /database /cache /tmp/namer; \
    chown -R namer:namer /database /cache /tmp/namer; \
    chmod 775 /database /cache /tmp/namer

ARG BUILD_DATE
ARG GIT_HASH  
ARG PROJECT_VERSION

ENV PYTHONUNBUFFERED=1
ENV NAMER_CONFIG=/config/namer.cfg
ENV BUILD_DATE=$BUILD_DATE
ENV GIT_HASH=$GIT_HASH
ENV PROJECT_VERSION=$PROJECT_VERSION
ENV LIBVA_DRIVER_NAME=iHD

EXPOSE 6980
HEALTHCHECK --interval=1m --timeout=30s CMD curl -sf "$(namer url)/api/healthcheck" >/dev/null || exit 1

# Enhanced entrypoint with Intel GPU support and user switching
COPY docker-entrypoint-user.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
# Run as root; the entrypoint will drop privileges via gosu to the resolved user
USER root
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]