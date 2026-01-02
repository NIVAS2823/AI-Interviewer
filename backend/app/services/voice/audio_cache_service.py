"""
Audio Cache Service
Manages pre-generated audio cache for frequently used phrases
"""
import logging
from typing import Optional, Dict, List
import asyncio

logger = logging.getLogger(__name__)


class AudioCacheService:
    """
    Service for caching pre-generated audio
    
    Responsibilities:
    - Cache audio for frequently used texts
    - Pre-generate audio in background
    - Retrieve cached audio quickly
    """

    def __init__(self, tts_service=None):
        """
        Initialize audio cache service
        
        Args:
            tts_service: TTS service instance for generating audio
        """
        self.tts_service = tts_service
        self.cache: Dict[str, bytes] = {}
        self.cache_by_voice: Dict[str, Dict[str, bytes]] = {}
        self.is_initialized = False

    async def initialize(
        self,
        texts: List[str],
        voice: str,
        tts_service=None,
    ) -> bool:
        """
        Pre-generate and cache audio for given texts
        
        Args:
            texts: List of texts to cache
            voice: Voice model to use
            tts_service: TTS service (optional, uses instance service)
            
        Returns:
            True if successful
        """
        tts = tts_service or self.tts_service
        
        if not tts:
            logger.error("❌ No TTS service available for caching")
            return False

        logger.info(f"🎤 Initializing audio cache for {len(texts)} phrases...")

        # Create voice-specific cache
        if voice not in self.cache_by_voice:
            self.cache_by_voice[voice] = {}

        success_count = 0
        
        for text in texts:
            try:
                audio_bytes = await tts.synthesize_speech(text, voice_name=voice)
                
                if audio_bytes:
                    # Store in both general and voice-specific cache
                    cache_key = self._generate_cache_key(text, voice)
                    self.cache[cache_key] = audio_bytes
                    self.cache_by_voice[voice][text] = audio_bytes
                    
                    success_count += 1
                    logger.info(f"   ✅ Cached: '{text[:50]}...' ({len(audio_bytes)} bytes)")
                else:
                    logger.warning(f"   ⚠️ Empty audio for: '{text[:50]}...'")
                    
            except Exception as e:
                logger.error(f"   ❌ Failed to cache '{text[:50]}...': {e}")

        self.is_initialized = True
        logger.info(f"✅ Audio cache initialized: {success_count}/{len(texts)} phrases")

        return success_count > 0

    async def initialize_background(
        self,
        texts: List[str],
        voice: str,
        tts_service=None,
    ):
        """
        Initialize cache in background (non-blocking)
        
        Args:
            texts: List of texts to cache
            voice: Voice model
            tts_service: TTS service
        """
        asyncio.create_task(self.initialize(texts, voice, tts_service))
        logger.info("🎤 Background cache initialization started")

    def get_cached(self, text: str, voice: str) -> Optional[bytes]:
        """
        Retrieve cached audio
        
        Args:
            text: Text to retrieve
            voice: Voice model
            
        Returns:
            Cached audio bytes or None
        """
        # Try voice-specific cache first
        if voice in self.cache_by_voice:
            audio = self.cache_by_voice[voice].get(text)
            if audio:
                logger.debug(f"✅ Cache hit: '{text[:30]}...' ({len(audio)} bytes)")
                return audio

        # Try general cache with key
        cache_key = self._generate_cache_key(text, voice)
        audio = self.cache.get(cache_key)
        
        if audio:
            logger.debug(f"✅ Cache hit (general): '{text[:30]}...'")
            return audio

        logger.debug(f"❌ Cache miss: '{text[:30]}...'")
        return None

    def has_cached(self, text: str, voice: str) -> bool:
        """Check if text is cached"""
        return self.get_cached(text, voice) is not None

    def clear_cache(self, voice: Optional[str] = None):
        """
        Clear cache
        
        Args:
            voice: Optional voice to clear (clears all if None)
        """
        if voice:
            if voice in self.cache_by_voice:
                count = len(self.cache_by_voice[voice])
                del self.cache_by_voice[voice]
                logger.info(f"🗑️ Cleared cache for voice '{voice}': {count} entries")
        else:
            count = len(self.cache)
            self.cache.clear()
            self.cache_by_voice.clear()
            logger.info(f"🗑️ Cleared entire cache: {count} entries")

    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache statistics
        
        Returns:
            Dict with cache stats
        """
        total_size = sum(len(audio) for audio in self.cache.values())
        
        voice_stats = {}
        for voice, voice_cache in self.cache_by_voice.items():
            voice_size = sum(len(audio) for audio in voice_cache.values())
            voice_stats[voice] = {
                "entry_count": len(voice_cache),
                "total_size_bytes": voice_size,
                "total_size_mb": round(voice_size / 1_000_000, 2),
            }

        return {
            "is_initialized": self.is_initialized,
            "total_entries": len(self.cache),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1_000_000, 2),
            "voices": list(self.cache_by_voice.keys()),
            "voice_stats": voice_stats,
        }

    def _generate_cache_key(self, text: str, voice: str) -> str:
        """Generate cache key from text and voice"""
        return f"{voice}:{text}"

    async def preload_common_phrases(
        self,
        voice: str,
        tts_service,
        phrase_type: str = "acknowledgments"
    ) -> bool:
        """
        Preload common phrases based on type
        
        Args:
            voice: Voice model
            tts_service: TTS service
            phrase_type: Type of phrases to load
            
        Returns:
            True if successful
        """
        phrase_sets = {
            "acknowledgments": [
                "Thank you for that answer.",
                "I appreciate your response.",
                "That's helpful to know.",
                "I see, thank you.",
                "Interesting perspective.",
                "Great, let's continue.",
                "Understood, thank you.",
            ],
            "transitions": [
                "Let's move on to the next question.",
                "Now, let me ask you about something else.",
                "Alright, next question.",
            ],
            "clarifications": [
                "Could you elaborate on that?",
                "Can you provide more details?",
                "That's interesting, tell me more.",
            ]
        }

        phrases = phrase_sets.get(phrase_type, [])
        
        if not phrases:
            logger.warning(f"⚠️ Unknown phrase type: {phrase_type}")
            return False

        return await self.initialize(phrases, voice, tts_service)

    def add_to_cache(self, text: str, voice: str, audio_bytes: bytes):
        """
        Manually add to cache
        
        Args:
            text: Text
            voice: Voice model
            audio_bytes: Audio data
        """
        if voice not in self.cache_by_voice:
            self.cache_by_voice[voice] = {}

        cache_key = self._generate_cache_key(text, voice)
        self.cache[cache_key] = audio_bytes
        self.cache_by_voice[voice][text] = audio_bytes

        logger.debug(f"➕ Added to cache: '{text[:30]}...' ({len(audio_bytes)} bytes)")

    def get_cache_size_limit_mb(self) -> float:
        """Get recommended cache size limit in MB"""
        return 10.0  # 10MB default limit

    def is_cache_size_exceeded(self) -> bool:
        """Check if cache size exceeds recommended limit"""
        stats = self.get_cache_stats()
        limit_mb = self.get_cache_size_limit_mb()
        return stats["total_size_mb"] > limit_mb