#!/bin/bash
#
# Intel Firmware Installation Script (Optimized)
# Attempts to get Intel GPU firmware for Arc B580 support quickly
#
set -euo pipefail

log() {
    echo "[FIRMWARE] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2
}

log "Installing Intel GPU firmware for Arc B580 support (optimized)..."

# Skip the large linux-firmware package and go straight to specific downloads
log "Downloading specific Intel GPU firmware files..."
mkdir -p /lib/firmware/i915

# Arc B580 (BMG) firmware files
FIRMWARE_BASE="https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/plain/i915"

# List of required firmware files for Arc B580
FIRMWARE_FILES=(
    "bmg_dmc.bin"
    "dg2_dmc_ver2_08.bin" 
    "dg2_guc_70.bin"
    "dg2_huc_gsc.bin"
)

declare -A FIRMWARE_SHA256=(
    ["bmg_dmc.bin"]=76e3ec6ea3a53ce727e43b84f5ea14c55400a2d118dac356d4e12a3cfac06b4d
    ["dg2_dmc_ver2_08.bin"]=cac5204087bba70a81c53778846340e57a4e35e5959b7b42006969f6e5f45466
    ["dg2_guc_70.bin"]=159e6148c21a8594d780cd710a9eb5fae8410da1e493b51b1ad3b87ad7a6830a
    ["dg2_huc_gsc.bin"]=045db8407373e0d688f17fc5e75621d7d0b7bdeb6eb67ba36c656aec145fe8fb
)

# NOTE FOR MAINTAINERS:
# When bumping firmware versions update FIRMWARE_FILES above and refresh FIRMWARE_SHA256 entries using:
#   shasum -a 256 <downloaded-file>

FIRMWARE_INSTALLED=false
DOWNLOAD_ERRORS=0

for file in "${FIRMWARE_FILES[@]}"; do
    log "Downloading $file..."
    if timeout 30 wget -q \
        --https-only \
        --secure-protocol=TLSv1_2 \
        --max-redirect=3 \
        --tries=3 \
        --connect-timeout=10 \
        --read-timeout=10 \
        -O "/lib/firmware/i915/$file" "$FIRMWARE_BASE/$file" 2>/dev/null; then
        if [ -s "/lib/firmware/i915/$file" ]; then
            expected_hash="${FIRMWARE_SHA256[$file]:-}"
            if [ -z "$expected_hash" ]; then
                log "No checksum available for $file; deleting to avoid unsafe firmware"
                rm -f "/lib/firmware/i915/$file"
                DOWNLOAD_ERRORS=$((DOWNLOAD_ERRORS + 1))
                continue
            fi

            if echo "$expected_hash  /lib/firmware/i915/$file" | sha256sum -c - >/dev/null 2>&1; then
                log "Successfully downloaded $file (checksum OK)"
                FIRMWARE_INSTALLED=true
            else
                log "Checksum mismatch for $file; removing corrupt download"
                rm -f "/lib/firmware/i915/$file"
                DOWNLOAD_ERRORS=$((DOWNLOAD_ERRORS + 1))
            fi
        else
            log "Downloaded $file but file is empty"
            rm -f "/lib/firmware/i915/$file"
            DOWNLOAD_ERRORS=$((DOWNLOAD_ERRORS + 1))
        fi
    else
        log "Failed to download $file (may not be available)"
        DOWNLOAD_ERRORS=$((DOWNLOAD_ERRORS + 1))
    fi
done

# If downloads failed, fall back to distro package to avoid broken GPU acceleration
if ! $FIRMWARE_INSTALLED; then
    log "No verified firmware files installed; attempting fallback installation via linux-firmware package."
    if command -v apt-get >/dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        if apt-get update && apt-get install -y --no-install-recommends linux-firmware; then
            log "Fallback linux-firmware installation completed."
            FIRMWARE_INSTALLED=true
            rm -rf /var/lib/apt/lists/*
        else
            log "Fallback linux-firmware installation failed."
        fi
    else
        log "apt-get not available; cannot perform fallback linux-firmware installation."
    fi
fi

if ! $FIRMWARE_INSTALLED; then
    log "Intel firmware installation unsuccessful; please provide firmware manually or ensure network access to $FIRMWARE_BASE"
    exit 1
fi

# Set proper permissions
chmod 644 /lib/firmware/i915/* 2>/dev/null || true

# List what we have
log "Available Intel GPU firmware files:"
ls -la /lib/firmware/i915/ 2>/dev/null || log "No firmware directory found"

log "Intel firmware installation completed"
exit 0
