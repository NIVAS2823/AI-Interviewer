"""
Voice Interview WebSocket Handler (Refactored)
Thin handler that delegates all business logic to orchestrator

Responsibilities (ONLY):
- Accept WebSocket connections
- Receive messages from client
- Send messages to client
- Delegate to orchestrator
"""
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from app.core.deps import get_current_user_ws
from app.core.database import get_database
from app.services.orchestration.voice_interview_orchestrator import VoiceInterviewOrchestrator
from app.services.voice_interview.audio_recording_service import AudioRecordingService
from app.services.voice_interview.websocket_message_service import WebSocketMessageService

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_AUDIO_BYTES = 1_048_576  # 1 MB hard cap
OPUS_BITRATE_BPS = 128_000   

class WebSocketHandler:
    """
    Lightweight WebSocket handler
    
    Responsibilities:
    - WebSocket I/O ONLY
    - Message routing
    - Connection management
    
    Does NOT:
    - Contain business logic
    - Access database directly
    - Generate questions
    - Process audio
    """

    def __init__(
        self,
        websocket: WebSocket,
        orchestrator: VoiceInterviewOrchestrator,
    ):
        """
        Initialize handler
        
        Args:
            websocket: WebSocket connection
            orchestrator: Voice interview orchestrator
        """
        self.websocket = websocket
        self.orchestrator = orchestrator
        self.message_service = WebSocketMessageService()
        self.audio_recording = AudioRecordingService()

    async def send_message(self, message: dict):
        """Send JSON message to client"""
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    async def send_error(self, error: str, code: str = None):
        """Send error message to client"""
        error_msg = self.message_service.format_error(error, code)
        await self.send_message(error_msg)

    async def handle_greeting_ack(self, session):
        """Handle greeting acknowledgment from client"""
        logger.info("Client acknowledged greeting — sending first question")
        
        question_msg = await self.orchestrator.generate_next_question(
            session,
            self.audio_recording
        )
        
        if question_msg:
            await self.send_message(question_msg)
        else:
            await self.send_error("Failed to generate first question")

    async def handle_audio_answer(self, audio_data: bytes, session):
        """Handle audio answer from client"""
        # Process answer
        success, error, ack_message = await self.orchestrator.process_answer(
            session,
            audio_data,
            self.audio_recording
        )

        if not success:
            await self.send_error(error or "Failed to process answer")
            return

        # Send transcription notification
        # (transcription is included in acknowledgment flow)

        # Send acknowledgment
        if ack_message:
            await self.send_message(ack_message)

        # Generate next question after brief pause
        await asyncio.sleep(0.5)
        
        question_msg = await self.orchestrator.generate_next_question(
            session,
            self.audio_recording
        )

        if question_msg:
            await self.send_message(question_msg)
        else:
            # All questions done, send closing
            await self.handle_stop(session)

    async def handle_text_answer(self, text: str, session):
        """Handle text answer from client (fallback mode)"""
        # Convert text to pseudo-audio format for processing
        # In real implementation, you'd handle this differently
        
        # For now, we'll add to conversation directly
        session.add_message("candidate", text)
        
        await self.orchestrator.repos.conversations.add_message(
            session.interview_id,
            "candidate",
            text
        )

        # Send transcription
        transcription_msg = self.message_service.format_transcription(text)
        await self.send_message(transcription_msg)

        # Generate acknowledgment
        ack = await self.orchestrator.voice_agent.generate_acknowledgment(text)
        
        session.add_message("ai", ack["text"], ack["timestamp"])
        
        ack_message = self.message_service.format_acknowledgment(
            text=ack["text"],
            audio_bytes=ack.get("audio_bytes", b""),
        )
        
        await self.send_message(ack_message)

        # Generate next question
        await asyncio.sleep(0.5)
        
        question_msg = await self.orchestrator.generate_next_question(
            session,
            self.audio_recording
        )

        if question_msg:
            await self.send_message(question_msg)
        else:
            await self.handle_stop(session)

    async def handle_stop(self, session):
        """Handle stop/end interview request"""
        logger.info("Ending interview session")
        
        closing_msg = await self.orchestrator.end_session(
            session,
            self.audio_recording
        )

        if closing_msg:
            await self.send_message(closing_msg)

        # Wait for closing to play
        await asyncio.sleep(12.0)

        # Send completion message
        completion_msg = self.message_service.format_interview_complete(
            total_questions=session.current_question_number,
            duration_seconds=session.get_session_duration(),
        )
        
        await self.send_message(completion_msg)

    async def handle_ping(self):
        """Handle ping request"""
        pong_msg = self.message_service.format_pong()
        await self.send_message(pong_msg)

    def _estimate_duration_seconds(self, byte_size: int) -> int:
        """
        Estimate audio duration from Opus byte size.
        Conservative on purpose.
        """
        bits = byte_size * 8
        return int(bits / OPUS_BITRATE_BPS)


