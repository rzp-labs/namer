FROM ubuntu:latest AS base

ENV PATH="/root/.local/bin:$PATH"
ENV TZ=Europe/London
ARG DEBIAN_FRONTEND=noninteractive

# Install dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3-pip \
       python3 \
       pipx \
       ffmpeg \
       tzdata \
       curl \
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
       wget \
       gnupg2 \
       xvfb \
       golang \
       git \
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
RUN rm -rf /work/namer/__pycache__/ || true \
    && rm -rf /work/test/__pycache__/ || true \
    && poetry install
RUN . /root/.bashrc && ( Xvfb :99 & cd /work/ && poetry run poe build_all )

FROM base
COPY --from=build /work/dist/namer-*.tar.gz /
RUN pipx install /namer-*.tar.gz \
    && rm /namer-*.tar.gz

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
