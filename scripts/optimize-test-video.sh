#!/usr/bin/env bash
#
# optimize-test-video.sh
#
# Optimizes video files for testing by re-encoding to AV1 at minimal resolution
# while preserving the perceptual hash (PHASH) used by namer for identification.
#
# This is useful for:
# - Reducing test file sizes for CI/CD pipelines
# - Speeding up development iterations
# - Minimizing repository size for test assets
#
# Usage:
#   ./scripts/optimize-test-video.sh INPUT_FILE [OUTPUT_FILE] [OPTIONS]
#
# Arguments:
#   INPUT_FILE   Path to the video file to optimize
#   OUTPUT_FILE  Optional output path (default: INPUT-av1-optimized.mp4)
#
# Options:
#   --target-crf CRF    Target CRF value (default: 60, range: 0-63)
#   --max-crf CRF       Maximum CRF to test (default: 63)
#   --min-width WIDTH   Minimum width to test (default: 160)
#   --preset PRESET     FFmpeg preset (default: 8, range: 0-13)
#   --skip-verify       Skip PHASH verification
#   --keep-audio        Keep audio track (default: remove)
#   --verbose           Enable verbose output
#   --help              Show this help message
#
# Example:
#   ./scripts/optimize-test-video.sh test.mp4
#   ./scripts/optimize-test-video.sh test.mp4 test-opt.mp4 --target-crf 50
#

set -euo pipefail

# Default configuration
DEFAULT_TARGET_CRF=60
DEFAULT_MAX_CRF=63
DEFAULT_MIN_WIDTH=160
DEFAULT_PRESET=8
SKIP_VERIFY=false
KEEP_AUDIO=false
VERBOSE=false

# Colors for output
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

log_success() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    echo -e "${RED}✗${NC} $*" >&2
}

show_help() {
    sed -n '/^# optimize-test-video.sh/,/^$/p' "$0" | sed 's/^# //; s/^#//'
    exit 0
}

check_dependencies() {
    local missing=()
    
    if ! command -v ffmpeg &>/dev/null; then
        missing+=("ffmpeg")
    fi
    
    if ! command -v ffprobe &>/dev/null; then
        missing+=("ffprobe")
    fi
    
    if ! command -v poetry &>/dev/null; then
        missing+=("poetry")
    fi
    
    # Check if ffmpeg has libsvtav1
    if command -v ffmpeg &>/dev/null; then
        if ! ffmpeg -encoders 2>/dev/null | grep -q libsvtav1; then
            log_error "FFmpeg is missing libsvtav1 encoder"
            missing+=("libsvtav1")
        fi
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing[*]}"
        log_info "Please install missing dependencies:"
        log_info "  brew install ffmpeg poetry  # macOS"
        exit 1
    fi
}

get_phash() {
    local file="$1"
    local basename_file
    basename_file=$(basename "$file")
    
    # Clear cache first
    poetry run python -m namer clear-cache "$basename_file" &>/dev/null || true
    
    # Get PHASH (extract from dict output)
    local output
    output=$(poetry run python -m namer hash -f "$file" 2>/dev/null || echo "")
    
    if [[ -z "$output" ]]; then
        return 1
    fi
    
    # Extract phash value from dictionary output
    echo "$output" | grep -oE "'phash': '[^']+'" | cut -d"'" -f4
}

get_duration() {
    local file="$1"
    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null || echo "0"
}

get_file_size() {
    local file="$1"
    stat -f%z "$file" 2>/dev/null || wc -c <"$file"
}

format_size() {
    local bytes="$1"
    if command -v numfmt &>/dev/null; then
        numfmt --to=iec "$bytes"
    else
        # Fallback for systems without numfmt
        if (( bytes > 1073741824 )); then
            echo "$(( bytes / 1073741824 ))GB"
        elif (( bytes > 1048576 )); then
            echo "$(( bytes / 1048576 ))MB"
        elif (( bytes > 1024 )); then
            echo "$(( bytes / 1024 ))KB"
        else
            echo "${bytes}B"
        fi
    fi
}

