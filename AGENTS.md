# AGENTS.md
This file provides guidance to AI coding assistants working in this repository.

**Note:** CLAUDE.md, .clinerules, .cursorrules, .windsurfrules, .replit.md, GEMINI.md, .github/copilot-instructions.md, and .idx/airules.md are symlinks to AGENTS.md in this project.

# Namer

**Purpose**: An adult video file renamer that matches files with metadata from StashDB/ThePornDB APIs. Operates in CLI, watchdog service, or web UI modes.

**Technology Stack**:
- **Backend**: Python 3.11-3.14 with Poetry, Flask web framework
- **Frontend**: Node.js 22.x with pnpm 10.x, Webpack 5, Bootstrap 5
- **External Tools**: FFmpeg, Go (for videohashes submodule), Docker

## Build & Commands

### Python Tasks (Poetry/Poe)

**CRITICAL**: This project uses **Poetry** for Python and **pnpm** (exclusively) for Node.js. No npm or yarn allowed - enforced via pre-commit hooks.

#### Build Tasks
- **Full build with tests**: `poetry run poe build_all`
- **Fast build without tests**: `poetry run poe build_fast`
- **Development build**: `poetry run poe dev_build`
- **Install Node dependencies**: `poetry run poe install_npm` (runs pnpm install)
- **Build frontend**: `poetry run poe build_node` (runs pnpm build)
- **Build videohashes**: `poetry run poe build_videohashes` (compiles Go tool)
- **Build Python package**: `poetry run poe build_namer`

#### Test Tasks
- **Format check**: `poetry run poe test_format` (ruff check)
- **Fast tests**: `poetry run poe test_namer` (excludes slow tests)
- **Slow tests**: `poetry run poe test_namer_slow`
- **All tests**: `poetry run poe test_full`
- **Quick check**: `poetry run poe test_quick` (format only)
- **Unit tests verbose**: `poetry run poe test_unit` (fail-fast)
- **Pre-commit hook**: `poetry run poe precommit` (format + unit tests)

#### Direct Commands
```bash
# Install dependencies
poetry install

# Run tests with coverage
poetry run pytest --cov

# Run lint check
poetry run ruff check .

# Format code
poetry run ruff format .

# Build frontend assets
pnpm install
pnpm build
```

### NPM Scripts (from package.json)

**EXACT script names** (use these, not generic placeholders):
- **Build frontend**: `pnpm build` (webpack production build)
- **Install Husky hooks**: `pnpm prepare`
- **Test**: `pnpm test` (currently no-op - displays message to use pytest)

**Note**: JavaScript testing is not yet implemented. The test script displays a helpful message directing to Python tests.

### Makefile Targets (Docker Development)
- **Fast Docker build**: `make build-fast` (~5 min)
- **Full Docker build**: `make build-full` (with tests, ~20 min)
- **Single arch builds**: `make build-amd64` / `make build-arm64`
- **Multi-arch build**: `make build-multiarch` (pushes to registry)
- **Test Docker image**: `make test`
- **Pre-push validation**: `make validate`
- **Development setup**: `make setup-dev` (bootstrap Poetry + install hooks)

