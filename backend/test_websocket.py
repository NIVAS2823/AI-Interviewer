"""
WebSocket endpoints for real-time voice communication
UPDATED: Dynamic question generation support
"""

import asyncio
import logging
import json
import base64
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from bson import ObjectId

from app.core.deps import get_current_user_ws
from app.core.database import get_database
from app.services.voice_agent_service import VoiceAgentService
from app.models.interview import Question, ConversationMessage
from app.models.resume import ParsedData

logger = logging.getLogger(__name__)
router = APIRouter()


class VoiceInterviewSession:
    """Manages a single voice interview session with dynamic question generation"""

    def __init__(self, websocket: WebSocket, interview_id: str, user_id: str, db):
        self.websocket = websocket
        self.interview_id = interview_id
        self.user_id = user_id
        self.db = db
        self.agent = VoiceAgentService()
        self.is_active = False
        self.current_question_number = 0  # Changed from index to number
        self.interview_data = None
        self.resume_data = None
        self.max_questions = 5  # Default
        self.conversation_history = []  # Track conversation for dynamic generation

    async def start(self) -> bool:
        """Initialize the voice interview session"""
        try:
            # Load interview document and verify ownership
            interview = await self.db.interviews.find_one(
                {"_id": ObjectId(self.interview_id)}
            )
            if not interview:
                logger.warning("Session start failed: interview not found: %s", self.interview_id)
                await self.send_error("Interview not found")
                return False

            # Verify ownership
            candidate = interview.get("candidate_id")
            candidate_id_str = str(candidate)

            if candidate_id_str != str(self.user_id):
                logger.warning(
                    "Session start failed: interview ownership mismatch (db=%s token=%s)",
                    candidate_id_str,
                    self.user_id,
                )
                await self.send_error("Not authorized for this interview")
                return False

            # Load resume
            resume = await self.db.resumes.find_one({"_id": interview.get("resume_id")})
            if not resume or not resume.get("parsed_data"):
                logger.warning("Session start failed: resume not parsed or missing")
                await self.send_error("Resume data not found or not parsed")
                return False

            self.interview_data = interview
            self.resume_data = ParsedData(**resume["parsed_data"])
            
            # Get max_questions from interview settings
            self.max_questions = interview.get("max_questions", 5)

            self.is_active = True
            logger.info(
                "🎤 Voice session started (interview=%s, user=%s, max_q=%d)", 
                self.interview_id, self.user_id, self.max_questions
            )

            # Send greeting + first question
            await self.send_greeting()
            return True

        except Exception as e:
            logger.exception("Exception during session.start: %s", e)
            await self.send_error("Failed to start session")
            return False

    async def send_greeting(self):
        """Send welcome message (text + audio)"""
        try:
            candidate_name = self.resume_data.personal_info.get("name", "there") if hasattr(self.resume_data, "personal_info") else "there"
            interview_type = self.interview_data.get("interview_type", "mixed")

            greeting = await self.agent.generate_greeting(
                candidate_name=candidate_name,
                interview_type=interview_type,
                num_questions=self.max_questions,
            )

            await self.send_audio_message(
                text=greeting.get("text", ""),
                audio_bytes=greeting.get("audio_bytes") or b"",
                message_type="greeting",
            )

            # Save to conversation history
            greeting_msg = ConversationMessage(
                speaker="ai",
                text=greeting.get("text", ""),
                timestamp=greeting.get("timestamp")
            )
            self.conversation_history.append(greeting_msg)
            await self.save_message("ai", greeting.get("text", ""))

            # Small pause then first question
            await asyncio.sleep(0.5)
            await self.generate_and_send_next_question()

        except Exception as e:
            logger.exception("Error in send_greeting: %s", e)
            await self.send_error("Failed to send greeting")

    async def generate_and_send_next_question(self):
        """
        Generate next question dynamically based on conversation history
        This is the KEY method for dynamic question generation
        """
        try:
            # Check if we've reached max questions
            if self.current_question_number >= self.max_questions:
                logger.info("Reached max questions (%d), sending closing", self.max_questions)
                await self.send_closing()
                return

            logger.info(
                "🧠 Generating dynamic question %d/%d", 
                self.current_question_number + 1, 
                self.max_questions
            )

            # Generate question dynamically using AI
            question = await self.agent.generate_next_question_dynamic(
                resume=self.resume_data,
                job_description=self.interview_data.get("job_description"),
                conversation_history=self.conversation_history,
                interview_type=self.interview_data.get("interview_type", "mixed"),
                difficulty=self.interview_data.get("difficulty", "medium"),
                question_number=self.current_question_number + 1,
                total_questions=self.max_questions,
            )

            if not question:
                logger.error("Failed to generate question dynamically")
                await self.send_error("Failed to generate next question")
                return

            # Send the question with audio
            question_response = await self.agent.ask_question(question)

            await self.send_audio_message(
                text=question_response.get("text", ""),
                audio_bytes=question_response.get("audio_bytes") or b"",
                message_type="question",
                metadata={
                    "question_number": self.current_question_number + 1,
                    "total_questions": self.max_questions,
                    "category": question.category,
                    "difficulty": question.difficulty,
                },
            )

            # Save to conversation history
            question_msg = ConversationMessage(
                speaker="ai",
                text=question_response.get("text", ""),
                timestamp=question_response.get("timestamp")
            )
            self.conversation_history.append(question_msg)
            await self.save_message("ai", question_response.get("text", ""))
            
            # Save question to interview document for record-keeping
            await self.save_question_to_db(question)

            self.current_question_number += 1

        except Exception as e:
            logger.exception("Failed in generate_and_send_next_question: %s", e)
            await self.send_error("Failed to generate next question")

    async def process_answer(self, audio_data: bytes):
        """Process candidate audio answer (transcribe -> ack -> next question)"""
        try:
            if not audio_data:
                await self.send_error("Empty audio received")
                return

            logger.debug("Processing answer audio (bytes=%d)", len(audio_data))
            transcript = await self.agent.process_answer(audio_data)

            if not transcript:
                logger.warning("Transcription returned empty for interview %s", self.interview_id)
                await self.send_error("Could not transcribe audio")
                return

            logger.info("📝 Transcribed: %s", transcript[:100])

            # Save to conversation history (IMPORTANT for dynamic questions)
            answer_msg = ConversationMessage(
                speaker="candidate",
                text=transcript,
                timestamp=__import__("datetime").datetime.utcnow().isoformat()
            )
            self.conversation_history.append(answer_msg)
            await self.save_message("candidate", transcript)

            # Send transcription back to client
            await self.send_message({"type": "transcription", "text": transcript})

            # Acknowledgment (TTS)
            ack = await self.agent.generate_acknowledgment(transcript)
            await self.send_audio_message(
                text=ack.get("text", ""),
                audio_bytes=ack.get("audio_bytes") or b"",
                message_type="acknowledgment",
            )

            # Save acknowledgment to history
            ack_msg = ConversationMessage(
                speaker="ai",
                text=ack.get("text", ""),
                timestamp=ack.get("timestamp")
            )
            self.conversation_history.append(ack_msg)

            await asyncio.sleep(0.5)
            
            # Generate next question based on this answer
            await self.generate_and_send_next_question()

        except Exception as e:
            logger.exception("Error in process_answer: %s", e)
            await self.send_error("Server error while processing answer")

    async def send_closing(self):
        """Send closing message, mark interview ready for evaluation"""
        try:
            candidate_name = self.resume_data.personal_info.get("name", "there") if hasattr(self.resume_data, "personal_info") else "there"
            closing = await self.agent.generate_closing(candidate_name)

            await self.send_audio_message(
                text=closing.get("text", ""),
                audio_bytes=closing.get("audio_bytes") or b"",
                message_type="closing",
            )

            await self.save_message("ai", closing.get("text", ""))

            # Update interview status
            await self.db.interviews.update_one(
                {"_id": ObjectId(self.interview_id)},
                {
                    "$set": {
                        "status": "completed",  # Changed from ready_for_evaluation
                        "completed_at": __import__("datetime").datetime.utcnow(),
                        "updated_at": __import__("datetime").datetime.utcnow()
                    }
                },
            )

            self.is_active = False
            await self.send_message({
                "type": "interview_complete", 
                "message": "Interview completed successfully",
                "total_questions": self.current_question_number
            })

        except Exception as e:
            logger.exception("Error in send_closing: %s", e)
            await self.send_error("Server error during closing")

    async def save_question_to_db(self, question: Question):
        """Save dynamically generated question to interview document"""
        try:
            question_dict = {
                "question_text": question.question_text,
                "category": question.category,
                "difficulty": question.difficulty,
                "expected_answer": getattr(question, "expected_answer", ""),
                "generated_at": __import__("datetime").datetime.utcnow()
            }
            
            await self.db.interviews.update_one(
                {"_id": ObjectId(self.interview_id)},
                {
                    "$push": {"questions": question_dict},
                    "$set": {"updated_at": __import__("datetime").datetime.utcnow()}
                }
            )
            logger.debug("Saved question to DB: %s", question.question_text[:60])
        except Exception as e:
            logger.exception("Failed to save question to DB: %s", e)

    async def send_audio_message(self, text: str, audio_bytes: bytes, message_type: str, metadata: Optional[dict] = None):
        """Send a JSON message containing base64 audio data"""
        try:
            audio_base64 = base64.b64encode(audio_bytes or b"").decode("utf-8")
            payload = {
                "type": message_type,
                "text": text,
                "audio": audio_base64,
                "metadata": metadata or {},
            }
            await self.websocket.send_json(payload)
            logger.debug("Sent audio message type=%s len_audio=%d", message_type, len(audio_bytes or b""))
        except Exception as e:
            logger.exception("Failed to send_audio_message: %s", e)

    async def send_message(self, message: dict):
        """Send raw JSON message"""
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.exception("Failed to send_message: %s", e)

    async def send_error(self, error: str):
        """Send error object to client"""
        try:
            await self.websocket.send_json({"type": "error", "message": error})
        except Exception:
            pass

    async def save_message(self, speaker: str, text: str):
        """Persist a conversation message to DB"""
        try:
            msg = {
                "speaker": speaker, 
                "text": text, 
                "timestamp": __import__("datetime").datetime.utcnow()
            }
            await self.db.interviews.update_one(
                {"_id": ObjectId(self.interview_id)},
                {
                    "$push": {"conversation": msg}, 
                    "$set": {"updated_at": __import__("datetime").datetime.utcnow()}
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
    """
    WebSocket endpoint for real-time voice interview with DYNAMIC question generation
    Authentication via JWT token query param: ?token=JWT_HERE
    """
    origin = websocket.headers.get("origin")
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.debug("WS handshake: interview=%s client=%s origin=%s", interview_id, client_host, origin)

    # Validate JWT before accepting connection
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

    # Accept connection
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
            logger.warning("Session start failed for %s", interview_id)
            await websocket.close(code=1011)
            return

        # Message loop
        while session.is_active:
            message = await websocket.receive()

            # Text/JSON messages
            if message.get("type") == "websocket.receive" and message.get("text"):
                try:
                    data = json.loads(message["text"])
                except Exception:
                    logger.warning("Invalid JSON received")
                    await session.send_error("Invalid JSON")
                    continue

                msg_type = data.get("type")
                if msg_type == "stop":
                    logger.info("Client requested stop for %s", interview_id)
                    await session.send_closing()
                    break
                elif msg_type == "ping":
                    await session.send_message({"type": "pong"})

            # Binary audio frames
            elif message.get("type") == "websocket.receive" and message.get("bytes"):
                audio_bytes = message["bytes"]
                await session.process_answer(audio_bytes)

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