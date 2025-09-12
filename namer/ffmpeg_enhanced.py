"""
Enhanced ffmpeg module with automatic QSV decoder selection and robust hardware acceleration fallback.
This module extends the original ffmpeg.py with intelligent codec detection and QSV decoder mapping.

⚠️  CRITICAL MAINTENANCE WARNING ⚠️

This file (ffmpeg_enhanced.py) is the PRODUCTION VERSION used in Docker containers!
During container builds, THIS FILE REPLACES ffmpeg.py (see Dockerfile line 77).

🚀 CONTAINER BUILD PROCESS:
   Dockerfile: COPY namer/ffmpeg_enhanced.py /work/namer/ffmpeg.py
   Result: This enhanced version becomes the active ffmpeg.py in containers

🔧 WHEN MAKING CHANGES TO THIS FILE:
   1. Apply the SAME changes to namer/ffmpeg.py (for local development)
   2. Test both files to ensure they work identically
   3. This file takes precedence in production containers

🔄 DUAL FILE SYNCHRONIZATION REQUIRED:
   - ffmpeg.py = Development/local version
   - ffmpeg_enhanced.py = Production/container version (THIS FILE)
   - Both must be kept in sync for consistent behavior

ℹ️ PURPOSE: This enhanced version includes optimizations for:
   - Intel GPU hardware acceleration (QSV)
   - Advanced codec detection and mapping
   - Robust fallback chains for different hardware configurations

📖 See FFMPEG_DUAL_FILE_MAINTENANCE.md for complete maintenance guidelines.
"""

import os
import subprocess
from contextlib import suppress
from dataclasses import dataclass
import shutil
import string
import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from random import choices
from typing import Dict, List, Optional, Tuple
from threading import Lock

import ffmpeg
import orjson
from loguru import logger
from PIL import Image
from pathvalidate import ValidationError

from namer.videophash.videophashstash import StashVideoPerceptualHash


class QSVCodecMapper:
    """Maps video codecs to their corresponding QSV decoders."""
    
    # Mapping of codec names to QSV decoder names
    CODEC_TO_QSV_DECODER = {
        'h264': 'h264_qsv',
        'hevc': 'hevc_qsv', 
        'h265': 'hevc_qsv',  # alias for hevc
        'av1': 'av1_qsv',
        'vp9': 'vp9_qsv',
        'vp8': 'vp8_qsv',
        'mpeg2': 'mpeg2_qsv',
        'mpeg2video': 'mpeg2_qsv',
        'vc1': 'vc1_qsv',
        'mjpeg': 'mjpeg_qsv',
    }
    
    @classmethod
    def get_qsv_decoder(cls, codec_name: str) -> Optional[str]:
        """Get the appropriate QSV decoder for a given codec."""
        if not codec_name:
            return None
        return cls.CODEC_TO_QSV_DECODER.get(codec_name.lower())
    
    @classmethod
    def is_qsv_supported(cls, codec_name: str) -> bool:
        """Check if a codec has QSV support."""
        return codec_name.lower() in cls.CODEC_TO_QSV_DECODER


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FFProbeStream:
    index: int  # stream number
    codec_name: str  # "mp3", "h264", "hvec", "png"
    codec_type: str  # "audio" or "video"
    disposition_default: bool  # default stream of this type
    disposition_attached_pic: bool  # is the "video" stream an attached picture.
    duration: float  # seconds
    bit_rate: int  # bitrate of the track
    # audio
    tags_language: Optional[str]  # 3 letters representing language of track (only matters for audio)
    # video only
    width: Optional[int] = None
    height: Optional[int] = None  # 720 1080 2160
    avg_frame_rate: Optional[float] = None  # average frames per second

    def __str__(self) -> str:
        data = self.to_dict()
        return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode('UTF-8')

    def to_dict(self) -> dict:
        data = {
            'codec_name': self.codec_name,
            'width': self.width,
            'height': self.height,
            'codec_type': self.codec_type,
            'framerate': self.avg_frame_rate,
            'duration': self.duration,
            'disposition_default': self.disposition_default,
        }
        return data

    def is_audio(self) -> bool:
        return self.codec_type == 'audio'

    def is_video(self) -> bool:
        return self.codec_type == 'video' and (not self.disposition_attached_pic or self.disposition_attached_pic is False)


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FFProbeFormat:
    duration: float
    size: int
    bit_rate: int
    tags: Dict[str, str]


