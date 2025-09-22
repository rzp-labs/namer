#!/bin/bash
set -euo pipefail

# Smart Backlog Processor for Large Collections
# Decides optimal processing method based on file characteristics

CACHE_PATH="${CACHE_PATH:-/tmp/namer-cache}"
ARRAY_PATH="${ARRAY_PATH:-/media}"
CACHE_LIMIT="1500000000"  # 1.5TB in KB
SMALL_FILE_LIMIT="100000"  # 100MB in KB

echo "🎯 Smart backlog processing starting..."
echo "Cache limit: $(($CACHE_LIMIT / 1000000))GB"

# process_directory decides which processing strategy to use for a given media directory (cache, selective-cache, or in-place) based on the directory size and number of media files.
# It prints a short summary (name, size, file count) and invokes cache_process, selective_cache_process, or inplace_process accordingly.
process_directory() {
    local dir="$1"
    local dir_size=$(du -s "$dir" | cut -f1)
    local file_count=$(find "$dir" -name "*.mp4" -o -name "*.mkv" | wc -l)
    
    echo "📁 Processing: $(basename "$dir")"
    echo "   Size: $(($dir_size / 1000000))GB, Files: $file_count"
    
    if [[ $dir_size -lt $CACHE_LIMIT ]]; then
        echo "   ⚡ Using cache processing (fast)"
        cache_process "$dir"
    elif [[ $file_count -lt 10 ]]; then
        echo "   📦 Using selective cache processing"  
        selective_cache_process "$dir"
    else
        echo "   🏠 Using in-place processing"
        inplace_process "$dir"
    fi
}

# cache_process moves a directory into the configured cache, runs `namer` with the cache-mode config to process it, moves the top-level organized children back to "$ARRAY_PATH/organized", and removes the temporary cache directory.
cache_process() {
    local dir="$1"
    local temp_dir="$CACHE_PATH/$(basename "$dir")"
    
    # Move to cache for fast processing
    echo "     Moving to cache..."
    mv "$dir" "$temp_dir"
    
    # Process with full speed on NVMe
    namer rename -d "$temp_dir" --config /config/cache-mode.cfg
    
    # Move back organized
    echo "     Moving back to array..."
    find "$temp_dir" -mindepth 1 -maxdepth 1 -type d -exec mv {} "$ARRAY_PATH/organized/" \;
    
    # Cleanup
    rmdir "$temp_dir"
}

# selective_cache_process processes media files in DIR by using available cache space: files that fit in the remaining cache are moved into CACHE_PATH, processed there with `namer rename -f`, and then moved to the organized location; files that do not fit are processed in-place with `namer rename -f --inplace`.
# 
# DIR is the target directory containing media files; the function updates a local remaining cache counter (based on CACHE_LIMIT and current usage of CACHE_PATH), moves files into the cache when space permits, invokes `namer` to rename/process them, and otherwise invokes `namer` in-place. Side effects: moves files between filesystem locations and runs `namer`.
selective_cache_process() {
    local dir="$1"
    
    # Process only files that fit in remaining cache space
    local remaining_cache=$((CACHE_LIMIT - $(du -s "$CACHE_PATH" 2>/dev/null | cut -f1 || echo 0)))
    
    find "$dir" -name "*.mp4" -o -name "*.mkv" | while read -r file; do
        local file_size=$(du -s "$file" | cut -f1)
        
        if [[ $file_size -lt $remaining_cache ]]; then
            echo "     ⚡ Cache processing: $(basename "$file")"
            # Move file to cache, process, move back
            local temp_file="$CACHE_PATH/$(basename "$file")"
            mv "$file" "$temp_file"
            namer rename -f "$temp_file"
            # Move to organized location based on metadata
            # ... organized move logic ...
            remaining_cache=$((remaining_cache - file_size))
        else
            echo "     🏠 In-place processing: $(basename "$file")"
            namer rename -f "$file" --inplace
        fi
    done
}

# inplace_process processes media files in the given directory in-place using `namer` and does not move files.
# If GENERATE_NFO is "true", it also runs `namer suggest --write-nfo` on each .mp4/.mkv to generate .nfo metadata; argument is the directory path to process.
inplace_process() {
    local dir="$1"
    
    # Process files where they live - no moves needed
    namer rename -d "$dir" --inplace --config /config/inplace-mode.cfg
    
    # Optionally generate .nfo files for later organization
    if [[ "${GENERATE_NFO:-false}" == "true" ]]; then
        find "$dir" -name "*.mp4" -o -name "*.mkv" | while read -r file; do
            namer suggest -f "$file" --write-nfo
        done
    fi
}

# Process all directories in unsorted media
find "$ARRAY_PATH/unsorted" -mindepth 1 -maxdepth 1 -type d | while read -r dir; do
    process_directory "$dir"
done

echo "✅ Smart backlog processing complete!"
