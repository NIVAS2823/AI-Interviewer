import asyncio
import websockets
import json
import logging
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

BACKEND_URL = "ws://localhost:8000/api/v1/ws/interview"

async def test_voice_interview():
    """Test complete voice interview flow"""
    
    # You'll need a real interview_id from your database
    # Create one via API first or use existing one
    interview_id = "YOUR_INTERVIEW_ID_HERE"
    user_id = "YOUR_USER_ID_HERE"
    
    uri = f"{BACKEND_URL}/{interview_id}?user_id={user_id}"
    
    print("\n" + "="*60)
    print("🎤 Testing Full Voice Interview Flow")
    print("="*60 + "\n")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to WebSocket")
            
            # Listen for messages
            step = 1
            while True:
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=30.0
                    )
                    
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    print(f"\n📨 [{step}] Received: {msg_type}")
                    
                    if msg_type == "greeting":
                        print(f"   Text: {data.get('text', '')[:60]}...")
                        audio_len = len(data.get('audio', ''))
                        print(f"   Audio: {audio_len} chars (base64)")
                        
                        # Send acknowledgment
                        await websocket.send(json.dumps({
                            "type": "greeting_ack"
                        }))
                        print("   ✅ Sent greeting_ack")
                    
                    elif msg_type == "question":
                        print(f"   Question: {data.get('text', '')[:60]}...")
                        audio_len = len(data.get('audio', ''))
                        print(f"   Audio: {audio_len} chars")
                        
                        # Simulate answer after 2 seconds
                        await asyncio.sleep(2)
                        
                        # Send mock answer (you'd send real audio here)
                        await websocket.send(json.dumps({
                            "type": "answer",
                            "audio": "base64_audio_data_here"
                        }))
                        print("   ✅ Sent answer")
                    
                    elif msg_type == "acknowledgment":
                        print(f"   Ack: {data.get('text', '')}")
                    
                    elif msg_type == "closing":
                        print(f"   Closing: {data.get('text', '')[:60]}...")
                        print("\n✅ Interview completed successfully!")
                        break
                    
                    elif msg_type == "error":
                        print(f"   ❌ Error: {data.get('message', '')}")
                        break
                    
                    step += 1
                    
                except asyncio.TimeoutError:
                    print("\n⏱️ Timeout waiting for message")
                    break
                except json.JSONDecodeError:
                    print("⚠️ Invalid JSON received")
                    continue
    
    except Exception as e:
        logger.exception(f"❌ WebSocket test failed: {e}")

if __name__ == "__main__":
    print("\n⚠️ NOTE: Update interview_id and user_id before running!")
    print("Create an interview via API/UI first.\n")