@dataclass(init=False, repr=False, eq=True, order=False, unsafe_hash=True, frozen=False)
class FFProbeResults:
    __results: List[FFProbeStream]
    __format: FFProbeFormat

    def __init__(self, data: List[FFProbeStream], probe_format: FFProbeFormat):
        self.__results = data
        self.__format = probe_format

    def get_default_video_stream(self) -> Optional[FFProbeStream]:
        for result in self.__results:
            if result.is_video() and result.disposition_default:
                return result
        return None

    def get_default_audio_stream(self) -> Optional[FFProbeStream]:
        for result in self.__results:
            if result.is_audio() and result.disposition_default:
                return result
        return None

    def get_audio_stream(self, language_code: str) -> Optional[FFProbeStream]:
        for result in self.__results:
            if result.is_audio() and result.tags_language == language_code:
                return result
        return None

    def get_all_streams(self) -> List[FFProbeStream]:
        return self.__results

    def get_format(self) -> FFProbeFormat:
        return self.__format

    def get_resolution(self) -> Optional[int]:
        stream = self.get_default_video_stream()
        if stream:
            return stream.height if stream.height else 0
        return None


class FFMpeg:
    """
    FFmpeg interface with hardware acceleration support.
    
    ⚠️  PRODUCTION VERSION - DUAL-FILE MAINTENANCE WARNING:
    This is the CONTAINER PRODUCTION version! Any changes here should also
    be applied to the base ffmpeg.py for local development consistency.
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
                raise ValidationError(f'could not find ffmpeg/ffprobe on path, or in tools dir: {self.__local_dir}')

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

        output: List[FFProbeStream] = []
        for stream in streams:
            ff_stream = FFProbeStream()
            ff_stream.bit_rate = int(stream['bit_rate']) if 'bit_rate' in stream else -1
            ff_stream.codec_name = stream['codec_name']
            ff_stream.codec_type = stream['codec_type']
            ff_stream.index = int(stream['index'])
            ff_stream.duration = float(stream['duration']) if 'duration' in stream else -1

            ff_stream.height = int(stream['height']) if 'height' in stream else -1
            ff_stream.width = int(stream['width']) if 'width' in stream else -1
            ff_stream.tags_language = stream['tags']['language'] if 'tags' in stream and 'language' in stream['tags'] else None

            if 'disposition' in stream:
                ff_stream.disposition_attached_pic = stream['disposition']['attached_pic'] == 1
                ff_stream.disposition_default = stream['disposition']['default'] == 1

            if 'avg_frame_rate' in stream:
                numer, denom = stream['avg_frame_rate'].split('/', 2)
                numer, denom = int(numer), int(denom)
                if numer != 0 and denom != 0:
                    ff_stream.avg_frame_rate = numer / denom

            output.append(ff_stream)

        probe_format = FFProbeFormat()
        if 'format' in ffprobe_out:
            probe_format.bit_rate = int(ffprobe_out['format']['bit_rate'])
            probe_format.duration = float(ffprobe_out['format']['duration'])
            probe_format.size = int(ffprobe_out['format']['size'])
            probe_format.tags = ffprobe_out['format']['tags'] if 'tags' in ffprobe_out['format'] else {}

        return FFProbeResults(output, probe_format)

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
            else:
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
        else:
            logger.debug("No GPU settings found in environment variables")
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

        random = ''.join(choices(population=string.ascii_uppercase + string.digits, k=10))
        temp_filename = f'{mp4_file.stem}_{random}' + mp4_file.suffix
        work_file = mp4_file.parent / temp_filename

        stream = self.get_audio_stream_for_lang(mp4_file, language) if language else None
        if stream and stream >= 0:
            # fmt: off
            process = (
                ffmpeg
                .input(mp4_file)
                .output(str(work_file), **{
                    'map': 0,  # copy all stream
                    'disposition:a': 'none',  # mark all audio streams as not default
                    f'disposition:a:{stream}': 'default',  # mark this audio stream as default
                    'c': 'copy'  # don't re-encode anything.
                })
                .run_async(quiet=True, cmd=self.__ffmpeg_cmd)
            )

            stdout, stderr = process.communicate()
            stdout, stderr = (stdout.decode('UTF-8') if isinstance(stdout, bytes) else stdout), (stderr.decode('UTF-8') if isinstance(stderr, bytes) else stderr)
            success = process.returncode == 0
            if not success:
                logger.warning("Could not update audio stream for {}", mp4_file)
                if stderr:
                    logger.error(stderr)
            else:
                logger.warning("Return code: {}", process.returncode)
                mp4_file.unlink()
                shutil.move(work_file, mp4_file)

            return success

        return True

    def attempt_fix_corrupt(self, mp4_file: Path) -> bool:
        random = ''.join(choices(population=string.ascii_uppercase + string.digits, k=10))
        temp_filename = f'{mp4_file.stem}_{random}' + mp4_file.suffix
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
        # fmt: off
        process = (
            ffmpeg
            .input(mp4_file)
            .output(str(output), c='copy')
            .overwrite_output()
            .run_async(quiet=True, cmd=self.__ffmpeg_cmd)
        )
        stdout, stderr = process.communicate()
        stdout, stderr = (stdout.decode('UTF-8') if isinstance(stdout, bytes) else stdout), (stderr.decode('UTF-8') if isinstance(stderr, bytes) else stderr)
        success = process.returncode == 0
        if not success:
            logger.warning("Could not convert/clean {} to {}", mp4_file, output)
            if stderr:
                logger.error(stderr)
        else:
            mp4_file.unlink()
        return success

    def extract_screenshot(self, file: Path, screenshot_time: float, screenshot_width: int = -1, use_gpu: bool = False,
                           hwaccel_backend: Optional[str] = None, hwaccel_device: Optional[str] = None,
                           hwaccel_decoder: Optional[str] = None) -> Image.Image:
        """
        Extract a single frame as an image with enhanced QSV support and automatic decoder selection.

        ⚠️  PRODUCTION VERSION - DUAL-FILE MAINTENANCE WARNING:
        This method contains critical hardware acceleration fixes that MUST be synchronized
        between ffmpeg.py (base) and ffmpeg_enhanced.py (THIS FILE - production).
        This version is used in Docker containers!

        Enhanced robust fallback order:
        1. If QSV is available: auto-detect decoder based on codec, try QSV decode+scale
        2. If backend == 'vaapi': try VAAPI (hwupload -> scale_vaapi -> hwdownload -> format)  
        3. Software fallback with multiple retry strategies
        """
        def _run_pipeline(stream_builder, global_args_list):
            return (
                stream_builder
                # Use APNG for backward-compatible image bytes (preserves historical phash baseline)
                .output('pipe:', vframes=1, format='apng')
                .global_args(*global_args_list)
                .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
            )

        # Normalize inputs and get environment-based GPU settings
        env_device, env_backend = self._get_gpu_settings_from_env()
        
        # Use environment settings if available, otherwise fall back to parameters
        final_backend = env_backend or hwaccel_backend
        final_device = env_device or hwaccel_device
        
        # Override use_gpu based on environment
        if env_backend:
            use_gpu = True
            
        backend = (final_backend or '').lower() if final_backend else None
        width = screenshot_width if screenshot_width and screenshot_width > 0 else -1

        # 1) Attempt QSV with auto-detected decoder (highest priority)
        if use_gpu and backend == 'qsv':
            try:
                # Auto-detect the best decoder for this video's codec
                auto_decoder = self._auto_detect_qsv_decoder(file) if not hwaccel_decoder else None
                selected_decoder = hwaccel_decoder or auto_decoder
                
                if selected_decoder:
                    logger.debug(f"Using QSV decoder: {selected_decoder} for {file}")
                else:
                    logger.debug(f"No QSV decoder specified or auto-detected for {file}, trying generic QSV")
                
                input_args = {'hwaccel': 'qsv'}
                if selected_decoder:
                    input_args['vcodec'] = selected_decoder

                global_args = []
                if final_device:
                    global_args.extend(['-qsv_device', final_device])

                # Build input
                stream = ffmpeg.input(file, ss=screenshot_time, **input_args)

                # Prefer QSV scale when a width is provided, with proper format conversion
                if width and width > 0:
                    # QSV decode -> QSV scale (maintaining aspect ratio) -> download to system memory -> format conversion -> encode
                    # Fix: Use named parameters to avoid colon escaping issues in ffmpeg-python
                    # ⚠️  CRITICAL: This fix must be mirrored in base ffmpeg.py!
                    # For QSV, we need to use -1 for aspect ratio since -2 is not supported
                    filtered = stream.filter('scale_qsv', w=width, h=-1).filter('hwdownload').filter('format', 'nv12')
                    out, _ = (
                        filtered
                        .output('pipe:', vframes=1, format='image2', vcodec='png', update=1)  # ⚠️  Mirror in ffmpeg.py!
                        .global_args(*global_args)
                        .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                    )
                else:
                    # QSV decode -> download to system memory -> format conversion -> encode 
                    filtered = stream.filter('hwdownload').filter('format', 'nv12')
                    out, _ = (
                        filtered
                        .output('pipe:', vframes=1, format='image2', vcodec='png', update=1)
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
                    # Try to include stderr if present on ffmpeg Error
                    try:
                        import ffmpeg as _ff
                        if isinstance(ex, _ff._run.Error) and getattr(ex, 'stderr', None):
                            err_msg = ex.stderr.decode('utf-8', errors='ignore')
                            err_msg_short = err_msg.strip().split('\n')[-5:]
                            logger.warning('QSV pipeline (device={}, decoder={}) failed for {}. Falling back to VAAPI/software. Details: {}',
                                           key_device, key_decoder, file, '\n'.join(err_msg_short))
                        else:
                            logger.warning('QSV pipeline (device={}, decoder={}) failed for {}, falling back to VAAPI/software: {}',
                                           key_device, key_decoder, file, ex)
                    except Exception:
                        logger.warning('QSV pipeline (device={}, decoder={}) failed for {}, falling back to VAAPI/software: {}',
                                       key_device, key_decoder, file, ex)
                else:
                    logger.debug('QSV pipeline (device={}, decoder={}) failed for {} (repeat), falling back to VAAPI/software: {}',
                                 key_device, key_decoder, file, ex)

        # 2) Attempt VAAPI fallback (if QSV failed or if VAAPI was explicitly requested)
        if use_gpu and (backend == 'vaapi' or backend == 'qsv'):  # Also try VAAPI if QSV failed
            try:
                # VAAPI: software decode, GPU scale. If configured device fails, try autodiscovery of /dev/dri/renderD*.

                def _try_device(device: Optional[str]) -> Optional[bytes]:
                    ga = []
                    if device:
                        ga.extend(['-vaapi_device', device])
                    stream_local = ffmpeg.input(file, ss=screenshot_time)
                    filt_local = stream_local.filter('hwupload')
                    if width and width > 0:
                        filt_local = filt_local.filter('scale_vaapi', width, -2)
                    filt_local = filt_local.filter('hwdownload').filter('format', 'rgba')
                    out_bytes, _err = (
                        filt_local
                        .output('pipe:', vframes=1, format='image2', vcodec='png', update=1)
                        .global_args(*ga)
                        .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                    )
                    return out_bytes

                # Build candidate list: env device -> configured -> all render nodes
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
                except Exception:
                    pass

                last_ex: Optional[Exception] = None
                for dev in candidates:
                    try:
                        out = _try_device(dev)
                        if out:
                            # cache working device
                            if dev:
                                with FFMpeg.__vaapi_lock:
                                    FFMpeg.__vaapi_device_cached = dev
                            logger.debug(f"VAAPI decode successful for {file} using device: {dev}")
                            return Image.open(BytesIO(out))
                    except Exception as ex2:
                        last_ex = ex2
                        continue
                # If all candidates failed, re-raise the last exception to trigger software fallback logging
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

        # 3) Software fallback (no hwaccel args)
        try:
            stream_sw = ffmpeg.input(file, ss=screenshot_time)
            if width and width > 0:
                stream_sw = stream_sw.filter('scale', width, -2)
            out, _err = _run_pipeline(stream_sw, [])
            try:
                return Image.open(BytesIO(out))
            except Exception as pil_ex:
                # Image bytes invalid; fall through to PNG and other fallbacks
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
            # Secondary attempt: retry with PNG encoder instead of APNG to mitigate encoder-specific failures
            try:
                stream_sw2 = ffmpeg.input(file, ss=screenshot_time)
                if width and width > 0:
                    stream_sw2 = stream_sw2.filter('scale', width, -2)
                out2, _err2 = (
                    stream_sw2
                    .output('pipe:', vframes=1, format='image2', vcodec='png', update=1)
                    .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                )
                try:
                    return Image.open(BytesIO(out2))
                except Exception as pil_ex2:
                    # Continue to post-seek fallbacks
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
                except Exception:
                    logger.error('Software PNG fallback failed for {} at t={}s: {}', file, screenshot_time, ex2)
            # Tertiary attempt: accurate seek using output-side -ss (post-seek), APNG then PNG
            try:
                stream_sw3 = ffmpeg.input(file)
                if width and width > 0:
                    stream_sw3 = stream_sw3.filter('scale', width, -2)
                out3, _err3 = (
                    stream_sw3
                    .output('pipe:', vframes=1, ss=screenshot_time, format='apng')
                    .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                )
                return Image.open(BytesIO(out3))
            except Exception:
                try:
                    stream_sw4 = ffmpeg.input(file)
                    if width and width > 0:
                        stream_sw4 = stream_sw4.filter('scale', width, -2)
                    out4, _err4 = (
                        stream_sw4
                        .output('pipe:', vframes=1, ss=screenshot_time, format='image2', vcodec='png')
                        .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                    )
                    return Image.open(BytesIO(out4))
                except Exception:
                    pass
            # Quaternary attempt: small jitter around timestamp with PNG post-seek
            for delta in (-0.25, 0.25, -0.5, 0.5):
                t2 = max(0.0, (screenshot_time or 0.0) + delta)
                try:
                    stream_sw5 = ffmpeg.input(file)
                    if width and width > 0:
                        stream_sw5 = stream_sw5.filter('scale', width, -2)
                    out5, _err5 = (
                        stream_sw5
                        .output('pipe:', vframes=1, ss=t2, format='image2', vcodec='png')
                        .run(quiet=True, capture_stdout=True, capture_stderr=True, cmd=self.__ffmpeg_cmd)
                    )
                    return Image.open(BytesIO(out5))
                except Exception:
                    continue
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
            # fmt: off
            args = [
                str(executable),
                '-version'
            ]

            process = None
            with suppress(Exception):
                process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)

            matches = None
            if process:
                stdout, _ = process.communicate()

                if stdout:
                    line = stdout.split('\n', 1)[0]
                    matches = reg.search(line)

            versions[tool] = matches.groupdict().get('version') if matches else None

        return versions
