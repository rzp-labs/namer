#!/bin/bash

# Script to enforce pnpm usage and prevent npm usage
#
# To bypass this check in CI environments, set SKIP_PNPM_CHECK=1 before running:
# SKIP_PNPM_CHECK=1 ./scripts/enforce-pnpm.sh

set -e

# Skip check if SKIP_PNPM_CHECK is set to 1
if [ "${SKIP_PNPM_CHECK:-0}" = "1" ]; then
  echo "⚠️ Skipping pnpm check as SKIP_PNPM_CHECK=1"
  exit 0
fi

# Check if package-lock.json exists
if [ -f "package-lock.json" ]; then
  echo "❌ Error: package-lock.json detected. This project uses pnpm exclusively."
  echo "Please remove package-lock.json and use pnpm instead:"
  echo "  rm package-lock.json"
  echo "  pnpm install"
  exit 1
fi

# Check if yarn.lock exists
if [ -f "yarn.lock" ]; then
  echo "❌ Error: yarn.lock detected. This project uses pnpm exclusively."
  echo "Please remove yarn.lock and use pnpm instead:"
  echo "  rm yarn.lock"
  echo "  pnpm install"
  exit 1
fi

# Check if npm-shrinkwrap.json exists
if [ -f "npm-shrinkwrap.json" ]; then
  echo "❌ Error: npm-shrinkwrap.json detected. This project uses pnpm exclusively."
  echo "Please remove npm-shrinkwrap.json and use pnpm instead:"
  echo "  rm npm-shrinkwrap.json"
  echo "  pnpm install"
  exit 1
fi

# Ensure pnpm is installed
if ! command -v pnpm &> /dev/null; then
  echo "❌ Error: pnpm is not installed."
  echo "Please install pnpm using corepack:"
  echo "  corepack enable"
  echo "  corepack prepare pnpm@10 --activate"
  exit 1
fi

# Check Node.js version compatibility
if command -v node &> /dev/null; then
  NODE_VERSION=$(node -v | cut -d 'v' -f 2)
  MAJOR_VERSION=$(echo $NODE_VERSION | cut -d '.' -f 1)
  
  if [ "$MAJOR_VERSION" -lt 22 ]; then
    echo "❌ Error: Node.js version $NODE_VERSION is not compatible."
    echo "This project requires Node.js v22 or later."
    echo "Please upgrade your Node.js version."
    exit 1
  fi
fi

echo "✅ pnpm check passed."
exit 0
