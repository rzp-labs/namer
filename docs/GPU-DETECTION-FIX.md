# GPU Detection Environment Variable Fix

## Problem Identified

The namer application has sophisticated Intel GPU acceleration support built-in, but there was a bug in the environment variable propagation between the GPU detection script and the main application.

### Issue Details

1. **GPU Detection Script Works Perfectly**: The `/usr/local/bin/detect-gpu.sh` script correctly:
   - Detects Intel Arc B580 at `/dev/dri/renderD128` 
   - Sets `NAMER_GPU_BACKEND=qsv` (Intel Quick Sync Video)
   - Sets `NAMER_GPU_DEVICE=/dev/dri/renderD128`
   - Successfully tests VAAPI and FFmpeg QSV functionality

2. **Environment Variable Propagation Failed**: The variables exported by the GPU detection script weren't making it back to the docker entrypoint script due to subprocess execution.

3. **Result**: The application would log:
   ```
   [ENTRYPOINT] Selected GPU: none
   [ENTRYPOINT] Backend: none
   ```
   And fall back to software-only processing.

## Root Cause

In `docker-entrypoint.sh`, the GPU detection script was called like this:
```bash
if DEBUG=true TEST_GPU=true /usr/local/bin/detect-gpu.sh; then
```

The environment variables (`NAMER_GPU_DEVICE`, `NAMER_GPU_BACKEND`) were exported in the subprocess but didn't propagate back to the parent shell.

## Solution Implemented

### 1. Modified GPU Detection Script (`scripts/detect-intel-gpu.sh`)

Added code to write environment variables to a file that can be sourced:

```bash
# Write environment variables to a file that can be sourced by the entrypoint
GPU_ENV_FILE="/tmp/gpu-detected-env"
cat > "$GPU_ENV_FILE" << EOF
export NAMER_GPU_DEVICE="$BEST_DEVICE"
export NAMER_GPU_BACKEND="$BEST_BACKEND"
export LIBVA_DRIVER_NAME="${LIBVA_DRIVER_NAME:-}"
EOF
```

### 2. Modified Docker Entrypoint (`docker-entrypoint.sh`)

Updated to source the environment variables file:

```bash
# Run GPU detection script
if DEBUG=true TEST_GPU=true /usr/local/bin/detect-gpu.sh; then
    # Source the environment variables written by the GPU detection script
    GPU_ENV_FILE="/tmp/gpu-detected-env"
    if [[ -f "$GPU_ENV_FILE" ]]; then
        source "$GPU_ENV_FILE"
        echo "[ENTRYPOINT] GPU detection successful"
        echo "[ENTRYPOINT] Selected GPU: ${NAMER_GPU_DEVICE:-none}"
        echo "[ENTRYPOINT] Backend: ${NAMER_GPU_BACKEND:-none}"
    fi
```

## Expected Result

After the fix, the container logs should show:

```
[ENTRYPOINT] GPU detection successful
[ENTRYPOINT] Selected GPU: /dev/dri/renderD128
[ENTRYPOINT] Backend: qsv
[ENTRYPOINT] Intel GPU detected - hardware acceleration enabled!
```

And the namer application will use Intel QSV hardware acceleration for:
- Video decoding (H.264, H.265/HEVC, AV1 with Arc B580)
- Video scaling 
- Phash generation

## GPU Utilization

With this fix, you should see:
1. **Faster phash generation** - Hardware-accelerated video decoding
2. **GPU activity** - Intel Arc B580 will show utilization during video processing
3. **Better performance** - Reduced CPU usage for video processing tasks

## Testing the Fix

1. **Build test image**:
   ```bash
   ./test-gpu-fix.sh
   ```

2. **Update compose file temporarily**:
   ```yaml
   image: ghcr.io/rzp-labs/namer:gpu-fix-test
   ```

3. **Deploy and verify**:
   ```bash
   docker compose up -d
   docker logs namer | grep -E "(Selected GPU|Backend)"
   ```

4. **Monitor GPU usage** during video processing to confirm hardware acceleration is active.

## Why This Approach Is Better Than Hard-coding

This solution maintains the dynamic GPU detection that properly handles:
- Multiple GPU scenarios
- GPU enumeration order changes
- Different Intel GPU models (Arc, UHD Graphics, etc.)
- System reconfigurations

The detection script will always select the best available Intel GPU automatically.