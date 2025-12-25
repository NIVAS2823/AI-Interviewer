# app/api/v1/stt.py
import os
import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi import status
from app.core.deps import get_current_user
from app.models.user import UserModel

import websockets

router = APIRouter()
logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen?punctuate=true&language=en-US"


@router.websocket("/ws/stt/{interview_id}")
async def stt_ws(
    websocket: WebSocket,
    interview_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """Realtime streaming STT proxy between browser <-> Deepgram."""

    if not DEEPGRAM_API_KEY:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        logger.error("DEEPGRAM_API_KEY not configured")
        return

    await websocket.accept()
    logger.info(
        f"Client connected to STT WS for interview {interview_id}, user={current_user.email}"
    )

    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
    dg_ws = None

    try:
        # Connect to Deepgram realtime WS
        dg_ws = await websockets.connect(DEEPGRAM_WS_URL, extra_headers=headers)
        logger.debug("Connected to Deepgram Realtime WebSocket")

        # -----------------------------------------
        # BACKGROUND TASK: Listen from Deepgram WS
        # -----------------------------------------
        async def recv_from_deepgram():
            """Receive transcripts from Deepgram and forward in clean format."""
            try:
                async for msg in dg_ws:
                    try:
                        data = json.loads(msg)
                    except Exception:
                        await websocket.send_text(json.dumps({
                            "type": "stt_event",
                            "data": {"raw": msg}
                        }))
                        continue

                    if data.get("type") == "Results":
                        channel = data.get("channel", {})
                        alternatives = channel.get("alternatives", []) or [{}]
                        alt = alternatives[0]

                        transcript = alt.get("transcript", "") or ""
                        is_final = data.get("is_final", False)

                        if transcript:
                            await websocket.send_text(json.dumps({
                                "type": "stt_result",
                                "transcript": transcript,
                                "is_final": is_final
                            }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "stt_event",
                            "data": data,
                        }))
            except websockets.ConnectionClosed:
                logger.info("Deepgram WS closed")
            except Exception as e:
                logger.exception(f"Error while receiving from Deepgram: {e}")

        # Start background listener
        dg_recv_task = asyncio.create_task(recv_from_deepgram())

        # -----------------------------------------
        # MAIN LOOP: Receive audio from browser
        # -----------------------------------------
        while True:
            message = await websocket.receive()

            # 🔥 AUDIO CHUNK
            if "bytes" in message and message["bytes"] is not None:
                await dg_ws.send(message["bytes"])
                continue

            # 🔥 TEXT MESSAGE
            text = message.get("text")
            if text is not None:
                try:
                    payload = json.loads(text)
                except Exception:
                    payload = {"_raw": text}

                if payload.get("type") == "start":
                    # Deepgram Stream Config
                    await dg_ws.send(json.dumps({
                        "type": "StartRequest",
                        "encoding": "webm",
                        "sample_rate": 48000,
                        "channels": 1,
                        "language": "en-US",
                        "punctuate": True,
                        "interim_results": True
                    }))

                elif payload.get("type") == "stop":
                    await dg_ws.send(json.dumps({"type": "Close"}))
                    break

                else:
                    await dg_ws.send(text)

            # Ignore ping/pong frames
            else:
                continue

    except WebSocketDisconnect:
        logger.info("Client disconnected from STT WS")

    except Exception as e:
        logger.exception(f"STT WS error: {e}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
        except:
            pass

    finally:
        try:
            if dg_ws:
                await dg_ws.close()
        except:
            pass

        try:
            await websocket.close()
        except:
            pass

        logger.info("STT WS closed")
