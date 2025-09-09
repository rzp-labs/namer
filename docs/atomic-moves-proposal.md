# Atomic Move Implementation for Namer

## Current Issues
The existing `shutil.move()` calls are not atomic and can fail across filesystems.

## Proposed Solution

### Enhanced Move Function
```python
import os
from pathlib import Path

def atomic_move(src: Path, dst: Path) -> bool:
    """
    Atomic file move with fallback strategies.
    Optimized for same-filesystem operations (ZFS cache).
    """
    # Ensure destination directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Strategy 1: Atomic rename (same filesystem)
        src.rename(dst)
        logger.debug(f"Atomic rename: {src} → {dst}")
        return True
    except OSError as e:
        if e.errno == 18:  # Cross-device link (different filesystems)
            return atomic_move_cross_fs(src, dst)
        else:
            logger.error(f"Move failed: {src} → {dst}: {e}")
            return False

def atomic_move_cross_fs(src: Path, dst: Path) -> bool:
    """
    Cross-filesystem move with verification.
    Used when cache → array moves are needed.
    """
    temp_dst = dst.with_suffix(dst.suffix + '.tmp')
    
    try:
        # Copy with metadata preservation
        shutil.copy2(src, temp_dst)
        
        # Verify copy integrity
        if src.stat().st_size != temp_dst.stat().st_size:
            logger.error(f"Size mismatch during copy: {src} → {temp_dst}")
            return False
            
        # Atomic rename to final location
        temp_dst.rename(dst)
        
        # Remove original only after successful atomic rename
        src.unlink()
        
        logger.info(f"Cross-filesystem move: {src} → {dst}")
        return True
        
    except Exception as e:
        logger.error(f"Cross-filesystem move failed: {src} → {dst}: {e}")
        # Cleanup temp file if it exists
        temp_dst.unlink(missing_ok=True)
        return False

def hard_link_move(src: Path, dst: Path) -> bool:
    """
    Zero-copy move using hard links (same filesystem only).
    Perfect for ZFS cache operations.
    """
    try:
        os.link(src, dst)
        src.unlink()
        logger.debug(f"Hard link move: {src} → {dst}")
        return True
    except OSError:
        # Fallback to regular atomic move
        return atomic_move(src, dst)
```

### Integration Points

Replace these existing calls:

1. **namer/command.py:241**
```python
# Before:
shutil.move(command.target_movie_file, movie_name)

# After:
if not atomic_move(command.target_movie_file, movie_name):
    raise RuntimeError(f"Failed to move {command.target_movie_file} to {movie_name}")
```

2. **namer/command.py:78-89** (move_command_files)
```python
# Use hard_link_move for cache operations
if not hard_link_move(target.target_directory, working_dir):
    raise RuntimeError(f"Failed to move to work directory")
```

### Configuration Option
Add to namer.cfg:
```ini
[namer]
# Prefer hard links for same-filesystem moves (faster, atomic)
prefer_hardlinks = true
# Verify file integrity on cross-filesystem moves  
verify_moves = true
```

This approach gives you:
- ⚡ **Instant moves** on ZFS cache (hard links)
- 🛡️ **Atomic operations** (no partial states)
- 🔍 **Verification** for cross-filesystem moves
- 📊 **Fallback strategies** for reliability
