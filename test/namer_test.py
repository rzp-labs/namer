"""
Fully test namer.py
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest
from loguru import logger
from mutagen.mp4 import MP4

from namer.configuration import NamerConfig
from namer.configuration_utils import to_ini
from namer.namer import check_arguments, main, set_permissions
from namer.__main__ import main as namer_main
from test import utils
from test.utils import new_ea, sample_config, validate_mp4_tags, environment, FakeTPDB


class UnitTestAsTheDefaultExecution(unittest.TestCase):
    """
    Always test first.
    """

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)

        if not utils.is_debugging():
            logger.remove()

    def test_check_arguments(self):
        """
        verify file system checks
        """
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            temp_dir = Path(tmpdir)
            target_dir = temp_dir / 'path/'
            file = temp_dir / 'file'
            config = temp_dir / 'config'
            error = check_arguments(dir_to_process=target_dir, file_to_process=file, config_override=config)
            self.assertTrue(error)
            target_dir.mkdir()
            file.write_text('test')
            config.write_text('test')
            error = check_arguments(dir_to_process=target_dir, file_to_process=file, config_override=config)
            self.assertFalse(error)

    @pytest.mark.slow
    def test_writing_metadata_file(self: unittest.TestCase):
        """
        test namer main method renames and tags in place when -f (video file) is passed
        """
        with environment() as (temp_dir, fake_tpdb, config):
            targets = [new_ea(temp_dir, use_dir=False)]
            main(['-f', str(targets[0].file), '-c', str(config.config_file)])
            output = MP4(targets[0].get_file().parent / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

    @pytest.mark.slow
    def test_writing_metadata_dir(self: unittest.TestCase):
        """
        test namer main method renames and tags in place when -d (directory) is passed
        """
        with environment() as (temp_dir, fake_tpdb, config):
            targets = [new_ea(temp_dir, use_dir=True)]
            main(['-d', str(targets[0].get_file().parent), '-c', str(config.config_file)])
            output = MP4(targets[0].get_file().parent.parent / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

    @pytest.mark.slow
    def test_writing_metadata_all_dirs(self: unittest.TestCase):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all subdirs of -d.
        """
        with environment() as (temp_dir, fake_tpdb, config):
            temp_dir: Path
            fake_tpdb: FakeTPDB
            config: NamerConfig
            targets = [
                new_ea(temp_dir, use_dir=True, post_stem='1'),
                new_ea(temp_dir, use_dir=True, post_stem='2'),
            ]
            main(['-d', str(targets[0].get_file().parent.parent), '-m', '-c', str(config.config_file)])
            output = MP4(targets[0].get_file().parent.parent / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])
            output = MP4(targets[1].get_file().parent.parent / 'Evil Angel' / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240](1).mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

    @pytest.mark.slow
    def test_writing_metadata_from_nfo(self):
        """
        Test renaming and writing a movie's metadata from a nfo file.
        """
        config = sample_config()
        config.enabled_tagging = True
        config.enabled_poster = True
        config.write_nfo = False
        config.min_file_size = 0
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            current = Path(__file__).resolve().parent
            temp_dir = Path(tmpdir)
            nfo_file = current / 'ea.nfo'
            mp4_file = current / 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4'
            poster_file = current / 'poster.png'
            target_nfo_file = temp_dir / 'ea.nfo'
            target_mp4_file = temp_dir / 'ea.mp4'
            target_poster_file = temp_dir / 'poster.png'
            shutil.copy(mp4_file, target_mp4_file)
            shutil.copy(nfo_file, target_nfo_file)
            shutil.copy(poster_file, target_poster_file)

            cfg_file = temp_dir / 'test_namer.cfg'
            with open(cfg_file, 'w') as file:
                content = to_ini(config)
                file.write(content)

            main(['-f', str(target_mp4_file), '-i', '-c', str(cfg_file)])
            output = MP4(target_mp4_file.parent / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4')
            self.assertEqual(output.get('\xa9nam'), ['Carmela Clutch: Fabulous Anal 3-Way!'])

    @pytest.mark.slow
    def test_writing_metadata_all_dirs_files(self):
        """
        Test multiple directories are processed when -d (directory) and -m are passed.
        Process all sub-dirs of -d.
        """
        config = sample_config()
        with environment(config) as (temp_dir, fake_tpdb, config):
            targets = [new_ea(temp_dir, use_dir=False, post_stem='1'), new_ea(temp_dir, use_dir=False, post_stem='2')]
            main(['-d', str(targets[0].get_file().parent), '-m', '-c', str(config.config_file)])
            output1 = targets[0].get_file().parent / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240].mp4'
            validate_mp4_tags(self, output1)
            output2 = targets[1].get_file().parent / 'Evil Angel - 2022-01-03 - Carmela Clutch Fabulous Anal 3-Way! [WEBDL-240](1).mp4'
            validate_mp4_tags(self, output2)

    def test_set_permissions(self):
        """
        Test set permissions
        """
        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            path = Path(tmpdir)
            test_file = path / 'test_file.txt'
            test_file.write_text('test')
            test_dir = path / 'test_dir'
            test_dir.mkdir()
            config = sample_config()
            if hasattr(os, 'getgroups'):
                config.set_gid = None if len(os.getgroups()) == 0 else os.getgroups()[0]
            if hasattr(os, 'getuid'):
                config.set_uid = os.getuid()
            config.set_dir_permissions = 777
            config.set_file_permissions = 666
            set_permissions(test_file, config)
            self.assertTrue(os.access(test_file, os.R_OK))
            config.set_file_permissions = None
            set_permissions(test_file, config)
            self.assertTrue(os.access(test_file, os.R_OK))
            set_permissions(test_dir, config)
            self.assertTrue(os.access(test_dir, os.R_OK))
            set_permissions(None, config)

    @patch('namer.namer.main')
    @patch('namer.watchdog.main')
    @patch('namer.__main__.default_config')
    def test_main_arg_passing(self: unittest.TestCase, mock_default_config, mock_watchdog_main, mock_namer_main):
        """
        Tests that arguments are passed correctly to sub commands, even with -c
        """
        config = NamerConfig()
        config.config_updater = sample_config().config_updater
        mock_default_config.return_value = config

        with tempfile.TemporaryDirectory(prefix='test') as tmpdir:
            temp_dir = Path(tmpdir)
            config_file = temp_dir / 'config.cfg'
            config_file.write_text('[watchdog]\nport=1234')

            # Test case 1: --config before command
            with patch('sys.argv', ['namer', '--config', str(config_file), 'watchdog']):
                namer_main()
                mock_default_config.assert_called_with(config_file)
                mock_watchdog_main.assert_called_once_with(config)
                mock_namer_main.assert_not_called()

            mock_default_config.reset_mock()
            mock_watchdog_main.reset_mock()
            mock_namer_main.reset_mock()

            # Test case 2: -c after command
            with patch('sys.argv', ['namer', 'watchdog', '-c', str(config_file)]):
                namer_main()
                mock_default_config.assert_called_with(config_file)
                mock_watchdog_main.assert_called_once_with(config)
                mock_namer_main.assert_not_called()

            mock_default_config.reset_mock()
            mock_watchdog_main.reset_mock()
            mock_namer_main.reset_mock()

            # Test case 3: rename command with args
            with patch('sys.argv', ['namer', '-c', str(config_file), 'rename', '-f', 'somefile.mp4']):
                namer_main()
                mock_default_config.assert_called_with(config_file)
                mock_watchdog_main.assert_not_called()
                mock_namer_main.assert_called_once_with(['-f', 'somefile.mp4'])


if __name__ == '__main__':
    unittest.main()
