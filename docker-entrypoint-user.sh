#!/bin/bash
#
# Enhanced Docker entrypoint with Intel GPU hardware acceleration support and user switching
# This script properly handles PUID/PGID environment variables to fix file ownership issues
#
set -e

echo "[ENTRYPOINT] Starting namer container with Intel GPU hardware acceleration..."
echo "[ENTRYPOINT] Container OS: $(lsb_release -d -s 2>/dev/null || echo 'Unknown')"

# Set default values for PUID/PGID if not provided
PUID=${PUID:-1000}
PGID=${PGID:-1000}
UMASK=${UMASK:-022}

echo "[ENTRYPOINT] User configuration:"
echo "[ENTRYPOINT]   PUID=${PUID}"
echo "[ENTRYPOINT]   PGID=${PGID}"
echo "[ENTRYPOINT]   UMASK=${UMASK}"

# Create group with specified GID if it doesn't exist
if ! getent group ${PGID} > /dev/null 2>&1; then
    echo "[ENTRYPOINT] Creating group with GID ${PGID}"
    groupadd -g ${PGID} -o namergroup
else
    echo "[ENTRYPOINT] Group with GID ${PGID} already exists"
fi

# Create user with specified UID if it doesn't exist
if ! getent passwd ${PUID} > /dev/null 2>&1; then
    echo "[ENTRYPOINT] Creating user with UID ${PUID}"
    useradd -u ${PUID} -g ${PGID} -o -m -s /bin/bash nameruser
else
    echo "[ENTRYPOINT] User with UID ${PUID} already exists"
fi

# Set the umask for the user
umask ${UMASK}

# Create necessary directories and set ownership
mkdir -p /config /app/media

# Fix ownership of application directories
echo "[ENTRYPOINT] Setting ownership of directories to ${PUID}:${PGID}"
chown -R ${PUID}:${PGID} /config /app || true

# Check if we're running the correct Ubuntu version for optimal Intel GPU support
if command -v lsb_release >/dev/null 2>&1; then
    UBUNTU_VERSION=$(lsb_release -r -s)
    if [[ "$UBUNTU_VERSION" < "24.10" ]]; then
        echo "[ENTRYPOINT] WARNING: Running Ubuntu $UBUNTU_VERSION. For full Intel Arc GPU support, Ubuntu 24.10+ is recommended."
    else
        echo "[ENTRYPOINT] Running Ubuntu $UBUNTU_VERSION - Full Intel GPU support available"
    fi
fi

# Check for GPU devices
if [[ -d "/dev/dri" ]] && [[ -n "$(ls -A /dev/dri 2>/dev/null)" ]]; then
    echo "[ENTRYPOINT] GPU devices detected:"
    ls -la /dev/dri/ | grep -E "(card|render)" | while read -r line; do
        echo "[ENTRYPOINT]   $line"
    done
    
    echo "[ENTRYPOINT] Running Intel GPU detection with debugging enabled..."
    
    # Run GPU detection script
    if DEBUG=true TEST_GPU=true /usr/local/bin/detect-gpu.sh; then
        # Source the environment variables written by the GPU detection script
        GPU_ENV_FILE="/tmp/gpu-detected-env"
        if [[ -f "$GPU_ENV_FILE" ]]; then
            source "$GPU_ENV_FILE"
            echo "[ENTRYPOINT] GPU detection successful"
            echo "[ENTRYPOINT] Selected GPU: ${NAMER_GPU_DEVICE:-none}"
            echo "[ENTRYPOINT] Backend: ${NAMER_GPU_BACKEND:-none}"
        else
            echo "[ENTRYPOINT] GPU detection failed - environment file not created"
            echo "[ENTRYPOINT] Selected GPU: none"
            echo "[ENTRYPOINT] Backend: none"
        fi
        
        # Identify the type of Intel GPU detected
        if [[ "${NAMER_GPU_DEVICE}" == *"renderD128"* ]]; then
            echo "[ENTRYPOINT] Primary Intel GPU (renderD128) detected - optimal performance enabled!"
        elif [[ -n "${NAMER_GPU_DEVICE}" ]]; then
            echo "[ENTRYPOINT] Intel GPU detected - hardware acceleration enabled!"
        fi
    else
        echo "[ENTRYPOINT] GPU detection failed or no compatible Intel GPU found"
        echo "[ENTRYPOINT] Will fall back to software encoding"
    fi
else
    echo "[ENTRYPOINT] No GPU devices found, using software processing"
fi

# Set environment variables that Namer can use
export NAMER_GPU_DEVICE="${NAMER_GPU_DEVICE:-}"
export NAMER_GPU_BACKEND="${NAMER_GPU_BACKEND:-}"
export LIBVA_DRIVER_NAME="${LIBVA_DRIVER_NAME:-iHD}"

# Show FFmpeg version and QSV capabilities
echo "[ENTRYPOINT] FFmpeg information:"
if command -v ffmpeg >/dev/null 2>&1; then
    ffmpeg -version | head -1
    echo "[ENTRYPOINT] Intel QSV encoders available:"
    ffmpeg -encoders 2>/dev/null | grep qsv | head -5 || echo "[ENTRYPOINT] No QSV encoders found"
else
    echo "[ENTRYPOINT] FFmpeg not found!"
fi

# Show Intel Media Driver version
echo "[ENTRYPOINT] Intel Media Driver version:"
dpkg -l intel-media-va-driver 2>/dev/null | tail -1 || echo "[ENTRYPOINT] Intel Media Driver not installed"

# Display final configuration
echo "[ENTRYPOINT] Final configuration:"
echo "[ENTRYPOINT]   User: $(getent passwd ${PUID} | cut -d: -f1) (${PUID})"
echo "[ENTRYPOINT]   Group: $(getent group ${PGID} | cut -d: -f1) (${PGID})"
echo "[ENTRYPOINT]   NAMER_GPU_DEVICE=${NAMER_GPU_DEVICE:-none}"
echo "[ENTRYPOINT]   NAMER_GPU_BACKEND=${NAMER_GPU_BACKEND:-software}"
echo "[ENTRYPOINT]   LIBVA_DRIVER_NAME=${LIBVA_DRIVER_NAME:-unset}"
echo "[ENTRYPOINT]   NAMER_CONFIG=${NAMER_CONFIG:-/config/namer.cfg}"

echo "[ENTRYPOINT] Starting namer watchdog as user ${PUID}:${PGID}..."

# Switch to specified user and execute the main application
# Using gosu to properly drop privileges and maintain environment
exec gosu ${PUID}:${PGID} namer watchdog