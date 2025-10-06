#!/bin/bash
# Lightweight build wrapper used by Makefile targets
# Usage: build-orbstack.sh <fast|full|dev> <image_name> <version>
set -Eeuo pipefail

MODE="${1:-fast}"
IMAGE_NAME="${2:-nehpz/namer}"
VERSION="${3:-latest}"

BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
PROJECT_VERSION=$(grep -E 'version\s*=\s*"' pyproject.toml 2>/dev/null | head -1 | cut -d'"' -f2 || echo "dev")

COMMON_ARGS=(
	-f Dockerfile
	--build-arg BUILD_DATE="$BUILD_DATE"
	--build-arg GIT_HASH="$GIT_HASH"
	--build-arg PROJECT_VERSION="$PROJECT_VERSION"
	-t "$IMAGE_NAME:$VERSION"
	-t "$IMAGE_NAME:latest"
	.
)

echo "[build-orbstack] Mode: $MODE"
echo "[build-orbstack] Image: $IMAGE_NAME:$VERSION"
echo "[build-orbstack] Build date: $BUILD_DATE"
echo "[build-orbstack] Git hash: $GIT_HASH"
echo "[build-orbstack] Project version: $PROJECT_VERSION"

run_build() {
	local -a docker_cmd=(docker build)
	if [[ $# -gt 0 ]]; then
		docker_cmd+=("$@")
	fi
	if [[ -n "${BUILD_ARGS:-}" ]]; then
		echo "[build-orbstack] Extra build args: ${BUILD_ARGS}"
		# shellcheck disable=SC2206 # intentional word splitting for docker CLI flags
		docker_cmd+=(${BUILD_ARGS})
	fi
	docker_cmd+=("${COMMON_ARGS[@]}")
	"${docker_cmd[@]}"
}

case "$MODE" in
fast)
	run_build
	;;
full)
	if [[ -x ./validate.sh ]]; then
		echo "[build-orbstack] Running validation before full build..."
		./validate.sh
	fi
	run_build --no-cache
	;;
dev)
	# If your Dockerfile has a dedicated builder stage, feel free to add --target here.
	run_build --progress=plain
	;;
*)
	echo "Usage: $0 <fast|full|dev> <image_name> <version>" >&2
	exit 2
	;;
esac
