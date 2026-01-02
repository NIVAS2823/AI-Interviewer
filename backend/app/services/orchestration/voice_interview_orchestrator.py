"""
Voice Interview Orchestrator
Coordinates voice interview flow using domain services
"""
import logging
import asyncio
from typing import Optional, Dict, Any

from app.models.interview import Question
from app.models.resume import ParsedData
from app.services.repositories.repository_factory import get_repositories
from app.services.voice_interview.voice_session_service import VoiceSessionState, VoiceSessionService
from app.services.voice_interview.audio_recording_service import AudioRecordingService
from app.services.voice_interview.websocket_message_service import WebSocketMessageService
from app.services.voice_agent_service import VoiceAgentService
from app.services.domain.template_question_service import TemplateQuestionService
from app.services.domain.deduplication_service import DeduplicationService

from app.services.integration.groq_service import GroqService

logger = logging.getLogger(__name__)


class VoiceInterviewOrchestrator:
    """
    Orchestrates voice interview flow
    
    Responsibilities:
    - Coordinate interview lifecycle
    - Generate questions
    - Process answers
    - Manage session state
    
    Does NOT:
    - Handle WebSocket I/O (that's the handler's job)
    - Access database directly (uses repositories)
    - Format messages (uses message service)
    """

    def __init__(self, db):
        """
        Initialize orchestrator
        
        Args:
            db: Database connection
        """
        self.db = db
        self.repos = get_repositories(db)
        
        # Services
        self.session_service = VoiceSessionService()
        self.message_service = WebSocketMessageService()
        self.voice_agent = VoiceAgentService()
        self.template_service = TemplateQuestionService()
        self.dedupe_service = DeduplicationService(similarity_threshold=0.94)

    async def start_session(
        self,
        interview_id: str,
        user_id: str,
        voice: str = "aura-athena-en"
    ) -> tuple[bool, Optional[VoiceSessionState], Optional[str]]:
        """
        Start voice interview session
        
        Args:
            interview_id: Interview ID
            user_id: User/candidate ID
            voice: Voice model to use
            
        Returns:
            Tuple of (success, session_state, error_message)
        """
        try:
            # Validate interview exists
            interview = await self.repos.interviews.get_interview(interview_id)
            
            if not interview:
                return False, None, "Interview not found"

            # Validate authorization
            if str(interview.candidate_id) != str(user_id):
                return False, None, "Not authorized for this interview"

            # Load resume
            resume_data = await self.repos.resumes.get_parsed_data(str(interview.resume_id))
            
            if not resume_data:
                return False, None, "Resume data not found or not parsed"

            # Reset questions for voice interview (clean slate)
            logger.info("🧹 Resetting questions for voice interview")
            await self.repos.interviews.update(
                interview_id,
                {"$set": {"questions": []}}
            )

            # Create session state
            session = self.session_service.create_session(
                interview_id=interview_id,
                user_id=user_id,
                max_questions=interview.max_questions,
                voice=voice,
            )

            # Load data into session
            session.interview_data = interview.model_dump()
            session.resume_data = resume_data
            session.candidate_name = resume_data.name or "there"

            session.groq_service = GroqService()

            logger.info(
        f"✓ Groq client initialized for session {session.interview_id}"
    )
            
            # Start session
            session.start_session()

            # Initialize voice agent cache (background)
            logger.info("🎤 Initializing voice agent cache...")
            asyncio.create_task(self.voice_agent.initialize_ack_cache(voice=voice))

            logger.info(f"✅ Session started: {interview_id}")
            
            return True, session, None

        except Exception as e:
            logger.exception(f"❌ Failed to start session: {e}")
            return False, None, f"Failed to start session: {str(e)}"

    async def generate_greeting(
        self,
        session: VoiceSessionState
    ) -> Optional[Dict[str, Any]]:
        """
        Generate greeting message
        
        Args:
            session: Session state
            
        Returns:
            Formatted greeting message dict
        """
        try:
            logger.info("👋 Generating greeting")

            greeting = await self.voice_agent.generate_greeting(
                candidate_name=session.candidate_name,
                interview_type=session.interview_data.get("interview_type", "mixed"),
                num_questions=session.max_questions,
                voice=session.voice,
            )

            # Add to conversation history
            session.add_message("ai", greeting["text"], greeting["timestamp"])

            # Save to database
            await self.repos.conversations.add_message(
                session.interview_id,
                "ai",
                greeting["text"]
            )

            # Format message
            return self.message_service.format_greeting(
                text=greeting["text"],
                audio_bytes=greeting["audio_bytes"],
                candidate_name=session.candidate_name,
                num_questions=session.max_questions,
            )

        except Exception as e:
            logger.exception(f"❌ Greeting generation failed: {e}")
            return None

    async def generate_next_question(
        self,
        session: VoiceSessionState,
        audio_recording: AudioRecordingService,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate and send next question
        
        Args:
            session: Session state
            audio_recording: Audio recording service (for saving AI audio)
            
        Returns:
            Formatted question message dict
        """
        try:
            # Check if complete
            if session.is_complete():
                logger.info(f"✅ All questions asked ({session.max_questions})")
                return None

            logger.info(
                f"🧠 Generating question {session.current_question_number + 1}/"
                f"{session.max_questions}"
            )

            # Generate question with deduplication
            question, question_audio = await self._generate_unique_question(session)

            if not question:
                logger.error("❌ Failed to generate unique question")
                return None

            # Save audio chunk (AI question)
            if question_audio:
                audio_recording.add_chunk(question_audio, speaker="ai")

            # Format message
            message = self.message_service.format_question(
                text=question.question_text,
                audio_bytes=question_audio or b"",
                question_number=session.current_question_number + 1,
                total_questions=session.max_questions,
                category=question.category,
                difficulty=question.difficulty,
            )

            # Update session state
            session.add_question(question)
            session.add_message("ai", question.question_text)

            # Save to database
            await self.repos.conversations.add_message(
                session.interview_id,
                "ai",
                question.question_text
            )
            
            await self.repos.interviews.add_question(session.interview_id, question)

            logger.info(
                f"📝 Question {session.current_question_number}/"
                f"{session.max_questions} sent"
            )

            return message

        except Exception as e:
            logger.exception(f"❌ Question generation failed: {e}")
            return None

    async def _generate_unique_question(
        self,
        session: VoiceSessionState,
        max_attempts: int = 5
    ) -> tuple[Optional[Question], Optional[bytes]]:
        """
        Generate unique question with retry logic
        
        Args:
            session: Session state
            max_attempts: Maximum generation attempts
            
        Returns:
            Tuple of (question, audio_bytes)
        """
        for attempt in range(1, max_attempts + 1):
            try:
                # Generate question + TTS in parallel
                result = await self.voice_agent.generate_and_synthesize_question(
                    resume=session.resume_data,
                    job_description=session.interview_data.get("job_description"),
                    conversation_history=session.conversation_history,
                    interview_type=session.interview_data.get("interview_type", "mixed"),
                    difficulty=session.interview_data.get("difficulty", "medium"),
                    question_number=session.current_question_number + 1,
                    total_questions=session.max_questions,
                    voice=session.voice,
                )

                if not result or not result.get("question"):
                    logger.warning(f"⚠️ Empty result on attempt {attempt}")
                    await asyncio.sleep(0.3)
                    continue

                candidate_q = result["question"]
                q_text = getattr(candidate_q, "question_text", "").strip()

                if not q_text:
                    logger.warning(f"⚠️ Empty question on attempt {attempt}")
                    continue

                # Check for duplicates using deduplication service
                is_duplicate = not self.dedupe_service.filter_duplicate_questions(
                    questions=[candidate_q],
                    asked_questions=session.asked_questions,
                    conversation_history=[],
                )

                if is_duplicate:
                    logger.warning(f"🔄 Duplicate question on attempt {attempt}")
                    await asyncio.sleep(0.5)
                    continue

                # Success!
                logger.info(f"✅ Unique question generated on attempt {attempt}")
                return candidate_q, result.get("audio_bytes")

            except Exception as e:
                logger.error(f"❌ Attempt {attempt} failed: {e}")
                await asyncio.sleep(0.3)

        # Fallback to template question
        logger.warning("⚠️ Using fallback template question")
        fallback_q = self.template_service.get_questions(
            interview_type=session.interview_data.get("interview_type", "mixed"),
            max_questions=1,
            difficulty=session.interview_data.get("difficulty", "medium"),
        )[0]

        # Generate TTS for fallback
        fallback_response = await self.voice_agent.ask_question(fallback_q)
        
        return fallback_q, fallback_response.get("audio_bytes")

    async def process_answer(
        self,
        session: VoiceSessionState,
        audio_data: bytes,
        audio_recording: AudioRecordingService,
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Process candidate's audio answer
        
        Args:
            session: Session state
            audio_data: Audio bytes
            audio_recording: Audio recording service
            
        Returns:
            Tuple of (success, error_message, acknowledgment_message)
        """
        try:
            # Validate audio
            is_valid, error = self.message_service.validate_audio_size(audio_data)
            if not is_valid:
                return False, error, None

            logger.info(f"🎤 Processing answer: {len(audio_data)} bytes")

            # Save audio chunk
            audio_recording.add_chunk(audio_data, speaker="candidate")

            # Transcribe
            transcript = await self.voice_agent.process_answer(audio_data)

            if not transcript or len(transcript.strip()) == 0:
                return False, "Could not transcribe audio. Please speak louder and try again.", None

            logger.info(f"📝 Transcribed: {transcript[:100]}...")

            # Update session
            session.add_message("candidate", transcript)

            # Save to database
            await self.repos.conversations.add_message(
                session.interview_id,
                "candidate",
                transcript
            )

            # Generate acknowledgment
            ack = await self.voice_agent.generate_acknowledgment(transcript)

            # Save AI acknowledgment audio
            if ack.get("audio_bytes"):
                audio_recording.add_chunk(ack["audio_bytes"], speaker="ai")

            # Update session
            session.add_message("ai", ack["text"], ack["timestamp"])

            # Save to database
            await self.repos.conversations.add_message(
                session.interview_id,
                "ai",
                ack["text"]
            )

            # Format acknowledgment message
            ack_message = self.message_service.format_acknowledgment(
                text=ack["text"],
                audio_bytes=ack["audio_bytes"],
            )

            return True, None, ack_message

        except Exception as e:
            logger.exception(f"❌ Answer processing failed: {e}")
            return False, f"Failed to process answer: {str(e)}", None

    async def end_session(
        self,
        session: VoiceSessionState,
        audio_recording: AudioRecordingService,
    ) -> Optional[Dict[str, Any]]:
        """
        End voice interview session
        
        Args:
            session: Session state
            audio_recording: Audio recording service
            
        Returns:
            Formatted closing message dict
        """
        try:
            logger.info(f"👋 Ending session: {session.interview_id}")

            # Generate closing message
            closing = await self.voice_agent.generate_closing(
                session.candidate_name,
                voice=session.voice
            )

            # Save AI closing audio
            if closing.get("audio_bytes"):
                audio_recording.add_chunk(closing["audio_bytes"], speaker="ai")

            # Save to database
            await self.repos.conversations.add_message(
                session.interview_id,
                "ai",
                closing["text"]
            )

            # Mark interview as completed
            await self.repos.interviews.update_status(
                session.interview_id,
                "completed",
                {"completed_at": session.completed_at}
            )

            # Upload recording
            upload_result = await audio_recording.upload_recording(
                interview_id=session.interview_id,
                candidate_id=session.user_id,
                question_count=session.current_question_number,
            )

            if upload_result:
                # Save recording URL to database
                await self.repos.interviews.update(
                    session.interview_id,
                    {
                        "$set": {
                            "recording_url": upload_result['public_url'],
                            "recording_key": upload_result['key'],
                            "recording_size": upload_result['size'],
                        }
                    }
                )
                logger.info(f"✅ Recording uploaded: {upload_result['public_url']}")

            # End session
            session.end_session()

            # Remove from session service
            self.session_service.remove_session(session.interview_id)

            logger.info(
                f"✅ Interview completed: {session.interview_id} "
                f"({session.current_question_number} questions)"
            )

            # Format closing message
            return self.message_service.format_closing(
                text=closing["text"],
                audio_bytes=closing["audio_bytes"],
                total_questions=session.current_question_number,
            )

        except Exception as e:
            logger.exception(f"❌ Failed to end session: {e}")
            return None