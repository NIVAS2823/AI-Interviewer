# test_tts_service.py
"""
Test Azure TTS Service
Run: python test_tts_service.py
"""
import asyncio
import logging
from app.services.tts_service import TTSService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_tts():
    print("="*60)
    print("🎤 Testing Azure TTS Service")
    print("="*60)
    
    # Initialize service
    tts = TTSService()
    
    if not tts.speech_config:
        print("❌ TTS Service failed to initialize")
        return
    
    # Test 1: Simple greeting
    print("\n📝 Test 1: Synthesizing greeting...")
    text1 = "Hello! Welcome to your AI interview. I'm excited to learn more about you."
    audio1 = await tts.synthesize_speech(text1)
    
    if audio1 and len(audio1) > 0:
        print(f"✅ Greeting synthesized: {len(audio1)} bytes")
        with open("test_greeting.wav", "wb") as f:
            f.write(audio1)
        print("   Saved to: test_greeting.wav")
    else:
        print("❌ Failed to synthesize greeting")
    
    # Test 2: Interview question
    print("\n📝 Test 2: Synthesizing interview question...")
    text2 = "Tell me about your experience with Python and backend development."
    audio2 = await tts.synthesize_speech(text2)
    
    if audio2 and len(audio2) > 0:
        print(f"✅ Question synthesized: {len(audio2)} bytes")
        with open("test_question.wav", "wb") as f:
            f.write(audio2)
        print("   Saved to: test_question.wav")
    else:
        print("❌ Failed to synthesize question")
    
    # Test 3: Different voice
    print("\n📝 Test 3: Testing male voice...")
    text3 = "This is a test with a male voice."
    audio3 = await tts.synthesize_speech(text3, voice_name="en-IN-PrabhatNeural")
    
    if audio3 and len(audio3) > 0:
        print(f"✅ Male voice synthesized: {len(audio3)} bytes")
        with open("test_male_voice.wav", "wb") as f:
            f.write(audio3)
        print("   Saved to: test_male_voice.wav")
    else:
        print("❌ Failed to synthesize with male voice")
    
    # Test 4: File output method
    print("\n📝 Test 4: Testing file output method...")
    text4 = "Thank you for completing the interview. Good luck!"
    success = await tts.synthesize_to_file(text4, "test_closing.wav")
    
    if success:
        print("✅ Closing message saved to: test_closing.wav")
    else:
        print("❌ Failed to save closing message")
    
    # Test 5: Available voices
    print("\n📝 Test 5: Available voices...")
    voices = tts.get_available_voices()
    print(f"✅ Available voices: {len(voices)}")
    for voice in voices:
        print(f"   - {voice}")
    
    print("\n" + "="*60)
    print("🎉 TTS Testing Complete!")
    print("="*60)
    print("\n🔊 Play the generated .wav files to verify audio quality")

if __name__ == "__main__":
    asyncio.run(test_tts())