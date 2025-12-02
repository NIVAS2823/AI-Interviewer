# test_interview_flow.py
"""
Test interview flow without audio - just logic and AI question generation
This bypasses TTS/STT issues to verify the core interview engine works
"""
import asyncio
import websockets
import json

async def test_interview_logic():
    print("="*70)
    print("🧪 Testing Interview Logic (No Audio)")
    print("="*70)
    
    # Load credentials
    try:
        with open("test_credentials.json", "r") as f:
            creds = json.load(f)
            token = creds["token"]
            interview_id = creds["interview_id"]
            print(f"✅ Credentials loaded")
            print(f"   Interview: {interview_id}")
    except Exception as e:
        print(f"❌ Failed: {e}")
        return
    
    url = f"ws://localhost:8000/api/v1/ws/interview/{interview_id}/voice?token={token}"
    print(f"\n📡 Connecting...")
    
    try:
        async with websockets.connect(url) as ws:
            print("✅ Connected!\n")
            
            question_count = 0
            
            for i in range(30):  # Up to 30 messages
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    data = json.loads(msg)
                    msg_type = data.get('type')
                    
                    print(f"📨 [{i+1}] Type: {msg_type}")
                    
                    if msg_type == 'greeting':
                        print(f"   👋 {data.get('text', '')[:100]}...")
                        
                    elif msg_type == 'question':
                        question_count += 1
                        meta = data.get('metadata', {})
                        print(f"   ❓ Question {meta.get('question_number')}/{meta.get('total_questions')}")
                        print(f"   📝 {data.get('text', '')[:100]}...")
                        print(f"   📊 Category: {meta.get('category')} | Difficulty: {meta.get('difficulty')}")
                        
                        # Send a text answer instead of audio
                        print(f"   💬 Sending text answer...")
                        answer_text = f"I have experience with {['Python', 'FastAPI', 'Docker', 'Microservices'][question_count % 4]}. I worked on building scalable systems using modern cloud technologies."
                        
                        # Send as JSON control message with answer
                        await ws.send(json.dumps({
                            "type": "text_answer",
                            "text": answer_text
                        }))
                        
                    elif msg_type == 'transcription':
                        print(f"   📝 Transcript: {data.get('text', '')[:100]}...")
                        
                    elif msg_type == 'acknowledgment':
                        print(f"   💬 {data.get('text')}")
                        
                    elif msg_type == 'closing':
                        print(f"   👋 {data.get('text', '')[:100]}...")
                        
                    elif msg_type == 'interview_complete':
                        print(f"   ✅ {data.get('message')}")
                        print(f"   🎯 Total questions asked: {data.get('total_questions', question_count)}")
                        break
                        
                    elif msg_type == 'error':
                        print(f"   ❌ Error: {data.get('message')}")
                        
                    print()
                    
                except asyncio.TimeoutError:
                    print(f"\n⏱️ Timeout after message {i+1}")
                    break
            
            print("="*70)
            print(f"📊 Summary: {question_count} questions generated")
            print("="*70)
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_interview_logic())