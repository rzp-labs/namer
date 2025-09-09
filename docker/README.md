# Namer Docker Deployment

This directory contains Docker Compose and configuration files for deploying Namer in your unRAID environment with dual instances for optimal performance.

## Architecture Overview

**Cache Instance** (`namer`): Processes new downloads quickly using cache storage
- Watches: `/mnt/cache/data/media/namer/1-watch` 
- Processes to: `/mnt/cache/data/media/namer/3-import`
- Web UI: `http://your-server:6980`

**Backlog Instance** (`namer-backlog`): Handles existing files in batches
- Intake: `/mnt/user/data/media/namer-backlog/0-intake` 
- Watches: `/mnt/user/data/media/namer-backlog/1-watch`
- Processes to: `/mnt/user/data/media/namer-backlog/3-import`  
- Web UI: `http://your-server:6981`

## Setup Instructions

### 1. Create Directory Structure

Create the required directories on your unRAID server:

```bash
# Cache instance directories (fast processing)
mkdir -p /mnt/cache/data/media/namer/{1-watch,2-work,3-import,4-failed}
mkdir -p /mnt/user/appdata/namer/{config,logs}

# Backlog instance directories (batch processing) 
mkdir -p /mnt/user/data/media/namer-backlog/{0-intake,1-watch,2-work,3-import,4-failed}
mkdir -p /mnt/user/appdata/namer-backlog/{config,logs}

# Set permissions
chown -R 99:100 /mnt/cache/data/media/namer/
chown -R 99:100 /mnt/user/data/media/namer-backlog/
chown -R 99:100 /mnt/user/appdata/namer*/
```

### 2. Configure API Keys (Optional)

1. Copy the environment template if you need to override defaults:
   ```bash
   cp .env.template .env
   ```

2. API keys are set directly in the configuration files (step 3 below)

### 3. Install Configuration Files

1. Copy the configuration templates:
   ```bash
   cp namer-cache.cfg /mnt/user/appdata/namer/config/namer.cfg
   cp namer-backlog.cfg /mnt/user/appdata/namer-backlog/config/namer.cfg
   ```

2. Edit both config files and replace `your_stashdb_api_key_here` with your actual StashDB API key:
   ```ini
   stashdb_token = your_actual_api_key_here
   ```

3. Customize the naming templates and other settings as needed.

### 4. Deploy with Docker Compose

```bash
docker-compose up -d
```

### 5. Verify Deployment

Check that both instances are running:
```bash
docker-compose ps
```

Access the web interfaces:
- Cache instance: `http://your-server:6980`
- Backlog instance: `http://your-server:6981`

## Workflow Integration

### Cache Instance (Fast Processing)
1. **Fileflows** processes new downloads in `/mnt/cache/data/media/downloads/complete`
2. **Fileflows** drops processed files into `/mnt/cache/data/media/namer/1-watch`
3. **Namer** detects, matches, and moves files to `/mnt/cache/data/media/namer/3-import`
4. Your **final media processor** picks up from `3-import`

### Backlog Instance (Controlled Batches)
1. Copy existing files to `/mnt/user/data/media/namer-backlog/0-intake`
2. Move batches from `0-intake` to `1-watch` when ready to process
3. **Namer-backlog** processes files and moves to `3-import`

## Configuration Options

### Key Settings in `namer.cfg`:

- **`name_template`**: Customize file naming pattern
- **`manual_mode`**: Set to `true` to review all matches manually
- **`queue_limit`**: Maximum files to process simultaneously
- **`retry_hour`**: When to retry failed files (cache: 3am, backlog: 4am)

### Provider Settings:
- **`provider = stashdb`**: Uses StashDB for metadata lookup
- **`phash = true`**: Enables perceptual hashing for better matching
- **`update_metadata = true`**: Tags MP4 files with metadata
- **`write_nfo = true`**: Creates .nfo files

## Troubleshooting

### Check Logs:
```bash
# View container logs
docker-compose logs -f namer
docker-compose logs -f namer-backlog

# View application logs
tail -f /mnt/user/appdata/namer/logs/namer-cache.log
tail -f /mnt/user/appdata/namer-backlog/logs/namer-backlog.log
```

### Common Issues:

1. **Permission Denied**: Verify PUID/PGID settings and directory ownership
2. **API Errors**: Check your StashDB API key in the `namer.cfg` files
3. **Files Not Moving**: Verify directory paths match between compose and config files
4. **Web UI Not Accessible**: Check firewall settings and port mappings

### Health Checks:
Both containers include health checks that verify the API endpoint is responding:
```bash
docker-compose exec namer curl -f http://localhost:6980/api/healthcheck
```

## Updates

The included `watchtower` service automatically updates containers daily at 3am when new images are available.

To manually update:
```bash
docker-compose pull
docker-compose up -d
```

## Security Notes

- The `.env` file contains your API keys - keep it secure and don't commit to version control
- Both instances use the same external `rzp-net` network as your other containers
- Health checks ensure containers restart if the application becomes unresponsive
