"""Production entrypoint for the FFmpeg integration.

Docker builds copy this file over `namer/ffmpeg.py`, so it must stay in sync
with the development entrypoint. The shared implementation lives in
`namer/ffmpeg_impl.py`; this module simply re-exports the runtime class and
related typed results for container builds.
"""

from namer.ffmpeg_impl import FFMpeg, FFProbeResults, FFProbeStream
from namer.ffmpeg_common import FFProbeFormat

__all__ = ['FFMpeg', 'FFProbeResults', 'FFProbeStream', 'FFProbeFormat']
