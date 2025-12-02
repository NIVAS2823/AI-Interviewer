"""
Audio Conversion Utility
Converts WebM audio (Opus) → WAV PCM 16kHz mono
Deepgram requires clean WAV for highest accuracy.
"""

import sys
sys.modules["pyaudioop"] = __import__("audioop")

import io
import logging
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class AudioConverter:
    """
    Converts audio bytes into Deepgram-friendly WAV (PCM 16kHz)
    """

    @staticmethod
    def webm_to_wav(audio_bytes: bytes) -> bytes:
        """
        Convert WebM/Opus bytes to WAV PCM 16kHz mono
        """

        if not audio_bytes:
            logger.error("❌ No audio bytes provided to converter")
            return b""

        try:
            # Load WebM/Opus data from memory
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")

            # Convert to Deepgram-friendly WAV format
            wav_audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

            out_buffer = io.BytesIO()
            wav_audio.export(out_buffer, format="wav")

            logger.info(f"🔄 Converted WebM → WAV ({len(out_buffer.getvalue())} bytes)")
            return out_buffer.getvalue()

        except Exception as e:
            logger.exception(f"❌ Failed to convert WebM to WAV: {e}")
            return b""
