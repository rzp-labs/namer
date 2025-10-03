"""Development entrypoint for the FFmpeg integration.

Historically this file duplicated the production implementation in
`namer/ffmpeg_enhanced.py`. The shared logic now lives in
`namer/ffmpeg_impl.py`; this module simply re-exports the runtime class and
related typed results for local development.
"""

from namer.ffmpeg_impl import FFMpeg, FFProbeFormat, FFProbeResults, FFProbeStream

__all__ = ['FFMpeg', 'FFProbeResults', 'FFProbeStream', 'FFProbeFormat']
