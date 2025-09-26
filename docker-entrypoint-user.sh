#!/bin/bash
#
# Enhanced Docker entrypoint with Intel GPU hardware acceleration support and user switching
# This script properly handles PUID/PGID environment variables to fix file ownership issues
#
set -Eeuo pipefail

echo "[ENTRYPOINT] Starting namer container with Intel GPU hardware acceleration..."
echo "[ENTRYPOINT] Container OS: $(lsb_release -d -s 2>/dev/null || echo 'Unknown')"

# Set default values for PUID/PGID if not provided
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
UMASK="${UMASK:-0002}"

echo "[ENTRYPOINT] User configuration:"
echo "[ENTRYPOINT]   PUID=${PUID}"
echo "[ENTRYPOINT]   PGID=${PGID}"
echo "[ENTRYPOINT]   UMASK=${UMASK}"

# Create group with specified GID if it doesn't exist
if ! getent group "${PGID}" > /dev/null 2>&1; then
    echo "[ENTRYPOINT] Creating group with GID ${PGID}"
    groupadd -g "${PGID}" -o namergroup
else
    echo "[ENTRYPOINT] Group with GID ${PGID} already exists"
fi

# Create user with specified UID if it doesn't exist
if ! getent passwd "${PUID}" > /dev/null 2>&1; then
    echo "[ENTRYPOINT] Creating user with UID ${PUID}"
    useradd -u "${PUID}" -g "${PGID}" -o -m -s /bin/bash nameruser
else
    echo "[ENTRYPOINT] User with UID ${PUID} already exists"
fi

# Set the umask for the user
umask "${UMASK}"

# Create necessary directories and set ownership, tolerating pre-created mounts
ensure_dir() {
    local target_dir="$1"
    local errf
    errf="$(mktemp -t entrypoint_mkdir_err.XXXXXX)"
    if ! mkdir -p "$target_dir" 2>"$errf"; then
        if [[ -d "$target_dir" ]]; then
            echo "[ENTRYPOINT] Warning: could not create $target_dir (likely read-only bind mount); assuming it already exists"
        else
            echo "[ENTRYPOINT] ERROR: failed to create $target_dir"
            cat "$errf"
            exit 1
        fi
    fi
    rm -f "$errf"
}
ensure_dir /config
ensure_dir /app/media

# Resolve username and home for the PUID (supports pre-existing users)
if entry="$(getent passwd "${PUID}")"; then
    USERNAME="${entry%%:*}"
    USER_HOME="$(echo "$entry" | awk -F: '{print $6}')"
else
    USERNAME="nameruser"
    USER_HOME="/home/nameruser"
fi
export USERNAME USER_HOME

# Ensure standard user home subdirectories exist
mkdir -p "${USER_HOME}/.local/bin" \
         "${USER_HOME}/.local/share" \
         "${USER_HOME}/.cache" \
         "${USER_HOME}/.config"

# Fix ownership of application directories
echo "[ENTRYPOINT] Setting ownership of directories to ${PUID}:${PGID}"
ownership="${PUID}:${PGID}"
for dir in /config /app "${USER_HOME}"; do
    if [[ -w "$dir" && -d "$dir" ]]; then
        chown -R "$ownership" -- "$dir" || true
    else
        echo "[ENTRYPOINT] Warning: skipping chown for $dir (not writable or not a directory)"
    fi
done

# Also fix ownership of common volume mounts and any env-configured directories
chown_dir_if_possible() {
    local d="$1"
    if [[ -n "$d" && -d "$d" ]]; then
        if [[ -w "$d" ]]; then
            echo "[ENTRYPOINT] Ensuring ownership for: $d"
            chown -R "$ownership" -- "$d" || true
        else
            echo "[ENTRYPOINT] Warning: cannot chown $d (read-only mount?)"
        fi
    fi
}

# From env (if provided)
chown_dir_if_possible "${WATCH_DIR:-}"
chown_dir_if_possible "${WORK_DIR:-}"
chown_dir_if_possible "${DEST_DIR:-}"
chown_dir_if_possible "${FAILED_DIR:-}"
chown_dir_if_possible "${AMBIGUOUS_DIR:-}"

# Common default mount points
for d in /watch /work /dest /failed /ambiguous; do
    chown_dir_if_possible "$d"
done

# From NAMER_CONFIG (if provided), parse common directory settings and chown them
if [[ -n "${NAMER_CONFIG:-}" && -f "${NAMER_CONFIG}" ]]; then
    echo "[ENTRYPOINT] Parsing config for directory ownership fixes: ${NAMER_CONFIG}"
    while IFS='=' read -r raw_key raw_val; do
        # trim spaces and normalize key
        key="$(echo "$raw_key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr '[:upper:]' '[:lower:]')"
        val="$(echo "$raw_val" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | sed 's/^"//;s/"$//' | sed "s/^'//;s/'$//")"
        case "$key" in
            watch_dir|work_dir|dest_dir|failed_dir|ambiguous_dir)
                chown_dir_if_possible "$val"
                ;;
        esac
    done < <(grep -E '^[[:space:]]*(watch_dir|work_dir|dest_dir|failed_dir|ambiguous_dir)[[:space:]]*=' "${NAMER_CONFIG}" || true)
fi

# We execute Namer via Python module; no need to copy any installed binary
echo "[ENTRYPOINT] Preparing Python environment..."

