# File Ownership Fix for Docker Containers

## Problem Description

When running the Namer application in a Docker container, files created by the application were being assigned root ownership (root:root) instead of the configured user ownership. This happened even when:

- `update_permissions_ownership = True` was set in the configuration
- `set_uid = 99` and `set_gid = 100` were properly configured
- PUID and PGID environment variables were passed to the container

## Root Cause

The issue was that the Docker container ran the Namer application as the root user. When the Python code called `os.lchown(target, uid=99, gid=100)`, it was executed by root, but the effective user creating the files was still root.

The container wasn't implementing proper user switching based on the PUID/PGID environment variables.

## Solution

The fix involves implementing proper user switching in the Docker container using the following approach:

### 1. Install `gosu` Package

The `gosu` utility is added to the Dockerfile to enable proper privilege dropping:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       # ... other packages ...
       gosu \
    && rm -rf /var/lib/apt/lists/*
```

### 2. Enhanced Entrypoint Script

A new entrypoint script (`docker-entrypoint-user.sh`) was created that:

- Creates a group with the specified PGID if it doesn't exist
- Creates a user with the specified PUID if it doesn't exist
- Sets proper ownership of application directories
- Switches to the specified user before running the Namer application

### 3. Environment Variable Support

The Docker Compose configuration now properly supports:

- `PUID`: User ID for file ownership (default: 1000)
- `PGID`: Group ID for file ownership (default: 1000)
- `UMASK`: File creation mask (default: 022)

## Usage

### Docker Compose

```yaml
services:
  namer:
    # ... other configuration ...
    environment:
      - PUID=99          # Set to your desired user ID
      - PGID=100         # Set to your desired group ID
      - UMASK=022        # Set to your desired umask
      - NAMER_CONFIG=/config/namer.cfg
      # ... other environment variables ...
```

### Manual Docker Run

```bash
docker run -d \
  --name namer \
  -e PUID=99 \
  -e PGID=100 \
  -e UMASK=022 \
  -e NAMER_CONFIG=/config/namer.cfg \
  -v /path/to/config:/config \
  -v /path/to/media:/app/media \
  namer:latest
```

## Configuration Requirements

Your `namer.cfg` should still include the ownership settings:

```ini
[namer]
# Enable permission/ownership updates
update_permissions_ownership = True

# Set permissions (octal format)
set_dir_permissions = 755
set_file_permissions = 644

# Set ownership (these should match your PUID/PGID environment variables)
set_uid = 99
set_gid = 100
```

## Testing the Fix

A test script (`test-file-ownership.sh`) is provided to verify the fix works correctly:

```bash
# Run the ownership test
./test-file-ownership.sh
```

This script will:
1. Build a test Docker image
2. Create test configuration and media directories
3. Run the container with PUID=99 and PGID=100
4. Verify that created files have the correct ownership
5. Clean up test containers

## Expected Results

After implementing this fix:

1. **Container Startup**: The container will start as root but immediately switch to the specified user
2. **File Creation**: All files created by the Namer application will have the ownership specified by PUID:PGID
3. **Directory Permissions**: New directories will have the permissions specified in the configuration
4. **Existing Functionality**: All existing functionality (Intel GPU support, watchdog, web UI) remains intact

## Troubleshooting

### Container Fails to Start

Check the container logs:
```bash
docker logs namer-container-name
```

Common issues:
- Invalid PUID/PGID values
- Missing volume mounts
- Configuration file issues

### Files Still Have Wrong Ownership

1. Verify PUID/PGID environment variables are set correctly
2. Check that `update_permissions_ownership = True` in your configuration
3. Ensure `set_uid` and `set_gid` match your PUID/PGID values
4. Verify volume mounts allow the container to modify files

### Permission Denied Errors

This may occur if:
- The host directories don't allow access by the specified PUID/PGID
- SELinux or AppArmor policies are blocking access
- The specified user doesn't have permission to access mounted volumes

## Backward Compatibility

This change is backward compatible:
- If PUID/PGID are not specified, defaults to 1000:1000
- Existing configurations continue to work without modification
- The container behavior remains the same except for proper user switching

## Security Considerations

- The container still starts as root to perform user management tasks
- Privileges are dropped to the specified user before running the application
- This approach is considered a security best practice for containerized applications
- The `gosu` utility is preferred over `su` or `sudo` for privilege dropping in containers