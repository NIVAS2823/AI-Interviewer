# test_voice_agent.py
"""
Test Voice Agent Service - Complete AI Interview Flow
Tests: STT → AI → TTS pipeline
Run: python test_voice_agent.py
"""
import asyncio
import logging
from app.services.voice_agent_service import VoiceAgentService
from app.models.resume import ParsedData

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_voice_agent():
    print("="*70)
    print("🤖 Testing Voice Agent Service (AI Interview Brain)")
    print("="*70)
    
    # Initialize agent
    agent = VoiceAgentService()
    
    # Check readiness
    print("\n📊 Service Readiness Check:")
    print(f"   STT Ready: {'✅' if getattr(agent.stt, 'client', None) else '❌'}")
    print(f"   TTS Ready: {'✅' if getattr(agent.tts, 'speech_config', None) else '❌'}")
    print(f"   AI Ready:  {'✅' if agent.question_generator else '❌'}")
    print(f"   Overall:   {'✅ READY' if agent.is_ready() else '❌ NOT READY'}")
    
    if not agent.is_ready():
        print("\n❌ Agent not ready. Please check your API keys.")
        return
    
    # Mock resume data for testing
    mock_resume = ParsedData(
        personal_info={
            "name": "Rahul Kumar",
            "email": "rahul.kumar@email.com",
            "phone": "+91-9876543210"
        },
        education=[
            {
                "degree": "B.Tech in Computer Science",
                "institution": "IIT Delhi",
                "year": "2020-2024"
            }
        ],
        experience=[
            {
                "title": "Backend Developer Intern",
                "company": "Tech Corp",
                "duration": "6 months",
                "description": "Worked on Python FastAPI microservices"
            }
        ],
        skills=[
            "Python",
            "FastAPI",
            "MongoDB",
            "Docker",
            "AWS",
            "Team collaboration",
            "Problem solving"
        ],


        projects=[
            {
                "name": "E-commerce API",
                "description": "Built RESTful API with FastAPI and PostgreSQL",
                "technologies": ["Python", "FastAPI", "PostgreSQL"]
            }
        ]
    )
    
    # Test 1: Generate Greeting
    print("\n" + "="*70)
    print("📝 Test 1: Generating Interview Greeting")
    print("="*70)
    
    greeting = await agent.generate_greeting(
        candidate_name="Rahul Kumar",
        interview_type="Technical",
        num_questions=5,
        voice="en-IN-NeerjaNeural"
    )
    
    print(f"✅ Greeting Text: {greeting['text']}")
    print(f"✅ Audio Size: {len(greeting['audio_bytes'])} bytes")
    
    if greeting['audio_bytes']:
        with open("test_agent_greeting.wav", "wb") as f:
            f.write(greeting['audio_bytes'])
        print("✅ Saved to: test_agent_greeting.wav")
    
    # Test 2: Generate Dynamic Question
    print("\n" + "="*70)
    print("📝 Test 2: Generating Dynamic Question")
    print("="*70)
    
    question = await agent.generate_next_question_dynamic(
        resume=mock_resume,
        job_description="Looking for a Python Backend Developer with FastAPI experience",
        conversation_history=[],
        interview_type="technical",
        difficulty="medium",
        question_number=1,
        total_questions=5
    )
    
    if question:
        print(f"✅ Question Generated:")
        print(f"   Text: {question.question_text}")
        print(f"   Category: {question.category}")
        print(f"   Difficulty: {question.difficulty}")
        
        # Ask the question with voice
        q_audio = await agent.ask_question(question, voice="en-IN-NeerjaNeural")
        print(f"✅ Question Audio: {len(q_audio['audio_bytes'])} bytes")
        
        if q_audio['audio_bytes']:
            with open("test_agent_question.wav", "wb") as f:
                f.write(q_audio['audio_bytes'])
            print("✅ Saved to: test_agent_question.wav")
    else:
        print("❌ Failed to generate question")
    
    # Test 3: Process Mock Answer (STT)
    print("\n" + "="*70)
    print("📝 Test 3: Processing Audio Answer (STT)")
    print("="*70)
    
    # Use one of our previously generated test files as mock audio input
    try:
        with open("test_greeting.wav", "rb") as f:
            mock_audio = f.read()
        
        print(f"📥 Processing {len(mock_audio)} bytes of audio...")
        transcript = await agent.process_answer(mock_audio)
        
        if transcript:
            print(f"✅ Transcription: {transcript}")
        else:
            print("⚠️ No transcription (may be expected if audio is TTS output)")
    except FileNotFoundError:
        print("⚠️ test_greeting.wav not found, skipping STT test")
    
    # Test 4: Generate Acknowledgment
    print("\n" + "="*70)
    print("📝 Test 4: Generating Acknowledgment")
    print("="*70)
    
    ack = await agent.generate_acknowledgment(
        answer="I have 6 months of experience with FastAPI...",
        voice="en-IN-NeerjaNeural"
    )
    
    print(f"✅ Acknowledgment: {ack['text']}")
    print(f"✅ Audio Size: {len(ack['audio_bytes'])} bytes")
    
    if ack['audio_bytes']:
        with open("test_agent_acknowledgment.wav", "wb") as f:
            f.write(ack['audio_bytes'])
        print("✅ Saved to: test_agent_acknowledgment.wav")
    
    # Test 5: Generate Closing
    print("\n" + "="*70)
    print("📝 Test 5: Generating Interview Closing")
    print("="*70)
    
    closing = await agent.generate_closing(
        candidate_name="Rahul Kumar",
        voice="en-IN-NeerjaNeural"
    )
    
    print(f"✅ Closing Text: {closing['text']}")
    print(f"✅ Audio Size: {len(closing['audio_bytes'])} bytes")
    
    if closing['audio_bytes']:
        with open("test_agent_closing.wav", "wb") as f:
            f.write(closing['audio_bytes'])
        print("✅ Saved to: test_agent_closing.wav")
    
    # Test 6: Voice Preferences
    print("\n" + "="*70)
    print("📝 Test 6: Testing Male Voice")
    print("="*70)
    
    male_greeting = await agent.generate_greeting(
        candidate_name="Rahul",
        interview_type="Technical",
        num_questions=3,
        voice="en-IN-PrabhatNeural"  # Male voice
    )
    
    print(f"✅ Male Voice Audio: {len(male_greeting['audio_bytes'])} bytes")
    
    if male_greeting['audio_bytes']:
        with open("test_agent_male_voice.wav", "wb") as f:
            f.write(male_greeting['audio_bytes'])
        print("✅ Saved to: test_agent_male_voice.wav")
    
    # Summary
    print("\n" + "="*70)
    print("🎉 Voice Agent Testing Complete!")
    print("="*70)
    print("\n📁 Generated Files:")
    print("   - test_agent_greeting.wav")
    print("   - test_agent_question.wav")
    print("   - test_agent_acknowledgment.wav")
    print("   - test_agent_closing.wav")
    print("   - test_agent_male_voice.wav")
    print("\n🔊 Play these files to verify the complete interview flow!")

if __name__ == "__main__":
    asyncio.run(test_voice_agent())