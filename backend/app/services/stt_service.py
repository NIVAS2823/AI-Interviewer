"""
Speech-to-Text Service using Deepgram Nova-2
Clean, production-ready implementation with WebM support
"""

import asyncio
import logging
from typing import Optional
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    PrerecordedOptions,
    FileSource,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class STTService:
    """
    Speech-to-Text service using Deepgram Nova-2
    Handles multiple audio formats including WebM from browsers
    """

    def __init__(self):
        """Initialize Deepgram client"""
        api_key = settings.DEEPGRAM_API_KEY

        if not api_key:
            logger.error("❌ DEEPGRAM_API_KEY not found in settings")
            self.client = None
            return

        try:
            config = DeepgramClientOptions(api_key=api_key, options={"keepalive": "true"})
            self.client = DeepgramClient(api_key, config)

            # 🔥 NEW: Timeout for long audio files
            self.timeout = 90.0

            logger.info("✅ Deepgram STT Service initialized")
            logger.info(f"   Timeout: {self.timeout}s")
        except Exception as e:
            logger.exception(f"❌ Failed to initialize Deepgram: {e}")
            self.client = None

    def _detect_audio_format(self, audio_bytes: bytes) -> str:
        """
        Detect audio format from byte signature (magic numbers)

        Returns:
            MIME type string
        """
        if not audio_bytes or len(audio_bytes) < 12:
            return "audio/webm"

        if audio_bytes[:4] == b'RIFF' and audio_bytes[8:12] == b'WAVE':
            return "audio/wav"
        elif audio_bytes[:4] == b'\x1a\x45\xdf\xa3':  # EBML (WebM/Matroska)
            return "audio/webm"
        elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
            return "audio/mpeg"
        elif audio_bytes[:4] == b'OggS':
            return "audio/ogg"
        elif audio_bytes[:4] == b'fLaC':
            return "audio/flac"
        else:
            logger.debug("Unknown format signature, defaulting to webm")
            return "audio/webm"

    # -------------------------------------------------------------
    # 🔥 UPDATED METHOD: Full Retry Logic + Timeout Support
    # -------------------------------------------------------------
    async def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        format: str = None,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Transcribe audio bytes to text with retry logic
        """
        if not self.client:
            logger.error("Deepgram client not initialized")
            return None

        if not audio_bytes or len(audio_bytes) == 0:
            logger.warning("Empty audio bytes provided")
            return None

        # detect format if not manually passed
        mimetype = format or self._detect_audio_format(audio_bytes)

        # 🔥 Retry loop
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"🎤 Transcribing audio: {len(audio_bytes)} bytes, "
                    f"format: {mimetype}, attempt {attempt}/{max_retries}"
                )

                source: FileSource = {
                    "buffer": audio_bytes,
                    "mimetype": mimetype
                }

                # Deepgram options
                options = PrerecordedOptions(
                    model="nova-2",
                    language="en-US",
                    punctuate=True,
                    smart_format=True,
                )

                # 🔥 Run transcription in a separate thread with a timeout
                response = await asyncio.to_thread(
                    self.client.listen.prerecorded.v("1").transcribe_file,
                    source,
                    options,
                    timeout=self.timeout
                )

                # Extract transcript
                transcript = response.results.channels[0].alternatives[0].transcript

                if transcript and transcript.strip():
                    logger.info(f"✅ Transcript: '{transcript[:120]}...'")
                    return transcript.strip()
                else:
                    logger.warning("⚠️ Empty transcript returned")
                    if attempt < max_retries:
                        logger.info("🔄 Retrying due to empty transcript...")
                        await asyncio.sleep(2)
                        continue
                    return None

            except Exception as e:
                error_msg = str(e).lower()
                is_timeout = any(t in error_msg for t in ["timeout", "timed out"])
                is_network = any(n in error_msg for n in ["connection", "network", "ssl", "handshake"])

                if is_timeout:
                    logger.warning(f"⏱️ Timeout attempt {attempt}/{max_retries}")
                elif is_network:
                    logger.warning(f"🌐 Network issue attempt {attempt}/{max_retries}")
                else:
                    logger.error(f"❌ Error attempt {attempt}/{max_retries}: {e}")

                if (is_timeout or is_network) and attempt < max_retries:
                    wait_time = attempt * 2
                    logger.info(f"🔄 Retrying in {wait_time}s ...")
                    await asyncio.sleep(wait_time)
                    continue

                if attempt == max_retries:
                    logger.exception(f"❌ All {max_retries} attempts failed: {e}")

                return None

        return None

    async def transcribe_audio_file(self, audio_path: str) -> Optional[str]:
        """Transcribe an audio file from disk"""
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            logger.info(f"📁 Reading audio file: {audio_path}")
            return await self.transcribe_audio_bytes(audio_bytes)

        except FileNotFoundError:
            logger.error(f"❌ Audio file not found: {audio_path}")
            return None
        except Exception as e:
            logger.exception(f"❌ Error reading audio file: {e}")
            return None
