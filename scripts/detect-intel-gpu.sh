#!/bin/bash
#
# Enhanced GPU Detection Script for Namer with Arc B580 Support
# Detects Intel Arc GPUs and sets environment variables for optimal hardware acceleration
#
set -euo pipefail

# Function to log messages
log() {
	echo "[GPU-DETECT] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2
}

# Function to get PCI device info for a render device
get_pci_info() {
	local render_device="$1"
	local card_device="${render_device/renderD/card}"
	card_device="${card_device/128/0}" # renderD128 -> card0, renderD129 -> card1, etc.
	card_device="${card_device/129/1}"
	card_device="${card_device/130/2}"
	card_device="${card_device/131/3}"

	if [[ -e "/sys/class/drm/${card_device}/device/vendor" && -e "/sys/class/drm/${card_device}/device/device" ]]; then
		local vendor
		vendor=$(cat "/sys/class/drm/${card_device}/device/vendor" 2>/dev/null || echo "unknown")
		local device
		device=$(cat "/sys/class/drm/${card_device}/device/device" 2>/dev/null || echo "unknown")
		echo "${vendor}:${device}"
	else
		echo "unknown:unknown"
	fi
}

# Function to get GPU name from PCI info
get_gpu_name() {
	local pci_info="$1"
	case "$pci_info" in
	# Intel Arc B-series (Battlemage)
	"0x8086:0xe20b") echo "Intel Arc B580" ;;
	"0x8086:0xe202") echo "Intel Arc B570" ;;
	"0x8086:0xe20c") echo "Intel Arc B770" ;;
	"0x8086:0xe20d") echo "Intel Arc B580" ;;
	"0x8086:0xe209") echo "Intel Arc B580" ;;
	# Intel Arc A-series (Alchemist)
	"0x8086:0x5690") echo "Intel Arc A770" ;;
	"0x8086:0x5691") echo "Intel Arc A750" ;;
	"0x8086:0x5692") echo "Intel Arc A580" ;;
	"0x8086:0x5693") echo "Intel Arc A380" ;;
	"0x8086:0x5694") echo "Intel Arc A310" ;;
	# Intel Xe Graphics (Integrated)
	"0x8086:0x4680") echo "Intel Xe Graphics (DG1)" ;;
	"0x8086:0x4682") echo "Intel Xe Graphics (DG1)" ;;
	"0x8086:0x4688") echo "Intel Xe Graphics (DG1)" ;;
	"0x8086:0x468a") echo "Intel Xe Graphics (DG1)" ;;
	"0x8086:0x468b") echo "Intel Xe Graphics (DG1)" ;;
	# Intel UHD Graphics (Integrated)
	"0x8086:0xa780") echo "Intel UHD Graphics 770" ;;
	"0x8086:0xa781") echo "Intel UHD Graphics 770" ;;
	"0x8086:0xa782") echo "Intel UHD Graphics 730" ;;
	"0x8086:0xa783") echo "Intel UHD Graphics 710" ;;
	# Fallback for other Intel devices
	"0x8086:"*) echo "Intel GPU (Unknown)" ;;
	*) echo "Unknown GPU" ;;
	esac
}

# Function to determine GPU priority (higher number = higher priority)
get_gpu_priority() {
	local pci_info="$1"
	case "$pci_info" in
	# Arc B-series (Battlemage) - highest priority for AV1 support
	"0x8086:0xe20"*) echo "100" ;;
	# Arc A-series (Alchemist) - high priority
	"0x8086:0x569"*) echo "90" ;;
	# Xe Graphics (Discrete) - medium-high priority
	"0x8086:0x468"*) echo "70" ;;
	# UHD Graphics (Integrated) - lower priority but still useful
	"0x8086:0xa78"*) echo "50" ;;
	# Other Intel GPUs
	"0x8086:"*) echo "30" ;;
	# Non-Intel GPUs
	*) echo "0" ;;
	esac
}

# Function to check if device supports QSV
check_qsv_support() {
	local device_path="$1"
	# Try a basic test to see if we can access the device
	if [[ -c "$device_path" && -r "$device_path" ]]; then
		# For Intel devices, assume QSV support
		return 0
	fi
	return 1
}

# Function to test VAAPI initialization
test_vaapi_init() {
	local device_path="$1"
	log "Testing VAAPI initialization for $device_path..."

	# Set environment for testing
	export LIBVA_DRIVER_NAME=iHD

	# Try to test with vainfo (if available)
	if command -v vainfo >/dev/null 2>&1; then
		if timeout 5 vainfo --display drm --device "$device_path" >/dev/null 2>&1; then
			log "VAAPI test successful for $device_path"
			return 0
		else
			log "VAAPI test failed for $device_path"
		fi
	fi

	return 1
}

