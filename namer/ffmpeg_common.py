from dataclasses import dataclass
from typing import Dict, List, Optional

import orjson


class QSVCodecMapper:
    """Maps video codecs to their corresponding QSV decoders."""

    # Mapping of codec names to QSV decoder names
    CODEC_TO_QSV_DECODER = {
        "h264": "h264_qsv",
        "hevc": "hevc_qsv",
        "h265": "hevc_qsv",  # alias for hevc
        "av1": "av1_qsv",
        "vp9": "vp9_qsv",
        "vp8": "vp8_qsv",
        "mpeg2": "mpeg2_qsv",
        "mpeg2video": "mpeg2_qsv",
        "vc1": "vc1_qsv",
        "mjpeg": "mjpeg_qsv",
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
        return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("UTF-8")

    def to_dict(self) -> dict:
        data = {
            "codec_name": self.codec_name,
            "width": self.width,
            "height": self.height,
            "codec_type": self.codec_type,
            "framerate": self.avg_frame_rate,
            "duration": self.duration,
            "disposition_default": self.disposition_default,
        }
        return data

    def is_audio(self) -> bool:
        return self.codec_type == "audio"

    def is_video(self) -> bool:
        return self.codec_type == "video" and (
            not self.disposition_attached_pic or self.disposition_attached_pic is False
        )


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
