"""
Voice Agent Service - AI Interviewer Brain
Optimized for FAST startup:
- Sends greeting immediately
- Loads acknowledgment cache in background
- Generates first question AFTER greeting
"""

import logging
import random
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from app.services.stt_service import STTService
from app.services.deepgram_tts_service import DeepgramTTSService as TTSService
from app.services.question_generator import QuestionGeneratorService
from app.models.interview import Question
from app.models.resume import ParsedData
from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceAgentService:

    DEFAULT_VOICE = "aura-athena-en"   # Updated

    def __init__(self):
        self.stt = STTService()
        self.tts = TTSService()
        self.question_generator = QuestionGeneratorService()

        self.ack_cache = {}
        self.ack_texts = [
            "Thank you for that answer.",
            "I appreciate your response.",
            "That's helpful to know.",
            "I see, thank you.",
            "Interesting perspective.",
            "Great, let's continue.",
            "Understood, thank you.",
        ]

        logger.info("🤖 Voice Agent initialized")
        logger.info(f"   STT: {'✅' if self.stt.client else '❌'}")
        logger.info(f"   TTS: {'✅' if self.tts.api_key else '❌'}")
        logger.info(f"   AI: {'✅' if settings.GROQ_API_KEY else '❌'}")

    # =====================================================================
    # ACK CACHE — NOW ASYNC BACKGROUND TASK
    # =====================================================================
    async def initialize_ack_cache(self, voice: Optional[str] = None):
        """Pre-generate acknowledgment audio WITHOUT blocking greeting."""
        logger.info("🎤 Background: Generating acknowledgment audio cache...")

        chosen_voice = voice or self.DEFAULT_VOICE

        for ack_text in self.ack_texts:
            try:
                audio_bytes = await self.tts.synthesize_speech(
                    text=ack_text, voice_name=chosen_voice
                )
                self.ack_cache[ack_text] = audio_bytes
                logger.info(f"   ✅ Cached: '{ack_text}' ({len(audio_bytes)} bytes)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to cache '{ack_text}': {e}")

        logger.info(f"✅ Background cache ready ({len(self.ack_cache)} entries)")

    # =====================================================================
    # GREETING — FIRST THING SENT
    # =====================================================================
    async def generate_greeting(
        self,
        candidate_name: str,
        interview_type: str,
        num_questions: int,
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:

        greeting_text = (
            f"Hello {candidate_name}! I'm Sarah, your AI interviewer. "
            f"This will be a {interview_type} interview with {num_questions} questions. "
            f"Please answer clearly and take your time. Let's begin!"
        )

        logger.info(f"👋 Generating greeting for '{candidate_name}'")

        audio_bytes = await self.tts.synthesize_speech(
            text=greeting_text, voice_name=voice or self.DEFAULT_VOICE
        )

        return {
            "text": greeting_text,
            "audio_bytes": audio_bytes or b"",
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": "greeting",
        }

    # =====================================================================
    # QUESTION GENERATION — FAST & SINGLE CALL
    # =====================================================================
    async def generate_and_synthesize_question(
        self,
        resume: ParsedData,
        job_description: Optional[str],
        conversation_history: list,
        interview_type: str,
        difficulty: str,
        question_number: int,
        total_questions: int,
        voice: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        logger.info(f"🚀 Generating question {question_number}/{total_questions}")

        try:
            asked_questions = [
                msg.text for msg in conversation_history
                if msg.speaker == "ai"
            ]

            questions = await self.question_generator.generate_questions(
                parsed_resume=resume,
                interview_type=interview_type,
                difficulty=difficulty,
                max_questions=1,
                job_description=job_description,
                asked_questions=asked_questions,
                conversation_history=conversation_history,
            )

            if not questions:
                logger.warning("⚠️ No question generated")
                return None

            question = questions[0]

            audio_bytes = await self.tts.synthesize_speech(
                text=question.question_text,
                voice_name=voice or self.DEFAULT_VOICE
            )

            return {
                "question": question,
                "audio_bytes": audio_bytes or b"",
                "text": question.question_text,
                "category": question.category,
                "difficulty": question.difficulty,
                "timestamp": datetime.utcnow().isoformat(),
                "message_type": "question",
            }

        except Exception as e:
            logger.exception(f"❌ Question generation failed: {e}")
            return None

    # =====================================================================
    # PROCESS ANSWER
    # =====================================================================
    async def process_answer(self, audio_bytes: bytes) -> Optional[str]:
        if not audio_bytes:
            return None

        try:
            logger.info(f"🎤 Processing answer ({len(audio_bytes)} bytes)")
            transcript = await self.stt.transcribe_audio_bytes(audio_bytes)
            return transcript
        except Exception as e:
            logger.exception(f"❌ STT error: {e}")
            return None

    # =====================================================================
    # ACK (uses cached audio instantly)
    # =====================================================================
    async def generate_acknowledgment(
        self,
        answer: str,
        voice: Optional[str] = None
    ) -> Dict[str, Any]:

        ack_text = random.choice(self.ack_texts)
        logger.info("💬 Sending acknowledgment")

        audio_bytes = self.ack_cache.get(ack_text)

        if not audio_bytes:  # fallback
            audio_bytes = await self.tts.synthesize_speech(
                text=ack_text,
                voice_name=voice or self.DEFAULT_VOICE
            )

        return {
            "text": ack_text,
            "audio_bytes": audio_bytes,
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": "acknowledgment",
        }

    # =====================================================================
    # CLOSING
    # =====================================================================
    async def generate_closing(
        self,
        candidate_name: str,
        voice: Optional[str] = None
    ) -> Dict[str, Any]:

        closing_text = (
            f"Thank you, {candidate_name}, for your time. "
            f"We'll now evaluate your answers. Good luck!"
        )

        audio_bytes = await self.tts.synthesize_speech(
            text=closing_text,
            voice_name=voice or self.DEFAULT_VOICE
        )

        return {
            "text": closing_text,
            "audio_bytes": audio_bytes or b"",
            "timestamp": datetime.utcnow().isoformat(),
            "message_type": "closing",
        }
