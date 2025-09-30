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

FIRMWARE_INSTALLED=false

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
            log "Successfully downloaded $file"
            FIRMWARE_INSTALLED=true
        else
            log "Downloaded $file but file is empty"
        fi
    else
        log "Failed to download $file (may not be available)"
    fi
done

# If downloads failed, create placeholder files
if ! $FIRMWARE_INSTALLED; then
    log "No firmware files downloaded; proceeding without installing placeholders."
    log "If firmware is required, ensure network access to $FIRMWARE_BASE during build."
fi

# Set proper permissions
chmod 644 /lib/firmware/i915/* 2>/dev/null || true

# List what we have
log "Available Intel GPU firmware files:"
ls -la /lib/firmware/i915/ 2>/dev/null || log "No firmware directory found"

log "Intel firmware installation completed"
exit 0
