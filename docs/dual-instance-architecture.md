# Dual Namer Instance Architecture for unRAID

## The Problem with Single Instance

- unRAID's `/mnt/user` appears unified but spans multiple filesystems
- Docker doesn't understand unRAID's filesystem boundaries
- Cross-filesystem operations are unpredictable and slow
- Complex logic needed to handle different storage locations

## 🎯 **Two-Instance Solution**

### **Instance 1: Cache Namer (New Files)**

```yaml
# namer-cache service
services:
  namer-cache:
    image: ghcr.io/nehpz/namer:latest
    container_name: namer-cache
    volumes:
      # All operations stay on cache filesystem
      - /mnt/cache/downloads:/media/watch
      - /mnt/cache/namer-work:/media/work
      - /mnt/cache/namer-failed:/media/failed
      - /mnt/cache/media-organized:/media/dest
      - /mnt/user/appdata/namer-cache/config:/config
    environment:
      - NAMER_CONFIG=/config/cache.cfg
    labels:
      - "net.unraid.docker.icon=https://github.com/nehpz/namer/raw/main/logo/cache-icon.png"
```

### **Instance 2: Array Namer (Backlog)**

```yaml
# namer-backlog service
services:
  namer-backlog:
    image: ghcr.io/nehpz/namer:latest
    container_name: namer-backlog
    volumes:
      # All operations stay on array filesystem
      - /mnt/user/media/backlog:/media/watch
      - /mnt/user/media/namer-work:/media/work
      - /mnt/user/media/namer-failed:/media/failed
      - /mnt/user/media/organized:/media/dest
      - /mnt/user/appdata/namer-backlog/config:/config
    environment:
      - NAMER_CONFIG=/config/backlog.cfg
    labels:
      - "net.unraid.docker.icon=https://github.com/nehpz/namer/raw/main/logo/backlog-icon.png"
```

## 🔄 **Complete Workflow**

### **New Files (Cache Instance)**

```text
Download Client → /mnt/cache/downloads
                ↓
Cache Namer → /mnt/cache/media-organized
                ↓ (mover nightly)
Final Location → /mnt/user/media/organized
```

- **Speed**: ⚡⚡⚡ NVMe performance
- **Operations**: 100% atomic (same ZFS filesystem)
- **Reliability**: ZFS mirror protection

### **Backlog Files (Array Instance)**

```text
Existing Files → /mnt/user/media/backlog
                ↓
Array Namer → /mnt/user/media/organized (in-place or move)
```

- **Speed**: ⚡ Array speed (fine for backlog)
- **Operations**: Native array operations
- **Capacity**: Unlimited (entire array)

### **Mover Integration**

```bash
# Mover handles:
/mnt/cache/media-organized → /mnt/user/media/organized
/mnt/cache/downloads → /mnt/user/downloads (if needed)
```

## ⚙️ **Configuration Differences**

### **Cache Instance Config** (`cache.cfg`)

```ini
[namer]
# Optimized for speed on cache
watch_dir = /media/watch
work_dir = /media/work
failed_dir = /media/failed
dest_dir = /media/dest
inplace = false
preserve_duplicates = false

[Phash]
# Enable phash for better matching
phash = true
search_phash = true

[watchdog]
# Responsive processing
queue_limit = 10
extra_sleep_time = 5
```

### **Backlog Instance Config** (`backlog.cfg`)

```ini
[namer]
# Optimized for large array processing
watch_dir = /media/watch
work_dir = /media/work
failed_dir = /media/failed
dest_dir = /media/dest
inplace = true  # Often better for array processing
preserve_duplicates = true

[Phash]
# May skip phash for speed on spinning disks
phash = false
search_phash = false

[watchdog]
# Less aggressive for background processing
queue_limit = 5
extra_sleep_time = 30
```

## 🎛️ **Management in Dockge**

### **Separate Stacks**

- **`namer-cache`** stack - High priority, always running
- **`namer-backlog`** stack - Background processing, can pause/resume

### **Resource Allocation**

```yaml
# Cache instance - high performance
namer-cache:
  deploy:
    resources:
      limits:
        cpus: "4.0"
        memory: 2G

# Backlog instance - background processing
namer-backlog:
  deploy:
    resources:
      limits:
        cpus: "2.0"
        memory: 1G
```

## 🔍 **Web UI Access**

### **Different Ports**

- **Cache Namer**: `http://unraid:6980` (primary UI)
- **Backlog Namer**: `http://unraid:6981` (backlog management)

### **Separate Failed Queues**

- New files that fail → Cache failed queue (fast retry)
- Backlog files that fail → Array failed queue (manual review)

## 🚀 **Benefits of This Architecture**

### **Performance**

- **Cache operations**: Lightning fast NVMe performance
- **Array operations**: Optimized for array characteristics
- **No cross-filesystem complexity**: Each instance optimized for its storage

### **Reliability**

- **Filesystem isolation**: No cross-filesystem atomic operation issues
- **Independent failure**: Cache issues don't affect backlog processing
- **Clear boundaries**: Each instance has clear responsibilities

### **Scalability**

- **Cache processing**: Limited by cache size, optimized for speed
- **Backlog processing**: Unlimited size, optimized for thoroughput
- **Resource control**: Can pause/prioritize each instance independently

### **Operational**

- **Simple configuration**: Each instance has single-purpose config
- **Easy troubleshooting**: Issues are isolated to specific instance
- **Flexible scheduling**: Can run backlog processing during off-hours

## 📋 **Implementation Steps**

1. **Create separate appdata directories**

   ```bash
   mkdir -p /mnt/user/appdata/namer-cache/config
   mkdir -p /mnt/user/appdata/namer-backlog/config
   ```

2. **Set up cache directories**

   ```bash
   mkdir -p /mnt/cache/namer-work
   mkdir -p /mnt/cache/namer-failed
   mkdir -p /mnt/cache/media-organized
   ```

3. **Set up array directories**

   ```bash
   mkdir -p /mnt/user/media/backlog
   mkdir -p /mnt/user/media/namer-work
   mkdir -p /mnt/user/media/namer-failed
   ```

4. **Deploy both stacks in Dockge**
5. **Configure mover to handle organized media**
6. **Start with cache instance, add backlog instance later**

This architecture is **much cleaner** and leverages unRAID's design instead of fighting it! 🎉
