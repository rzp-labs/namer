# Intel Arc B580 Hardware Acceleration for Namer

This document explains the hardware acceleration setup for Namer using Intel Arc B580 GPU with QSV (Quick Sync Video) technology.

## Overview

The enhanced hardware acceleration system provides:
- **Automatic GPU detection** with Intel Arc B580 prioritization over integrated graphics
- **Dynamic decoder selection** based on video codec (h264_qsv, hevc_qsv, av1_qsv, etc.)
- **Robust fallback chain**: QSV → VAAPI → Software decoding
- **Performance monitoring** and diagnostic tools
- **Zero-configuration** operation with intelligent device mapping

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Container     │    │  GPU Detection   │    │ Enhanced FFMPEG │
│   Startup       │───▶│     Script       │───▶│     Module      │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Environment     │    │ Device Priority  │    │ Codec Mapping   │
│ Variables       │    │ Intel Arc > iGPU │    │ H264→h264_qsv   │
│ NAMER_GPU_*     │    │ /dev/dri/renderD*│    │ HEVC→hevc_qsv   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Deploy with Hardware Acceleration

```bash
cd /mnt/user/system/dev/namer

# Stop current containers
docker-compose -f compose-prod.yaml down

# Deploy with hardware acceleration
docker-compose -f compose-hwaccel.yaml up -d

# Monitor startup logs
docker logs -f namer-backlog
```

### 2. Verify GPU Detection

```bash
# Check GPU detection in container startup logs
docker logs namer-backlog 2>&1 | grep -i "GPU-DETECT"

# Expected output:
# [GPU-DETECT] Found Intel Arc GPU: Intel Arc B580 at /dev/dri/renderD128
# [GPU-DETECT] Selected Intel Arc GPU: /dev/dri/renderD128 (backend: qsv)
```

### 3. Test Hardware Acceleration

```bash
# Run GPU acceleration test
/mnt/user/system/dev/namer/scripts/test-gpu-acceleration.sh

# Test with specific file
/mnt/user/system/dev/namer/scripts/test-gpu-acceleration.sh /path/to/video.mp4
```

## Configuration Files

### Enhanced Configuration (`namer-backlog-qsv.cfg`)
```ini
[Phash]
search_phash = true
use_alt_phash_tool = true
use_gpu = true
# QSV backend provides best performance for Intel Arc GPUs
ffmpeg_hwaccel_backend = qsv  
# Device auto-detected by startup script
ffmpeg_hwaccel_device = /dev/dri/renderD128
# Decoder auto-selected based on video codec
ffmpeg_hwaccel_decoder = 
```

### Docker Compose (`compose-hwaccel.yaml`)
Key features:
- **All DRI devices mapped**: `/dev/dri:/dev/dri`
- **Video group access**: `group_add: ["18"]`
- **GPU detection script**: Mounted as `/usr/local/bin/detect-gpu.sh`
- **Enhanced FFMPEG module**: Replaces original with QSV support
- **Startup integration**: Runs GPU detection before application start

## GPU Detection Logic

### Device Priority (High to Low)
1. **Intel Arc B580** (`/dev/dri/renderD128`) - Discrete GPU with full QSV support
2. **Intel Integrated Graphics** (`/dev/dri/renderD129+`) - Basic QSV support
3. **Software Fallback** - CPU-only processing

### PCI Device Mapping
- **Intel Arc B580**: PCI ID `0x8086:0xe20b` → `/dev/dri/renderD128`
- **Intel iGPU**: PCI ID `0x8086:0xa780` → `/dev/dri/renderD129`

The detection script automatically maps PCI devices to render nodes and selects the optimal device.

## Automatic Decoder Selection

### Codec to QSV Decoder Mapping
| Video Codec | QSV Decoder | Intel Arc B580 Support |
|-------------|-------------|------------------------|
| H.264       | h264_qsv    | ✅ Full Support       |
| HEVC/H.265  | hevc_qsv    | ✅ Full Support       |
| AV1         | av1_qsv     | ✅ Full Support       |
| VP9         | vp9_qsv     | ✅ Full Support       |
| VP8         | vp8_qsv     | ✅ Full Support       |
| MPEG-2      | mpeg2_qsv   | ✅ Full Support       |

### Fallback Chain
1. **QSV Hardware Decoding** (Primary)
   - Intel Arc B580 → `/dev/dri/renderD128`
   - Uses codec-specific decoder (e.g., `h264_qsv`)
   - Hardware scaling with `scale_qsv`

2. **VAAPI Hardware Scaling** (Secondary)  
   - Software decode + GPU scaling
   - `hwupload` → `scale_vaapi` → `hwdownload`
   - Compatible with all Intel GPUs

3. **Software Processing** (Tertiary)
   - CPU-only decode and scaling
   - Guaranteed compatibility
   - Performance baseline for comparison

## Performance Expectations