@router.websocket("/ws/interview/{interview_id}/voice")
async def voice_interview_websocket(
    websocket: WebSocket,
    interview_id: str,
    db=Depends(get_database)
):
    """
    Voice interview WebSocket endpoint
    
    This is now a thin handler that just manages WebSocket I/O
    All business logic is delegated to VoiceInterviewOrchestrator
    """
    origin = websocket.headers.get("origin")
    client_host = websocket.client.host if websocket.client else "unknown"
    
    logger.debug(
        f"WS handshake: interview={interview_id} client={client_host} origin={origin}"
    )

    # =====================================================
    # 1. AUTHENTICATION
    # =====================================================
    try:
        token = websocket.query_params.get("token")
        user_id = await get_current_user_ws(websocket, token)
        
        if not user_id:
            logger.warning(f"WS auth failed for interview {interview_id}")
            try:
                await websocket.close(code=4401)
            except Exception:
                pass
            return
            
    except Exception as e:
        logger.exception(f"Exception during WS auth: {e}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
        return

    # =====================================================
    # 2. ACCEPT CONNECTION
    # =====================================================
    await websocket.accept()
    logger.info(f"🔌 WebSocket accepted: interview={interview_id} user={user_id}")

    # =====================================================
    # 3. INITIALIZE ORCHESTRATOR AND HANDLER
    # =====================================================
    orchestrator = VoiceInterviewOrchestrator(db)
    handler = WebSocketHandler(websocket, orchestrator)

    try:
        # =====================================================
        # 4. START SESSION
        # =====================================================
        success, session, error = await orchestrator.start_session(
            interview_id=interview_id,
            user_id=user_id,
            voice="aura-athena-en"
        )

        if not success:
            await handler.send_error(error or "Failed to start session")
            await websocket.close(code=1011)
            return

        # =====================================================
        # 5. SEND GREETING
        # =====================================================
        greeting_msg = await orchestrator.generate_greeting(session)
        
        if greeting_msg:
            await handler.send_message(greeting_msg)
        else:
            await handler.send_error("Failed to send greeting")
            await websocket.close(code=1011)
            return

        # =====================================================
        # 6. MESSAGE LOOP
        # =====================================================
        while session.is_active:
            message = await websocket.receive()

            # Handle text messages
            if message.get("type") == "websocket.receive" and message.get("text"):
                try:
                    data = json.loads(message["text"])
                except Exception:
                    logger.warning(f"Invalid JSON received for interview {interview_id}")
                    await handler.send_error("Invalid JSON")
                    continue

                msg_type = data.get("type")

                if msg_type == "greeting_ack":
                    await handler.handle_greeting_ack(session)

                elif msg_type == "text_answer":
                    text_answer = data.get("text", "")
                    await handler.handle_text_answer(text_answer, session)

                elif msg_type == "stop":
                    logger.info(f"Client requested stop for {interview_id}")
                    await handler.handle_stop(session)
                    break

                elif msg_type == "ping":
                    await handler.handle_ping()

            # Handle binary messages (audio)
            elif message.get("type") == "websocket.receive" and message.get("bytes"):
                audio_bytes = message["bytes"]
                size = len(audio_bytes)

                if size > MAX_AUDIO_BYTES:
                    estimated_seconds = handler._estimate_duration_seconds(size)
                    max_seconds = handler._estimate_duration_seconds(MAX_AUDIO_BYTES)

                    logger.warning(
            f"Audio rejected early: {size} bytes (max {MAX_AUDIO_BYTES})"
        )

                    await handler.send_error(
            error="Audio too long. Please keep answers shorter.",
            code="AUDIO_LIMIT_EXCEEDED",
        )

        # 🚫 DO NOT process further
                    continue

    # ✅ ONLY valid audio reaches here
                await handler.handle_audio_answer(audio_bytes, session)


    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {interview_id}")

    except Exception as e:
        logger.exception(f"Unhandled websocket error for {interview_id}: {e}")
        try:
            await handler.send_error("Server error")
        except Exception:
            pass

    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info(f"WebSocket closed: {interview_id}")


    