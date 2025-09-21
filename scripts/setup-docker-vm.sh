#!/bin/bash
#
# Setup Docker in OrbStack VM
# Usage: ./scripts/setup-docker-vm.sh [VM_NAME]
#

set -euo pipefail

ORBSTACK_VM="${1:-namer-build-env}"

echo "🔧 Setting up Docker in VM: $ORBSTACK_VM..."

# Update package lists
orbctl run -m "$ORBSTACK_VM" sudo apt-get update

# Install Docker if not present
orbctl run -m "$ORBSTACK_VM" bash -c 'command -v docker >/dev/null || (curl -fsSL https://get.docker.com | sudo sh && sudo systemctl start docker)'

echo "✅ Docker setup complete in VM: $ORBSTACK_VM"