encode_video() {
    local input="$1"
    local output="$2"
    local crf="$3"
    local width="$4"
    local preset="$5"
    local keep_audio="$6"
    
    local audio_opts=("-an")
    if [[ "$keep_audio" == "true" ]]; then
        audio_opts=("-c:a" "copy")
    fi
    
    local ffmpeg_cmd=(
        ffmpeg -hide_banner -y -i "$input"
        -map 0:v:0
        -c:v libsvtav1
        -crf "$crf"
        -preset "$preset"
        -vf "scale=${width}:-2"
        -pix_fmt yuv420p
        "${audio_opts[@]}"
        -map_metadata -1
        -map_chapters -1
        -movflags +faststart
        "$output"
    )
    
    if [[ "$VERBOSE" == "true" ]]; then
        "${ffmpeg_cmd[@]}" 2>&1
    else
        "${ffmpeg_cmd[@]}" -loglevel error -stats 2>&1 | tail -n 3
    fi
}

# Parse arguments
INPUT_FILE=""
OUTPUT_FILE=""
TARGET_CRF=$DEFAULT_TARGET_CRF
MAX_CRF=$DEFAULT_MAX_CRF
MIN_WIDTH=$DEFAULT_MIN_WIDTH
PRESET=$DEFAULT_PRESET

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            ;;
        --target-crf)
            TARGET_CRF="$2"
            shift 2
            ;;
        --max-crf)
            MAX_CRF="$2"
            shift 2
            ;;
        --min-width)
            MIN_WIDTH="$2"
            shift 2
            ;;
        --preset)
            PRESET="$2"
            shift 2
            ;;
        --skip-verify)
            SKIP_VERIFY=true
            shift
            ;;
        --keep-audio)
            KEEP_AUDIO=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        -*)
            log_error "Unknown option: $1"
            show_help
            ;;
        *)
            if [[ -z "$INPUT_FILE" ]]; then
                INPUT_FILE="$1"
            elif [[ -z "$OUTPUT_FILE" ]]; then
                OUTPUT_FILE="$1"
            else
                log_error "Too many arguments"
                show_help
            fi
            shift
            ;;
    esac
done

# Validate arguments
if [[ -z "$INPUT_FILE" ]]; then
    log_error "Input file is required"
    show_help
fi

if [[ ! -f "$INPUT_FILE" ]]; then
    log_error "Input file does not exist: $INPUT_FILE"
    exit 1
fi

# Set default output file if not provided
if [[ -z "$OUTPUT_FILE" ]]; then
    OUTPUT_DIR=$(dirname "$INPUT_FILE")
    OUTPUT_BASE=$(basename "$INPUT_FILE" .mp4)
    OUTPUT_FILE="${OUTPUT_DIR}/${OUTPUT_BASE}-av1-optimized.mp4"
fi

# Main execution
log_info "Namer Test Video Optimizer"
echo

# Check dependencies
check_dependencies
log_success "All dependencies found"

# Get baseline information
log_info "Analyzing input file..."
ORIGINAL_SIZE=$(get_file_size "$INPUT_FILE")
ORIGINAL_DURATION=$(get_duration "$INPUT_FILE")
ORIGINAL_DURATION_INT=$(printf '%.0f' "$ORIGINAL_DURATION")

log_info "Input: $INPUT_FILE"
log_info "Size: $(format_size "$ORIGINAL_SIZE")"
log_info "Duration: ${ORIGINAL_DURATION_INT}s"

if [[ "$SKIP_VERIFY" == "false" ]]; then
    log_info "Calculating original PHASH..."
    ORIGINAL_PHASH=$(get_phash "$INPUT_FILE")
    
    if [[ -z "$ORIGINAL_PHASH" ]]; then
        log_error "Failed to calculate PHASH for input file"
        exit 1
    fi
    
    log_success "Original PHASH: $ORIGINAL_PHASH"
else
    log_warn "Skipping PHASH verification"
    ORIGINAL_PHASH=""
