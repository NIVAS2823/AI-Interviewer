from app.core.config import settings

def test_config():
    print("=" * 60)
    print("🔧 CONFIGURATION TEST")
    print("=" * 60)
    
    # Check each service
    services = {
        "Groq AI": bool(settings.GROQ_API_KEY),
        "Deepgram STT": bool(settings.DEEPGRAM_API_KEY),
        "Azure TTS": bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION),
        "Cloudflare R2": bool(settings.R2_ACCESS_KEY_ID and settings.R2_BUCKET_NAME),
        "MongoDB": bool(settings.MONGODB_URL),
        "Redis": bool(settings.REDIS_URL),
    }
    
    print("\n📊 Service Configuration:")
    for service, configured in services.items():
        status = "✅" if configured else "❌"
        print(f"   {status} {service}")
    
    # Show key prefixes (first 5 chars only)
    print("\n🔑 API Keys (first 5 chars):")
    if settings.GROQ_API_KEY:
        print(f"   Groq: {settings.GROQ_API_KEY[:5]}...")
    if settings.DEEPGRAM_API_KEY:
        print(f"   Deepgram: {settings.DEEPGRAM_API_KEY[:5]}...")
    if settings.AZURE_SPEECH_KEY:
        print(f"   Azure: {settings.AZURE_SPEECH_KEY[:5]}...")
    
    print("\n🌍 Azure Region:", settings.AZURE_SPEECH_REGION)
    print("🪣 R2 Bucket:", settings.R2_BUCKET_NAME)
    
    print("\n" + "=" * 60)
    
    all_configured = all(services.values())
    if all_configured:
        print("✅ ALL SERVICES CONFIGURED!")
    else:
        print("⚠️  Some services not configured")
    
    print("=" * 60)
    
    return all_configured

if __name__ == "__main__":
    test_config()