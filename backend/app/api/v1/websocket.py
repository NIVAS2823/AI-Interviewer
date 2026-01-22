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
from app.services.integration.deepgram_streaming_service import DeepgramStreamingService

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_AUDIO_BYTES = 1_048_576
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
        success, error, ack_message = await self.orchestrator.process_answer(
            session,
            audio_data,
            self.audio_recording
        )

        if not success:
            await self.send_error(error or "Failed to process answer")
            return


        if ack_message:
            await self.send_message(ack_message)

        await asyncio.sleep(0.5)
        
        question_msg = await self.orchestrator.generate_next_question(
            session,
            self.audio_recording
        )

        if question_msg:
            await self.send_message(question_msg)
        else:
            await self.handle_stop(session)

    async def handle_text_answer(self, text: str, session):
        """Handle text answer from client (fallback mode)"""
        
        session.add_message("candidate", text)
        
        await self.orchestrator.repos.conversations.add_message(
            session.interview_id,
            "candidate",
            text
        )

        transcription_msg = self.message_service.format_transcription(text)
        await self.send_message(transcription_msg)

        ack = await self.orchestrator.voice_agent.generate_acknowledgment(text)
        
        session.add_message("ai", ack["text"], ack["timestamp"])
        
        ack_message = self.message_service.format_acknowledgment(
            text=ack["text"],
            audio_bytes=ack.get("audio_bytes", b""),
        )
        
        await self.send_message(ack_message)

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

        await asyncio.sleep(12.0)

        completion_msg = self.message_service.format_interview_complete(
            total_questions=session.current_question_number,
            duration_seconds=session.get_session_duration(),
        )
        
        await self.send_message(completion_msg)

    async def handle_ping(self):
        """Handle ping request"""
        pong_msg = self.message_service.format_pong()
        await self.send_message(pong_msg)

    async def handle_start_streaming(self, session):
        """Handle start streaming request"""
        try:
            logger.info(f"🎙️ Starting streaming for interview {session.interview_id}")
            
            if session.is_streaming:
                logger.warning("⚠️ Streaming already active")
                return
            
            async def on_interim_transcript(text: str, is_final: bool):
                """Callback when Deepgram sends interim transcript"""
                try:
                    interim_msg = self.message_service.format_interim_transcript(
                        text=text,
                        is_final=is_final
                    )
                    await self.send_message(interim_msg)
                    
                except Exception as e:
                    logger.error(f"❌ Error sending interim transcript: {e}")
            
            streaming_service = DeepgramStreamingService(
                on_transcript=on_interim_transcript
            )
            
            success = await streaming_service.start_streaming()
            
            if success:
                session.streaming_service = streaming_service
                session.is_streaming = True
                logger.info("✅ Streaming started successfully")
            else:
                logger.error("❌ Failed to start streaming")
                await self.send_error("Failed to start streaming")
                
        except Exception as e:
            logger.exception(f"❌ Error starting streaming: {e}")
            await self.send_error("Failed to start streaming")

    async def handle_audio_chunk(self, audio_chunk: bytes, session):
        """Handle audio chunk during streaming"""
        try:
            if not session.is_streaming or not session.streaming_service:
                logger.warning("⚠️ Received audio chunk but streaming not active")
                return
            
            success = await session.streaming_service.send_audio_chunk(audio_chunk)

            if not success:
                logger.error("❌ Streaming failed — stopping stream")
                await self.handle_stop_streaming(session)
            
        except Exception as e:
            logger.error(f"❌ Error forwarding audio chunk: {e}")

    async def handle_stop_streaming(self, session):
        """Handle stop streaming request"""
        try:
            logger.info(f"🔇 Stopping streaming for interview {session.interview_id}")
            
            if not session.is_streaming or not session.streaming_service:
                logger.warning("⚠️ Streaming not active")
                return
            
            await session.streaming_service.stop_streaming()
            session.streaming_service = None
            session.is_streaming = False
            
            logger.info("✅ Streaming stopped successfully")
            
        except Exception as e:
            logger.exception(f"❌ Error stopping streaming: {e}")

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

    await websocket.accept()
    logger.info(f"🔌 WebSocket accepted: interview={interview_id} user={user_id}")

    orchestrator = VoiceInterviewOrchestrator(db)
    handler = WebSocketHandler(websocket, orchestrator)

    try:
        success, session, error = await orchestrator.start_session(
            interview_id=interview_id,
            user_id=user_id,
            voice="aura-athena-en"
        )

        if not success:
            await handler.send_error(error or "Failed to start session")
            await websocket.close(code=1011)
            return

        greeting_msg = await orchestrator.generate_greeting(session)
        
        if greeting_msg:
            await handler.send_message(greeting_msg)
        else:
            await handler.send_error("Failed to send greeting")
            await websocket.close(code=1011)
            return

        while session.is_active:
            try:
                message = await websocket.receive()
            except RuntimeError as e:
                logger.info(f"WebSocket receive error (expected during close): {e}")
                break

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

                elif msg_type == "start_streaming":
                    await handler.handle_start_streaming(session)

                elif msg_type == "stop_streaming":
                    await handler.handle_stop_streaming(session)

                elif msg_type == "text_answer":
                    text_answer = data.get("text", "")
                    await handler.handle_text_answer(text_answer, session)

                elif msg_type == "stop":
                    logger.info(f"Client requested stop for {interview_id}")
                    await handler.handle_stop(session)
                    break

                elif msg_type == "ping":
                    await handler.handle_ping()

            elif message.get("type") == "websocket.receive" and message.get("bytes"):
                audio_bytes = message["bytes"]
                size = len(audio_bytes)

                logger.debug(f"📥 Received audio: {size} bytes, streaming={session.is_streaming}")

                is_pcm_chunk = (
                    session.is_streaming and 
                    7500 <= size <= 8500
                )
                
                if is_pcm_chunk:
                    logger.debug(f"📤 Forwarding PCM chunk: {size} bytes")
                    await handler.handle_audio_chunk(audio_bytes, session)
                    continue

                if 7500 <= size <= 8500:
                    logger.debug(f"⚠️ Not treating as PCM chunk (streaming={session.is_streaming})")

                if size < 10000:  # Less than 10KB
                    logger.warning(f"⚠️ Ignoring small audio blob: {size} bytes (likely incomplete)")
                    continue


                if size > MAX_AUDIO_BYTES:
                    logger.warning(
                        f"Audio rejected early: {size} bytes (max {MAX_AUDIO_BYTES})"
                    )

                    await handler.send_error(
                        error="Audio too long. Please keep answers shorter.",
                        code="AUDIO_LIMIT_EXCEEDED",
                    )
                    continue
                logger.info(f"🎤 Processing full audio answer: {size} bytes")
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