### Intel Arc B580 Performance Gains
| Video Codec | Resolution | Expected Speedup |
|-------------|------------|------------------|
| H.264       | 1080p      | 3-5x faster      |
| HEVC        | 1080p      | 4-6x faster      |
| AV1         | 1080p      | 2-4x faster      |
| H.264       | 4K         | 5-8x faster      |
| HEVC        | 4K         | 6-10x faster     |

*Performance varies based on video complexity and system configuration*

### Phash Processing Impact
- **Before**: ~15-30 seconds per video (CPU-only)
- **After**: ~3-8 seconds per video (Intel Arc B580)
- **Overall throughput**: 3-5x improvement in video processing rate

## Troubleshooting

### Common Issues

#### 1. GPU Not Detected
```bash
# Check if devices are accessible
ls -la /dev/dri/

# Run GPU detection manually
DEBUG=true /mnt/user/system/dev/namer/scripts/detect-gpu.sh

# Check PCI devices
lspci | grep -i vga
```

#### 2. QSV Acceleration Fails
```bash
# Test QSV availability in container
docker exec namer-backlog ffmpeg -hwaccels 2>/dev/null | grep qsv

# Test specific decoder
docker exec namer-backlog ffmpeg -decoders 2>/dev/null | grep h264_qsv

# Check device permissions
docker exec namer-backlog ls -la /dev/dri/renderD128
```

#### 3. Performance Issues
```bash
# Run performance comparison
/mnt/user/system/dev/namer/scripts/test-gpu-acceleration.sh /path/to/test/video.mp4

# Check if software fallback is being used
docker logs namer-backlog 2>&1 | grep -i "falling back to software"

# Monitor GPU usage
nvidia-smi  # For NVIDIA GPUs
intel_gpu_top  # For Intel GPUs (if available)
```

### Environment Variables

The GPU detection script sets these environment variables:

```bash
# Primary GPU device path (auto-detected)
NAMER_GPU_DEVICE=/dev/dri/renderD128

# Hardware acceleration backend
NAMER_GPU_BACKEND=qsv

# Intel VA-API driver
LIBVA_DRIVER_NAME=iHD
```

### Advanced Configuration

#### Override GPU Selection
```yaml
# In docker-compose file, add manual override:
environment:
  - NAMER_GPU_DEVICE=/dev/dri/renderD129  # Force integrated GPU
  - NAMER_GPU_BACKEND=vaapi               # Force VAAPI backend
```

#### Enable Debug Logging
```yaml
environment:
  - DEBUG=true  # Enable detailed GPU detection logging
```

#### Test GPU Access
```yaml
environment:
  - TEST_GPU=true  # Test GPU accessibility during detection
```

## Monitoring and Maintenance

### Regular Health Checks
```bash
# 1. Weekly performance verification
/mnt/user/system/dev/namer/scripts/test-gpu-acceleration.sh

# 2. Check for GPU-related errors in logs
docker logs namer-backlog --since=24h 2>&1 | grep -i -E "(qsv|vaapi|gpu|hardware)"

# 3. Verify GPU device accessibility
docker exec namer-backlog ls -la /dev/dri/ | grep renderD128
```

### Performance Monitoring
```bash
# Monitor processing times in logs
docker logs namer-backlog 2>&1 | grep -E "(Calculating phash|phash.*completed)"

# Check for software fallback warnings
docker logs namer-backlog 2>&1 | grep -i "falling back to software"
```

### Updating the System

#### After unRAID Updates
```bash
# 1. Verify GPU devices are still accessible
ls -la /dev/dri/

# 2. Check PCI mapping hasn't changed  
lspci | grep -i vga

# 3. Restart containers to re-detect GPU
docker-compose -f compose-hwaccel.yaml restart
```

#### After Container Updates
```bash
# 1. Ensure volume mounts are preserved
docker-compose -f compose-hwaccel.yaml config

# 2. Restart with GPU detection
docker-compose -f compose-hwaccel.yaml up -d
```

## Files Reference

### Core Files
- `compose-hwaccel.yaml` - Docker Compose with hardware acceleration
- `namer-backlog-qsv.cfg` - Optimized configuration for QSV
- `scripts/detect-gpu.sh` - GPU detection and device selection
- `namer/ffmpeg_enhanced.py` - Enhanced FFMPEG module with QSV support
- `scripts/test-gpu-acceleration.sh` - Performance testing and validation

### Backup Files  
- `compose-prod.yaml.backup` - Original Docker Compose configuration
- `namer-backlog.cfg.backup` - Original backlog configuration
- `namer/ffmpeg.py.backup` - Original FFMPEG module

## Support

For issues or questions regarding Intel Arc B580 hardware acceleration:

1. **Check logs**: Review startup and processing logs for GPU-related messages
2. **Run diagnostics**: Use the test script to verify acceleration functionality  
3. **Verify hardware**: Ensure Intel Arc B580 is properly installed and recognized by the system
4. **Review configuration**: Confirm Docker Compose and application configurations are correct

The hardware acceleration system is designed to be self-healing with automatic fallback to software processing if hardware acceleration fails.
