"""
Logging utilities for Namer
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from namer.configuration import NamerConfig


def setup_file_logging(config: NamerConfig) -> Optional[Path]:
    """
    Configure a Loguru file sink based on configuration. Returns the log file path if enabled.
    This is safe to call multiple times; Loguru will add multiple sinks if called repeatedly,
    so callers should ensure they do not duplicate calls unnecessarily.
    """
    try:
        if getattr(config, 'file_logging_enabled', False):
            log_dir = getattr(config, 'file_logging_directory', None)
            if not log_dir:
                log_dir_path = Path('./logs').resolve()
            else:
                log_dir_path = Path(log_dir).resolve()
            log_dir_path.mkdir(parents=True, exist_ok=True)

            file_level = getattr(config, 'file_logging_level', 'INFO') or 'INFO'
            rotation = getattr(config, 'file_logging_rotation', '10 MB') or '10 MB'
            retention = getattr(config, 'file_logging_retention', '7 days') or '7 days'
            fmt = config.console_format or '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}'

            log_path = log_dir_path / 'namer.log'
            logger.add(
                log_path,
                level=file_level,
                rotation=rotation,
                retention=retention,
                enqueue=True,
                backtrace=config.diagnose_errors,
                diagnose=config.diagnose_errors,
                format=fmt,
            )
            return log_path
    except Exception as e:  # pragma: no cover - non-critical logging setup
        logger.warning(f'Failed to initialize file logging: {e}')
    return None
