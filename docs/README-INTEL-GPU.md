# Intel GPU Hardware Acceleration for Namer

This document describes the automated Intel GPU hardware acceleration support for Namer, supporting Intel Arc GPUs, UHD Graphics, and other Intel GPUs with QSV.

## Overview

Intel GPU hardware acceleration requires Ubuntu 24.10+ with the latest Intel Media Driver and OneVPL runtime. This setup provides:

- **🏆 Intel Arc GPUs** - AV1 + H.264/H.265 hardware encoding (optimal performance)
- **🥈 Intel UHD Graphics** - H.264/H.265 hardware encoding (good performance) 
- **🥉 Other Intel GPUs** - QSV hardware acceleration where supported
- **⚡ Automatic GPU detection** with intelligent prioritization
- **🔄 Graceful fallback** to software encoding if no Intel GPU found

## Supported GPUs

### **✅ Fully Supported Intel GPUs**

| GPU Family | Examples | Priority | Codecs | Performance |
|------------|----------|----------|---------|-------------|
| **Arc B-series** | B580, B570, B770 | Highest (100) | **AV1** + H.264/H.265 + VP9 | **Excellent** |
| **Arc A-series** | A770, A750, A580, A380, A310 | High (90) | H.264/H.265 + VP9 | **Very Good** |
| **Xe Graphics** | DG1 (discrete) | Medium-High (70) | H.264/H.265 | **Good** |
| **UHD Graphics** | UHD 770, 730, 710 | Medium (50) | H.264/H.265 | **Good** |
| **Other Intel** | Any Intel GPU | Low (30) | Basic QSV | **Basic** |

### **❌ Not Supported**
- NVIDIA GPUs (requires separate NVENC/CUDA setup)
- AMD GPUs (requires separate VAAPI/ROCm setup)  
- Non-Intel GPUs

## Files Structure

### **Core Files**
```
📁 namer/
├── 🐋 Dockerfile.intel-gpu            # Ubuntu 24.10 + Intel drivers
├── 🚀 docker-entrypoint-intel.sh     # Enhanced entrypoint with GPU detection  
├── 🛠️  build-intel-gpu.sh            # Build script
└── 📋 README-INTEL-GPU.md            # This documentation

📁 scripts/
├── 🔍 detect-intel-gpu.sh            # Intel GPU detection & prioritization
└── 📦 install-intel-firmware.sh       # Intel GPU firmware installer
```

### **Key Features**

#### **1. Automatic Intel GPU Detection**
- Scans all available Intel GPUs
- Prioritizes by performance capability (Arc B > Arc A > UHD Graphics)
- Automatically configures optimal settings
- Tests hardware acceleration functionality

#### **2. Ubuntu 24.10 Base**
- Latest Intel Media Driver (24.3.4+) for Arc GPU support
- Intel OneVPL GPU Runtime (libmfx-gen1.2) for QSV
- Full Intel GPU firmware support

#### **3. Smart Fallback System**
- Multiple Intel GPUs → Chooses best one automatically
- No Intel GPU found → Falls back to software encoding
- Arc GPU priority → Optimizes for AV1 support when available

## Usage

### **Building the Container**
```bash
./build-intel-gpu.sh
```

### **Testing Intel GPU Detection**
```bash
docker run --rm --device /dev/dri:/dev/dri \
  -e DEBUG=true -e TEST_GPU=true \
  namer:intel-gpu /usr/local/bin/detect-gpu.sh
```

### **Running with Intel GPU Acceleration**
```bash
docker run -d \
  --name namer-intel-gpu \
  --device /dev/dri:/dev/dri \
  -v ./config:/config \
  -v ./media:/app/media \
  -p 6980:6980 \
  namer:intel-gpu
```

### **Docker Compose Example**
```yaml
services:
  namer:
    image: namer:intel-gpu
    container_name: namer-intel-gpu
    restart: unless-stopped
    devices:
      - /dev/dri:/dev/dri
    volumes:
      - ./config:/config
      - ./media:/app/media
    ports:
      - "6980:6980"
    environment:
      - LIBVA_DRIVER_NAME=iHD
      - DEBUG=false
```

