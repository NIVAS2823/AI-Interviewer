# app/api/v1/stt.py
import os
import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi import status
from app.core.deps import get_current_user
from app.models.user import UserModel

# websocket client lib
import websockets

router = APIRouter()
logger = logging.getLogger(__name__)

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")  # set in environment

# Deepgram realtime endpoint (listening)
DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen?punctuate=true&language=en-US"

# Optional: additional query params: model=general, interim_results=true etc.

@router.websocket("/ws/stt/{interview_id}")
async def stt_ws(
    websocket: WebSocket,
    interview_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """
    WebSocket endpoint that proxies browser audio to Deepgram Realtime,
    and forwards transcript messages from Deepgram back to the browser.
    Security: requires authentication (cookie/token) via get_current_user dependency.
    Client should send binary chunks (ArrayBuffer) or base64 strings.
    """

    if not DEEPGRAM_API_KEY:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        logger.error("DEEPGRAM_API_KEY not configured")
        return

    # accept connection
    await websocket.accept()
    logger.info(f"Client connected to STT WS for interview {interview_id} user={current_user.email}")

    # Create connection to Deepgram Realtime
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}"
    }

    dg_ws = None

    try:
        # Connect to Deepgram WS
        dg_ws = await websockets.connect(DEEPGRAM_WS_URL, extra_headers=headers)
        logger.debug("Connected to Deepgram Realtime WebSocket")

        async def recv_from_deepgram():
            """Relay Deepgram messages to client websocket"""
            try:
                async for msg in dg_ws:
                    # dg returns JSON strings - forward them to browser
                    try:
                        data = json.loads(msg)
                    except Exception:
                        data = {"raw": msg}
                    # optionally filter messages:
                    await websocket.send_text(json.dumps({"from": "deepgram", "data": data}))
            except websockets.ConnectionClosed:
                logger.info("Deepgram connection closed")
            except Exception as e:
                logger.exception("Error while receiving from Deepgram: %s", e)

        # Start background task to read from Deepgram
        dg_recv_task = asyncio.create_task(recv_from_deepgram())

        # Read audio chunks from browser and forward to Deepgram
        while True:
            message = await websocket.receive()

            # message could be bytes or text or json type dict depending on ASGI server
            if "bytes" in message and message["bytes"] is not None:
                # binary audio chunk -> forward as binary
                audio_chunk = message["bytes"]
                await dg_ws.send(audio_chunk)
            elif message.get("text") is not None:
                text = message["text"]

                # client control messages (JSON)
                try:
                    payload = json.loads(text)
                except Exception:
                    payload = {"_raw": text}

                # Example client control messages:
                # { "type": "start" }  -> maybe to send a config event to Deepgram
                # { "type": "stop"  }  -> close Deepgram connection
                if payload.get("type") == "start":
                    # Deepgram accepts a JSON config event to set options:
                    config_msg = {
                        "type": "StartRequest",
                        "encoding": "webm",
                        "sample_rate": 48000,
                        "channels": 1,
                        "language": "en-US",
                        "punctuate": True,
                        "interim_results": True
                    }
                    await dg_ws.send(json.dumps(config_msg))
                elif payload.get("type") == "stop":
                    # gracefully close Deepgram connection
                    await dg_ws.send(json.dumps({"type": "Close"}))
                    break
                else:
                    # forward unknown text to Deepgram (rare)
                    await dg_ws.send(text)
            else:
                # handle ping/pong/close
                continue

    except WebSocketDisconnect:
        logger.info("Client disconnected from STT WS")
    except Exception as e:
        logger.exception("STT WS error: %s", e)
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
        except:
            pass
    finally:
        # cleanup
        try:
            if dg_ws:
                await dg_ws.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("STT WS closed")
