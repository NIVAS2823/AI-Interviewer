"""
WebSocket Message Service
Handles message formatting and serialization for voice interviews
"""
import base64
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketMessageService:
    """
    Service for formatting WebSocket messages
    
    Responsibilities:
    - Message formatting
    - Audio encoding (base64)
    - Message type standardization
    """

    @staticmethod
    def format_audio_message(
        text: str,
        audio_bytes: bytes,
        message_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format audio message for WebSocket transmission
        
        Args:
            text: Message text
            audio_bytes: Audio data
            message_type: Message type (greeting, question, acknowledgment, closing)
            metadata: Optional metadata
            
        Returns:
            Formatted message dict
        """
        try:
            audio_base64 = base64.b64encode(audio_bytes or b"").decode("utf-8")
            
            payload = {
                "type": message_type,
                "text": text,
                "audio": audio_base64,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }
            
            logger.debug(
                f"📤 Formatted {message_type} message: "
                f"{len(text)} chars, {len(audio_bytes or b'')} bytes audio"
            )
            
            return payload
            
        except Exception as e:
            logger.error(f"Failed to format audio message: {e}")
            return {
                "type": "error",
                "message": "Failed to format audio message"
            }

    @staticmethod
    def format_greeting(
        text: str,
        audio_bytes: bytes,
        candidate_name: str,
        num_questions: int,
    ) -> Dict[str, Any]:
        """Format greeting message"""
        return WebSocketMessageService.format_audio_message(
            text=text,
            audio_bytes=audio_bytes,
            message_type="greeting",
            metadata={
                "candidate_name": candidate_name,
                "num_questions": num_questions,
            }
        )

    @staticmethod
    def format_question(
        text: str,
        audio_bytes: bytes,
        question_number: int,
        total_questions: int,
        category: str,
        difficulty: str,
    ) -> Dict[str, Any]:
        """Format question message"""
        return WebSocketMessageService.format_audio_message(
            text=text,
            audio_bytes=audio_bytes,
            message_type="question",
            metadata={
                "question_number": question_number,
                "total_questions": total_questions,
                "category": category,
                "difficulty": difficulty,
            }
        )

    @staticmethod
    def format_acknowledgment(
        text: str,
        audio_bytes: bytes,
    ) -> Dict[str, Any]:
        """Format acknowledgment message"""
        return WebSocketMessageService.format_audio_message(
            text=text,
            audio_bytes=audio_bytes,
            message_type="acknowledgment",
        )

    @staticmethod
    def format_closing(
        text: str,
        audio_bytes: bytes,
        total_questions: int,
    ) -> Dict[str, Any]:
        """Format closing message"""
        return WebSocketMessageService.format_audio_message(
            text=text,
            audio_bytes=audio_bytes,
            message_type="closing",
            metadata={
                "total_questions": total_questions,
            }
        )

    @staticmethod
    def format_transcription(text: str) -> Dict[str, Any]:
        """Format transcription message"""
        return {
            "type": "transcription",
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    def format_interim_transcript(text: str, is_final: bool = False) -> Dict[str, Any]:
        """
        Format interim transcript message for real-time display
        
        Args:
            text: Interim transcript text
            is_final: Whether this is the final result from streaming
            
        Returns:
            Formatted interim transcript message
        """
        return {
            "type": "interim_transcript",
            "text": text,
            "is_final": is_final,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def format_error(
        error: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format error message (P0-safe, frontend-readable)
        """
        payload = {
        "type": "error",
        "message": error,
        "code": code,
        "timestamp": datetime.utcnow().isoformat(),
        }

        if details:
            payload["details"] = details

        return payload


    @staticmethod
    def format_status(
        status: str,
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format status message"""
        return {
            "type": "status",
            "status": status,
            "message": message,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def format_progress(
        current_question: int,
        total_questions: int,
        percentage: float,
    ) -> Dict[str, Any]:
        """Format progress update message"""
        return {
            "type": "progress",
            "current_question": current_question,
            "total_questions": total_questions,
            "percentage": round(percentage, 1),
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def format_interview_complete(
        total_questions: int,
        duration_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Format interview completion message"""
        return {
            "type": "interview_complete",
            "message": "Interview completed successfully",
            "total_questions": total_questions,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def format_pong() -> Dict[str, Any]:
        """Format pong response"""
        return {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def validate_audio_size(audio_bytes: bytes, max_size_mb: float = 1.0) -> tuple[bool, Optional[str]]:
        """
        Validate audio size
        
        Args:
            audio_bytes: Audio data
            max_size_mb: Maximum size in MB
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not audio_bytes:
            return False, "No audio data provided"
        
        size_mb = len(audio_bytes) / 1_000_000
        
        if size_mb > max_size_mb:
            return False, f"Audio too large: {size_mb:.1f}MB (max: {max_size_mb}MB)"
        
        return True, None

    @staticmethod
    def parse_client_message(message: Dict[str, Any]) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Parse message from client
        
        Args:
            message: Raw message dict
            
        Returns:
            Tuple of (message_type, message_data)
        """
        try:
            msg_type = message.get("type")
            
            if not msg_type:
                logger.warning("Received message without type")
                return None, None
            
            return msg_type, message
            
        except Exception as e:
            logger.error(f"Failed to parse client message: {e}")
            return None, None