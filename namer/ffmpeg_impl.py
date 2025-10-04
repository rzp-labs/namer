"""
Core FFmpeg integration shared by `namer.ffmpeg` (development entrypoint)
and `namer.ffmpeg_enhanced` (production entrypoint).

All behavioural logic for the `FFMpeg` wrapper lives here to avoid the
historical duplication between those two modules. Any changes to hardware
acceleration, probing, or screenshot extraction should be made in this file so
that both entrypoints stay in sync automatically.

See the thin wrappers in `namer.ffmpeg` and `namer.ffmpeg_enhanced` for
context on how this module is consumed.
"""

from __future__ import annotations

import os
import secrets
import shutil
import string
import subprocess  # nosec: trusted invocations with shell disabled
import re
from contextlib import suppress
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Tuple

import ffmpeg
from loguru import logger
from PIL import Image
# from pathvalidate import ValidationError  # Not needed, using ValueError instead

from namer.videophash.videophashstash import StashVideoPerceptualHash

from namer.ffmpeg_common import QSVCodecMapper, FFProbeStream, FFProbeFormat, FFProbeResults

__all__ = ['FFMpeg']


class FFMpeg:
    """
    FFmpeg interface with hardware acceleration support.
    """

    __local_dir: Optional[Path] = None
    __ffmpeg_cmd: str = 'ffmpeg'
    __ffprobe_cmd: str = 'ffprobe'
    # Log throttling for repeated GPU fallback warnings: warn once per (backend, file), else debug
    __gpu_warned_keys: set = set()
    __gpu_warned_lock: Lock = Lock()
    # Cache a working VAAPI render node across calls
    __vaapi_device_cached: Optional[str] = None
    __vaapi_lock: Lock = Lock()

    def __init__(self):
        versions = self.__ffmpeg_version()
        if not versions['ffmpeg'] or not versions['ffprobe']:
            home_path: Path = Path(__file__).parent
            phash_path: Path = home_path / 'tools'
            if not phash_path.is_dir():
                phash_path.mkdir(exist_ok=True, parents=True)

            self.__local_dir = phash_path
            versions = self.__ffmpeg_version(phash_path)
            if not versions['ffmpeg'] and not versions['ffprobe']:
                StashVideoPerceptualHash().install_ffmpeg()

            versions = self.__ffmpeg_version(phash_path)
            if not versions['ffmpeg'] and not versions['ffprobe']:
                raise ValueError(f'could not find ffmpeg/ffprobe on path, or in tools dir: {self.__local_dir}')

            self.__ffmpeg_cmd = str(phash_path / 'ffmpeg')
            self.__ffprobe_cmd = str(phash_path / 'ffprobe')

    @logger.catch
    def ffprobe(self, file: Path) -> Optional[FFProbeResults]:
        """
        Get the typed results of probing a video stream with ffprobe.
        """

        stat = file.stat()
        return self._ffprobe(file, stat.st_size, stat.st_mtime)

    @lru_cache(maxsize=1024)  # noqa: B019
    def _ffprobe(self, file: Path, file_size: int, file_update: float) -> Optional[FFProbeResults]:
        """
        Get the typed results of probing a video stream with ffprobe.
        """

        logger.info(f'ffprobe file "{file}"')
        ffprobe_out = None
        with suppress(Exception):
            ffprobe_out = ffmpeg.probe(file, self.__ffprobe_cmd)

        if not ffprobe_out:
            return None

        streams = [stream for stream in ffprobe_out['streams'] if stream['codec_type'] in ('video', 'audio')]
        if not streams:
            return None

        output = []
        for stream in streams:
            ff_stream = FFProbeStream()
            ff_stream.bit_rate = -1
            bit_rate = stream.get('bit_rate')
            if bit_rate is not None:
                try:
                    ff_stream.bit_rate = int(bit_rate)
                except (TypeError, ValueError):
                    logger.debug('Unable to parse stream bit_rate: %s', bit_rate)
            ff_stream.codec_name = stream['codec_name']
            ff_stream.codec_type = stream['codec_type']
            ff_stream.index = int(stream['index'])
            ff_stream.duration = -1
            duration = stream.get('duration')
            if duration is not None:
                try:
                    ff_stream.duration = float(duration)
                except (TypeError, ValueError):
                    logger.debug('Unable to parse stream duration: %s', duration)
            ff_stream.height = -1
            height = stream.get('height')
            if height is not None:
                try:
                    ff_stream.height = int(height)
                except (TypeError, ValueError):
                    logger.debug('Unable to parse stream height: %s', height)
            ff_stream.width = -1
            width = stream.get('width')
            if width is not None:
                try:
                    ff_stream.width = int(width)
                except (TypeError, ValueError):
                    logger.debug('Unable to parse stream width: %s', width)
            tags = stream.get('tags') or {}
            ff_stream.tags_language = tags.get('language')

            if 'disposition' in stream:
                ff_stream.disposition_attached_pic = stream['disposition']['attached_pic'] == 1
                ff_stream.disposition_default    = stream['disposition']['default']    == 1

            if 'avg_frame_rate' in stream:
                numer, denom = stream['avg_frame_rate'].split('/', 1)
                numer, denom = int(numer), int(denom)
                if numer != 0 and denom != 0:
                    ff_stream.avg_frame_rate = numer / denom

            output.append(ff_stream)

        # Process format information
        format_info = ffprobe_out.get('format', {})
        ff_format = FFProbeFormat()
        ff_format.duration = -1
        duration = format_info.get('duration')
        if duration is not None:
            try:
                ff_format.duration = float(duration)
            except (TypeError, ValueError):
                logger.debug('Unable to parse format duration: %s', duration)
        
        ff_format.size = -1
        size = format_info.get('size')
        if size is not None:
            try:
                ff_format.size = int(size)
            except (TypeError, ValueError):
                logger.debug('Unable to parse format size: %s', size)
        
        ff_format.bit_rate = -1
        bit_rate = format_info.get('bit_rate')
        if bit_rate is not None:
            try:
                ff_format.bit_rate = int(bit_rate)
            except (TypeError, ValueError):
                logger.debug('Unable to parse format bit_rate: %s', bit_rate)
        
        ff_format.tags = format_info.get('tags', {})

        return FFProbeResults(output, ff_format)

    def _auto_detect_qsv_decoder(self, file: Path) -> Optional[str]:
        """
        Automatically detect the best QSV decoder for the video file by analyzing its codec.
        """

        try:
            probe_result = self.ffprobe(file)
            if not probe_result:
                return None

            video_stream = probe_result.get_default_video_stream()
            if not video_stream:
                return None

            codec_name = video_stream.codec_name
            qsv_decoder = QSVCodecMapper.get_qsv_decoder(codec_name)

            if qsv_decoder:
                logger.debug(f"Auto-detected QSV decoder for {file}: {codec_name} -> {qsv_decoder}")
                return qsv_decoder

            logger.debug(f"No QSV decoder available for codec: {codec_name}")
            return None
        except Exception as ex:
            logger.debug(f"Failed to auto-detect QSV decoder for {file}: {ex}")
            return None

    def _get_gpu_settings_from_env(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get GPU device and backend settings from environment variables set by the GPU detection script.
        Returns (device_path, backend) tuple.
        """

        device = os.environ.get('NAMER_GPU_DEVICE')
        backend = os.environ.get('NAMER_GPU_BACKEND')

        if device and backend:
            logger.debug(f"Using GPU settings from environment: device={device}, backend={backend}")
            return device, backend

        logger.debug('No GPU settings found in environment variables')
        return None, None

    def get_audio_stream_for_lang(self, file: Path, language: str) -> int:
        """
        given a mp4 input file and a desired language will return the stream position of that language in the mp4.
        if the language is None, or the stream is not found, or the desired stream is the only default no action is
        taken, no streams (audio/video) are re-encoded.  See: https://iso639-3.sil.org/code_tables/639/data/

        Returns -1 if stream can not be determined
        """

        stream_index = -1
        probe = self.ffprobe(file)
        if probe:
            stream = probe.get_audio_stream(language)
            if stream:
                stream_index = stream.index - 1 if not stream.disposition_default else -1

        return stream_index

    def update_audio_stream_if_needed(self, mp4_file: Path, language: Optional[str]) -> bool:
        """
        Returns true if the file had to be edited to have a default audio stream equal to the desired language,
        mostly a concern for apple players (Quicktime/Apple TV/etc.)
        Copies, and potentially updates the default audio stream of a video file.
        """

        random_suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        temp_filename = f'{mp4_file.stem}_{random_suffix}' + mp4_file.suffix
        work_file = mp4_file.parent / temp_filename

        stream = self.get_audio_stream_for_lang(mp4_file, language) if language else None
        if stream and stream >= 0:
            process = (
                ffmpeg
                .input(mp4_file)
                .output(
                    str(work_file),
                    **{
                        'map': 0,
                        'disposition:a': 'none',
                        f'disposition:a:{stream}': 'default',
                        'c': 'copy',
                    },
                )
                .run_async(quiet=True, cmd=self.__ffmpeg_cmd)
            )

            stdout, stderr = process.communicate()
            stdout, stderr = (
                stdout.decode('UTF-8') if isinstance(stdout, bytes) else stdout,
                stderr.decode('UTF-8') if isinstance(stderr, bytes) else stderr,
            )
            success = process.returncode == 0
            if not success:
                logger.warning('Could not update audio stream for {}', mp4_file)
                if stderr:
                    logger.error(stderr)
            else:
                logger.warning('Return code: {}', process.returncode)
                mp4_file.unlink()
                shutil.move(work_file, mp4_file)

            return success

        return True

    def attempt_fix_corrupt(self, mp4_file: Path) -> bool:
        random_suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        temp_filename = f'{mp4_file.stem}_{random_suffix}' + mp4_file.suffix
        work_file = mp4_file.parent / temp_filename
        success = self.convert(mp4_file, work_file)
        if success:
            shutil.move(work_file, mp4_file)
        return success

    def convert(self, mp4_file: Path, output: Path) -> bool:
        """
        Attempt to fix corrupt mp4 files.
        """

        logger.info('Attempt to fix damaged mp4 file: {}', mp4_file)
        process = (
            ffmpeg
            .input(mp4_file)
            .output(str(output), c='copy')
            .overwrite_output()
            .run_async(quiet=True, cmd=self.__ffmpeg_cmd)
        )
        stdout, stderr = process.communicate()
        stdout, stderr = (
            stdout.decode('UTF-8') if isinstance(stdout, bytes) else stdout,
            stderr.decode('UTF-8') if isinstance(stderr, bytes) else stderr,
        )
        success = process.returncode == 0
        if not success:
            logger.warning('Could not convert/clean {} to {}', mp4_file, output)
            if stderr:
                logger.error(stderr)
        else:
            mp4_file.unlink()
        return success

    def extract_screenshot(
        self,
        file: Path,
        screenshot_time: float,
        screenshot_width: int = -1,
        use_gpu: bool = False,
        hwaccel_backend: Optional[str] = None,
        hwaccel_device: Optional[str] = None,
        hwaccel_decoder: Optional[str] = None,
    ) -> Optional[Image.Image]:
        """
        Extract a single frame as an image with enhanced QSV support and automatic decoder selection.

        Enhanced robust fallback order:
        1. If QSV is available: auto-detect decoder based on codec, try QSV decode+scale
        2. If backend == 'vaapi': try VAAPI (hwupload -> scale_vaapi -> hwdownload -> format)
        3. Software fallback with multiple retry strategies
        """

        def _run_pipeline(stream_builder, global_args_list):
            return (
                stream_builder
                .output('pipe:', vframes=1, format='apng')
                .global_args(*global_args_list)
                .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
            )

        env_device, env_backend = self._get_gpu_settings_from_env()

        final_backend = env_backend or hwaccel_backend
        final_device = env_device or hwaccel_device

        if env_backend:
            use_gpu = True

        backend = (final_backend or '').lower() if final_backend else None
        width = screenshot_width if screenshot_width and screenshot_width > 0 else -1

        if use_gpu and backend == 'qsv':
            try:
                auto_decoder = self._auto_detect_qsv_decoder(file) if not hwaccel_decoder else None
                selected_decoder = hwaccel_decoder or auto_decoder

                if selected_decoder:
                    logger.debug(f"Using QSV decoder: {selected_decoder} for {file}")
                else:
                    logger.debug(f"No QSV decoder specified or auto-detected for {file}, trying generic QSV")

                input_args = {'hwaccel': 'qsv'}
                if selected_decoder:
                    input_args['vcodec'] = selected_decoder

                global_args: List[str] = []
                if final_device:
                    global_args.extend(['-qsv_device', final_device])

                stream = ffmpeg.input(file, ss=screenshot_time, **input_args)

                if width and width > 0:
                    filtered = (
                        stream
                        .filter('scale_qsv', w=width, h=-1)
                        .filter('hwdownload')
                        .filter('format', 'nv12')
                        .filter('format', 'rgb24')
                    )
                    out, _ = (
                        filtered
                        .output('pipe:', vframes=1, format='apng')
                        .global_args(*global_args)
                        .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                    )
                else:
                    filtered = (
                        stream
                        .filter('hwdownload')
                        .filter('format', 'nv12')
                        .filter('format', 'rgb24')
                    )
                    out, _ = (
                        filtered
                        .output('pipe:', vframes=1, format='apng')
                        .global_args(*global_args)
                        .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                    )

                logger.debug(f"QSV decode successful for {file} using decoder: {selected_decoder or 'generic'}")
                return Image.open(BytesIO(out))

            except Exception as ex:
                key_backend = backend or 'none'
                key_device = final_device or 'none'
                key_decoder = hwaccel_decoder or auto_decoder or 'auto'
                key = (key_backend, key_device, str(file))
                first_time = False
                with FFMpeg.__gpu_warned_lock:
                    if key not in FFMpeg.__gpu_warned_keys:
                        FFMpeg.__gpu_warned_keys.add(key)
                        first_time = True

                if first_time:
                    try:
                        import ffmpeg as _ff
                        if isinstance(ex, _ff._run.Error) and getattr(ex, 'stderr', None):
                            err_msg = ex.stderr.decode('utf-8', errors='ignore')
                            err_msg_short = err_msg.strip().split('\n')[-5:]
                            logger.warning(
                                'QSV pipeline (device={}, decoder={}) failed for {}. Falling back to VAAPI/software. Details: {}',
                                key_device,
                                key_decoder,
                                file,
                                '\n'.join(err_msg_short),
                            )
                        else:
                            logger.warning(
                                'QSV pipeline (device={}, decoder={}) failed for {}, falling back to VAAPI/software: {}',
                                key_device,
                                key_decoder,
                                file,
                                ex,
                            )
                    except Exception:
                        logger.warning(
                            'QSV pipeline (device={}, decoder={}) failed for {}, falling back to VAAPI/software: {}',
                            key_device,
                            key_decoder,
                            file,
                            ex,
                        )
                else:
                    logger.debug(
                        'QSV pipeline (device={}, decoder={}) failed for {} (repeat), falling back to VAAPI/software: {}',
                        key_device,
                        key_decoder,
                        file,
                        ex,
                    )

                if selected_decoder == 'av1_qsv' and not hwaccel_decoder:
                    try:
                        logger.debug(f"Retrying QSV without av1_qsv decoder for {file}")
                        input_args_generic = {'hwaccel': 'qsv'}
                        global_args_generic: List[str] = []
                        if final_device:
                            global_args_generic.extend(['-qsv_device', final_device])

                        stream_generic = ffmpeg.input(file, ss=screenshot_time, **input_args_generic)

                        if width and width > 0:
                            filtered_generic = (
                                stream_generic
                                .filter('scale_qsv', w=width, h=-1)
                                .filter('hwdownload')
                                .filter('format', 'rgb24')
                            )
                        else:
                            filtered_generic = (
                                stream_generic
                                .filter('hwdownload')
                                .filter('format', 'rgb24')
                            )

                        out_generic, _ = (
                            filtered_generic
                            .output('pipe:', vframes=1, format='apng')
                            .global_args(*global_args_generic)
                            .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                        )

                        logger.debug(f"QSV decode successful for {file} using generic QSV (av1_qsv fallback)")
                        return Image.open(BytesIO(out_generic))
                    except Exception as ex_generic:
                        logger.debug(f"Generic QSV fallback also failed for {file}: {ex_generic}")

        if use_gpu and (backend == 'vaapi' or backend == 'qsv'):
            try:
                def _try_device(device: Optional[str]) -> Optional[bytes]:
                    ga: List[str] = []
                    if device:
                        ga.extend(['-vaapi_device', device])
                    stream_local = ffmpeg.input(file, ss=screenshot_time)
                    filt_local = stream_local.filter('hwupload')
                    if width and width > 0:
                        filt_local = filt_local.filter('scale_vaapi', width, -2)
                    filt_local = filt_local.filter('hwdownload').filter('format', 'rgb24')
                    out_bytes, _err = (
                        filt_local
                        .output('pipe:', vframes=1, format='image2', vcodec='png', update=1)
                        .global_args(*ga)
                        .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                    )
                    return out_bytes

                candidates: List[Optional[str]] = []
                if final_device:
                    candidates.append(final_device)
                with FFMpeg.__vaapi_lock:
                    if FFMpeg.__vaapi_device_cached and FFMpeg.__vaapi_device_cached not in candidates:
                        candidates.append(FFMpeg.__vaapi_device_cached)
                try:
                    dri_path = Path('/dev/dri')
                    if dri_path.exists():
                        for p in sorted(dri_path.glob('renderD*')):
                            s = str(p)
                            if s not in candidates:
                                candidates.append(s)
                except Exception as render_discovery_error:
                    logger.debug('Failed enumerating /dev/dri render nodes: %s', render_discovery_error)

                last_ex: Optional[Exception] = None
                for dev in candidates:
                    try:
                        out = _try_device(dev)
                        if out:
                            if dev:
                                with FFMpeg.__vaapi_lock:
                                    FFMpeg.__vaapi_device_cached = dev
                            logger.debug(f"VAAPI decode successful for {file} using device: {dev}")
                            return Image.open(BytesIO(out))
                    except Exception as ex2:
                        last_ex = ex2
                        logger.debug('VAAPI candidate %s failed for %s: %s', dev, file, ex2)
                        continue
                if last_ex:
                    raise last_ex

            except Exception as ex:
                key_backend = 'vaapi'
                key_device = final_device or 'none'
                key = (key_backend, key_device, str(file))
                first_time = False
                with FFMpeg.__gpu_warned_lock:
                    if key not in FFMpeg.__gpu_warned_keys:
                        FFMpeg.__gpu_warned_keys.add(key)
                        first_time = True

                if first_time:
                    logger.warning('VAAPI pipeline failed for {}, falling back to software: {}', file, ex)
                else:
                    logger.debug('VAAPI pipeline failed for {} (repeat), falling back to software: {}', file, ex)

        try:
            stream_sw = ffmpeg.input(file, ss=screenshot_time)
            if width and width > 0:
                stream_sw = stream_sw.filter('scale', width, -2)

            stream_sw = stream_sw.filter('format', 'rgb24')
            out, _err = _run_pipeline(stream_sw, [])
            try:
                return Image.open(BytesIO(out))
            except Exception as pil_ex:
                raise pil_ex
        except Exception as ex:
            try:
                import ffmpeg as _ff
                if isinstance(ex, _ff._run.Error) and getattr(ex, 'stderr', None):
                    err_msg = ex.stderr.decode('utf-8', errors='ignore')
                    err_tail = '\n'.join(err_msg.strip().split('\n')[-5:])
                    logger.error('Software pipeline failed for {} at t={}s. Details: {}', file, screenshot_time, err_tail)
                else:
                    logger.error('Software pipeline failed for {} at t={}s: {}', file, screenshot_time, ex)
            except Exception:
                logger.error('Software pipeline failed for {} at t={}s: {}', file, screenshot_time, ex)
            try:
                stream_sw2 = ffmpeg.input(file, ss=screenshot_time)
                if width and width > 0:
                    stream_sw2 = stream_sw2.filter('scale', width, -2)
                stream_sw2 = stream_sw2.filter('format', 'rgb24')
                out2, _err2 = (
                    stream_sw2
                    .output('pipe:', vframes=1, format='image2', vcodec='png', update=1)
                    .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                )
                try:
                    return Image.open(BytesIO(out2))
                except Exception as pil_ex2:
                    raise pil_ex2
            except Exception as ex2:
                try:
                    import ffmpeg as _ff
                    if isinstance(ex2, _ff._run.Error) and getattr(ex2, 'stderr', None):
                        err_msg2 = ex2.stderr.decode('utf-8', errors='ignore')
                        err_tail2 = '\n'.join(err_msg2.strip().split('\n')[-5:])
                        logger.error('Software PNG fallback failed for {} at t={}s. Details: {}', file, screenshot_time, err_tail2)
                    else:
                        logger.error('Software PNG fallback failed for {} at t={}s: {}', file, screenshot_time, ex2)
                except Exception as png_fallback_ex:
                    logger.debug('Software PNG fallback failed for %s at t=%s: %s', file, screenshot_time, png_fallback_ex)
            try:
                stream_sw3 = ffmpeg.input(file)
                if width and width > 0:
                    stream_sw3 = stream_sw3.filter('scale', width, -2)
                stream_sw3 = stream_sw3.filter('format', 'rgb24')
                out3, _err3 = (
                    stream_sw3
                    .output('pipe:', vframes=1, ss=screenshot_time, format='apng')
                    .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                )
                return Image.open(BytesIO(out3))
            except Exception as post_seek_ex:
                logger.debug('Post-seek APNG fallback failed for %s at t=%s: %s', file, screenshot_time, post_seek_ex)
                try:
                    stream_sw4 = ffmpeg.input(file)
                    if width and width > 0:
                        stream_sw4 = stream_sw4.filter('scale', width, -2)
                    stream_sw4 = stream_sw4.filter('format', 'rgb24')
                    out4, _err4 = (
                        stream_sw4
                        .output('pipe:', vframes=1, ss=screenshot_time, format='image2', vcodec='png')
                        .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                    )
                    return Image.open(BytesIO(out4))
                except Exception as png_post_seek_ex:
                    logger.debug('Post-seek PNG fallback failed for %s at t=%s: %s', file, screenshot_time, png_post_seek_ex)
            for delta in (-0.25, 0.25, -0.5, 0.5):
                t2 = max(0.0, (screenshot_time or 0.0) + delta)
                try:
                    stream_sw5 = ffmpeg.input(file)
                    if width and width > 0:
                        stream_sw5 = stream_sw5.filter('scale', width, -2)
                    stream_sw5 = stream_sw5.filter('format', 'rgb24')
                    out5, _err5 = (
                        stream_sw5
                        .output('pipe:', vframes=1, ss=t2, format='image2', vcodec='png')
                        .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                    )
                    return Image.open(BytesIO(out5))
                except Exception as jitter_ex:
                    logger.debug('Timestamp jitter fallback failed for %s at t=%s (delta=%s): %s', file, t2, delta, jitter_ex)
            return None

    def ffmpeg_version(self) -> Dict:
        return self.__ffmpeg_version(self.__local_dir)

    @staticmethod
    def __ffmpeg_version(local_dir: Optional[Path] = None) -> Dict:
        tools = ['ffmpeg', 'ffprobe']
        re_tools = '|'.join(tools)
        reg = re.compile(rf'({re_tools}) version (?P<version>.*) Copyright')

        versions = {}

        for tool in tools:
            executable = local_dir / tool if local_dir else tool
            args = [str(executable), '-version']

            matches = None
            try:
                completed = subprocess.run(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    check=False,
                    shell=False,
                )
            except Exception as error:
                logger.debug('Failed to query %s version via %s: %s', tool, executable, error)
            else:
                if completed.stdout:
                    line = completed.stdout.split('\n', 1)[0]
                    matches = reg.search(line)

            versions[tool] = matches.groupdict().get('version') if matches else None

        return versions
