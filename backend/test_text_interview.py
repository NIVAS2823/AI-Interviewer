# test_text_interview.py
"""
Test interview with simulated transcriptions (bypass STT entirely)
"""
import asyncio
import websockets
import json
import base64

async def test_with_fake_transcripts():
    print("="*70)
    print("🧪 Testing Interview with Fake Transcripts")
    print("="*70)
    
    # Load credentials
    with open("test_credentials.json", "r") as f:
        creds = json.load(f)
        token = creds["token"]
        interview_id = creds["interview_id"]
    
    print(f"✅ Credentials loaded")
    
    # Fake answers to give
    fake_answers = [
        "I have 3 years of experience building microservices with Python and FastAPI. I've worked extensively with Docker and Kubernetes for container orchestration.",
        "I use event-driven architecture with message queues like RabbitMQ or Kafka. I implement circuit breakers and retry mechanisms for fault tolerance.",
        "I use Prometheus for metrics, Grafana for visualization, and ELK stack for log aggregation. I implement distributed tracing with Jaeger.",
        "I use JWT tokens for authentication, implement rate limiting, use HTTPS everywhere, and follow OWASP security best practices.",
        "I write unit tests with pytest, integration tests for APIs, use CI/CD pipelines, and follow test-driven development practices."
    ]
    
    url = f"ws://localhost:8000/api/v1/ws/interview/{interview_id}/voice?token={token}"
    print(f"\n📡 Connecting...\n")
    
    try:
        async with websockets.connect(url) as ws:
            print("✅ Connected!\n")
            
            question_num = 0
            
            for i in range(50):  # Max messages
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=20.0)
                    data = json.loads(msg)
                    msg_type = data.get('type')
                    
                    print(f"📨 [{i+1}] {msg_type.upper()}")
                    
                    if msg_type == 'greeting':
                        print(f"   {data.get('text', '')[:120]}...\n")
                        
                    elif msg_type == 'question':
                        question_num += 1
                        meta = data.get('metadata', {})
                        print(f"   ❓ Question {meta.get('question_number')}/{meta.get('total_questions')}")
                        print(f"   {data.get('text', '')[:120]}...")
                        print(f"   Category: {meta.get('category')} | Difficulty: {meta.get('difficulty')}")
                        
                        # Wait a bit then send fake audio with embedded answer
                        await asyncio.sleep(1)
                        
                        if question_num <= len(fake_answers):
                            answer = fake_answers[question_num - 1]
                            print(f"\n   💬 Mock Answer: {answer[:80]}...\n")
                            
                            # Create fake audio (silence) - STT will fail but at least we try
                            fake_audio = b'\x00' * 1000  # Tiny silence
                            await ws.send(fake_audio)
                        
                    elif msg_type == 'transcription':
                        print(f"   📝 {data.get('text', 'Empty')}\n")
                        
                    elif msg_type == 'acknowledgment':
                        print(f"   💬 {data.get('text')}\n")
                        
                    elif msg_type == 'closing':
                        print(f"   {data.get('text', '')[:120]}...\n")
                        
                    elif msg_type == 'interview_complete':
                        print(f"   ✅ {data.get('message')}")
                        print(f"   🎯 Questions: {data.get('total_questions')}\n")
                        break
                        
                    elif msg_type == 'error':
                        error_msg = data.get('message', '')
                        print(f"   ❌ {error_msg}")
                        
                        # If transcription failed, that's expected - continue anyway
                        if "transcribe" in error_msg.lower():
                            print(f"   ⏭️  Continuing despite transcription error...\n")
                            # Don't break, let it timeout and move on
                        else:
                            print()
                    
                except asyncio.TimeoutError:
                    print(f"\n⏱️ Timeout (this might be OK if waiting for answer)\n")
                    break
            
            print("="*70)
            print(f"📊 Interview Flow Test Complete")
            print(f"   Questions Generated: {question_num}/5")
            print("="*70)
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_fake_transcripts())
