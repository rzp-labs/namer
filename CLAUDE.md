# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Namer is a Python-based video file renaming and tagging tool that integrates with ThePornDB and StashDB APIs. It provides:
- Command-line tool for renaming video files based on metadata
- Watchdog service for automated file processing
- Web UI for manual file matching and management
- Perceptual hash-based video identification

## Key Development Commands

### Environment Setup
```bash
# Install dependencies (requires Poetry, pnpm, Go)
poetry install
poetry run poe install_npm
poetry run poe build_videohashes

# Activate virtual environment
poetry shell
```

### Build Commands
```bash
# Full build with all tests (~20 minutes)
poetry run poe build_all

# Fast build for development
poetry run poe build_fast

# Development build (fastest)
poetry run poe dev_build

# Build specific components
poetry run poe build_node      # Build frontend
poetry run poe build_videohashes # Build Go videohash tool
poetry run poe build_namer      # Build Python package
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest test/namer_test.py

# Run with verbose output and stop on first failure
poetry run pytest -x -v --log-cli-level=info --capture=no

# Format checking
poetry run ruff check .

# Quick test (format only)
poetry run poe test_quick

# Pre-commit checks
poetry run poe precommit
```

### Running the Application
```bash
# Run as Python module
python -m namer [command]

# Available commands:
python -m namer watchdog              # Start watchdog service
python -m namer rename -f <file>      # Rename single file
python -m namer rename -d <dir>       # Rename files in directory
python -m namer rename -m -d <dir>    # Rename many files recursively
python -m namer suggest -f <filename> # Suggest name without renaming
python -m namer hash <file>           # Calculate perceptual hash
python -m namer url                   # Print web UI URL
python -m namer clear-cache <pattern> # Clear cached hashes
```

### Docker Operations
```bash
# Build Docker image (auto-detects platform)
make build

# Fast Docker build (~5 minutes)
make build-fast

# Full Docker build with tests (~20 minutes)
make build-full

# Development build (build stage only)
make build-dev

# Run validation before build
make build-validated

# Test the built image
make test
```

## Architecture Overview

### Core Components

**namer/namer.py**: Main renaming logic and file processing engine. Handles name parsing, metadata matching, and file operations.

**namer/metadataapi.py**: API client for ThePornDB/StashDB integration. Manages authentication, search queries, and result processing.

**namer/metadata_providers/**: Provider pattern implementation for different metadata sources (ThePornDB, StashDB). Each provider implements scene search, hash lookup, and metadata retrieval.

**namer/videophash/**: Perceptual hash calculation for video identification. Uses FFmpeg to extract frames and generates hashes for content-based matching.

**namer/watchdog.py**: File system monitoring service that watches directories for new files and processes them automatically using configured rules.

**namer/web/**: Flask-based web interface for manual file matching. Provides API endpoints and UI for reviewing failed matches and manually selecting metadata.

**namer/fileinfo.py**: File name parsing and metadata extraction. Uses regex patterns to extract site, date, and performer information from filenames.

**namer/name_formatter.py**: Configurable output name formatting based on metadata fields.

### Data Flow

1. **File Discovery**: Watchdog monitors `watch_dir` or CLI processes specified files
2. **Name Parsing**: Extract site, date, and scene/performer info using configurable regex
3. **Metadata Search**: Query providers using parsed data and/or perceptual hash
4. **Match Scoring**: Evaluate results using fuzzy string matching (95% threshold)
5. **File Operations**: Rename, tag (if MP4), move to destination, write NFO files
6. **Failure Handling**: Move unmatched files to `fail_dir` for daily retry

### Key Configuration

Configuration is managed through `namer.cfg` (copy from `namer.cfg.default`):
- API tokens for metadata providers
- Directory paths (watch, work, fail, dest)
- File naming patterns and formats
- Tagging and poster embedding settings
- Web UI configuration

### Database

Uses Pony ORM with SQLite for:
- File processing history and status
- Perceptual hash caching
- Failed match tracking for retry logic

## Development Notes

- The project uses Poetry for Python dependency management and poe for task automation
- Perceptual hashes are built using a Go submodule in `videohashes/`
- Frontend is built with pnpm and webpack
- Docker builds use OrbStack optimization on macOS ARM64
- Tests use pytest with assertpy for assertions
- Code formatting: 320 char line length, single quotes, 4-space indent (configured in pyproject.toml)
- The Makefile contains merge conflicts that need resolution before use