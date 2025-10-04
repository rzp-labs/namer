#!/bin/bash

# Script to enforce pnpm usage and prevent npm usage

set -e

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

# Ensure pnpm is installed
if ! command -v pnpm &> /dev/null; then
  echo "❌ Error: pnpm is not installed."
  echo "Please install pnpm using corepack:"
  echo "  corepack enable"
  echo "  corepack prepare pnpm@10 --activate"
  exit 1
fi

echo "✅ pnpm check passed."
exit 0

