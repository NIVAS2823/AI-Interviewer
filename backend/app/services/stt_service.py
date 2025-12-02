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
        if not settings.DEEPGRAM_API_KEY:
            logger.error("❌ DEEPGRAM_API_KEY not found in settings")
            self.client = None
            return
        
        try:
            config = DeepgramClientOptions(
                api_key=settings.DEEPGRAM_API_KEY,
                options={"keepalive": "true"}
            )
            self.client = DeepgramClient("", config)
            logger.info("✅ Deepgram STT Service initialized")
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
            return "audio/webm"  # Default for browser recordings
        
        # Check magic numbers at start of file
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
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio from bytes with automatic format detection
        
        Args:
            audio_bytes: Audio data as bytes (WebM, WAV, MP3, etc.)
            
        Returns:
            Transcribed text or None if transcription fails
        """
        if not self.client:
            logger.error("❌ Deepgram client not initialized")
            return None
        
        if not audio_bytes or len(audio_bytes) == 0:
            logger.warning("⚠️ Empty audio bytes provided")
            return None
        
        try:
            # Detect audio format
            mimetype = self._detect_audio_format(audio_bytes)
            
            logger.info(f"🎤 Transcribing audio: {len(audio_bytes)} bytes, format: {mimetype}")
            
            # Create payload with proper typing
            payload: FileSource = {
                "buffer": audio_bytes,
                "mimetype": mimetype
            }
            
            # Configure transcription options
            options = PrerecordedOptions(
                model="nova-2",
                smart_format=True,
                punctuate=True,
                language="en-US",
            )
            
            # Transcribe (run sync method in thread to avoid blocking)
            response = await asyncio.to_thread(
                self.client.listen.prerecorded.v("1").transcribe_file,
                payload,
                options
            )
            
            # Extract and validate transcript
            if response and response.results and response.results.channels:
                channel = response.results.channels[0]
                if channel.alternatives and len(channel.alternatives) > 0:
                    transcript = channel.alternatives[0].transcript
                    
                    if transcript and len(transcript.strip()) > 0:
                        logger.info(f"✅ Transcript: '{transcript[:100]}...'")
                        return transcript.strip()
                    else:
                        logger.warning("⚠️ STT returned empty transcript")
                        return None
                else:
                    logger.warning("⚠️ No alternatives in STT response")
                    return None
            else:
                logger.error("❌ Invalid response from Deepgram")
                return None
            
        except Exception as e:
            logger.exception(f"❌ Transcription error: {e}")
            return None
    
    async def transcribe_audio_file(self, audio_path: str) -> Optional[str]:
        """
        Transcribe an audio file from disk
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text or None if failed
        """
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