log "Starting enhanced GPU detection for Arc B580 hardware acceleration..."

# Initialize variables
BEST_DEVICE=""
BEST_BACKEND=""
BEST_PRIORITY=0
BEST_GPU_NAME=""

# Check all render devices
for render_path in /dev/dri/renderD*; do
	if [[ -e "$render_path" ]]; then
		render_device=$(basename "$render_path")
		pci_info=$(get_pci_info "$render_device")
		gpu_name=$(get_gpu_name "$pci_info")
		priority=$(get_gpu_priority "$pci_info")

		log "Found device: $render_path -> $gpu_name (PCI: $pci_info, Priority: $priority)"

		# Check if this is a better choice than our current best
		if [[ "$priority" -gt "$BEST_PRIORITY" ]]; then
			# Check if it's an Intel device and supports QSV
			if [[ "$pci_info" == "0x8086:"* ]]; then
				if check_qsv_support "$render_path"; then
					BEST_DEVICE="$render_path"
					BEST_BACKEND="qsv"
					BEST_PRIORITY="$priority"
					BEST_GPU_NAME="$gpu_name"
					log "New best device: $gpu_name at $render_path (priority: $priority)"
				else
					log "Device $render_path is not accessible, skipping"
				fi
			fi
		fi
	fi
done

# Log the final selection
if [[ -n "$BEST_DEVICE" ]]; then
	log "Selected GPU: $BEST_GPU_NAME at $BEST_DEVICE (backend: $BEST_BACKEND)"

	# Test VAAPI if this is an Arc GPU
	if [[ "$BEST_GPU_NAME" == *"Arc"* ]]; then
		if test_vaapi_init "$BEST_DEVICE"; then
			log "VAAPI initialization successful for Arc GPU"
		else
			log "VAAPI initialization failed, but continuing with QSV"
		fi
	fi
else
	log "No compatible Intel GPUs found, will use software processing"
	BEST_DEVICE=""
	BEST_BACKEND=""
fi

# Export environment variables for the application
export NAMER_GPU_DEVICE="$BEST_DEVICE"
export NAMER_GPU_BACKEND="$BEST_BACKEND"

# Set VAAPI driver for Intel hardware
if [[ -n "$BEST_DEVICE" ]]; then
	export LIBVA_DRIVER_NAME="iHD"       # Intel hybrid driver for modern GPUs
	export INTEL_MEDIA_RUNTIME_VERBOSE=1 # Enable verbose logging for debugging
fi

# Write environment variables to a file that can be sourced by the entrypoint
GPU_ENV_FILE="/tmp/gpu-detected-env"
cat >"$GPU_ENV_FILE" <<EOF
export NAMER_GPU_DEVICE="$BEST_DEVICE"
export NAMER_GPU_BACKEND="$BEST_BACKEND"
export LIBVA_DRIVER_NAME="${LIBVA_DRIVER_NAME:-}"
EOF

log "Environment variables written to $GPU_ENV_FILE for entrypoint sourcing"

# Log the results
log "GPU detection complete:"
log "  GPU: ${BEST_GPU_NAME:-none}"
log "  Device: ${BEST_DEVICE:-none}"
log "  Backend: ${BEST_BACKEND:-software}"

# Print environment for debugging
if [[ "${DEBUG:-false}" == "true" ]]; then
	log "Environment variables set:"
	log "  NAMER_GPU_DEVICE=$NAMER_GPU_DEVICE"
	log "  NAMER_GPU_BACKEND=$NAMER_GPU_BACKEND"
	log "  LIBVA_DRIVER_NAME=${LIBVA_DRIVER_NAME:-unset}"
fi

# Additional testing if requested
if [[ "${TEST_GPU:-false}" == "true" && -n "$BEST_DEVICE" ]]; then
	log "Running additional GPU tests..."

	# Test basic FFmpeg QSV availability
	if command -v ffmpeg >/dev/null 2>&1; then
		log "Testing FFmpeg QSV support..."
		if timeout 10 ffmpeg -f lavfi -i testsrc=duration=0.1:size=64x64:rate=1 -c:v h264_qsv -init_hw_device qsv=qsv:"$BEST_DEVICE" -f null - >/dev/null 2>&1; then
			log "FFmpeg QSV test successful!"
		else
			log "FFmpeg QSV test failed - may need manual debugging"
		fi
	fi
fi

# Return success if we found a compatible GPU
if [[ -n "$BEST_DEVICE" ]]; then
	exit 0
else
	exit 1
fi
