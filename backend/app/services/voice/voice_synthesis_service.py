"""
Voice Synthesis Service
Coordinates TTS operations with caching support
"""
import logging
from typing import Optional, List, Dict, Any

from app.services.voice.audio_cache_service import AudioCacheService

logger = logging.getLogger(__name__)


class VoiceSynthesisService:
    """
    Service for voice synthesis with caching
    
    Responsibilities:
    - Coordinate TTS generation
    - Use cache when available
    - Batch audio generation
    
    Does NOT:
    - Manage cache (delegates to AudioCacheService)
    - Generate message text (that's VoiceMessageGenerator's job)
    """

    def __init__(
        self,
        tts_service=None,
        audio_cache: Optional[AudioCacheService] = None,
    ):
        """
        Initialize voice synthesis service
        
        Args:
            tts_service: TTS service instance
            audio_cache: Audio cache service (optional)
        """
        self.tts_service = tts_service
        self.audio_cache = audio_cache or AudioCacheService(tts_service)
        self.default_voice = "aura-athena-en"

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        use_cache: bool = True,
    ) -> bytes:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize
            voice: Voice model (uses default if None)
            use_cache: Whether to use cache
            
        Returns:
            Audio bytes
        """
        voice = voice or self.default_voice

        # Try cache first
        if use_cache:
            cached_audio = self.audio_cache.get_cached(text, voice)
            if cached_audio:
                logger.debug(f"✅ Using cached audio: '{text[:30]}...'")
                return cached_audio

        # Generate with TTS
        if not self.tts_service:
            logger.error("❌ No TTS service available")
            return b""

        try:
            logger.debug(f"🎤 Synthesizing: '{text[:50]}...' (voice: {voice})")
            
            audio_bytes = await self.tts_service.synthesize_speech(
                text=text,
                voice_name=voice
            )

            if audio_bytes:
                # Add to cache for future use
                if use_cache:
                    self.audio_cache.add_to_cache(text, voice, audio_bytes)
                
                logger.debug(f"✅ Synthesized: {len(audio_bytes)} bytes")
                return audio_bytes
            else:
                logger.warning(f"⚠️ TTS returned empty audio")
                return b""

        except Exception as e:
            logger.error(f"❌ Synthesis failed: {e}")
            return b""

    async def synthesize_batch(
        self,
        texts: List[str],
        voice: Optional[str] = None,
    ) -> Dict[str, bytes]:
        """
        Synthesize multiple texts in batch
        
        Args:
            texts: List of texts
            voice: Voice model
            
        Returns:
            Dict mapping text to audio bytes
        """
        voice = voice or self.default_voice
        results = {}

        logger.info(f"🎤 Batch synthesis: {len(texts)} texts")

        for text in texts:
            audio = await self.synthesize(text, voice, use_cache=True)
            results[text] = audio

        logger.info(f"✅ Batch synthesis complete: {len(results)} audio files")

        return results

    async def synthesize_with_fallback(
        self,
        text: str,
        voice: Optional[str] = None,
        fallback_text: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """
        Synthesize with fallback text
        
        Args:
            text: Primary text
            voice: Voice model
            fallback_text: Fallback text if primary fails
            
        Returns:
            Tuple of (audio_bytes, actual_text_used)
        """
        audio = await self.synthesize(text, voice)
        
        if audio and len(audio) > 0:
            return audio, text

        # Try fallback
        if fallback_text:
            logger.warning(f"⚠️ Using fallback text: '{fallback_text[:50]}...'")
            fallback_audio = await self.synthesize(fallback_text, voice)
            return fallback_audio, fallback_text

        return b"", text

    async def preload_cache(
        self,
        texts: List[str],
        voice: Optional[str] = None,
    ) -> bool:
        """
        Preload cache with texts
        
        Args:
            texts: Texts to preload
            voice: Voice model
            
        Returns:
            True if successful
        """
        voice = voice or self.default_voice
        
        return await self.audio_cache.initialize(
            texts=texts,
            voice=voice,
            tts_service=self.tts_service,
        )

    async def preload_cache_background(
        self,
        texts: List[str],
        voice: Optional[str] = None,
    ):
        """
        Preload cache in background (non-blocking)
        
        Args:
            texts: Texts to preload
            voice: Voice model
        """
        voice = voice or self.default_voice
        
        await self.audio_cache.initialize_background(
            texts=texts,
            voice=voice,
            tts_service=self.tts_service,
        )

    def get_synthesis_stats(self) -> Dict[str, Any]:
        """
        Get synthesis statistics
        
        Returns:
            Dict with stats
        """
        cache_stats = self.audio_cache.get_cache_stats()
        
        return {
            "cache_enabled": True,
            "cache_stats": cache_stats,
            "default_voice": self.default_voice,
            "tts_available": self.tts_service is not None,
        }

    def clear_cache(self, voice: Optional[str] = None):
        """
        Clear audio cache
        
        Args:
            voice: Optional voice to clear
        """
        self.audio_cache.clear_cache(voice)

    async def validate_synthesis(self, text: str, voice: str) -> tuple[bool, Optional[str]]:
        """
        Validate that text can be synthesized
        
        Args:
            text: Text to validate
            voice: Voice model
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text or len(text.strip()) == 0:
            return False, "Empty text"

        if len(text) > 5000:
            return False, f"Text too long: {len(text)} chars (max: 5000)"

        if not self.tts_service:
            return False, "TTS service not available"

        return True, None

    async def synthesize_with_retry(
        self,
        text: str,
        voice: Optional[str] = None,
        max_retries: int = 3,
    ) -> bytes:
        """
        Synthesize with retry logic
        
        Args:
            text: Text to synthesize
            voice: Voice model
            max_retries: Maximum retry attempts
            
        Returns:
            Audio bytes
        """
        voice = voice or self.default_voice

        for attempt in range(1, max_retries + 1):
            try:
                audio = await self.synthesize(text, voice, use_cache=True)
                
                if audio and len(audio) > 0:
                    return audio

                logger.warning(f"⚠️ Empty audio on attempt {attempt}")

            except Exception as e:
                logger.error(f"❌ Synthesis attempt {attempt} failed: {e}")

            if attempt < max_retries:
                import asyncio
                await asyncio.sleep(0.5 * attempt)  # Exponential backoff

        logger.error(f"❌ All {max_retries} synthesis attempts failed")
        return b""

    def estimate_audio_duration(self, text: str, words_per_minute: int = 150) -> float:
        """
        Estimate audio duration
        
        Args:
            text: Text to estimate
            words_per_minute: Speaking rate
            
        Returns:
            Estimated duration in seconds
        """
        word_count = len(text.split())
        duration_seconds = (word_count / words_per_minute) * 60
        return round(duration_seconds, 1)