fi

echo

# Create temporary directory for test encodes
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Encode with target CRF
log_info "Encoding at ${MIN_WIDTH}px width, CRF ${TARGET_CRF}..."
TEMP_OUTPUT="${TEMP_DIR}/test-w${MIN_WIDTH}-crf${TARGET_CRF}.mp4"

encode_video "$INPUT_FILE" "$TEMP_OUTPUT" "$TARGET_CRF" "$MIN_WIDTH" "$PRESET" "$KEEP_AUDIO"

# Verify duration
NEW_DURATION=$(get_duration "$TEMP_OUTPUT")
NEW_DURATION_INT=$(printf '%.0f' "$NEW_DURATION")

if [[ "$NEW_DURATION_INT" -ne "$ORIGINAL_DURATION_INT" ]]; then
    log_error "Duration mismatch: ${ORIGINAL_DURATION_INT}s != ${NEW_DURATION_INT}s"
    exit 1
fi

log_success "Duration verified: ${NEW_DURATION_INT}s"

# Verify PHASH if requested
if [[ "$SKIP_VERIFY" == "false" ]]; then
    log_info "Verifying PHASH..."
    NEW_PHASH=$(get_phash "$TEMP_OUTPUT")
    
    if [[ -z "$NEW_PHASH" ]]; then
        log_error "Failed to calculate PHASH for output file"
        exit 1
    fi
    
    if [[ "$NEW_PHASH" != "$ORIGINAL_PHASH" ]]; then
        log_error "PHASH mismatch!"
        log_error "  Original: $ORIGINAL_PHASH"
        log_error "  New:      $NEW_PHASH"
        
        # Try lower CRF
        if [[ "$TARGET_CRF" -lt "$MAX_CRF" ]]; then
            log_warn "Trying lower CRF values..."
            
            for crf in $(seq $((TARGET_CRF - 5)) 5 0); do
                log_info "Testing CRF ${crf}..."
                TEST_OUTPUT="${TEMP_DIR}/test-w${MIN_WIDTH}-crf${crf}.mp4"
                
                encode_video "$INPUT_FILE" "$TEST_OUTPUT" "$crf" "$MIN_WIDTH" "$PRESET" "$KEEP_AUDIO"
                
                TEST_PHASH=$(get_phash "$TEST_OUTPUT")
                
                if [[ "$TEST_PHASH" == "$ORIGINAL_PHASH" ]]; then
                    log_success "PHASH match found at CRF ${crf}"
                    TEMP_OUTPUT="$TEST_OUTPUT"
                    TARGET_CRF=$crf
                    NEW_PHASH="$TEST_PHASH"
                    break
                fi
            done
            
            if [[ "$NEW_PHASH" != "$ORIGINAL_PHASH" ]]; then
                log_error "Could not find matching PHASH at any tested CRF value"
                exit 1
            fi
        else
            exit 1
        fi
    else
        log_success "PHASH verified: $NEW_PHASH"
    fi
fi

# Get final file size
NEW_SIZE=$(get_file_size "$TEMP_OUTPUT")

# Calculate reduction
REDUCTION=$(awk "BEGIN {printf \"%.2f\", (($ORIGINAL_SIZE - $NEW_SIZE) / $ORIGINAL_SIZE) * 100}")

# Move to final location
mv "$TEMP_OUTPUT" "$OUTPUT_FILE"

# Final summary
echo
log_success "Optimization complete!"
echo
log_info "Output: $OUTPUT_FILE"
log_info "Size: $(format_size "$NEW_SIZE") ($(format_size "$ORIGINAL_SIZE") → $(format_size "$NEW_SIZE"))"
log_info "Reduction: ${REDUCTION}%"
log_info "Settings: ${MIN_WIDTH}px width, CRF ${TARGET_CRF}, preset ${PRESET}"

if [[ "$SKIP_VERIFY" == "false" ]]; then
    log_info "PHASH: $NEW_PHASH ✓"
fi

echo
log_success "Done!"
