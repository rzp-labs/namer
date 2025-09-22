#!/bin/bash
#
# Simple Docker entrypoint for ARM64 development builds
# No Intel GPU support, no user switching - just basic functionality
#
set -e

echo "[ENTRYPOINT] Starting namer container in development mode..."
echo "[ENTRYPOINT] Container OS: $(lsb_release -d -s 2>/dev/null || echo 'Unknown')"

# Set environment variables
export NAMER_GPU_DEVICE=""
export NAMER_GPU_BACKEND="software"
export LIBVA_DRIVER_NAME=""

# Show basic FFmpeg version (software only)
echo "[ENTRYPOINT] FFmpeg information:"
if command -v ffmpeg >/dev/null 2>&1; then
    ffmpeg -version | head -1
    echo "[ENTRYPOINT] Software encoding only (no GPU acceleration)"
else
    echo "[ENTRYPOINT] FFmpeg not found!"
fi

# Display final configuration
echo "[ENTRYPOINT] Final configuration:"
echo "[ENTRYPOINT]   NAMER_GPU_DEVICE=none"
echo "[ENTRYPOINT]   NAMER_GPU_BACKEND=software"
echo "[ENTRYPOINT]   NAMER_CONFIG=${NAMER_CONFIG:-/config/namer.cfg}"

echo "[ENTRYPOINT] Starting namer watchdog..."

# Execute the main application using python3 -m to avoid PATH issues
exec python3 -m namer watchdog