import asyncio
import websockets
import json
import base64

async def test():
    uri = "ws://localhost:8000/api/v1/ws/interview/692fd567d39b66d48772c6de/voice?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTJmZDUyMTk2ZmZkYzJlMmY5MDBiYjciLCJlbWFpbCI6ImpvaG4uZG9lMkBleGFtcGxlLmNvbSIsInJvbGUiOiJqb2Jfc2Vla2VyIiwiZXhwIjoxNzY3MzM0NDMzLCJpYXQiOjE3NjQ3NDI0MzN9.ucginHa2MhrmQrfN11iVAcp8254ptAGSa68vuw8ulG4"
    
    print("🔌 Connecting...")
    async with websockets.connect(uri) as ws:
        print("✅ Connected! Waiting for greeting...")
        
        # Wait for greeting
        message = await ws.recv()
        data = json.loads(message)
        
        print(f"📨 Received: {data['type']}")
        print(f"📝 Text: {data['text'][:60]}...")
        print(f"🎵 Audio: {len(data.get('audio', ''))} bytes")
        
        # Send acknowledgment
        await ws.send(json.dumps({"type": "greeting_ack"}))
        print("✅ Sent greeting_ack")
        
        # Wait for question
        message = await ws.recv()
        data = json.loads(message)
        print(f"\n📨 Received: {data['type']}")
        print(f"❓ Question: {data['text'][:60]}...")
        
        print("\n✅ Backend is working perfectly!")

asyncio.run(test())