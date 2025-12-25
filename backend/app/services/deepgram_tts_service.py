"""
Text-to-Speech Service using Deepgram Aura
Drop-in replacement for Azure TTS with identical interface
Ultra-low latency streaming TTS
"""

import logging
import os
from typing import Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class DeepgramTTSService:
    """
    Text-to-Speech service using Deepgram Aura
    Compatible interface with Azure TTS service
    """

    # Available Deepgram voices
    AVAILABLE_VOICES = {
        # Female voices
        "en-US-JennyNeural": "aura-asteria-en",      # Map Azure voice to Deepgram
        "en-US-AriaNeural": "aura-luna-en",
        "en-IN-NeerjaNeural": "aura-athena-en",      # Your current default
        "female-professional": "aura-hera-en",
        "female-warm": "aura-luna-en",
        "female-expressive": "aura-stella-en",
        
        # Male voices
        "en-US-GuyNeural": "aura-orion-en",
        "en-IN-PrabhatNeural": "aura-perseus-en",
        "male-deep": "aura-orion-en",
        "male-clear": "aura-perseus-en",
        "male-authoritative": "aura-angus-en",
    }

    DEFAULT_VOICE = "aura-athena-en"  # Natural female voice (maps to your Neerja)

    def __init__(self):
        """Initialize Deepgram Speech Service"""
        self.api_key = settings.DEEPGRAM_API_KEY if hasattr(settings, 'DEEPGRAM_API_KEY') else os.getenv("DEEPGRAM_API_KEY")
        
        if not self.api_key:
            logger.error("❌ Deepgram API key not found")
            self.api_key = None
            return

        try:
            # Deepgram API configuration
            self.base_url = "https://api.deepgram.com/v1/speak"
            
            # Audio format settings (matching quality with Azure)
            self.encoding = "linear16"      # High quality PCM (same as Azure WAV)
            self.sample_rate = 24000        # 24kHz (Azure uses 24kHz for Neural voices)
            self.container = "wav"          # WAV format for compatibility
            
            # Set default voice (can use mapped name or direct Deepgram model)
            default_voice_setting = getattr(settings, "AZURE_DEFAULT_VOICE", "en-IN-NeerjaNeural")
            self.current_voice = self._map_voice(default_voice_setting)
            
            # HTTP client for async requests
            self.client = httpx.AsyncClient(timeout=30.0)
            
            logger.info("✅ Deepgram TTS Service initialized")
            logger.info(f"   Voice: {self.current_voice}")
            logger.info(f"   Sample Rate: {self.sample_rate}Hz")

        except Exception as e:
            logger.exception(f"❌ Failed to initialize Deepgram TTS: {e}")
            self.api_key = None

    def _map_voice(self, voice_name: str) -> str:
        """
        Map Azure voice names to Deepgram models
        Falls back to direct Deepgram model name if no mapping found
        """
        if not voice_name:
            return self.DEFAULT_VOICE
        
        # Check if it's already a Deepgram model (starts with "aura-")
        if voice_name.startswith("aura-"):
            return voice_name
        
        # Map Azure voice to Deepgram
        mapped = self.AVAILABLE_VOICES.get(voice_name, self.DEFAULT_VOICE)
        logger.debug(f"Mapped voice '{voice_name}' -> '{mapped}'")
        return mapped

    async def synthesize_speech(
        self,
        text: str,
        voice_name: Optional[str] = None,
        voice: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Convert text to speech audio bytes.
        Compatible interface with Azure TTS service.

        Args:
            text: Text to synthesize
            voice_name: Optional voice name (preferred parameter)
            voice: Optional voice name (alternate parameter for compatibility)

        Returns:
            Audio bytes (WAV) or empty bytes on failure
        """
        if not self.api_key:
            logger.error("Deepgram TTS not initialized")
            return b""

        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return b""

        # Determine which voice to use
        chosen_voice_param = voice_name or voice
        if chosen_voice_param:
            chosen_voice = self._map_voice(chosen_voice_param)
        else:
            chosen_voice = self.current_voice

        logger.debug(f"TTS synthesize request: {len(text)} chars, voice='{chosen_voice}'")

        try:
            # Build request URL with parameters
            url = (
                f"{self.base_url}"
                f"?model={chosen_voice}"
                f"&encoding={self.encoding}"
                f"&sample_rate={self.sample_rate}"
                f"&container={self.container}"
            )

            # Request headers
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }

            # Request body
            payload = {"text": text.strip()}

            logger.debug(f"Calling Deepgram TTS API...")

            # Make async request
            response = await self.client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                audio_data = response.content
                logger.info(f"✅ TTS synthesis complete ({len(audio_data)} bytes)")
                return audio_data
            else:
                error_msg = response.text
                logger.error(f"❌ Deepgram TTS API error: {response.status_code}")
                logger.error(f"   Details: {error_msg}")
                return b""

        except httpx.TimeoutException:
            logger.error("❌ TTS request timed out (30s)")
            return b""
        except Exception as e:
            logger.exception(f"❌ TTS synthesis error: {e}")
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
        if not self.api_key:
            logger.error("Deepgram TTS not initialized")
            return False

        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return False

        try:
            # Get audio bytes
            audio_data = await self.synthesize_speech(text, voice_name=voice_name, voice=voice)
            
            if not audio_data or len(audio_data) == 0:
                logger.error("❌ TTS synthesis returned no data")
                return False

            # Write to file
            logger.debug(f"Writing audio to file '{output_path}'")
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"✅ Audio saved to: {output_path}")
            return True

        except Exception as e:
            logger.exception(f"❌ TTS error when writing file: {e}")
            return False

    def get_available_voices(self) -> list:
        """
        Get list of available voices
        Returns Azure-compatible voice names for easy migration
        """
        return [
            "en-US-JennyNeural",      # Maps to aura-asteria-en
            "en-US-AriaNeural",       # Maps to aura-luna-en
            "en-US-GuyNeural",        # Maps to aura-orion-en
            "en-IN-NeerjaNeural",     # Maps to aura-athena-en (default)
            "en-IN-PrabhatNeural",    # Maps to aura-perseus-en
            "female-professional",    # Direct: aura-hera-en
            "female-warm",            # Direct: aura-luna-en
            "male-deep",              # Direct: aura-orion-en
            "male-clear",             # Direct: aura-perseus-en
        ]

    def set_voice(self, voice_name: str):
        """
        Set the default voice for subsequent synthesis calls
        """
        self.current_voice = self._map_voice(voice_name)
        logger.info(f"🎤 Default voice changed to: {self.current_voice}")

    async def close(self):
        """Close the HTTP client"""
        if hasattr(self, 'client'):
            await self.client.aclose()
            logger.debug("✅ Deepgram TTS client closed")

    def __del__(self):
        """Cleanup on deletion"""
        try:
            import asyncio
            asyncio.create_task(self.close())
        except:
            pass


# Alias for compatibility with existing code that imports TTSService
TTSService = DeepgramTTSService