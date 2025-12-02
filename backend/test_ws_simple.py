# test_ws_simple.py
import asyncio
import websockets
import json
import struct

async def create_minimal_wav() -> bytes:
    """Create a minimal valid WAV file (silence)"""
    # WAV header for 1 second of silence, 16kHz, mono, 16-bit
    sample_rate = 16000
    num_channels = 1
    bits_per_sample = 16
    duration = 1  # second
    
    num_samples = sample_rate * duration
    data_size = num_samples * num_channels * (bits_per_sample // 8)
    
    # WAV header
    wav = b'RIFF'
    wav += struct.pack('<I', 36 + data_size)
    wav += b'WAVE'
    wav += b'fmt '
    wav += struct.pack('<I', 16)  # fmt chunk size
    wav += struct.pack('<H', 1)   # PCM
    wav += struct.pack('<H', num_channels)
    wav += struct.pack('<I', sample_rate)
    wav += struct.pack('<I', sample_rate * num_channels * bits_per_sample // 8)
    wav += struct.pack('<H', num_channels * bits_per_sample // 8)
    wav += struct.pack('<H', bits_per_sample)
    wav += b'data'
    wav += struct.pack('<I', data_size)
    wav += b'\x00' * data_size  # silence
    
    return wav

async def test_simple():
    print("Starting simple WebSocket test...")
    
    # Load credentials
    try:
        with open("test_credentials.json", "r") as f:
            creds = json.load(f)
            token = creds["token"]
            interview_id = creds["interview_id"]
            print(f"✅ Loaded credentials")
            print(f"   Interview: {interview_id}")
            print(f"   Token: {token[:20]}...")
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return
    
    url = f"ws://localhost:8000/api/v1/ws/interview/{interview_id}/voice?token={token}"
    print(f"\n📡 Connecting to: {url[:80]}...")
    
    # Create mock audio once
    mock_audio = await create_minimal_wav()
    print(f"🎤 Created mock audio: {len(mock_audio)} bytes")
    
    try:
        async with websockets.connect(url) as ws:
            print("✅ Connected!")
            
            # Wait for messages
            for i in range(20):  # Increased to 20 to see full flow
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(msg)
                    print(f"\n📨 Message {i+1}: Type={data.get('type')}")
                    print(f"   Text: {data.get('text', '')[:80]}...")
                    
                    if data.get('audio'):
                        print(f"   🔊 Audio: {len(data['audio'])} chars (base64)")
                    
                    if data.get('type') == 'interview_complete':
                        print("✅ Interview complete!")
                        break
                        
                    # If it's a question, send valid audio
                    if data.get('type') == 'question':
                        print("   🎤 Sending audio answer...")
                        await ws.send(mock_audio)
                        
                except asyncio.TimeoutError:
                    print(f"⏱️ Timeout on message {i+1}")
                    break
                    
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed: {e.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("="*70)
    asyncio.run(test_simple())
    print("="*70)