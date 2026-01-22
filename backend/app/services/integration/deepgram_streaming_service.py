"""
Deepgram Streaming Service
Real-time speech-to-text for interim transcripts during recording
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class DeepgramStreamingService:
    """
    Real-time streaming STT service using Deepgram Live API
    
    Provides interim transcripts while user is speaking
    Separate from prerecorded API used for final transcripts
    """

    def __init__(self, on_transcript: Callable[[str, bool], Awaitable[None]]):
        """
        Initialize streaming service
        
        Args:
            on_transcript: Async callback function(text: str, is_final: bool)
                          Called when interim or final transcript is received
        """
        self.on_transcript = on_transcript
        self.client: Optional[DeepgramClient] = None
        self.connection = None
        self.is_connected = False
        self._lock = asyncio.Lock()
        self._event_loop = None  # Store the event loop

    async def start_streaming(self) -> bool:
        """
        Start Deepgram streaming connection
        
        Returns:
            True if connection successful, False otherwise
        """
        api_key = settings.DEEPGRAM_API_KEY

        if not api_key:
            logger.error("❌ DEEPGRAM_API_KEY not found")
            return False

        try:
            async with self._lock:
                # Store the current event loop
                self._event_loop = asyncio.get_running_loop()
                
                # Initialize Deepgram client
                config = DeepgramClientOptions(
                    api_key=api_key,
                    options={"keepalive": "true"}
                )
                self.client = DeepgramClient(api_key, config)

                # Configure streaming options
                options = LiveOptions(
                    model="nova-2",
                    language="en-US",
                    punctuate=True,
                    smart_format=True,
                    interim_results=True,  # ✅ Enable interim transcripts
                    encoding="linear16",  # PCM format
                    sample_rate=16000,
                    channels=1,
                )

                # Connect to live transcription
                self.connection = self.client.listen.live.v("1")

                # Register event handlers
                self.connection.on(
                    LiveTranscriptionEvents.Transcript,
                    self._on_transcript_received
                )

                self.connection.on(
                    LiveTranscriptionEvents.Error,
                    self._on_error
                )

                self.connection.on(
                    LiveTranscriptionEvents.Close,
                    self._on_close
                )

                # Start connection (synchronous)
                if not self.connection.start(options):
                    logger.error("❌ Failed to start Deepgram streaming")
                    return False

                self.is_connected = True
                logger.info("✅ Deepgram streaming started")
                return True

        except Exception as e:
            logger.exception(f"❌ Failed to start streaming: {e}")
            return False

    async def send_audio_chunk(self, audio_bytes: bytes) -> bool:
        """
        Send audio chunk to Deepgram for processing
        
        Args:
            audio_bytes: Raw audio data (PCM)
            
        Returns:
            True if sent successfully
        """
        if not self.is_connected or not self.connection:
            logger.warning("⚠️ Cannot send audio: not connected")
            return False

        try:
            # Send to Deepgram (synchronous)
            logger.debug(f"📤 Sending {len(audio_bytes)} bytes to Deepgram")
            success = self.connection.send(audio_bytes)

            if not success:
                logger.error("❌ Deepgram send returned False")
                self.is_connected = False
                return False
            
            logger.debug(f"✅ Sent {len(audio_bytes)} bytes successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send audio chunk: {e}")
            self.is_connected = False
            return False

    async def stop_streaming(self):
        """Stop streaming and close connection"""
        try:
            async with self._lock:
                if self.connection:
                    try:
                        # Finish connection (synchronous)
                        self.connection.finish()
                    except Exception as e:
                        logger.warning(f"⚠️ Error finishing connection: {e}")

                    self.connection = None

                self.is_connected = False
                self._event_loop = None
                logger.info("✅ Deepgram streaming stopped")

        except Exception as e:
            logger.error(f"❌ Error stopping streaming: {e}")

    # ============================================================
    # Event Handlers (called from Deepgram thread)
    # ============================================================

    def _on_transcript_received(self, *args, **kwargs):
        """
        Handle transcript received from Deepgram
        
        This runs in Deepgram's thread, not the main asyncio loop
        """
        try:
            # Extract result from args
            result = kwargs.get("result") or (args[1] if len(args) > 1 else None)
            if not result:
                return

            # Get transcript from result
            alternatives = result.channel.alternatives
            if not alternatives:
                return

            transcript_text = alternatives[0].transcript
            if not transcript_text or not transcript_text.strip():
                return

            # Check if this is a final result
            is_final = getattr(result, "is_final", False)

            # Schedule callback in the main event loop
            if self.on_transcript and self._event_loop:
                try:
                    # Use asyncio.run_coroutine_threadsafe for thread safety
                    asyncio.run_coroutine_threadsafe(
                        self.on_transcript(transcript_text.strip(), is_final),
                        self._event_loop
                    )
                except Exception as e:
                    logger.error(f"❌ Error scheduling callback: {e}")

        except Exception as e:
            logger.error(f"❌ Error processing transcript: {e}")

    def _on_error(self, *args, **kwargs):
        """Handle streaming errors"""
        error = kwargs.get("error") or (args[1] if len(args) > 1 else "Unknown error")
        logger.error(f"❌ Deepgram streaming error: {error}")
        self.is_connected = False

    def _on_close(self, *args, **kwargs):
        """Handle connection close"""
        logger.info("🔌 Deepgram streaming connection closed")
        self.is_connected = False