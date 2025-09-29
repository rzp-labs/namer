"""
Tests for file logging configuration and wiring
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from configupdater import ConfigUpdater
from importlib import resources

from namer.configuration import NamerConfig
from namer.configuration_utils import from_config
from namer.logging_utils import setup_file_logging


class FileLoggingConfigTest(unittest.TestCase):
    def test_parsing_file_logging_fields(self):
        # Load default config
        updater = ConfigUpdater(allow_no_value=True)
        cfg_str = ''
        if hasattr(resources, 'files'):
            cfg_str = resources.files('namer').joinpath('namer.cfg.default').read_text()
        elif hasattr(resources, 'read_text'):
            cfg_str = resources.read_text('namer', 'namer.cfg.default')
        updater.read_string(cfg_str)

        # Inject file logging overrides into [watchdog]
        if not updater.has_section('watchdog'):
            updater.add_section('watchdog')
        updater['watchdog']['file_logging_enabled'] = 'True'
        updater['watchdog']['file_logging_level'] = 'DEBUG'
        updater['watchdog']['file_logging_rotation'] = '1 MB'
        updater['watchdog']['file_logging_retention'] = '3 days'
        updater['watchdog']['file_logging_directory'] = '/tmp/namer-logs'

        cfg = from_config(updater, NamerConfig())

        self.assertTrue(getattr(cfg, 'file_logging_enabled', False))
        self.assertEqual(getattr(cfg, 'file_logging_level', ''), 'DEBUG')
        self.assertEqual(getattr(cfg, 'file_logging_rotation', ''), '1 MB')
        self.assertEqual(getattr(cfg, 'file_logging_retention', ''), '3 days')
        # file_logging_directory is converted to a Path in __init__ resolution, so type may vary
        self.assertTrue(str(getattr(cfg, 'file_logging_directory', '')).endswith('namer-logs'))


class FileLoggingWiringTest(unittest.TestCase):
    def test_setup_file_logging_adds_sink_and_creates_file(self):
        cfg = NamerConfig()
        cfg.file_logging_enabled = True  # type: ignore[attr-defined]
        cfg.file_logging_level = 'INFO'  # type: ignore[attr-defined]
        cfg.file_logging_rotation = '10 MB'  # type: ignore[attr-defined]
        cfg.file_logging_retention = '7 days'  # type: ignore[attr-defined]
        cfg.console_format = '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}'

        with tempfile.TemporaryDirectory(prefix='namer-log-test') as td:
            log_dir = Path(td) / 'logs'
            cfg.file_logging_directory = log_dir  # type: ignore[attr-defined]

            # Intercept logger.add to avoid polluting global sinks while still exercising logic
            with patch('namer.logging_utils.logger.add') as mock_add:
                log_path = setup_file_logging(cfg)
                self.assertIsNotNone(log_path)
                self.assertTrue(log_dir.exists())
                # Ensure logger.add called once with expected path
                mock_add.assert_called()
                args, kwargs = mock_add.call_args
                self.assertTrue(str(args[0]).endswith('namer.log'))
                self.assertEqual(kwargs.get('level'), 'INFO')
                self.assertEqual(kwargs.get('rotation'), '10 MB')
                self.assertEqual(kwargs.get('retention'), '7 days')
                self.assertIn('format', kwargs)


if __name__ == '__main__':
    unittest.main()
