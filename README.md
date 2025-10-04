# Namer

Renames adult video files so that the plex/jellyfin plugins and stash script will match without user input. Runs server or command mode.

## Package Management

This project uses [pnpm](https://pnpm.io/) exclusively as its package manager. Do not use npm or yarn.

### Setup

1. Install Node.js v22 or later
2. Enable corepack: `corepack enable`
3. Prepare pnpm: `corepack prepare pnpm@10 --activate`
4. Install dependencies: `pnpm install`
5. Build the project: `pnpm run build`

### Why pnpm?

- Faster installation times
- More efficient disk space usage
- Better dependency management
- Workspace support
- Consistent dependency resolution

### Enforcement

The project includes several mechanisms to enforce pnpm usage:

- Pre-commit hooks that prevent npm artifacts
- CI checks that validate pnpm usage
- Scripts that enforce pnpm for dependency management

If you encounter any issues with package management, run `./scripts/enforce-pnpm.sh` to check your setup.