## Configuration

### **Namer Configuration**
Your `namer.cfg` should include:
```ini
[Phash]
use_gpu = true
ffmpeg_hwaccel_backend = qsv
ffmpeg_hwaccel_device = /dev/dri/renderD128  # Auto-detected
ffmpeg_hwaccel_decoder = 
```

### **Environment Variables**
The detection script automatically sets:
- `NAMER_GPU_DEVICE` - Selected Intel GPU device path
- `NAMER_GPU_BACKEND` - Backend type (qsv)  
- `LIBVA_DRIVER_NAME` - VAAPI driver (iHD)

## Troubleshooting

### **Check Intel GPU Detection**
```bash
docker exec namer-intel-gpu /usr/local/bin/detect-gpu.sh
```

### **Verify Hardware Acceleration**
```bash
# Check Intel GPUs
docker exec namer-intel-gpu lspci | grep Intel

# Test QSV encoding  
docker exec namer-intel-gpu ffmpeg \
  -f lavfi -i testsrc=duration=1:size=640x480:rate=30 \
  -c:v h264_qsv -init_hw_device qsv=qsv:/dev/dri/renderD128 \
  -f null -
```

### **Common Issues**

#### **"No Intel GPUs found"**
- Ensure `--device /dev/dri:/dev/dri` is passed to container
- Check host has Intel GPU: `lspci | grep Intel`  
- Verify render device permissions: `ls -la /dev/dri/`

#### **"VAAPI initialization failed"**  
- Still works with QSV (VAAPI not always required)
- Check driver version: `dpkg -l intel-media-va-driver`
- Ensure Ubuntu 24.10+ for latest Intel Arc support

#### **"QSV encoding parameters unsupported"**
- Try different codecs: H.264, H.265, AV1
- Check GPU capabilities with specific encoder tests
- Some older Intel GPUs have limited codec support

## Performance Benefits

### **With Intel GPU Acceleration:**
- **Intel Arc GPUs**: Up to 10x faster encoding (especially AV1)
- **Intel UHD Graphics**: Up to 5x faster than software  
- **Reduced CPU usage**: GPU handles video processing
- **Better quality/bitrate**: Hardware encoders often more efficient

### **GPU Performance Hierarchy:**
```
🏆 Arc B580 → Best (AV1 + H.264/H.265, ~10x faster)
🥈 Arc A750 → Excellent (H.264/H.265, ~8x faster)  
🥉 UHD 770 → Good (H.264/H.265, ~5x faster)
📺 UHD 630 → Basic (H.264 only, ~3x faster)
```

## GPU Detection Logic

The detection script:
1. **Scans** all `/dev/dri/renderD*` devices
2. **Identifies** Intel GPUs via PCI vendor ID `0x8086`
3. **Prioritizes** by GPU series (Arc B > Arc A > UHD Graphics)
4. **Tests** hardware acceleration functionality  
5. **Configures** optimal QSV settings
6. **Falls back** to software if no Intel GPU found

## Development

### **Adding New Intel GPU Support**
1. Update `scripts/detect-intel-gpu.sh` with new PCI IDs
2. Add GPU name mapping in `get_gpu_name()` function
3. Set appropriate priority in `get_gpu_priority()` function
4. Test with `./build-intel-gpu.sh`

### **Modifying GPU Priority**
Edit the priority values in `detect-intel-gpu.sh`:
- Arc B-series: 100 (highest - AV1 support)
- Arc A-series: 90 (high - good performance)
- Xe Graphics: 70 (medium-high)  
- UHD Graphics: 50 (medium)
- Other Intel: 30 (low)

The system automatically selects the highest priority GPU available.

---

**Note:** This setup is specifically designed for Intel GPUs with QSV support. For NVIDIA or AMD GPU acceleration, separate container configurations would be required.
