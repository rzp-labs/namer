#!/bin/bash

set -eo pipefail

version_bump=$1

GHCR_OWNER=${GHCR_OWNER:-nehpz}
repo="${GHCR_OWNER}"

found=false
for bump in 'minor' 'major' 'patch'; do 
  if [[ "$version_bump" == "$bump" ]]; then
    found=true
  fi  
done

if [[ "$found" == false ]]; then
  echo "invalid argument; please use one of 'minor' 'major' 'patch'"
  exit 1
fi

CLEAN=$(git diff-index --quiet HEAD; echo $?)
if [[ "${CLEAN}" != "0" ]]; then
  echo "Your git repo is not clean, can't release."
  exit 1
fi

branch=$(git rev-parse --abbrev-ref HEAD)

if [[ "$branch" != "main" ]]; then
  echo "May only release off of the main branch, not other branches."
  exit 1
fi

poetry version "$version_bump"
new_version=$(poetry version -s)
git add pyproject.toml

poetry run pytest
poetry run ruff check .

command -v pnpm >/dev/null || { echo "pnpm not found; install or enable corepack"; exit 1; }
pnpm install
pnpm run build

poetry build

echo pushing new git tag v"${new_version}"
git commit -m "prepare release v${new_version}"
git push
git tag v"${new_version}" main
git push origin v"${new_version}"

echo building docker image
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
GIT_HASH=$(git rev-parse --verify HEAD)
docker build . --build-arg "BUILD_DATE=${BUILD_DATE}" --build-arg "GITHASH=${GIT_HASH}" -t "${repo}"/namer:"${new_version}"

echo logging into ghcr.io
gh auth token | docker login ghcr.io -u nehpz --password-stdin
docker tag "${repo}"/namer:"${new_version}" ghcr.io/"${repo}"/namer:"${new_version}"
docker tag "${repo}"/namer:"${new_version}" ghcr.io/"${repo}"/namer:latest
docker push ghcr.io/"${repo}"/namer:"${new_version}"
docker push ghcr.io/"${repo}"/namer:latest
