#!/bin/bash
#
# Check OrbStack availability and VM architecture
# Usage: ./scripts/check-orbstack.sh [VM_NAME]
#

set -euo pipefail

ORBSTACK_VM="${1:-namer-build-env}"

# Check if OrbStack CLI is available
if ! command -v orbctl >/dev/null 2>&1; then
    echo "❌ OrbStack CLI 'orbctl' not found. Install from https://orbstack.dev" >&2
    exit 1
fi

echo "✅ OrbStack CLI found"

# Check if VM exists and verify architecture
if orbctl list | grep -q "$ORBSTACK_VM"; then
    echo "🔍 Checking existing VM architecture..."
    VM_ARCH=$(orbctl run -m "$ORBSTACK_VM" uname -m 2>/dev/null || echo "unknown")
    
    if [ "$VM_ARCH" != "x86_64" ]; then
        echo "⚠️  Existing VM is $VM_ARCH, need AMD64 for Intel GPU packages. Recreating..." >&2
        orbctl delete -f "$ORBSTACK_VM" 2>/dev/null || true
        orbctl create --arch amd64 ubuntu "$ORBSTACK_VM"
        echo "✅ Created new AMD64 VM: $ORBSTACK_VM"
    else
        echo "✅ Existing VM is already AMD64"
    fi
else
    echo "📦 Creating new AMD64 VM: $ORBSTACK_VM..."
    orbctl create --arch amd64 ubuntu "$ORBSTACK_VM"
    echo "✅ Created AMD64 VM: $ORBSTACK_VM"
fi

# Ensure VM is running
orbctl start "$ORBSTACK_VM" || true
echo "✅ VM $ORBSTACK_VM is running"