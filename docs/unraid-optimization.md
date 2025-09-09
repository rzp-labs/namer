# unRAID File Movement Optimization

## Your Setup Analysis
- **Cache**: 2x 2TB NVMe (ZFS mirror) - Fast, reliable
- **Array**: XFS storage - Larger capacity, slower
- **Mover**: Nightly transfer cache → array

## Optimal Processing Strategy

### 🎯 **Best Approach: Process on Cache First**

```
Downloads → Cache/downloads → Cache/processing → Cache/completed → [mover] → Array/media
```

#### **Benefits:**
- ✅ **All moves are atomic** (same ZFS filesystem)  
- ✅ **Maximum speed** (NVMe performance)
- ✅ **Minimal cross-filesystem moves** (only final mover transfer)
- ✅ **Fault tolerant** (ZFS mirror protection during processing)

### 📁 **Recommended Directory Structure**

```
/mnt/cache/
├── downloads/           # Download client target
├── namer-watch/        # Namer watch directory  
├── namer-work/         # Namer processing
├── namer-failed/       # Failed processing
└── media-ready/        # Completed, ready for mover
```

### ⚙️ **Docker Compose Configuration**

```yaml
services:
  namer:
    image: ghcr.io/rzp-labs/namer:latest
    volumes:
      # All processing happens on cache
      - /mnt/cache/namer-watch:/media/watch
      - /mnt/cache/namer-work:/media/work  
      - /mnt/cache/namer-failed:/media/failed
      - /mnt/cache/media-ready:/media/dest    # Final cache location
      - /mnt/user/appdata/namer/config:/config
    environment:
      - NAMER_CONFIG=/config/namer.cfg
```

### 📝 **Namer Configuration**

```ini
[namer]
# All paths on cache for atomic moves
watch_dir = /media/watch
work_dir = /media/work  
failed_dir = /media/failed
dest_dir = /media/dest

# Enable in-place processing for speed
inplace = false  # Process to dest_dir for organization
```

### 🔄 **Complete Workflow**

1. **Download** → `/mnt/cache/downloads/`
2. **Auto-move** → `/mnt/cache/namer-watch/` (symlink or hardlink)
3. **Namer Processing** → `/mnt/cache/namer-work/` (atomic move)
4. **Success** → `/mnt/cache/media-ready/` (atomic move, organized)
5. **Mover (nightly)** → `/mnt/user/media/` (single cross-filesystem move)

### 🚀 **Advanced: Use Hard Links for Zero-Copy**

For even better performance, use hard links instead of moves:

```bash
# In download completion script
ln /mnt/cache/downloads/movie.mp4 /mnt/cache/namer-watch/movie.mp4
rm /mnt/cache/downloads/movie.mp4
```

This is **instant** and **atomic** on the same filesystem.

### ⚡ **Performance Benefits**

| Operation | Before | After |
|-----------|--------|-------|
| Download→Processing | Copy across filesystems | Atomic move/hardlink |
| Processing moves | Multiple cross-FS copies | All atomic on ZFS |
| Final organization | Cross-FS per file | Single mover batch |
| Total cross-FS operations | 3-4 per file | 1 per file |
| Processing time | ~Minutes per file | ~Seconds per file |

### 🛡️ **Reliability Benefits**

- **ZFS Protection**: All processing under ZFS mirror protection
- **Atomic Operations**: No partial files during processing  
- **Crash Safety**: Interrupted processing leaves clean state
- **Easy Recovery**: Failed files stay on fast cache for retry

### 📋 **Implementation Steps**

1. **Update Docker paths** to use cache locations
2. **Configure mover** to include `media-ready` → `media` 
3. **Set up download client** to use cache downloads
4. **Test with small files first**
5. **Monitor cache usage** vs processing speed

This approach minimizes cross-filesystem operations to just the final mover transfer, maximizing both speed and reliability! 🚀
