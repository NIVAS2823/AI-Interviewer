"""
Test Deepgram STT Service
"""

import asyncio
import os
from app.services.stt_service import STTService


async def test_stt_with_existing_file():
    """Test STT with existing audio file"""
    
    print("=" * 60)
    print("🎤 TESTING DEEPGRAM STT SERVICE")
    print("=" * 60)
    
    # Initialize service
    stt_service = STTService()
    
    if not stt_service.client:
        print("❌ STT Service not initialized")
        print("   Check DEEPGRAM_API_KEY in .env")
        return False
    
    # Look for test audio file
    test_file = "test_output.wav"
    
    if not os.path.exists(test_file):
        print(f"⚠️  Audio file '{test_file}' not found")
        print("\n💡 Creating test audio file using Azure TTS...")
        
        # Import TTS to create test file
        try:
            from app.services.tts_service import TTSService
            tts_service = TTSService()
            
            if not tts_service.speech_config:
                print("❌ TTS not configured, cannot create test file")
                return False
            
            # Create test audio
            success = await tts_service.synthesize_to_file(
                text="Hello! This is a test of speech to text transcription using Deepgram.",
                output_path=test_file
            )
            
            if not success:
                print("❌ Failed to create test audio")
                return False
            
            print(f"✅ Test audio created: {test_file}")
            
        except Exception as e:
            print(f"❌ Error creating test audio: {e}")
            return False
    
    # Transcribe the file
    print(f"\n🎙️  Transcribing: {test_file}")
    print("   This may take a few seconds...")
    
    transcript = await stt_service.transcribe_audio_file(test_file)
    
    if transcript:
        print(f"\n✅ Transcription successful!")
        print(f"📝 Original text: 'Hello! This is a test of speech to text transcription using Deepgram.'")
        print(f"📝 Transcript:    '{transcript}'")
        
        # Check accuracy
        if "speech to text" in transcript.lower():
            print("\n🎯 Accuracy: GOOD - Key phrases detected!")
        
        print("\n" + "=" * 60)
        return True
    else:
        print("\n❌ Transcription failed")
        print("=" * 60)
        return False


async def main():
    """Run test"""
    
    test_passed = await test_stt_with_existing_file()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"STT Service: {'✅ WORKING' if test_passed else '❌ FAILED'}")
    print("=" * 60)
    
    if test_passed:
        print("\n🎉 Deepgram STT is ready for voice interviews!")
        print("\n💡 Next: We'll integrate this with real-time WebSocket streaming")
    else:
        print("\n⚠️  Please check:")
        print("   1. DEEPGRAM_API_KEY is correct in .env")
        print("   2. You have credits in Deepgram account")
        print("   3. Internet connection is working")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())