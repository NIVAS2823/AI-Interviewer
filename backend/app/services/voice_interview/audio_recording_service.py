"""
Audio Recording Service
Manages audio chunk collection and upload for voice interviews
"""
import io
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.r2_storage_service import R2StorageService

logger = logging.getLogger(__name__)


class AudioChunk:
    """Represents a single audio chunk with metadata"""
    
    def __init__(self, data: bytes, speaker: str, timestamp: datetime = None):
        self.data = data
        self.speaker = speaker
        self.timestamp = timestamp or datetime.utcnow()
        self.size = len(data)


class AudioRecordingService:
    """
    Service for managing audio recording during voice interviews
    
    Responsibilities:
    - Store audio chunks
    - Combine chunks
    - Upload to R2 storage
    """

    def __init__(self, r2_storage: Optional[R2StorageService] = None):
        """
        Initialize audio recording service
        
        Args:
            r2_storage: R2 storage service (optional, creates default)
        """
        self.r2_storage = r2_storage or R2StorageService()
        self.chunks: List[AudioChunk] = []
        self.recording_enabled = True

    def add_chunk(self, audio_data: bytes, speaker: str = "candidate") -> bool:
        """
        Add audio chunk to recording
        
        Args:
            audio_data: Raw audio bytes
            speaker: Speaker identifier ('candidate' or 'ai')
            
        Returns:
            True if chunk added successfully
        """
        if not self.recording_enabled or not audio_data:
            return False

        try:
            chunk = AudioChunk(
                data=audio_data,
                speaker=speaker,
                timestamp=datetime.utcnow()
            )
            
            self.chunks.append(chunk)
            
            logger.debug(
                f"💾 Saved audio chunk: {speaker}, {len(audio_data)} bytes "
                f"(total chunks: {len(self.chunks)})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save audio chunk: {e}")
            return False

    def get_chunk_count(self, speaker: Optional[str] = None) -> int:
        """
        Get number of chunks
        
        Args:
            speaker: Optional filter by speaker
            
        Returns:
            Number of chunks
        """
        if speaker:
            return len([c for c in self.chunks if c.speaker == speaker])
        return len(self.chunks)

    def get_total_size(self, speaker: Optional[str] = None) -> int:
        """
        Get total audio size
        
        Args:
            speaker: Optional filter by speaker
            
        Returns:
            Total size in bytes
        """
        chunks = self.chunks if not speaker else [c for c in self.chunks if c.speaker == speaker]
        return sum(c.size for c in chunks)

    def combine_chunks(self, speaker: Optional[str] = None) -> bytes:
        """
        Combine audio chunks into single audio file
        
        Args:
            speaker: Optional filter by speaker (default: all)
            
        Returns:
            Combined audio bytes
        """
        if not self.chunks:
            logger.warning("⚠️ No audio chunks to combine")
            return b""

        try:
            combined_audio = io.BytesIO()
            chunks_to_combine = self.chunks
            
            if speaker:
                chunks_to_combine = [c for c in self.chunks if c.speaker == speaker]

            for chunk in chunks_to_combine:
                combined_audio.write(chunk.data)

            audio_bytes = combined_audio.getvalue()
            
            logger.info(
                f"📦 Combined audio: {len(audio_bytes)} bytes from "
                f"{len(chunks_to_combine)} chunks"
            )
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Failed to combine audio chunks: {e}")
            return b""

    async def upload_recording(
        self,
        interview_id: str,
        candidate_id: str,
        question_count: int,
        speaker: str = "candidate",
        file_type: str = "webm",
    ) -> Optional[Dict[str, Any]]:
        """
        Combine chunks and upload to R2 storage
        
        Args:
            interview_id: Interview ID
            candidate_id: Candidate user ID
            question_count: Number of questions asked
            speaker: Speaker to upload (default: candidate only)
            file_type: Audio file format
            
        Returns:
            Upload result dict with URL and metadata, or None on failure
        """
        try:
            # Combine chunks for specified speaker
            audio_bytes = self.combine_chunks(speaker=speaker)
            
            if not audio_bytes or len(audio_bytes) == 0:
                logger.warning(f"⚠️ No {speaker} audio to upload")
                return None

            logger.info(
                f"📼 Uploading interview recording: {len(audio_bytes)} bytes "
                f"({len(audio_bytes) / 1_000_000:.2f} MB)"
            )

            # Upload to R2
            result = await self.r2_storage.upload_recording(
                interview_id=interview_id,
                audio_data=audio_bytes,
                file_type=file_type,
                metadata={
                    'candidate_id': str(candidate_id),
                    'question_count': str(question_count),
                    'total_chunks': str(len(self.chunks)),
                    'speaker': speaker,
                }
            )

            if result:
                logger.info(f"✅ Recording uploaded to R2")
                logger.info(f"   URL: {result.get('public_url')}")
                return result
            else:
                logger.error("❌ Failed to upload recording to R2")
                return None

        except Exception as e:
            logger.exception(f"❌ Error uploading interview recording: {e}")
            return None

    def clear_chunks(self):
        """Clear all audio chunks (cleanup)"""
        self.chunks.clear()
        logger.debug("🗑️ Cleared all audio chunks")

    def disable_recording(self):
        """Disable recording"""
        self.recording_enabled = False
        logger.info("⏸️ Recording disabled")

    def enable_recording(self):
        """Enable recording"""
        self.recording_enabled = True
        logger.info("▶️ Recording enabled")

    def get_recording_stats(self) -> Dict[str, Any]:
        """
        Get recording statistics
        
        Returns:
            Dict with recording stats
        """
        candidate_chunks = self.get_chunk_count("candidate")
        ai_chunks = self.get_chunk_count("ai")
        candidate_size = self.get_total_size("candidate")
        ai_size = self.get_total_size("ai")
        
        return {
            "total_chunks": len(self.chunks),
            "candidate_chunks": candidate_chunks,
            "ai_chunks": ai_chunks,
            "total_size_bytes": self.get_total_size(),
            "candidate_size_bytes": candidate_size,
            "ai_size_bytes": ai_size,
            "candidate_size_mb": round(candidate_size / 1_000_000, 2),
            "ai_size_mb": round(ai_size / 1_000_000, 2),
            "recording_enabled": self.recording_enabled,
        }

    def validate_audio_size(self, audio_data: bytes, max_size_mb: float = 1.0) -> bool:
        """
        Validate audio size
        
        Args:
            audio_data: Audio bytes to validate
            max_size_mb: Maximum size in MB
            
        Returns:
            True if valid, False otherwise
        """
        size_mb = len(audio_data) / 1_000_000
        
        if size_mb > max_size_mb:
            logger.warning(
                f"⚠️ Large audio file: {len(audio_data)} bytes ({size_mb:.1f}MB) "
                f"exceeds max of {max_size_mb}MB"
            )
            return False
        
        return True