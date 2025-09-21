#!/bin/bash
#
# Clean up build artifacts, containers, and VMs
# Usage: ./scripts/cleanup.sh [LEVEL]
#
# LEVEL: "light", "medium", "deep"
#

set -euo pipefail

LEVEL="${1:-medium}"
ORBSTACK_VM="namer-build-env"

echo "🧹 Cleaning up build artifacts and containers..."

case "$LEVEL" in
    "light")
        echo "   Light cleanup - removing temporary build files..."
        rm -f *.tar .DS_Store Makefile.old 2>/dev/null || true
        echo "✅ Light cleanup complete"
        ;;
    
    "medium")
        echo "   Medium cleanup - Docker containers and images..."
        # Clean up any test containers
        docker ps -a --filter "name=namer-test" --format "{{.Names}}" | xargs -r docker rm -f 2>/dev/null || true
        
        # Remove temporary files (but preserve test infrastructure)
        rm -f *.tar .DS_Store Makefile.old dist/*.tar 2>/dev/null || true
        
        # Docker cleanup
        docker image prune -f
        docker system prune -f
        
        echo "✅ Medium cleanup complete"
        ;;
    
    "deep")
        echo "   Deep cleanup - everything including OrbStack VM..."
        # Stop and remove any test containers
        docker ps -a --filter "name=namer-test" --format "{{.Names}}" | xargs -r docker rm -f 2>/dev/null || true
        
        # Remove temporary files (but preserve test infrastructure)
        rm -f *.tar .DS_Store Makefile.old dist/*.tar 2>/dev/null || true
        
        # Aggressive Docker cleanup
        docker system prune -af
        docker volume prune -f
        
        # Stop and remove OrbStack VM
        if command -v orbctl >/dev/null 2>&1; then
            orbctl stop "$ORBSTACK_VM" 2>/dev/null || true
            orbctl delete -f "$ORBSTACK_VM" 2>/dev/null || true
            echo "✅ OrbStack VM removed: $ORBSTACK_VM"
        fi
        
        echo "✅ Deep cleanup complete"
        ;;
    
    *)
        echo "❌ Unknown cleanup level: $LEVEL. Use 'light', 'medium', or 'deep'" >&2
        exit 1
        ;;
esac