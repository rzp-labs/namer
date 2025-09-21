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