### Script Command Consistency
**Important**: When modifying npm scripts in package.json, ensure all references are updated:
- GitHub Actions workflows (.github/workflows/*.yml)
- README.md documentation
- Dockerfile (frontend build step)
- validate.sh script

Common places that reference scripts:
- Build commands → Check: .github/workflows/pr-validate.yml, Dockerfile
- Pre-commit hooks → Check: .husky/pre-commit, package.json
- Validation → Check: validate.sh, Makefile

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

## Code Style

### Python (Ruff)
- **Line Length**: 320 characters (very permissive, but prefer reasonable line lengths)
- **Indentation**: 4 spaces
- **Quote Style**: Single quotes (`'`) - enforced by ruff format
- **Target**: Python 3.11+
- **Linting Rules**:
  - Enabled: E (pycodestyle errors), F (pyflakes)
  - Ignored: E501 (line too long), E722 (bare except)
- **Formatter**: `ruff format` with auto line ending detection

### Import Conventions
```python
# Standard library imports first
import os
from pathlib import Path

# Third-party imports
import requests
from loguru import logger

# Local imports
from namer.command import Command
from namer.configuration import NamerConfig
```

### Naming Conventions
- **Classes**: PascalCase (e.g., `NamerConfig`, `ComparisonResults`)
- **Functions/Methods**: snake_case (e.g., `parse_file_name`, `get_metadata`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_TIMEOUT`, `API_BASE_URL`)
- **Private methods**: Leading underscore (e.g., `_validate_config`)

### Type Usage
- Use type hints for function signatures
- Dataclasses for structured data (Command, NamerConfig, FileInfo)
- Pydantic for validation where needed

### Error Handling
- Use Loguru with `@logger.catch` decorators for error catching
- Graceful degradation - failed files moved to `failed_dir`
- Configuration validation at startup
- Errors should bubble up with context

### JavaScript/Frontend (ESLint + Webpack)
- **ESLint**: Browser globals, @eslint/js recommended config
- **Formatting**: Auto-formatted via webpack build
- **Linting**: lint-staged with husky pre-commit hooks
- **jQuery**: Used for DOM manipulation (jQuery 3.7.1)
- **DataTables**: Bootstrap 5 integration for tables

### Shell Scripts
- **Linting**: shellcheck (run in CI)
- **Formatting**: shfmt (run in CI)

## Testing

### Testing Framework
- **Framework**: pytest with pytest-cov (coverage plugin)
- **Markers**: `@pytest.mark.slow` for slow tests (excluded in CI)
- **Assertions**: Standard unittest.TestCase with assertpy for enhanced assertions
- **Mocking**: unittest.mock for mocking dependencies
- **Web Testing**: Selenium WebDriver for E2E web UI tests
- **Coverage Target**: ~80% (enforced in CI)

### Test File Patterns
- **Naming**: `*_test.py` (e.g., `namer_file_parser_test.py`)
- **Location**: `test/` directory with subdirectories:
  - `test/unit/` - Unit tests
  - `test/integration/` - Integration tests
  - `test/web/` - Web UI tests

### Test Conventions
```python
# Test class naming
class UnitTestAsTheDefaultExecution(unittest.TestCase):

    # Test method naming
    def test_parse_file_name(self):
        # Arrange
        config = sample_config()

        # Act
        result = parse_file_name("example.mp4", config)

        # Assert
        assert_that(result.site).is_equal_to("example")
```

### Running Tests
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

# Verbose unit tests (fail-fast)
poetry run poe test_unit
```

### Testing Philosophy
**When tests fail, fix the code, not the test.**

Key principles:
- **Tests should be meaningful** - Avoid tests that always pass regardless of behavior
- **Test actual functionality** - Call the functions being tested, don't just check side effects
- **Failing tests are valuable** - They reveal bugs or missing features
- **Fix the root cause** - When a test fails, fix the underlying issue, don't modify the test to pass
- **Test edge cases** - Tests that reveal limitations help improve the code
- **Document test purpose** - Each test should clearly show what it validates

## Security

### Custom Quality Rules (lifeguard.yaml)

The project includes custom quality rules enforced via lifeguard.yaml:

1. **Database transactions must be properly handled**
   - Wrap all database operations in transactions with proper rollback handling
   - Ensure commit/rollback is called in all code paths including error scenarios

2. **API responses must include proper error context**
   - Include sufficient context for debugging (request ID, timestamp, user context)
   - Do not expose sensitive information in error messages

3. **Async operations should have timeout handling**
   - Include appropriate timeout mechanisms for long-running operations
   - Applies to: API calls, database queries, file operations

### API Token Management
- **Environment Variables**: `STASHDB_TOKEN` or `TPDB_TOKEN`
- **Never commit tokens** to version control
- **Use .env.example** as a template, create .env locally
- StashDB: https://stashdb.org/register
- ThePornDB: https://theporndb.net/register

### Data Validation
- Validate all user inputs before processing
- Use configuration validation at startup
- Sanitize filenames and paths to prevent path traversal

## Directory Structure & File Organization

### Project Structure
```
namer/
├── .claude/
│   ├── agents/              # 16 specialized AI subagents
│   ├── commands/            # Custom slash commands
│   └── settings.json        # Shared team settings (commit)
├── .github/
│   ├── workflows/           # 6 GitHub Actions workflows
│   └── copilot-instructions.md  # → symlink to AGENTS.md
├── namer/                   # Python source code
│   ├── __main__.py          # CLI entry point
│   ├── namer.py             # Core file processing logic
│   ├── watchdog.py          # Directory monitoring service
│   ├── command.py           # File operations & Command dataclass
│   ├── configuration.py     # Config dataclass
│   ├── fileinfo.py          # Filename parsing
│   ├── metadata_providers/  # StashDB/ThePornDB implementations
│   ├── comparison_results.py # Match ranking
│   ├── videohashes.py       # Perceptual hashing interface
│   ├── web/                 # Flask web UI
│   │   ├── server.py        # Web server
│   │   ├── routes/          # API and web routes
│   │   ├── templates/       # Jinja2 templates
│   │   └── public/assets/   # Built frontend assets
│   └── tools/               # Compiled Go binaries (videohashes)
├── src/                     # Frontend source
│   ├── css/                 # SCSS stylesheets
│   ├── js/                  # JavaScript modules
│   └── templates/           # HTML templates (pre-build)
├── test/                    # Python tests
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   ├── web/                 # Web UI tests
│   └── *_test.py            # Test modules
├── reports/                 # All project reports (see below)
├── temp/                    # Temporary files and debugging
├── docs/                    # Technical documentation (25+ docs)
├── scripts/                 # Build and utility scripts
├── videohashes/             # Git submodule (Go project)
├── config/                  # Default configuration
└── dist/                    # Build artifacts
```

### Reports Directory
**ALL project reports and documentation should be saved to the `reports/` directory:**

```
reports/
├── README.md                # Report directory documentation
├── PHASE_*_VALIDATION_REPORT.md      # Phase validation reports
├── IMPLEMENTATION_SUMMARY_*.md       # Implementation summaries
├── FEATURE_*_REPORT.md               # Feature completion reports
├── TEST_RESULTS_*.md                 # Test execution results
├── COVERAGE_REPORT_*.md              # Coverage analysis
├── PERFORMANCE_ANALYSIS_*.md         # Performance benchmarks
└── SECURITY_SCAN_*.md                # Security analysis
```

**Report Naming Conventions:**
- Use descriptive names: `[TYPE]_[SCOPE]_[DATE].md`
- Include dates: `YYYY-MM-DD` format
- Group with prefixes: `TEST_`, `PERFORMANCE_`, `SECURITY_`
- Markdown format: All reports end in `.md`

**Report Types:**

**Implementation Reports:**
- Phase validation: `PHASE_X_VALIDATION_REPORT.md`
- Implementation summaries: `IMPLEMENTATION_SUMMARY_[FEATURE].md`
- Feature completion: `FEATURE_[NAME]_REPORT.md`

**Testing & Analysis Reports:**
- Test results: `TEST_RESULTS_[DATE].md`
- Coverage reports: `COVERAGE_REPORT_[DATE].md`
- Performance analysis: `PERFORMANCE_ANALYSIS_[SCENARIO].md`
- Security scans: `SECURITY_SCAN_[DATE].md`

**Quality & Validation:**
- Code quality: `CODE_QUALITY_REPORT.md`
- Dependency analysis: `DEPENDENCY_REPORT.md`
- API compatibility: `API_COMPATIBILITY_REPORT.md`

### Temporary Files & Debugging
All temporary files, debugging scripts, and test artifacts should be organized in `/temp`:

**Temporary File Organization:**
- **Debug scripts**: `temp/debug-*.js`, `temp/analyze-*.py`
- **Test artifacts**: `temp/test-results/`, `temp/coverage/`
- **Generated files**: `temp/generated/`, `temp/build-artifacts/`
- **Logs**: `temp/logs/debug.log`, `temp/logs/error.log`

**Guidelines:**
- Never commit files from `/temp` directory
- Use `/temp` for all debugging and analysis scripts
- Clean up `/temp` directory regularly
- `/temp/` is included in `.gitignore`

### Claude Code Settings (.claude Directory)

**Version Controlled Files (commit these):**
- `.claude/settings.json` - Shared team settings for hooks, tools, and environment
- `.claude/commands/*.md` - Custom slash commands available to all team members
- `.claude/hooks/*.sh` - Hook scripts for automated validations and actions
- `.claude/agents/**/*.md` - Specialized AI subagents (16 available)

**Ignored Files (do NOT commit):**
- `.claude/settings.local.json` - Personal preferences and local overrides
- Any `*.local.json` files - Personal configuration not meant for sharing

**Important Notes:**
- The shared `settings.json` should contain team-wide standards
- Personal preferences or experimental settings belong in `settings.local.json`
- Hook scripts in `.claude/hooks/` should be executable (`chmod +x`)

## Configuration

### Environment Setup
```bash
# Copy default config to home directory
cp namer/namer.cfg.default ~/.namer.cfg

# Or use local config
cp namer/namer.cfg.default ./.namer.cfg

# Set API token
export STASHDB_TOKEN="your_token_here"
# OR
export TPDB_TOKEN="your_token_here"
```

### Required Environment Variables
- `STASHDB_TOKEN` - StashDB API token (recommended)
- `TPDB_TOKEN` - ThePornDB API token (alternative)
- `TZ` - Timezone (default: America/Phoenix)
- `PUID` / `PGID` - User/Group IDs for Docker
- `UMASK` - File permission mask
- `NAMER_CONFIG` - Path to custom config file
- `LIBVA_DRIVER_NAME` - Intel GPU driver (iHD for QSV acceleration)

### Configuration File Sections
- `[namer]` - File naming templates, metadata provider selection, processing options
- `[Phash]` - Perceptual hash thresholds and settings
- `[metadata]` - MP4 tagging and .nfo file generation
- `[watchdog]` - Directory monitoring, web UI settings, processing limits

### Directory Structure (Watchdog Mode)
- `watch_dir` - Where new files are detected
- `work_dir` - Temporary processing location
- `failed_dir` - Files that couldn't be matched (retried daily)
- `dest_dir` - Final location for successfully processed files

## Architecture Overview

### Processing Flow
1. **File Input** → Command object (`namer/command.py`)
2. **Name Parsing** → Extract site, date, scene (`namer/fileinfo.py`)
3. **Hash Calculation** → Perceptual hashes (`namer/videohashes.py`)
4. **API Matching** → Query metadata provider via GraphQL
5. **Result Comparison** → Rank matches (`namer/comparison_results.py`)
6. **File Operations** → Rename, tag, move files

### Entry Points
- `namer/__main__.py` - CLI dispatcher routes to subcommands
- `namer/namer.py` - File processing logic (rename mode)
- `namer/watchdog.py` - Directory monitoring service
- `namer/web/server.py` - Flask web interface

### Key Data Classes
- `Command` - Processing context for a file/directory
- `LookedUpFileInfo` - Metadata from API
- `ComparisonResults` - Ranked list of potential matches
- `NamerConfig` - Application configuration
- `FileInfo` - Parsed filename components

### Metadata Providers
- **Default**: StashDB (recommended)
- **Alternative**: ThePornDB
- **Location**: `namer/metadata_providers/`
- **Factory Pattern**: `factory.py` selects provider based on config

## Agent Delegation & Tool Execution

### ⚠️ MANDATORY: Always Delegate to Specialists & Execute in Parallel

**When specialized agents are available, you MUST use them instead of attempting tasks yourself.**

**When performing multiple operations, send all tool calls (including Task calls for agent delegation) in a single message to execute them concurrently for optimal performance.**

### Available Specialized AI Subagents (16)

**General Experts:**
1. **code-review-expert** - Multi-aspect code review (architecture, quality, security, performance, testing, docs)
2. **code-search** - Deep code search and analysis
3. **oracle** - General wisdom/decision-making
4. **research-expert** - Deep research with citations
5. **triage-expert** - Issue triage and prioritization

**Specialized by Domain:**
6. **testing-expert** - Test structure, mocking, coverage, E2E testing (Jest/Vitest/Pytest)
7. **git-expert** - Git operations and workflows
8. **refactoring-expert** - Code refactoring strategies
9. **documentation-expert** - Documentation best practices
10. **database-expert** - Database design and optimization
11. **devops-expert** - DevOps and CI/CD
12. **linting-expert** - Linting and quality checks
13. **webpack-expert** - Webpack build configuration
14. **css-styling-expert** - CSS and styling
15. **docker-expert** - Docker containerization
16. **github-actions-expert** - GitHub Actions CI/CD

### Why Agent Delegation Matters
- Specialists have deeper, more focused knowledge
- They're aware of edge cases and subtle bugs
- They follow established patterns and best practices
- They can provide more comprehensive solutions

### Key Principles
- **Agent Delegation**: Always check if a specialized agent exists for your task domain
- **Complex Problems**: Delegate to domain experts, use diagnostic agents when scope is unclear
- **Multiple Agents**: Send multiple Task tool calls in a single message to delegate to specialists in parallel
- **DEFAULT TO PARALLEL**: Unless you have a specific reason why operations MUST be sequential (output of A required for input of B), always execute multiple tools simultaneously
- **Plan Upfront**: Think "What information do I need to fully answer this question?" Then execute all searches together

### Discovering Available Agents
```bash
# Quick check: List agents if claudekit is installed
command -v claudekit >/dev/null 2>&1 && claudekit list agents || echo "claudekit not installed"

# If claudekit is installed, you can explore available agents:
claudekit list agents
```

### Critical: Always Use Parallel Tool Calls

**Err on the side of maximizing parallel tool calls rather than running sequentially.**

**IMPORTANT: Send all tool calls in a single message to execute them in parallel.**

**These cases MUST use parallel tool calls:**
- Searching for different patterns (imports, usage, definitions)
- Multiple grep searches with different regex patterns
- Reading multiple files or searching different directories
- Combining Glob with Grep for comprehensive results
- Searching for multiple independent concepts
- Any information gathering where you know upfront what you're looking for
- Agent delegations with multiple Task calls to different specialists

**Sequential calls ONLY when:**
You genuinely REQUIRE the output of one tool to determine the usage of the next tool.

**Planning Approach:**
1. Before making tool calls, think: "What information do I need to fully answer this question?"
2. Send all tool calls in a single message to execute them in parallel
3. Most of the time, parallel tool calls can be used rather than sequential

**Performance Impact:** Parallel tool execution is 3-5x faster than sequential calls, significantly improving user experience.

**Remember:** This is not just an optimization—it's the expected behavior. Both delegation and parallel execution are requirements, not suggestions.

## External Dependencies

- **videohashes** - Git submodule with Go tools for perceptual hashing
- **FFmpeg** - Video analysis (must be in PATH)
- **StashDB/ThePornDB GraphQL APIs** - Metadata lookup
- **Node.js + pnpm** - Frontend build for web UI (pnpm ONLY, enforced)
- **Poetry** - Python dependency management
- **Go compiler** - Required for building videohashes submodule

## Critical Gotchas & Development Notes

### Dual FFmpeg Implementation
**⚠️ CRITICAL MAINTENANCE WARNING**: Two versions of FFmpeg functionality exist:
- `namer/ffmpeg.py` - Base/development version
- `namer/ffmpeg_enhanced.py` - Production/container version with Intel GPU acceleration

**Both must be kept in sync** when making FFmpeg-related changes!

### Package Management Enforcement
- **pnpm ONLY** - No npm or yarn allowed
- Enforced via:
  - Pre-commit hooks (`.husky/pre-commit`)
  - CI validation (`.github/workflows/pr-validate.yml`)
  - `scripts/enforce-pnpm.sh`
- Requires `corepack enable` for pnpm setup

### Git Submodules
```bash
# REQUIRED: Initialize git submodules first
git submodule update --init
```
- `videohashes/` is a Git submodule (Go project)
- Builds architecture-specific binaries (amd64, arm64)
- Must be initialized before building

### Other Gotchas
- **Path separators**: Config uses forward slashes on all platforms (including Windows)
- **Permissions**: `update_permissions_ownership` requires appropriate user privileges
- **Watchdog behavior**:
  - Waits for file locks to release before processing
  - `queue_limit` prevents memory issues with large batches
  - Failed files automatically retried daily at configured time
  - `manual_mode = True` sends all matches to `failed_dir` for manual web review
- **API rate limiting**: Respect `requests_cache_expire_minutes` setting
- **Database**: `use_database = False` by default - hash cache stored when enabled

## Best Practices for AI Agents

- **Follow existing patterns**: Match coding style and error handling already in the codebase
- **DRY principle**: Check for existing utilities before creating new ones
- **Minimal changes**: Keep changes scoped and aligned with existing conventions
- **Test first**: Add tests for bug fixes; ensure tests pass before committing
- **No architectural changes** without explicit approval
- **Respect configuration**: Don't hardcode values that should be configurable
- **Delegate to specialists**: Use available subagents for domain-specific tasks
- **Execute in parallel**: Send multiple tool calls in a single message when possible
- **Fix code, not tests**: When tests fail, fix the underlying issue

## Workflow: Git & Pull Requests

### Branch Strategy
- **Main branch**: `main` (protected, no direct pushes)
- **Development branch**: `develop`
- **Feature branches**: `feature/description` or `fix/description`

### Creating Pull Requests
1. Create feature branch from `develop` (or `main` if hotfix)
2. Make changes and commit with descriptive messages
3. Push branch to remote
4. Open PR with:
   - Clear title describing the change
   - Summary of what was done
   - Test plan or verification steps
   - Link to related issues if applicable

### Commit Message Guidelines
- Use conventional commits format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Example: `feat(web): add file preview to web UI`

## CI/CD Workflows

### GitHub Actions Workflows
1. **pr-validate.yml** - Linting, pytest (no slow tests), static analysis
2. **pr-container-smoke.yml** - Docker build smoke test
3. **docker-build.yml** - Multi-arch Docker image builds (linux/amd64, linux/arm64)
4. **release-bump.yml** - Version bumping automation
5. **claude.yml** - Claude Code integration
6. **claude-code-review.yml** - Automated code reviews

### Pre-Push Validation
```bash
# Comprehensive validation (recommended before pushing)
./validate.sh

# Or use make target
make validate
```

## Docker Development

### Multi-Platform Builds
- **Platforms**: linux/amd64, linux/arm64
- **Buildx**: Uses docker buildx for cross-compilation
- **Base Image**: Ubuntu 24.04
- **Features**: Intel GPU hardware acceleration (QSV), VAAPI drivers

### Docker Commands
```bash
# Fast build for local testing (~5 min)
make build-fast

# Full build with tests (~20 min)
make build-full

# Single architecture builds
make build-amd64
make build-arm64

# Multi-arch build and push to registry
make build-multiarch

# Test Docker image
make test
```

## Related Documentation

- **README.md** - User-facing documentation, setup instructions
- **docs/** - Technical documentation (25+ docs)
- **SECURITY.md** - Security policy
- **AGENTS.md** (this file) - AI agent guidance, build/test/run commands
