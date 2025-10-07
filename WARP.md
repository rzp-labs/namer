# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Namer** is a Python application for renaming and tagging adult video files using metadata from StashDB or ThePornDB. It operates in three main modes:
- **Command-line tool**: Rename individual files or directories
- **Watchdog service**: Monitor directories for new files and process them automatically  
- **Web UI**: Manual matching interface for files that couldn't be auto-matched

The application uses perceptual hashing and filename parsing to match video files against metadata provider databases (StashDB by default, ThePornDB as alternative).

## Essential Development Commands

### Prerequisites
- Python 3.11+ with Poetry
- Node.js 22+ with pnpm
- Go (for videohashes submodule)
- FFmpeg

### Core Build Commands
```bash
# Install all dependencies and build everything
poetry install
poetry run poe build_all

# Individual build steps
poetry run poe install_npm      # Install npm dependencies  
poetry run poe build_node       # Build frontend assets
poetry run poe build_videohashes # Build Go videohash tools
poetry run poe build_namer      # Build Python package
```

### Testing
```bash
# Run all tests with coverage
poetry run pytest --cov

# Run linting
poetry run ruff check .

# Combined test and lint (CI equivalent)
poetry run poe test
```

### Running the Application
```bash
# Watchdog mode (requires namer.cfg configuration)
python -m namer watchdog

# Rename a single file
python -m namer rename -f /path/to/file.mp4

# Suggest name for a file
python -m namer suggest -f filename.mp4

# Get web UI URL
python -m namer url

# Generate perceptual hash
python -m namer hash -f /path/to/file.mp4

# Clear cached hashes for files matching pattern
python -m namer clear-cache <filename_pattern>

# Use custom config file
python -m namer --config /path/to/config.cfg watchdog
```

### Development Tools
```bash
# Format code
poetry run ruff format .

# Coverage report  
poetry run coverage html

# Docker build
./docker_build.sh
```

## High-Level Architecture

### Core Entry Points
- **`namer/__main__.py`**: Main CLI dispatcher, routes commands to appropriate modules
- **`namer/namer.py`**: File processing logic (rename mode)
- **`namer/watchdog.py`**: Directory monitoring service
- **`namer/web/server.py`**: Flask web interface

### Key Processing Flow
1. **File Input** → Command object creation (`namer/command.py`)
2. **Name Parsing** → Extract site, date, scene info (`namer/fileinfo.py`)
3. **Hash Calculation** → Generate perceptual hashes (`namer/videohashes.py`)
4. **API Matching** → Query metadata provider via GraphQL (`namer/metadata_providers/`)
5. **Result Comparison** → Rank matches by similarity (`namer/comparison_results.py`)
6. **File Operations** → Rename, tag, move files (`namer/command.py`)

### Configuration System
- **Primary config**: `namer.cfg` (copy from `namer/namer.cfg.default`)
- **Config class**: `NamerConfig` in `namer/configuration.py`
- **Validation**: `configuration_utils.py` verifies setup

### Web Architecture
- **Framework**: Flask with Jinja2 templates
- **Frontend**: Bootstrap 5 + jQuery + DataTables
- **Build**: Webpack (config in root directory)
- **Assets**: Built from `namer/web/` to `namer/web/public/assets/`

### External Dependencies
- **Videohashes**: Git submodule with Go tools for perceptual hashing
- **FFmpeg**: External binary for video analysis via `namer/ffmpeg.py`
- **StashDB GraphQL API**: Primary metadata provider (recommended, default)
- **ThePornDB GraphQL API**: Alternative metadata provider (opt-in via config)

## File Organization Patterns

### Python Module Structure
```
namer/
├── __main__.py              # CLI entry point
├── namer.py                 # File processing core
├── watchdog.py              # Directory monitoring  
├── command.py               # File operations & Command dataclass
├── configuration.py         # Config dataclass
├── configuration_utils.py   # Config loading & validation
├── fileinfo.py              # Filename parsing logic
├── metadataapi.py           # Legacy API utilities
├── metadata_providers/      # Metadata provider implementations
│   ├── stashdb_provider.py  # StashDB GraphQL provider (default)
│   ├── theporndb_provider.py # ThePornDB GraphQL provider
│   ├── factory.py           # Provider factory
│   └── provider.py          # Base provider interface
├── comparison_results.py    # Match ranking & results
├── videohashes.py           # Perceptual hashing interface
├── web/                     # Flask web interface
├── models/                  # Database models (optional)
└── tools/                   # External Go binaries (built)
```

### Key Naming Conventions
- **Command objects**: Represent processing context for a file/directory
- **LookedUpFileInfo**: Metadata from ThePornDB API
- **ComparisonResults**: Ranked list of potential matches  
- **NamerConfig**: Application configuration container
- **FileInfo**: Parsed filename components

### Error Handling Approach
- **Loguru**: Structured logging throughout (`@logger.catch` decorators)
- **Graceful degradation**: Failed files moved to `failed_dir` for retry
- **Configuration validation**: Early validation prevents runtime issues
- **Exception propagation**: Errors bubble up with context

## Configuration Requirements

### Essential Setup
1. **Copy default config**: `cp namer/namer.cfg.default ~/.namer.cfg` 
2. **Get API token**: 
   - StashDB (recommended): Register at https://stashdb.org/register
   - ThePornDB (alternative): Register at https://theporndb.net/register
