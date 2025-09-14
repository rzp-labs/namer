# syntax=docker/dockerfile:1
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive

# OS-level deps needed for this repo
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
        libffi-dev \
        libssl-dev \
        python3-dev \
        pkg-config \
        git \
        curl \
        ca-certificates \
        make \
        unzip \
    && rm -rf /var/lib/apt/lists/*

