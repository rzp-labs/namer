"""
Hardware-accelerated pHash tests (optional backends).

These tests validate that enabling GPU decode/scaling paths produces the same pHash
as the baseline software path. Backend-specific tests are conditionally skipped
if the required hardware/driver support is not detected.
"""

import os
import platform
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from loguru import logger

from namer.videophash import imagehash
from namer.videophash.videophash import VideoPerceptualHash
from test import utils
from test.utils import sample_config


def _ffmpeg_has_hwaccel(accel_name: str) -> bool:
    """Return True if 'ffmpeg -hwaccels' lists the given accelerator."""
    try:
        proc = subprocess.run(['ffmpeg', '-hwaccels'], capture_output=True, text=True, check=False)
        out = (proc.stdout or '') + (proc.stderr or '')
        return accel_name.lower() in out.lower()
    except Exception:
        return False


class HWAccelPHashTests(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        if not utils.is_debugging():
            logger.remove()

    def setUp(self):
        # Prepare common inputs
        self.config = sample_config()
        self.generator = VideoPerceptualHash(self.config.ffmpeg)
        self.expected_phash = imagehash.hex_to_hash('88982eebd3552d9c')
        self.expected_oshash = 'ae547a6b1d8488bc'
        self.expected_duration = 30

        self.tmpdir = tempfile.TemporaryDirectory(prefix='test')
        self.temp_dir_path = Path(self.tmpdir.name)
        shutil.copytree(Path(__file__).resolve().parent, self.temp_dir_path / 'test')
        self.sample_file = self.temp_dir_path / 'test' / 'Site.22.01.01.painful.pun.XXX.720p.xpost.mp4'

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_phash_gpu_auto(self):
        """
        Validate pHash using use_gpu=True with automatic backend selection (no hard requirement).
        Should match the baseline pHash even if ffmpeg falls back to software.
        """
        res = self.generator.get_hashes(
            self.sample_file,
            use_gpu=True,
            hwaccel_backend='auto',
            hwaccel_device=None,
            hwaccel_decoder=None,
        )
        self.assertIsNotNone(res)
        if res:
            self.assertEqual(res.phash, self.expected_phash)
            self.assertEqual(res.oshash, self.expected_oshash)
            self.assertEqual(res.duration, self.expected_duration)

    @unittest.skipUnless(_ffmpeg_has_hwaccel('qsv'), 'QSV hwaccel not available')
    def test_phash_gpu_qsv_if_available(self):
        """
        Validate pHash via Intel QSV decode/scaling if available. Requires ffmpeg with QSV support
        and access to a QSV device (may not be present in most CI/macOS environments).
        """
        # Optional device path can be provided via env; skip if known device path is missing
        device = os.environ.get('QSV_DEVICE', '/dev/dri/renderD128')
        if platform.system() != 'Linux' or not Path(device).exists():
            self.skipTest('QSV device path not available')

        # Prefer a QSV decoder if present; otherwise let ffmpeg decide
        decoder = os.environ.get('QSV_DECODER')  # e.g., 'h264_qsv'
        res = self.generator.get_hashes(
            self.sample_file,
            use_gpu=True,
            hwaccel_backend='qsv',
            hwaccel_device=device,
            hwaccel_decoder=decoder,
        )
        self.assertIsNotNone(res)
        if res:
            self.assertEqual(res.phash, self.expected_phash)
            self.assertEqual(res.oshash, self.expected_oshash)
            self.assertEqual(res.duration, self.expected_duration)

    @unittest.skipUnless(_ffmpeg_has_hwaccel('videotoolbox'), 'videotoolbox hwaccel not available')
    def test_phash_gpu_videotoolbox_if_available(self):
        """
        Validate pHash via Apple's VideoToolbox on macOS if available.
        """
        if platform.system() != 'Darwin':
            self.skipTest('VideoToolbox test only applicable on macOS')

        # Decoder hint for macOS (if ffmpeg supports it); this is optional
        decoder = os.environ.get('VTB_DECODER', 'h264_videotoolbox')
        try:
            res = self.generator.get_hashes(
                self.sample_file,
                use_gpu=True,
                hwaccel_backend='videotoolbox',
                hwaccel_device=None,
                hwaccel_decoder=decoder,
            )
        except Exception as e:
            # Some environments expose VideoToolbox but cannot use it due to sandboxing/permissions/build flags
            self.skipTest(f'videotoolbox present but unusable: {e}')

        self.assertIsNotNone(res)
        if res:
            self.assertEqual(res.phash, self.expected_phash)
            self.assertEqual(res.oshash, self.expected_oshash)
            self.assertEqual(res.duration, self.expected_duration)
