import platform
import tempfile
import os
import subprocess  # nosec B404: fixed binary path, shell disabled
from functools import lru_cache
from pathlib import Path
from typing import Optional

import orjson
from loguru import logger
from orjson import JSONDecodeError

from namer.videophash import PerceptualHash, return_perceptual_hash


class StashVideoPerceptualHash:
    __home_path: Path = Path(__file__).parent.parent
    __phash_path: Path = __home_path / 'tools'
    __phash_name: str = 'videohashes'
    __supported_arch: dict = {
        'amd64': 'amd64',
        'x86_64': 'amd64',
        'arm64': 'arm64',
        'aarch64': 'arm64',
        'arm': 'arm',
    }
    __phash_suffixes: dict = {
        'windows': '.exe',
        'linux': '-linux',
        'darwin': '-macos',
    }

    def __init__(self):
        if not self.__phash_path.is_dir():
            try:
                self.__phash_path.mkdir(exist_ok=True, parents=True)
            except PermissionError:
                # Fall back to a user-writable location when site-packages is read-only
                # 1) Prefer a user-specific tmp dir to avoid collisions with restrictive parents
                uid = os.getuid() if hasattr(os, 'getuid') else 0
                tmp_fallback = Path(tempfile.gettempdir()) / f'namer-{uid}' / 'tools'
                try:
                    tmp_fallback.mkdir(exist_ok=True, parents=True)
                    self.__phash_path = tmp_fallback
                except PermissionError:
                    # 2) Final fallback: user's cache directory
                    home_cache = Path.home() / '.cache' / 'namer' / 'tools'
                    home_cache.mkdir(exist_ok=True, parents=True)
                    self.__phash_path = home_cache

        system = platform.system().lower()
        arch = platform.machine().lower()
        if arch not in self.__supported_arch.keys():
            raise SystemError(f'Unsupported architecture error {arch}')

        self.__phash_name += '-' + self.__supported_arch[arch] + self.__phash_suffixes[system]

    def install_ffmpeg(self) -> None:
        # videohasher installs ffmpeg next to itself by default, even if
        # there's nothing to process.
        self.__execute_stash_phash()

    def get_hashes(self, file: Path, **kwargs) -> Optional[PerceptualHash]:
        stat = file.stat()
        return self._get_stash_phash(file, stat.st_size, stat.st_mtime)

    @lru_cache(maxsize=1024)  # noqa: B019
    def _get_stash_phash(self, file: Path, file_size: int, file_update: float) -> Optional[PerceptualHash]:
        logger.info(f'Calculating phash for file "{file}"')
        return self.__execute_stash_phash(file)

    def __execute_stash_phash(self, file: Optional[Path] = None) -> Optional[PerceptualHash]:
        output = None
        if not self.__phash_path:
            return output

        args = [
            str(self.__phash_path / self.__phash_name),
            '-json',
        ]

        if file:
            # fmt: off
            args.extend([
                '--video', str(file)
            ])

        try:
            completed = subprocess.run(  # nosec B603: fixed executable path without user input
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                shell=False,
            )
        except Exception as error:  # pragma: no cover - defensive logging
            logger.error('Failed to execute videohash binary %s: %s', args[0], error)
            return output

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()

        if completed.returncode == 0:
            data = None
            try:
                data = orjson.loads(stdout)
            except JSONDecodeError:
                logger.error(stdout)

            if data:
                output = return_perceptual_hash(data['duration'], data['phash'], data['oshash'])
        else:
            logger.error('videohash execution failed (%s): %s', completed.returncode, stderr)

        return output
