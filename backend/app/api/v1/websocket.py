import asyncio
import logging
import json
import base64
from typing import Optional, Any, Dict, List
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from bson import ObjectId

from app.core.deps import get_current_user_ws
from app.core.database import get_database
from app.services.voice_agent_service import VoiceAgentService
from app.services.evaluation_service import EvaluationService
from app.services.question_generator import QuestionGeneratorService
from app.models.interview import Question, ConversationMessage
from app.models.resume import ParsedData

logger = logging.getLogger(__name__)
router = APIRouter()


class VoiceInterviewSession:
    """Manages a single voice interview session with dynamic question generation (Smart Mode)."""

    def __init__(self, websocket: WebSocket, interview_id: str, user_id: str, db):
        self.websocket = websocket
        self.interview_id = interview_id
        self.user_id = user_id
        self.db = db

        # Services
        self.agent = VoiceAgentService()
        self.evaluator = EvaluationService()
        self.question_generator = QuestionGeneratorService()

        # Session state
        self.is_active = False
        self.current_question_number = 0
        self.interview_data = None
        self.resume_data = None
        self.max_questions = 5
        self.conversation_history: List[ConversationMessage] = []
        self.asked_questions: List[str] = []  # track asked question texts to avoid repetition

    async def start(self) -> bool:
        """Validate interview, load resume, and begin by sending greeting."""
        try:
            interview = await self.db.interviews.find_one({"_id": ObjectId(self.interview_id)})
            if not interview:
                await self.send_error("Interview not found")
                return False

            candidate_id_str = str(interview.get("candidate_id"))
            if candidate_id_str != str(self.user_id):
                await self.send_error("Not authorized for this interview")
                return False

            resume = await self.db.resumes.find_one({"_id": interview.get("resume_id")})
            if not resume or not resume.get("parsed_data"):
                await self.send_error("Resume data not found or not parsed")
                return False

            logger.info("🧹 Resetting previous questions for voice interview")
            await self.db.interviews.update_one(
                 {"_id": ObjectId(self.interview_id)},
                 {"$set": {"questions": [], "updated_at": datetime.utcnow()}}
                 )
            self.current_question_number = 0
            self.asked_questions = []
            self.interview_data = interview
            self.resume_data = ParsedData(**resume["parsed_data"])
            self.max_questions = interview.get("max_questions", 5)
            self.is_active = True

            await self.send_greeting()
            return True

        except Exception as e:
            logger.exception("Exception during session.start: %s", e)
            await self.send_error("Failed to start session")
            return False

    async def send_greeting(self):
        """Send welcome message with audio"""
        try:
            if hasattr(self.resume_data, "name"):
                candidate_name = self.resume_data.name
            elif hasattr(self.resume_data, "personal_info"):
                candidate_name = self.resume_data.personal_info.get("name", "there")
            else:
                candidate_name = "there"

            interview_type = self.interview_data.get("interview_type", "mixed")

            logger.info("👋 Sending greeting (will not count as question)")

            greeting = await self.agent.generate_greeting(
                candidate_name=candidate_name,
                interview_type=interview_type,
                num_questions=self.max_questions,
            )

            await self.send_audio_message(
                text=greeting["text"],
                audio_bytes=greeting["audio_bytes"],
                message_type="greeting",
            )

            self.conversation_history.append(
                ConversationMessage(
                    speaker="ai",
                    text=greeting["text"],
                    timestamp=greeting["timestamp"]
                )
            )
            await self.save_message("ai", greeting["text"])

            logger.info("⏳ Waiting 3 seconds for greeting to play...")
            await asyncio.sleep(12.0)

            logger.info("🧠 Generating first question...")
            await self.generate_and_send_next_question()

        except Exception as e:
            logger.exception(f"❌ Greeting error: {e}")
            await self.send_error("Failed to send greeting")

    async def generate_and_send_next_question(self):
        """Generate a non-repeating, context-aware next question"""
        try:
            # Check if interview is complete
            if self.current_question_number >= self.max_questions:
                logger.info(f"✅ All questions asked ({self.max_questions}), sending closing")
                await self.send_closing()
                return

            logger.info(f"🧠 Generating question {self.current_question_number + 1}/{self.max_questions}")

            # Attempt to generate a unique question
            question = None
            attempts = 0
            max_attempts = 5  # Increased from 3

            while attempts < max_attempts and question is None:
                attempts += 1

                try:
                    # Generate ONE question
                    questions = await self.question_generator.generate_questions(
                        parsed_resume=self.resume_data,
                        interview_type=self.interview_data.get("interview_type", "mixed"),
                        difficulty=self.interview_data.get("difficulty", "medium"),
                        max_questions=1,
                    )

                    if not questions or len(questions) == 0:
                        logger.warning(f"⚠️ Question generator returned empty on attempt {attempts}")
                        await asyncio.sleep(0.3)
                        continue

                    candidate_q = questions[0]
                    q_text = getattr(candidate_q, "question_text", "").strip()

                    if not q_text:
                        logger.warning(f"⚠️ Generated empty question on attempt {attempts}")
                        continue

                    # ✅ CRITICAL: Check for duplicates using fuzzy matching
                    is_duplicate = False
                    q_text_normalized = q_text.lower()[:80]  # First 80 chars normalized

                    for asked_q in self.asked_questions:
                        asked_normalized = asked_q.lower()[:80]

                        # Check if questions are too similar (>70% overlap)
                        if self._calculate_similarity(q_text_normalized, asked_normalized) > 0.7:
                            logger.warning(f"🔄 Skipping similar question (attempt {attempts}): {q_text[:60]}...")
                            is_duplicate = True
                            break

                    if is_duplicate:
                        await asyncio.sleep(0.5)  # Wait before retry
                        continue

                    # ✅ Question is unique!
                    question = candidate_q
                    logger.info(f"✅ Unique question generated on attempt {attempts}")
                    break

                except Exception as e:
                    logger.exception(f"❌ Question generation attempt {attempts} failed: {e}")
                    await asyncio.sleep(0.3)

            # If still no unique question after max attempts, use a fallback
            if not question:
                logger.warning(f"⚠️ Could not generate unique question after {max_attempts} attempts")

                # Create a simple fallback question based on what we haven't asked
                question = self._create_fallback_question()

                if not question:
                    await self.send_error("Failed to generate next question")
                    return

            # Convert question to speech
            question_response = await self.agent.ask_question(question)

            # Send to client
            await self.send_audio_message(
                text=question_response["text"],
                audio_bytes=question_response["audio_bytes"],
                message_type="question",
                metadata={
                    "question_number": self.current_question_number + 1,
                    "total_questions": self.max_questions,
                    "category": getattr(question, "category", "mixed"),
                    "difficulty": getattr(question, "difficulty", "easy"),
                },
            )

            # Save question text to prevent duplicates
            q_text = question_response["text"] or getattr(question, "question_text", "")
            self.asked_questions.append(q_text)

            logger.info(f"📌 Saved to asked_questions (total: {len(self.asked_questions)}): {q_text[:60]}...")

            # Save to conversation history
            question_msg = ConversationMessage(
                speaker="ai",
                text=question_response["text"],
                timestamp=question_response["timestamp"]
            )
            self.conversation_history.append(question_msg)

            # Save to database
            await self.save_message("ai", question_response["text"])
            await self.save_question_to_db(question)

            self.current_question_number += 1

            logger.info(f"📝 Question {self.current_question_number}/{self.max_questions} sent and saved")

        except Exception as e:
            logger.exception(f"❌ Question generation error: {e}")
            await self.send_error("Failed to generate question")

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings (0.0 to 1.0)"""
        # Simple character overlap calculation
        if not str1 or not str2:
            return 0.0

        # Convert to sets of words
        words1 = set(str1.split())
        words2 = set(str2.split())

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _create_fallback_question(self) -> Optional[Question]:
        """Create a simple fallback question when AI fails to generate unique ones"""
        fallback_questions = [
            "Tell me about a challenging project you worked on recently.",
            "What technical skills are you most proud of?",
            "Describe your experience with team collaboration.",
            "What motivates you in your career?",
            "How do you approach learning new technologies?",
        ]

        # Pick one that hasn't been asked yet
        for fb_text in fallback_questions:
            is_used = any(fb_text.lower() in asked.lower() for asked in self.asked_questions)
            if not is_used:
                logger.info(f"📋 Using fallback question: {fb_text}")
                # Create a Question object
                try:
                    from app.models.interview import Question
                    return Question(
                        question_text=fb_text,
                        category=self.interview_data.get("interview_type", "mixed"),
                        difficulty=self.interview_data.get("difficulty", "easy"),
                        expected_answer=""
                    )
                except Exception as e:
                    logger.error(f"Failed to create fallback question: {e}")
                    return None

        return None

    async def process_answer(self, audio_data: bytes):
        """Process candidate's audio answer"""
        try:
            if not audio_data or len(audio_data) == 0:
                await self.send_error("No audio received")
                return

            logger.info(f"🎤 Processing answer: {len(audio_data)} bytes")

            transcript = await self.agent.process_answer(audio_data)

            if not transcript or len(transcript.strip()) == 0:
                logger.warning("⚠️ Empty transcription")
                await self.send_error(
                    "Could not transcribe audio. Please speak louder and try again."
                )
                return

            logger.info(f"📝 Transcribed: {transcript[:100]}...")

            answer_msg = ConversationMessage(
                speaker="candidate",
                text=transcript,
                timestamp=datetime.utcnow().isoformat()
            )
            self.conversation_history.append(answer_msg)
            await self.save_message("candidate", transcript)

            await self.send_message({"type": "transcription", "text": transcript})

            ack = await self.agent.generate_acknowledgment(transcript)

            await self.send_audio_message(
                text=ack["text"],
                audio_bytes=ack["audio_bytes"],
                message_type="acknowledgment",
            )

            ack_msg = ConversationMessage(
                speaker="ai",
                text=ack["text"],
                timestamp=ack["timestamp"]
            )
            self.conversation_history.append(ack_msg)

            await self.save_message("ai", ack["text"])

            await asyncio.sleep(0.5)
            await self.generate_and_send_next_question()

        except Exception as e:
            logger.exception(f"❌ Answer processing error: {e}")
            await self.send_error("Failed to process answer")

    async def send_closing(self):
        """Send closing message and mark interview complete"""
        try:
            if hasattr(self.resume_data, "name"):
                candidate_name = self.resume_data.name
            elif hasattr(self.resume_data, "personal_info"):
                candidate_name = self.resume_data.personal_info.get("name", "there")
            else:
                candidate_name = "there"

            logger.info(f"👋 Generating closing message for {candidate_name}")

            closing = await self.agent.generate_closing(candidate_name)

            await self.send_audio_message(
                text=closing["text"],
                audio_bytes=closing["audio_bytes"],
                message_type="closing",
            )

            await self.save_message("ai", closing["text"])

            logger.info("⏳ Waiting 5 seconds for closing to play...")
            await asyncio.sleep(20.0)

            await self.db.interviews.update_one(
                {"_id": ObjectId(self.interview_id)},
                {
                    "$set": {
                        "status": "completed",
                        "completed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                },
            )

            self.is_active = False

            await self.send_message({
                "type": "interview_complete",
                "message": "Interview completed successfully",
                "total_questions": self.current_question_number
            })

            logger.info(
                f"✅ Interview completed: {self.interview_id} "
                f"({self.current_question_number} questions)"
            )

        except Exception as e:
            logger.exception(f"❌ Closing error: {e}")
            await self.send_error("Failed to complete interview")

    async def save_question_to_db(self, question: Question):
        """Append generated question to interviews.questions array (safe)."""
        try:
            question_dict = {
                "question_text": getattr(question, "question_text", ""),
                "category": getattr(question, "category", ""),
                "difficulty": getattr(question, "difficulty", ""),
                "expected_answer": getattr(question, "expected_answer", ""),
                "generated_at": datetime.utcnow()
            }

            await self.db.interviews.update_one(
                {"_id": ObjectId(self.interview_id)},
                {
                    "$push": {"questions": question_dict},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

        except Exception as e:
            logger.exception("Failed to save question to DB: %s", e)

    async def send_audio_message(self, text: str, audio_bytes: bytes, message_type: str, metadata: Optional[dict] = None):
        """Send an audio message payload (base64) to the client."""
        try:
            audio_base64 = base64.b64encode(audio_bytes or b"").decode("utf-8")
            payload = {
                "type": message_type,
                "text": text,
                "audio": audio_base64,
                "metadata": metadata or {},
            }
            await self.websocket.send_json(payload)
            logger.debug(
                "Sent audio message type=%s len_audio=%d",
                message_type,
                len(audio_bytes or b"")
            )
        except Exception as e:
            logger.exception("Failed to send_audio_message: %s", e)

    async def send_message(self, message: dict):
        """Send a JSON message (non-audio) to the client."""
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.exception("Failed to send_message: %s", e)

    async def send_error(self, error: str):
        """Helper to send error message to client."""
        try:
            await self.websocket.send_json({"type": "error", "message": error})
        except Exception:
            pass

    async def save_message(self, speaker: str, text: str):
        """Save a conversation message into the interviews.conversation array."""
        try:
            msg = {
                "speaker": speaker,
                "text": text,
                "timestamp": datetime.utcnow()
            }
            await self.db.interviews.update_one(
                {"_id": ObjectId(self.interview_id)},
                {
                    "$push": {"conversation": msg},
                    "$set": {"updated_at": datetime.utcnow()}
                },
            )
        except Exception:
            logger.exception("Failed to save_message to DB")


@router.websocket("/ws/interview/{interview_id}/voice")
async def voice_interview_websocket(
    websocket: WebSocket,
    interview_id: str,
    db=Depends(get_database)
):
    origin = websocket.headers.get("origin")
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.debug(
        "WS handshake: interview=%s client=%s origin=%s",
        interview_id, client_host, origin
    )

    try:
        token = websocket.query_params.get("token")
        user_id = await get_current_user_ws(websocket, token)
        if not user_id:
            logger.warning("WS auth failed for interview %s", interview_id)
            try:
                await websocket.close(code=4401)
            except Exception:
                pass
            return
    except Exception as e:
        logger.exception("Exception during WS auth: %s", e)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
        return

    await websocket.accept()
    logger.info("🔌 WebSocket accepted: interview=%s user=%s", interview_id, user_id)

    session = VoiceInterviewSession(
        websocket=websocket,
        interview_id=interview_id,
        user_id=user_id,
        db=db
    )

    try:
        started = await session.start()
        if not started:
            await websocket.close(code=1011)
            return

        while session.is_active:
            message = await websocket.receive()

            if message.get("type") == "websocket.receive" and message.get("text"):
                try:
                    data = json.loads(message["text"])
                except Exception:
                    logger.warning(
                        "Invalid JSON received for interview %s",
                        interview_id
                    )
                    await session.send_error("Invalid JSON")
                    continue

                msg_type = data.get("type")

                if msg_type == "stop":
                    logger.info("Client requested stop for %s", interview_id)
                    await session.send_closing()
                    break

                elif msg_type == "ping":
                    await session.send_message({"type": "pong"})

                elif msg_type == "greeting_ack":
                    logger.info(
                        "Received greeting_ack from client - sending first question"
                    )
                    await session.generate_and_send_next_question()

                elif msg_type == "text_answer":
                    text_answer = data.get("text", "")

                    await session.save_message("candidate", text_answer)
                    session.conversation_history.append(
                        ConversationMessage(
                            speaker="candidate",
                            text=text_answer,
                            timestamp=datetime.utcnow().isoformat()
                        )
                    )

                    await session.send_message(
                        {"type": "transcription", "text": text_answer}
                    )

                    ack = await session.agent.generate_acknowledgment(text_answer)
                    await session.send_audio_message(
                        text=ack.get("text", ""),
                        audio_bytes=ack.get("audio_bytes") or b"",
                        message_type="acknowledgment",
                    )

                    session.conversation_history.append(
                        ConversationMessage(
                            speaker="ai",
                            text=ack.get("text", ""),
                            timestamp=ack.get("timestamp")
                        )
                    )

                    await asyncio.sleep(0.5)
                    await session.generate_and_send_next_question()

            elif message.get("type") == "websocket.receive" and message.get("bytes"):
                await session.process_answer(message["bytes"])

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", interview_id)

    except Exception as e:
        logger.exception("Unhandled websocket error for %s: %s", interview_id, e)
        try:
            await websocket.send_json({"type": "error", "message": "Server error"})
        except Exception:
            pass

    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("Websocket closed: %s", interview_id)
