# app/services/tts_service.py
"""
Text-to-Speech Service using Azure Neural TTS
Robust implementation that:
 - prefers file-synthesis (more reliable on Windows / headless)
 - falls back to in-memory audio_data if available
 - supports both voice_name and voice parameter names
 - returns bytes (empty bytes on failure)
"""

import logging
import tempfile
import os
from typing import Optional
import azure.cognitiveservices.speech as speechsdk
from app.core.config import settings

logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-Speech service using Azure Neural TTS
    """

    DEFAULT_VOICE = "en-IN-NeerjaNeural"

    def __init__(self):
        """Initialize Azure Speech Service"""
        if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
            logger.error("❌ Azure Speech credentials not found")
            self.speech_config = None
            return

        try:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_SPEECH_REGION,
            )

            # Set default voice
            default_voice = getattr(settings, "AZURE_DEFAULT_VOICE", self.DEFAULT_VOICE)
            self.speech_config.speech_synthesis_voice_name = default_voice

            logger.info("✅ Azure TTS Service initialized")
            logger.info(f"   Region: {settings.AZURE_SPEECH_REGION}")
            logger.info(f"   Voice: {self.speech_config.speech_synthesis_voice_name}")

        except Exception as e:
            logger.exception(f"❌ Failed to initialize Azure TTS: {e}")
            self.speech_config = None

    async def synthesize_speech(
        self,
        text: str,
        voice_name: Optional[str] = None,
        voice: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Convert text to speech audio bytes.

        Args:
            text: Text to synthesize
            voice_name: Optional voice name (preferred parameter)
            voice: Optional voice name (alternate parameter for compatibility)

        Returns:
            Audio bytes (WAV) or empty bytes on failure
        """
        if not self.speech_config:
            logger.error("Azure TTS not initialized")
            return b""

        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return b""

        chosen_voice = voice_name or voice or getattr(self.speech_config, "speech_synthesis_voice_name", self.DEFAULT_VOICE)
        logger.debug(f"TTS synthesize request: {len(text)} chars, voice='{chosen_voice}'")

        # Temporarily set voice
        previous_voice = getattr(self.speech_config, "speech_synthesis_voice_name", None)
        try:
            self.speech_config.speech_synthesis_voice_name = chosen_voice
        except Exception:
            # non-fatal; continue with whatever is set
            logger.debug("Could not set speech_synthesis_voice_name on config; continuing")

        # 1) Preferred: synthesize to a temporary file (most robust across platforms)
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fh:
                tmp_file = fh.name

            logger.debug(f"Attempting file-based TTS to '{tmp_file}'")
            audio_config = speechsdk.audio.AudioOutputConfig(filename=tmp_file)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_config)

            result = synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                try:
                    with open(tmp_file, "rb") as f:
                        data = f.read()
                    logger.info(f"✅ TTS file-based synthesis complete ({len(data)} bytes)")
                    return data
                except Exception as e:
                    logger.exception(f"Failed to read synthesized file '{tmp_file}': {e}")
                    # fall through to next attempt
            else:
                # Log cancellation / failure details
                if result.reason == speechsdk.ResultReason.Canceled:
                    cd = result.cancellation_details
                    logger.error(f"❌ TTS canceled: {cd.reason} - {getattr(cd, 'error_details', '')}")
                else:
                    logger.error(f"❌ TTS failed with reason: {result.reason}")
        except Exception as e:
            # Common Windows/device/file permission errors surface here
            logger.exception(f"❌ TTS file-based synthesis error: {e}")
        finally:
            # Clean up temp file if it exists
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    logger.debug(f"Could not remove temp file {tmp_file}; leaving it for inspection")

        # 2) Fallback: try in-memory route (result.audio_data)
        try:
            logger.debug("Attempting in-memory TTS (audio_data)")
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=None)
            result = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_bytes = result.audio_data
                logger.info(f"✅ In-memory TTS complete ({len(audio_bytes)} bytes)")
                return audio_bytes
            else:
                if result.reason == speechsdk.ResultReason.Canceled:
                    cd = result.cancellation_details
                    logger.error(f"❌ In-memory TTS canceled: {cd.reason} - {getattr(cd, 'error_details', '')}")
                else:
                    logger.error(f"❌ In-memory TTS failed with reason: {result.reason}")
        except Exception as e:
            logger.exception(f"❌ In-memory TTS error: {e}")

        # 3) Final fallback: return empty bytes so callers can safely call len(...)
        logger.warning("TTS synthesis failed; returning empty bytes as fallback")
        # restore previous voice if possible
        try:
            if previous_voice:
                self.speech_config.speech_synthesis_voice_name = previous_voice
        except Exception:
            pass

        return b""

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice_name: Optional[str] = None,
        voice: Optional[str] = None,
    ) -> bool:
        """
        Synthesize speech and save to file.
        Returns True if successful.
        """
        if not self.speech_config:
            logger.error("Azure TTS not initialized")
            return False

        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return False

        chosen_voice = voice_name or voice or getattr(self.speech_config, "speech_synthesis_voice_name", self.DEFAULT_VOICE)
        previous_voice = getattr(self.speech_config, "speech_synthesis_voice_name", None)
        try:
            self.speech_config.speech_synthesis_voice_name = chosen_voice
        except Exception:
            logger.debug("Could not set speech_synthesis_voice_name on config; continuing")

        try:
            logger.debug(f"Synthesizing to file '{output_path}' with voice '{chosen_voice}'")
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_config)
            result = synthesizer.speak_text_async(text).get()
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(f"✅ Audio saved to: {output_path}")
                return True
            else:
                if result.reason == speechsdk.ResultReason.Canceled:
                    cd = result.cancellation_details
                    logger.error(f"❌ TTS canceled when writing file: {cd.reason} - {getattr(cd, 'error_details', '')}")
                else:
                    logger.error(f"❌ TTS failed when writing file: {result.reason}")
                return False
        except Exception as e:
            logger.exception(f"❌ TTS error when writing file: {e}")
            return False
        finally:
            try:
                if previous_voice:
                    self.speech_config.speech_synthesis_voice_name = previous_voice
            except Exception:
                pass

    def get_available_voices(self) -> list:
        """
        Get a small curated list of common Azure Neural voices
        """
        return [
            "en-US-JennyNeural",
            "en-US-AriaNeural",
            "en-US-GuyNeural",
            "en-IN-NeerjaNeural",
            "en-IN-PrabhatNeural",
        ]
