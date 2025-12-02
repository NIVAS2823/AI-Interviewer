"""
Voice Agent Service - AI Interviewer Brain
Orchestrates STT (Deepgram) + AI (Groq) + TTS (Azure)
Clean, production-ready implementation
"""

import logging
import random
from typing import Optional, Dict, Any
from datetime import datetime

from app.services.stt_service import STTService
from app.services.tts_service import TTSService
from app.services.question_generator import QuestionGeneratorService
from app.models.interview import Question, ConversationMessage
from app.models.resume import ParsedData
from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceAgentService:
    """
    Intelligent Voice Interview Agent
    """

    DEFAULT_VOICE = "en-IN-NeerjaNeural"

    def __init__(self):
        """Initialize all AI services"""
        self.stt = STTService()
        self.tts = TTSService()
        self.question_generator = QuestionGeneratorService()

        logger.info("🤖 Voice Agent initialized")
        logger.info(f"   STT: {'✅' if self.stt.client else '❌'}")
        logger.info(f"   TTS: {'✅' if self.tts.speech_config else '❌'}")
        logger.info(f"   AI: {'✅' if settings.GROQ_API_KEY else '❌'}")

    def is_ready(self) -> bool:
        return (
            self.stt.client is not None
            and self.tts.speech_config is not None
            and bool(settings.GROQ_API_KEY)
        )

    # ==================== GREETING ====================

    async def generate_greeting(
        self,
        candidate_name: str,
        interview_type: str,
        num_questions: int,
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:

        greeting_text = (
            f"Hello {candidate_name}! I'm Sarah, your AI interviewer. "
            f"Today, I'll be conducting a {interview_type} interview with {num_questions} questions. "
            f"Please answer each question clearly and take your time. Let's begin!"
        )

        logger.info(f"👋 Generating greeting for '{candidate_name}'")

        audio_bytes = await self.tts.synthesize_speech(
            text=greeting_text,
            voice_name=voice or self.DEFAULT_VOICE
        )

        return {
            "text": greeting_text,
            "audio_bytes": audio_bytes or b"",
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": "greeting",   # 🔥 FIX
        }

    # ==================== QUESTION ASKING ====================

    async def ask_question(
        self,
        question: Question,
        voice: Optional[str] = None
    ) -> Dict[str, Any]:

        question_text = question.question_text

        logger.info(f"❓ Asking question: '{question_text[:80]}...'")

        audio_bytes = await self.tts.synthesize_speech(
            text=question_text,
            voice_name=voice or self.DEFAULT_VOICE
        )

        return {
            "text": question_text,
            "audio_bytes": audio_bytes or b"",
            "category": question.category,
            "difficulty": question.difficulty,
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": "question",   # 🔥 FIX
        }

    async def generate_next_question_dynamic(
        self,
        resume: ParsedData,
        job_description: Optional[str],
        conversation_history: list,
        interview_type: str,
        difficulty: str,
        question_number: int,
        total_questions: int,
    ) -> Optional[Question]:

        logger.info(f"🧠 Generating question {question_number}/{total_questions}")

        try:
            questions = await self.question_generator.generate_questions(
                parsed_resume=resume,
                interview_type=interview_type,
                difficulty=difficulty,
                max_questions=1,
            )

            if questions and len(questions) > 0:
                logger.info("✅ Question generated successfully")
                return questions[0]

            logger.warning("⚠️ Question generator returned empty list")
            return None

        except Exception as e:
            logger.exception(f"❌ Question generation failed: {e}")
            return None

    # ==================== PROCESS ANSWER ====================

    async def process_answer(self, audio_bytes: bytes) -> Optional[str]:

        if not audio_bytes or len(audio_bytes) == 0:
            logger.warning("⚠️ Empty audio bytes provided")
            return None

        try:
            logger.info(f"🎤 Processing answer ({len(audio_bytes)} bytes)")
            transcript = await self.stt.transcribe_audio_bytes(audio_bytes)

            if transcript:
                logger.info(f"✅ Transcript: '{transcript[:120]}...'")
                return transcript

            logger.warning("⚠️ Transcription returned None")
            return None

        except Exception as e:
            logger.exception(f"❌ Answer processing failed: {e}")
            return None

    # ==================== ACKNOWLEDGMENT ====================

    async def generate_acknowledgment(
        self,
        answer: str,
        voice: Optional[str] = None
    ) -> Dict[str, Any]:

        acknowledgments = [
            "Thank you for that answer.",
            "I appreciate your response.",
            "That's helpful to know.",
            "I see, thank you.",
            "Interesting perspective.",
        ]

        ack_text = random.choice(acknowledgments)

        logger.info("💬 Generating acknowledgment")

        audio_bytes = await self.tts.synthesize_speech(
            text=ack_text,
            voice_name=voice or self.DEFAULT_VOICE
        )

        return {
            "text": ack_text,
            "audio_bytes": audio_bytes or b"",
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": "acknowledgment",   # 🔥 FIX
        }

    # ==================== CLOSING ====================

    async def generate_closing(
        self,
        candidate_name: str,
        voice: Optional[str] = None
    ) -> Dict[str, Any]:

        closing_text = (
            f"Thank you, {candidate_name}, for your time today. "
            f"You've answered all the questions. We'll now evaluate your responses "
            f"and generate your detailed feedback. Good luck!"
        )

        logger.info("👋 Generating closing message")

        audio_bytes = await self.tts.synthesize_speech(
            text=closing_text,
            voice_name=voice or self.DEFAULT_VOICE
        )

        return {
            "text": closing_text,
            "audio_bytes": audio_bytes or b"",
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": "closing",   # 🔥 FIX
        }
