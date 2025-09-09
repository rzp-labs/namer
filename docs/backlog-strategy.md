# Backlog Processing Strategy for Large Collections

## The Challenge
- **45TB+ of existing files** on array
- **2TB cache limit** - can't move everything to cache
- **Need efficient processing** without endless shuttling

## 🎯 **Multi-Mode Processing Strategy**

### **Mode 1: Cache Processing (< 1.5TB collections)**
```
Array → Cache → Process → Organize → Array
```
- **Best for**: Small collections, recent downloads
- **Speed**: Maximum (NVMe performance)
- **File safety**: Atomic moves on ZFS

### **Mode 2: Selective Cache Processing (Mixed sizes)**
```
Large files: Process in-place on array
Small files: Cache → Process → Array
```
- **Best for**: Mixed collections with some large files
- **Strategy**: Cherry-pick files that fit in available cache space

### **Mode 3: In-Place Processing (Large collections)**
```
Process directly on array (no moves)
```
- **Best for**: Large collections > 2TB
- **Trade-off**: Slower but handles unlimited size

### **Mode 4: Metadata-Only Processing**
```
Generate .nfo files only → Organize later with mover
```
- **Best for**: Initial scanning of huge collections
- **Benefit**: Fast identification, deferred organization

## 📊 **Decision Matrix**

| Collection Size | File Count | Recommended Mode | Speed | Safety |
|----------------|------------|------------------|-------|---------|
| < 500GB | Any | Cache Processing | ⚡⚡⚡ | 🛡️🛡️🛡️ |
| 500GB - 1.5TB | < 100 files | Cache Processing | ⚡⚡⚡ | 🛡️🛡️🛡️ |
| 1.5TB - 5TB | < 50 files | Selective Cache | ⚡⚡ | 🛡️🛡️ |
| > 5TB | Any | In-Place Processing | ⚡ | 🛡️ |
| Any | > 1000 files | Metadata-Only First | ⚡⚡ | 🛡️ |

## 🚀 **Implementation Strategy**

### **Phase 1: Smart Assessment**
```bash
# Analyze your collection first
find /mnt/user/media -name "*.mp4" -o -name "*.mkv" | \
while read file; do
    size=$(stat -c%s "$file")
    echo "$size $(dirname "$file")"
done | awk '{
    dirs[$2] += $1
    counts[$2]++
} END {
    for (dir in dirs) {
        printf "%s: %.1fGB (%d files)\n", dir, dirs[dir]/1024/1024/1024, counts[dir]
    }
}' | sort -k2 -n
```

### **Phase 2: Batch Processing**
```bash
# Process in optimal order (smallest first)
process_smart_batch() {
    # 1. Process all small collections via cache
    find_collections_under_size "1500GB" | process_via_cache
    
    # 2. Process medium collections selectively  
    find_collections_between_size "1500GB" "5TB" | process_selectively
    
    # 3. Process large collections in-place
    find_collections_over_size "5TB" | process_inplace
}
```

### **Phase 3: Continuous Processing**
```bash
# Set up different namer instances for different modes
docker compose up namer-cache     # Handles new downloads
docker compose up namer-backlog   # Processes existing files
```

## ⚙️ **Configuration Examples**

### **Cache Mode Config** (`cache-mode.cfg`)
```ini
[namer]
# Optimized for cache processing
dest_dir = /media/dest
work_dir = /media/work
inplace = false
preserve_duplicates = false

[Phash]
# Enable for better matching
phash = true
```

### **In-Place Mode Config** (`inplace-mode.cfg`)
```ini
[namer]
# Process where files live
inplace = true
preserve_duplicates = true  # Don't delete on array

[Phash]
# May be slower on spinning disks
phash = false
```

### **Metadata-Only Config** (`metadata-mode.cfg`)
```ini
[namer]
# Generate .nfo files only
write_nfo = true
inplace = true
write_tags = false  # Skip MP4 tagging for speed
```

## 📋 **Execution Plan for 45TB**

### **Week 1: Assessment & Quick Wins**
1. **Analyze collection** structure and sizes
2. **Process small collections** (< 500GB) via cache
3. **Generate statistics** on what's left

### **Week 2-4: Batch Processing**
1. **Process medium collections** selectively
2. **Start in-place processing** for large collections
3. **Monitor cache usage** and performance

### **Ongoing: Hybrid Mode**
1. **New files** → Cache processing (fast)
2. **Backlog** → In-place processing (background)
3. **Failed matches** → Manual review via web UI

## 🎯 **Expected Results**

- **Small collections (< 500GB)**: ~100x faster processing
- **Medium collections**: ~10x faster for small files
- **Large collections**: Same speed, but organized processing
- **Overall**: 45TB processed efficiently without constant shuttling

This strategy maximizes your ZFS cache benefits while handling the reality of large existing collections! 🚀