# Check if we're running the correct Ubuntu version for optimal Intel GPU support
if command -v lsb_release >/dev/null 2>&1 && command -v dpkg >/dev/null 2>&1; then
    UBUNTU_VERSION=$(lsb_release -r -s)
    if dpkg --compare-versions "$UBUNTU_VERSION" lt "24.10"; then
        echo "[ENTRYPOINT] WARNING: Running Ubuntu $UBUNTU_VERSION. For full Intel Arc GPU support, Ubuntu 24.10+ is recommended."
    else
        echo "[ENTRYPOINT] Running Ubuntu $UBUNTU_VERSION - Full Intel GPU support available"
    fi
fi

# Check for GPU devices
if [[ -d "/dev/dri" ]] && compgen -G "/dev/dri/*" > /dev/null; then
    echo "[ENTRYPOINT] GPU devices detected:"
    for gpu_node in /dev/dri/card* /dev/dri/render*; do
        [[ -e "$gpu_node" ]] || continue
        echo "[ENTRYPOINT]   $(ls -ld "$gpu_node")"
    done
    
    echo "[ENTRYPOINT] Running Intel GPU detection with debugging enabled..."
    
    # Run GPU detection script
    if DEBUG=true TEST_GPU=true /usr/local/bin/detect-gpu.sh; then
        # Source the environment variables written by the GPU detection script
        GPU_ENV_FILE="/tmp/gpu-detected-env"
        if [[ -f "$GPU_ENV_FILE" ]]; then
            # shellcheck source=/dev/null
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

# Ensure GPU device access using proper group membership (secure approach)
if [[ -d "/dev/dri" ]]; then
    echo "[ENTRYPOINT] Setting up GPU device access via group membership..."
    # USERNAME already resolved; if empty, derive from PUID and fail if unresolved
    if [[ -z "${USERNAME:-}" ]]; then
        USERNAME="$(getent passwd "${PUID}" | cut -d: -f1)"
        [[ -n "$USERNAME" ]] || { echo "[ENTRYPOINT] ERROR: could not resolve username for PUID ${PUID}"; exit 1; }
    fi
    
    # Add the user to video and render groups if they exist (standard approach)
    if getent group video >/dev/null 2>&1; then
        if usermod -a -G video "$USERNAME" 2>/dev/null; then
            echo "[ENTRYPOINT] Added user to video group"
        else
            echo "[ENTRYPOINT] Warning: failed to add user to video group"
        fi
    fi
    if getent group render >/dev/null 2>&1; then
        if usermod -a -G render "$USERNAME" 2>/dev/null; then
            echo "[ENTRYPOINT] Added user to render group"
        else
            echo "[ENTRYPOINT] Warning: failed to add user to render group"
        fi
    fi
    
    # DO NOT change device permissions - rely on group membership
    # The devices should already have proper group permissions
    for entry in /dev/dri/*; do
        [[ -e "$entry" ]] || continue
        stat -c '%A %G %U %n' "$entry" 2>/dev/null || true
    done
fi

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
echo "[ENTRYPOINT]   User: ${USERNAME} (${PUID})"
echo "[ENTRYPOINT]   Group: $(getent group | awk -F: -v gid="${PGID}" '$3==gid{print $1; exit}') (${PGID})"
echo "[ENTRYPOINT]   NAMER_GPU_DEVICE=${NAMER_GPU_DEVICE:-none}"
echo "[ENTRYPOINT]   NAMER_GPU_BACKEND=${NAMER_GPU_BACKEND:-software}"
echo "[ENTRYPOINT]   LIBVA_DRIVER_NAME=${LIBVA_DRIVER_NAME:-unset}"
echo "[ENTRYPOINT]   NAMER_CONFIG=${NAMER_CONFIG:-/config/namer.cfg}"

echo "[ENTRYPOINT] Starting namer watchdog as user ${USERNAME}..."


# Set up environment for the switched user
export HOME="$USER_HOME"
export USER="${USERNAME}"
export PATH="$USER_HOME/.local/bin:$PATH"

# Switch to specified user and execute the main application
# Using gosu to properly drop privileges and maintain environment
echo "[ENTRYPOINT] Switching to user and starting application..."

# Most secure approach: Use Python module execution
# This avoids copying executables and maintains proper Python environment
echo "[ENTRYPOINT] Final security check..."
echo "[ENTRYPOINT] User: $(getent passwd ${PUID} | cut -d: -f1)"
echo "[ENTRYPOINT] Home: $USER_HOME"
echo "[ENTRYPOINT] Groups: $(id -nG "${USERNAME}" 2>/dev/null || groups "${USERNAME}" 2>/dev/null || echo 'unknown')"

# Execute via Python module to maintain proper Python environment
# Resolve root's user site-packages for current python
PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo '3.12')"
PY_ROOT_SITE="/root/.local/lib/python${PY_VER}/site-packages"
exec gosu "${USERNAME}" env \
    HOME="$USER_HOME" \
    USER="${USERNAME}" \
    PATH="$USER_HOME/.local/bin:/usr/local/bin:/usr/bin:/bin" \
    PYTHONPATH="${PY_ROOT_SITE}:/usr/lib/python3/dist-packages" \
    NAMER_CONFIG="${NAMER_CONFIG:-/config/namer.cfg}" \
    LIBVA_DRIVER_NAME="${LIBVA_DRIVER_NAME:-iHD}" \
    python3 -m namer watchdog
