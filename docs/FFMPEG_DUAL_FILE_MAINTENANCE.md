# FFmpeg Dual File Maintenance Guide

⚠️  **CRITICAL MAINTENANCE INFORMATION** ⚠️

## Overview

Namer uses a **dual-file architecture** for FFmpeg functionality to support both development and production environments with different hardware acceleration capabilities.

## File Architecture

| File | Purpose | Environment | Usage |
|------|---------|-------------|--------|
| `namer/ffmpeg.py` | Base/Development | Local development, testing | Standard FFmpeg operations |
| `namer/ffmpeg_enhanced.py` | Production/Container | Docker containers | Intel GPU hardware acceleration (QSV) |

## Container Build Process

During Docker container builds (`Dockerfile` line 88):

```dockerfile
COPY namer/ffmpeg_enhanced.py /work/namer/ffmpeg.py
```

**Result:** `ffmpeg_enhanced.py` **REPLACES** `ffmpeg.py` in the container!

## 🔧 Maintenance Requirements

### When Making Changes to FFmpeg Functionality:

1. **✅ ALWAYS update BOTH files**
   - Apply identical changes to `ffmpeg.py` AND `ffmpeg_enhanced.py`
   - Both files must remain functionally equivalent

2. **✅ Test both environments**
   - Test locally with `ffmpeg.py` 
   - Test container builds with `ffmpeg_enhanced.py`

3. **✅ Verify hardware acceleration still works**
   - QSV (Intel Quick Sync Video) functionality
   - VAAPI fallback chains
   - Software fallback paths

### Critical Areas Requiring Dual Maintenance:

- **Hardware acceleration logic** in `extract_screenshot()` method
- **QSV decoder selection and mapping**  
- **Error handling and fallback chains**
- **Filter parameter formatting** (especially scale_qsv parameters)
- **Output format specifications** (image2, update flags, etc.)

## 🚨 Consequences of Not Maintaining Both Files:

- **❌ Changes lost during container builds**
- **❌ Development vs production behavior inconsistencies**  
- **❌ Hardware acceleration failures in containers**
- **❌ Broken Intel Arc GPU support**
- **❌ Silent regressions in production**

## 📋 Verification Checklist

Before committing changes:

- [ ] Changes applied to both `ffmpeg.py` AND `ffmpeg_enhanced.py`
- [ ] Both files compile and import successfully
- [ ] Local development works (using `ffmpeg.py`)
- [ ] Container build completes successfully  
- [ ] Hardware acceleration tests pass in containers
- [ ] No regressions in software fallback modes

## 🔍 Finding Synchronized Code Sections

Look for these warning comments in the code:

```python
# ⚠️  CRITICAL: This fix must be mirrored in ffmpeg_enhanced.py!
# ⚠️  Mirror in ffmpeg.py!
```

These mark areas where dual-file maintenance is especially critical.

## Why This Architecture Exists

- **Separation of concerns**: Base functionality vs hardware-optimized functionality
- **Backwards compatibility**: Maintains standard FFmpeg behavior for development
- **Container optimization**: Provides Intel GPU acceleration only where supported
- **Flexibility**: Allows different feature sets for different deployment scenarios

## Future Considerations

Consider consolidating to a single file with runtime feature detection if:
- Maintenance overhead becomes too high
- Hardware detection becomes more standardized
- Development/production parity becomes more important than optimization

---

**Remember: Consistency between both files is critical for reliable video processing!**