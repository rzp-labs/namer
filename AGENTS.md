# Namer

**Context for AI coding agents.** This file provides build, test, run, and architecture information for working with Namer. For user-facing documentation, see README.md.

## Build & Test

```bash
# Install all dependencies and build everything
poetry install
poetry run poe build_all

# Run tests with coverage
poetry run pytest --cov

# Run lint check
poetry run ruff check .

# Format code
poetry run ruff format .

# Quick pre-commit check
poetry run poe precommit
```

## Run Locally

```bash
# Watchdog mode (requires ~/.namer.cfg or .namer.cfg)
python -m namer watchdog

# Rename a single file
python -m namer rename -f /path/to/file.mp4

# Suggest name for a file (no actual rename)
python -m namer suggest -f filename.mp4

# Get web UI URL
python -m namer url

# Generate perceptual hash for a file
python -m namer hash -f /path/to/file.mp4

# Clear cached hashes for files matching pattern
python -m namer clear-cache <filename_pattern>

# Use custom config file
python -m namer --config /path/to/config.cfg watchdog
```

## Architecture Overview

**Modes**: CLI tool, Watchdog service, Web UI

**Processing Flow**:
1. File Input → Command object (`namer/command.py`)
2. Name Parsing → Extract site, date, scene (`namer/fileinfo.py`)
3. Hash Calculation → Perceptual hashes (`namer/videohashes.py`)
4. API Matching → Query metadata provider via GraphQL
5. Result Comparison → Rank matches (`namer/comparison_results.py`)
6. File Operations → Rename, tag, move files

**Entry Points**:
- `namer/__main__.py` - CLI dispatcher routes to subcommands
- `namer/namer.py` - File processing logic (rename mode)
- `namer/watchdog.py` - Directory monitoring service
- `namer/web/server.py` - Flask web interface

**Metadata Providers**:
- Default: StashDB (recommended)
- Alternative: ThePornDB
- Located in `namer/metadata_providers/`
- Factory pattern in `factory.py`

## Configuration

```bash
# Copy default config to home directory
cp namer/namer.cfg.default ~/.namer.cfg

# Or use local config
cp namer/namer.cfg.default ./.namer.cfg
```

**Critical Config Sections**:
- `[namer]` - File naming templates, processing options, metadata provider selection
- `[Phash]` - Perceptual hash settings and thresholds
- `[metadata]` - MP4 tagging and .nfo file generation  
- `[watchdog]` - Directory monitoring and web UI settings

**API Tokens**: Set `STASHDB_TOKEN` or `TPDB_TOKEN` environment variables
- StashDB: https://stashdb.org/register
- ThePornDB: https://theporndb.net/register

**Directory Structure (Watchdog Mode)**:
- `watch_dir` - Where new files are detected
- `work_dir` - Temporary processing location
- `failed_dir` - Files that couldn't be matched (retried daily)
- `dest_dir` - Final location for successfully processed files

## Conventions & Patterns

**Module Structure**:
```
namer/
├── __main__.py              # CLI entry point
├── namer.py                 # File processing core
├── watchdog.py              # Directory monitoring
├── command.py               # File operations & Command dataclass
├── configuration.py         # Config dataclass
├── configuration_utils.py   # Config loading & validation
├── fileinfo.py              # Filename parsing
├── metadata_providers/      # Metadata provider implementations
│   ├── stashdb_provider.py  # StashDB GraphQL provider (default)
│   ├── theporndb_provider.py# ThePornDB GraphQL provider
│   ├── factory.py           # Provider factory
│   └── provider.py          # Base provider interface
├── comparison_results.py    # Match ranking & results
├── videohashes.py           # Perceptual hashing interface
├── web/                     # Flask web interface
│   ├── server.py            # Web server
│   ├── routes/              # API and web routes
│   └── templates/           # Jinja2 templates
└── tools/                   # External Go binaries (built)
```

**Key Data Classes**:
- `Command` - Processing context for a file/directory
- `LookedUpFileInfo` - Metadata from API
- `ComparisonResults` - Ranked list of potential matches
- `NamerConfig` - Application configuration
- `FileInfo` - Parsed filename components

**Error Handling**:
- Loguru with `@logger.catch` decorators
- Graceful degradation - failed files moved to `failed_dir`
- Configuration validation at startup
- Errors bubble up with context

## External Dependencies

- **videohashes** - Git submodule with Go tools for perceptual hashing
- **FFmpeg** - Video analysis (must be in PATH)
- **StashDB/ThePornDB GraphQL APIs** - Metadata lookup
- **Node.js + pnpm** - Frontend build for web UI
- **Poetry** - Python dependency management
- **Go compiler** - Required for building videohashes submodule

## Gotchas

```bash
# Initialize git submodules first
git submodule update --init
```

- **Requires Poetry, pnpm, Go, and FFmpeg in PATH**
- **Path separators**: Config uses forward slashes on all platforms (including Windows)
- **Permissions**: `update_permissions_ownership` requires appropriate user privileges  
- **Watchdog behavior**:
  - Waits for file locks to release before processing
  - `queue_limit` prevents memory issues with large batches
  - Failed files automatically retried daily at configured time
  - `manual_mode = True` sends all matches to `failed_dir` for manual web review
- **API rate limiting**: Respect `requests_cache_expire_minutes` setting
- **Database**: `use_database = False` by default - hash cache stored when enabled

## Testing

**Test Structure**:
```
test/
├── *_test.py        # Unit tests for each module
├── *.json           # Mock API responses
├── *.mp4            # Sample video files
└── *.nfo            # Sample metadata files
```

**Run Tests**:
```bash
# All tests with coverage
poetry run pytest --cov

# Specific test file
poetry run pytest test/namer_file_parser_test.py -v

# Test by keyword
poetry run pytest test/ -k "ffmpeg" -v

# Fast tests only (exclude slow tests)
poetry run poe test_namer

# All tests including slow
poetry run poe test_full
```

## Agent Notes

- **Follow existing patterns**: Match coding style and error handling already in the codebase
- **DRY principle**: Check for existing utilities before creating new ones
- **Minimal changes**: Keep changes scoped and aligned with existing conventions
- **Test first**: Add tests for bug fixes; ensure tests pass before committing
- **No architectural changes**: without explicit approval
- **Respect configuration**: Don't hardcode values that should be configurable
- **This complements README.md**: Focus on code-level context, not user instructions
