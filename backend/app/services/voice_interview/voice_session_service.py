"""
Voice Session Service
Manages voice interview session state and conversation history
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.interview import ConversationMessage, Question
from app.services.integration.groq_service import GroqService

logger = logging.getLogger(__name__)


class VoiceSessionState:
    """
    Voice interview session state
    Tracks all session-level data
    """

    def __init__(
        self,
        interview_id: str,
        user_id: str,
        max_questions: int = 5,
        voice: str = "aura-athena-en",
    ):
        """
        Initialize session state
        
        Args:
            interview_id: Interview ID
            user_id: User/candidate ID
            max_questions: Maximum questions to ask
            voice: Voice model to use
        """
        self.interview_id = interview_id
        self.user_id = user_id
        self.max_questions = max_questions
        self.voice = voice
        
        # Session status
        self.is_active = False
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # Progress tracking
        self.current_question_number = 0
        self.asked_questions: List[str] = []
        
        # Conversation
        self.conversation_history: List[ConversationMessage] = []
        
        # Interview data (loaded on start)
        self.interview_data: Optional[Dict[str, Any]] = None
        self.resume_data: Optional[Any] = None
        self.candidate_name: Optional[str] = None
        self.groq_service: GroqService | None = None

    def start_session(self):
        """Mark session as started"""
        self.is_active = True
        self.started_at = datetime.utcnow()
        logger.info(f"✅ Session started: {self.interview_id}")

    def end_session(self):
        """Mark session as completed"""
        self.is_active = False
        self.completed_at = datetime.utcnow()
        logger.info(f"✅ Session completed: {self.interview_id}")

    def add_question(self, question: Question):
        """
        Add question to asked questions
        
        Args:
            question: Question that was asked
        """
        self.asked_questions.append(question.question_text)
        self.current_question_number += 1
        
        logger.info(
            f"📝 Question {self.current_question_number}/{self.max_questions} tracked"
        )

    def add_message(self, speaker: str, text: str, timestamp: Optional[datetime] = None):
        """
        Add message to conversation history
        
        Args:
            speaker: Speaker identifier ('ai' or 'candidate')
            text: Message text
            timestamp: Message timestamp (optional)
        """
        message = ConversationMessage(
            speaker=speaker,
            text=text,
            timestamp=timestamp or datetime.utcnow()
        )
        
        self.conversation_history.append(message)
        
        logger.debug(f"💬 Message added: {speaker} ({len(text)} chars)")

    def is_complete(self) -> bool:
        """Check if interview is complete"""
        return self.current_question_number >= self.max_questions

    def get_progress_percentage(self) -> float:
        """Get interview progress as percentage"""
        if self.max_questions == 0:
            return 0.0
        return (self.current_question_number / self.max_questions) * 100

    def get_session_duration(self) -> Optional[int]:
        """Get session duration in seconds"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        duration = end_time - self.started_at
        return int(duration.total_seconds())

    def get_statistics(self) -> Dict[str, Any]:
        """Get session statistics"""
        ai_messages = [m for m in self.conversation_history if m.speaker == "ai"]
        candidate_messages = [m for m in self.conversation_history if m.speaker == "candidate"]
        
        return {
            "interview_id": self.interview_id,
            "is_active": self.is_active,
            "current_question": self.current_question_number,
            "max_questions": self.max_questions,
            "progress_percentage": self.get_progress_percentage(),
            "total_messages": len(self.conversation_history),
            "ai_messages": len(ai_messages),
            "candidate_messages": len(candidate_messages),
            "asked_questions_count": len(self.asked_questions),
            "duration_seconds": self.get_session_duration(),
            "is_complete": self.is_complete(),
        }


class VoiceSessionService:
    """
    Service for managing voice interview sessions
    
    Responsibilities:
    - Session lifecycle management
    - Conversation history tracking
    - Progress tracking
    """

    def __init__(self):
        """Initialize voice session service"""
        self.sessions: Dict[str, VoiceSessionState] = {}

    def create_session(
        self,
        interview_id: str,
        user_id: str,
        max_questions: int = 5,
        voice: str = "aura-athena-en",
    ) -> VoiceSessionState:
        """
        Create new session
        
        Args:
            interview_id: Interview ID
            user_id: User/candidate ID
            max_questions: Maximum questions
            voice: Voice model
            
        Returns:
            New VoiceSessionState instance
        """
        session = VoiceSessionState(
            interview_id=interview_id,
            user_id=user_id,
            max_questions=max_questions,
            voice=voice,
        )
        
        self.sessions[interview_id] = session
        
        logger.info(f"📝 Session created: {interview_id}")
        
        return session

    def get_session(self, interview_id: str) -> Optional[VoiceSessionState]:
        """Get session by interview ID"""
        return self.sessions.get(interview_id)

    def remove_session(self, interview_id: str):
        """Remove session (cleanup)"""
        if interview_id in self.sessions:
            del self.sessions[interview_id]
            logger.info(f"🗑️ Session removed: {interview_id}")

    def get_active_sessions(self) -> List[VoiceSessionState]:
        """Get all active sessions"""
        return [s for s in self.sessions.values() if s.is_active]

    def get_session_count(self) -> int:
        """Get total number of sessions"""
        return len(self.sessions)

    def validate_session(self, session: VoiceSessionState) -> tuple[bool, Optional[str]]:
        """
        Validate session state
        
        Args:
            session: Session to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not session.interview_data:
            return False, "Interview data not loaded"
        
        if not session.resume_data:
            return False, "Resume data not loaded"
        
        if session.is_complete():
            return False, "Interview already completed"
        
        if not session.is_active:
            return False, "Session not active"
        
        return True, None

    def can_ask_next_question(self, session: VoiceSessionState) -> bool:
        """Check if next question can be asked"""
        return (
            session.is_active and
            not session.is_complete() and
            session.interview_data is not None
        )

    def format_conversation_for_ai(
        self,
        session: VoiceSessionState,
        max_messages: int = 8
    ) -> List[Dict[str, str]]:
        """
        Format conversation history for AI/LLM
        
        Args:
            session: Session state
            max_messages: Maximum recent messages to include
            
        Returns:
            List of formatted message dicts
        """
        recent_messages = session.conversation_history[-max_messages:]
        
        formatted = []
        for msg in recent_messages:
            formatted.append({
                "role": "assistant" if msg.speaker == "ai" else "user",
                "content": msg.text,
            })
        
        return formatted

    def get_session_summary(self, session: VoiceSessionState) -> str:
        """
        Get human-readable session summary
        
        Args:
            session: Session state
            
        Returns:
            Summary string
        """
        stats = session.get_statistics()
        
        duration = stats["duration_seconds"]
        duration_str = f"{duration}s" if duration else "N/A"
        
        return (
            f"Interview {session.interview_id}: "
            f"Q{stats['current_question']}/{stats['max_questions']} "
            f"({stats['progress_percentage']:.0f}%), "
            f"{stats['total_messages']} messages, "
            f"Duration: {duration_str}, "
            f"Status: {'Active' if session.is_active else 'Inactive'}"
        )