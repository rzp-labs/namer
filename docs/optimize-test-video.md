# Test Video Optimization Script

## Overview

`optimize-test-video.sh` is a utility script that dramatically reduces test video file sizes while preserving the perceptual hash (PHASH) used by namer for video identification.

This script is essential for:
- **CI/CD pipelines**: Reducing disk space and bandwidth requirements
- **Development**: Faster test iterations with smaller files
- **Repository management**: Keeping test assets manageable
- **Testing**: Maintaining PHASH accuracy while minimizing file size

## Quick Start

```bash
# Basic usage - optimizes to default settings
./scripts/optimize-test-video.sh input.mp4

# Specify output file
./scripts/optimize-test-video.sh input.mp4 output.mp4

# Custom compression level
./scripts/optimize-test-video.sh input.mp4 --target-crf 50

# Keep audio track
./scripts/optimize-test-video.sh input.mp4 --keep-audio

# Show detailed progress
./scripts/optimize-test-video.sh input.mp4 --verbose
```

## How It Works

The script re-encodes videos using these optimizations:

1. **Resolution**: Scales to 160px width (matching namer's PHASH analysis resolution)
2. **Codec**: AV1 (libsvtav1) for superior compression
3. **CRF**: Default 60 (high compression, acceptable quality for testing)
4. **Audio**: Removed by default (not needed for PHASH)
5. **Metadata**: Stripped to minimize file size

### Why These Settings Work

Namer's PHASH algorithm:
1. Extracts 25 screenshots (5x5 grid) at time intervals
2. Resizes each screenshot to **160px width**
3. Generates a hash from the composite image

Since the optimized video is already at 160px width (the PHASH analysis resolution), the hash remains identical despite extreme compression.

## Options Reference

### Basic Options

| Option | Description | Default |
|--------|-------------|---------|
| `INPUT_FILE` | Path to video to optimize | Required |
| `OUTPUT_FILE` | Output path | `INPUT-av1-optimized.mp4` |

### Compression Options

| Option | Description | Default | Range |
|--------|-------------|---------|-------|
| `--target-crf CRF` | Target compression level | 60 | 0-63 |
| `--max-crf CRF` | Maximum CRF to test if target fails | 63 | 0-63 |
| `--min-width WIDTH` | Output video width | 160 | Any |
| `--preset PRESET` | Encoding speed/efficiency | 8 | 0-13 |

**CRF Guide:**
- Lower = Better quality, larger file
- Higher = Lower quality, smaller file
- 0 = Lossless
- 60 = Default (99%+ size reduction)
- 63 = Maximum compression (may break PHASH)

**Preset Guide:**
- 0-3 = Slow, best compression
- 4-8 = Balanced (default: 8)
- 9-13 = Fast, larger files

### Control Options

| Option | Description |
|--------|-------------|
| `--skip-verify` | Skip PHASH verification (faster, risky) |
| `--keep-audio` | Keep audio track (increases file size) |
| `--verbose` | Show detailed FFmpeg output |
| `--help` | Show help message |

## Examples

### Basic Optimization

```bash
./scripts/optimize-test-video.sh test.mp4
```

**Result**: `test-av1-optimized.mp4` (typically 99%+ smaller)

### Conservative Compression

```bash
./scripts/optimize-test-video.sh large-test.mp4 --target-crf 45
```

**Use case**: When PHASH stability is critical

### Fast Encoding

```bash
./scripts/optimize-test-video.sh test.mp4 --preset 10
```

**Use case**: Quick iterations during development

### Keep Audio for Testing

```bash
./scripts/optimize-test-video.sh test.mp4 --keep-audio
```

**Use case**: When audio stream testing is needed

### Batch Processing

```bash
for file in test/*.mp4; do
    ./scripts/optimize-test-video.sh "$file"
done
```

### Custom Output Directory

```bash
INPUT="test/videos/large-file.mp4"
OUTPUT="test/videos/optimized/small-file.mp4"
./scripts/optimize-test-video.sh "$INPUT" "$OUTPUT"
```

## Expected Results

### Typical Optimization

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Size | 3.3 GB | 15 MB | -99.56% |
| Resolution | 1920x1080 | 160x90 | -98.5% |
| PHASH | `a18f...` | `a18f...` | ✓ Same |
| Duration | 3408s | 3408s | ✓ Same |

### Performance

- **Encoding speed**: ~20-25x realtime (on Apple Silicon M-series)
- **Processing time**: ~2.5 minutes per hour of video
- **Compression ratio**: Typically 200:1 to 300:1

## Troubleshooting

### PHASH Mismatch

If the script reports a PHASH mismatch:

1. **Automatic retry**: Script will automatically try lower CRF values (55, 50, 45...)
2. **Manual adjustment**: Use `--target-crf 50` or lower
3. **Last resort**: Use `--target-crf 35` with `--min-width 240`

### Duration Mismatch

This indicates a serious encoding issue. Check:
- Input file is not corrupt
- FFmpeg is working correctly
- Sufficient disk space available

### Slow Encoding

Options to speed up:
```bash
# Faster preset (larger file)
./scripts/optimize-test-video.sh input.mp4 --preset 10

# Skip verification (risky)
./scripts/optimize-test-video.sh input.mp4 --skip-verify
```

### Missing Dependencies

Error: `Missing required dependencies`

**Solution**:
```bash
# macOS
brew install ffmpeg poetry

# Linux (Ubuntu/Debian)
apt-get install ffmpeg poetry

# Verify libsvtav1 support
ffmpeg -encoders | grep libsvtav1
```

## Advanced Usage

### Integration with CI/CD

**GitHub Actions example**:
```yaml
- name: Optimize test videos
  run: |
    for video in test/fixtures/*.mp4; do
      ./scripts/optimize-test-video.sh "$video" --skip-verify
    done
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Auto-optimize large test videos
find test -name "*.mp4" -size +100M | while read file; do
    echo "Optimizing $file..."
    ./scripts/optimize-test-video.sh "$file"
done
```

### Custom Encoding Settings

For special cases, modify the script or use FFmpeg directly:

```bash
# Lower resolution for tiny files
./scripts/optimize-test-video.sh input.mp4 --min-width 80

# Extreme compression (may break PHASH)
./scripts/optimize-test-video.sh input.mp4 --target-crf 63
```

## Technical Details

### Encoding Command

The script generates this FFmpeg command:
```bash
ffmpeg -hide_banner -y -i INPUT \
  -map 0:v:0 \
  -c:v libsvtav1 \
  -crf 60 \
  -preset 8 \
  -vf "scale=160:-2" \
  -pix_fmt yuv420p \
  -an \
  -map_metadata -1 \
  -map_chapters -1 \
  -movflags +faststart \
  OUTPUT
```

### PHASH Verification

After encoding, the script:
1. Clears namer's hash cache
2. Calculates PHASH of output file
3. Compares to original PHASH
4. Retries with lower CRF if mismatch

### Safety Features

- **Duration check**: Ensures encoded video has same duration
- **Temporary files**: Uses temp directory, cleaned on exit
- **Error handling**: Exits on any failure with clear message
- **Automatic retry**: Tries lower CRF if PHASH fails

## Limitations

- **OSHASH will change**: File-based hash depends on file size
- **Visual quality**: Output not suitable for viewing
- **Audio**: Removed by default (use `--keep-audio` if needed)
- **Metadata**: Stripped completely
- **File format**: Only MP4 output supported

## Best Practices

### DO

- ✓ Use for integration tests and CI/CD
- ✓ Verify PHASH matches before committing
- ✓ Keep original files until tests pass
- ✓ Document optimization settings in commit messages

### DON'T

- ✗ Use optimized files for visual quality tests
- ✗ Skip PHASH verification in production
- ✗ Optimize files that need audio
- ✗ Delete originals without backup

## Related Documentation

- [AV1 Optimization README](../test/integration/media/0-intake/README-av1-optimization.md)
- [WARP.md - Project Overview](../WARP.md)
- [Namer Configuration Guide](../namer/namer.cfg.default)

## Support

Issues or questions:
1. Check this README first
2. Review the optimization guide in test assets
3. Run with `--verbose` for detailed output
4. Check FFmpeg and Poetry versions
5. Open an issue with reproduction steps

## License

Same as the parent namer project.
