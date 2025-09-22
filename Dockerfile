FROM ubuntu:24.04 AS base

# Automatically provided by Docker BuildKit
ARG TARGETARCH

ENV PATH="/usr/local/bin:/root/.local/bin:$PATH"
ENV TZ=Europe/London
ARG DEBIAN_FRONTEND=noninteractive

# Switch to Ubuntu development repositories to get latest Intel GPU support
RUN echo "Switching to Ubuntu development repositories for Intel Arc B580 support..." \
    && echo "deb http://archive.ubuntu.com/ubuntu devel main restricted universe multiverse" > /etc/apt/sources.list \
    && echo "deb http://archive.ubuntu.com/ubuntu devel-updates main restricted universe multiverse" >> /etc/apt/sources.list \
    && echo "deb http://archive.ubuntu.com/ubuntu devel-backports main restricted universe multiverse" >> /etc/apt/sources.list \
    && echo "deb http://security.ubuntu.com/ubuntu devel-security main restricted universe multiverse" >> /etc/apt/sources.list


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
RUN ARCH=$(dpkg --print-architecture) \
  && if [ "$ARCH" = "amd64" ]; then \
       CHROME_URL="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"; \
     elif [ "$ARCH" = "arm64" ]; then \
       CHROME_URL="https://dl.google.com/linux/direct/google-chrome-stable_current_arm64.deb"; \
     else \
       echo "Unsupported architecture: $ARCH" && exit 1; \
     fi \
  && curl -fsSL "$CHROME_URL" -o chrome.deb \
  && apt-get update \
  && apt-get install -y --no-install-recommends ./chrome.deb \
  && rm chrome.deb \
  && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

RUN pipx install poetry
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
RUN . /root/.bashrc && nvm install 22
RUN . /root/.bashrc && npm i -g pnpm@latest-10

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
    && poetry install
RUN bash -c "source /root/.bashrc && export PATH=/root/.nvm/versions/node/$(ls /root/.nvm/versions/node | head -1)/bin:$PATH && ( Xvfb :99 & cd /work/ && poetry run poe build_deps && poetry run poe build_namer )"

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

# Create necessary directories with appropriate permissions
RUN mkdir -p /database /cache /tmp/namer \
    && chmod 777 /database /cache /tmp/namer

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
HEALTHCHECK --interval=1m --timeout=30s CMD curl -s $(namer url)/api/healthcheck >/dev/null || exit 1

# Enhanced entrypoint with Intel GPU support and user switching
COPY docker-entrypoint-user.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
