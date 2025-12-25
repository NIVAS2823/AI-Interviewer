import asyncio
import logging
from app.services.voice_agent_service import VoiceAgentService
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
load_dotenv()

async def test():
    print("\n" + "="*50)
    print("Testing Voice Agent with Deepgram TTS")
    print("="*50 + "\n")
    
    agent = VoiceAgentService()
    
    print(f"Agent Ready: {agent.is_ready()}")
    
    # Test greeting
    result = await agent.generate_greeting(
        candidate_name="John Doe",
        interview_type="Technical",
        num_questions=3
    )
    
    print(f"\n✅ Greeting generated:")
    print(f"   Text: {result['text'][:60]}...")
    print(f"   Audio: {len(result['audio_bytes'])} bytes")
    print(f"   Type: {result['message_type']}")
    
    if len(result['audio_bytes']) > 0:
        print("\n✅ SUCCESS! Deepgram TTS is working!")
    else:
        print("\n❌ FAILED! No audio generated")

if __name__ == "__main__":
    asyncio.run(test())