3. **Set environment variable**: `export STASHDB_TOKEN=your_token` or `export TPDB_TOKEN=your_token`
4. **Set directories**: Configure watch/work/failed/dest directories
5. **Permissions**: Set appropriate file/directory permissions for your system

### Directory Structure (Watchdog Mode)
- **watch_dir**: Where new files are detected
- **work_dir**: Temporary processing location  
- **failed_dir**: Files that couldn't be matched (retried daily)
- **dest_dir**: Final location for successfully processed files

### Critical Config Sections
- **[namer]**: File naming templates, processing options, and metadata provider selection (`metadata_provider = stashdb` or `theporndb`)
- **[Phash]**: Perceptual hash settings and disambiguation thresholds (enabled by default)
- **[metadata]**: MP4 tagging and .nfo file generation
- **[watchdog]**: Directory monitoring and web UI settings

## Testing Strategy

### Test Structure
```
test/
├── *_test.py                # Unit tests for each module
├── *.json                   # Mock API responses  
├── *.mp4                    # Sample video files
└── *.nfo                    # Sample metadata files
```

### Key Test Files
- **`namer_file_parser_test.py`**: Filename parsing logic
- **`namer_metadataapi_test.py`**: API client functionality
- **`namer_ffmpeg_test.py`**: FFmpeg integration
- **`namer_moviexml_test.py`**: .nfo file processing

### Running Specific Tests
```bash
# Test filename parsing
poetry run pytest test/namer_file_parser_test.py -v

# Test API integration  
poetry run pytest test/namer_metadataapi_test.py -v

# Test with sample files
poetry run pytest test/ -k "test_filename" -v
```

## Common Development Patterns

### File Processing Pipeline
1. Create `Command` object with file/directory path
2. Parse filename → `FileInfo` object  
3. Calculate perceptual hash (if enabled)
4. Query ThePornDB API → `ComparisonResults`
5. Select best match → `LookedUpFileInfo`
6. Apply naming template and move file
7. Tag MP4 metadata (if enabled)

### Adding New Filename Patterns
1. **Modify regex**: Update `name_parser` tokens in `fileinfo.py`
2. **Test parsing**: Add test cases in `namer_file_parser_test.py`  
3. **Validate config**: Ensure new patterns work with existing naming templates

### Web UI Extensions
1. **Routes**: Add endpoints in `namer/web/routes/`
2. **Templates**: Create Jinja2 templates in `namer/web/templates/`
3. **Assets**: Add JS/CSS to webpack build process
4. **API**: JSON endpoints use `/api/` prefix

## Development Gotchas

### Git Configuration
- **Submodules**: Project uses `videohashes` git submodule - run `git submodule update --init`
- **Pre-commit**: Husky pre-commit hook runs `pnpm lint-staged` 

### Build Dependencies
- **Poetry + pnpm**: Both package managers required (Python + Node.js)
- **Go build**: Videohashes requires Go compiler for perceptual hash tools
- **FFmpeg**: Must be available in PATH for video analysis

### Configuration Edge Cases
- **Path separators**: Config uses forward slashes even on Windows
- **Permissions**: `update_permissions_ownership` requires appropriate user privileges
- **API limits**: ThePornDB has rate limiting - respect `requests_cache_expire_minutes`

### Watchdog Behavior
- **File locks**: Waits for files to finish copying before processing
- **Queue limits**: `queue_limit` prevents memory issues with large batches
- **Retry logic**: Failed files automatically retried daily at configured time
- **Manual mode**: `manual_mode = True` sends all matches to failed_dir for manual review

## Where to Find Key Functionality

### File Name Parsing
- **Core logic**: `fileinfo.py` → `parse_file_name()`
- **Regex patterns**: `configuration.py` → `name_parser` field
- **Test cases**: `test/namer_file_parser_test.py`

### API Integration  
- **Provider Factory**: `metadata_providers/factory.py` → `get_metadata_provider()`
- **StashDB Provider**: `metadata_providers/stashdb_provider.py`
- **ThePornDB Provider**: `metadata_providers/theporndb_provider.py`
- **Caching**: HTTP request cache configured in `configuration.py`
- **Mock responses**: `test/*.json` files

### Web Interface
- **Server**: `namer/web/server.py` → `NamerWebServer` class
- **Routes**: `namer/web/routes/web.py` and `api.py`
- **Frontend build**: Root `webpack.prod.js` and `package.json`

### Perceptual Hashing
- **Python interface**: `namer/videohashes.py`
- **Go implementation**: `videohashes/` submodule  
- **Built binaries**: `namer/tools/` (copied during build)

### Configuration Management
- **Loading**: `configuration_utils.py` → `default_config()`
- **Validation**: `configuration_utils.py` → `verify_configuration()`
- **Schema**: `NamerConfig` dataclass in `configuration.py`

This documentation focuses on the existing architecture and proven patterns. Modifications should follow the established conventions and maintain compatibility with the extensive configuration system.

<citations>
<document>
<document_type>RULE</document_type>
<document_id>K9I8HJ64FD1FEDbh4edhea</document_id>
</document>
<document>
<document_type>RULE</document_type>
<document_id>MdzU95u5UHeefMVgbkz282</document_id>
</document>
</citations>
