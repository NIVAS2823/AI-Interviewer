"""
Test R2 Storage Service
Run: python test_r2_upload.py
"""
import asyncio
import logging
from app.services.r2_storage_service import R2StorageService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_r2():
    print("="*70)
    print("🪣 Testing Cloudflare R2 Storage")
    print("="*70)
    
    # Initialize service
    r2 = R2StorageService()
    
    if not r2.client:
        print("❌ R2 client not initialized - check credentials")
        return
    
    # Test 1: Upload test file
    print("\n📤 Test 1: Uploading test recording...")
    test_audio = b"This is test audio data" * 1000  # ~23KB
    
    result = await r2.upload_recording(
        interview_id="test_interview_123",
        audio_data=test_audio,
        file_type="webm",
        metadata={
            "candidate_name": "Test Candidate",
            "interview_type": "technical"
        }
    )
    
    if result:
        print(f"✅ Upload successful!")
        print(f"   Key: {result['key']}")
        print(f"   Size: {result['size']} bytes")
        print(f"   URL: {result['public_url']}")
        
        # Test 2: Download
        print("\n📥 Test 2: Downloading recording...")
        downloaded = await r2.download_recording(result['key'])
        
        if downloaded:
            print(f"✅ Download successful: {len(downloaded)} bytes")
            if downloaded == test_audio:
                print("✅ Data integrity verified!")
            else:
                print("⚠️ Downloaded data doesn't match original")
        else:
            print("❌ Download failed")
        
        # Test 3: Get public URL
        print("\n🔗 Test 3: Generating public URL...")
        url = r2.get_public_url(result['key'])
        print(f"✅ Public URL: {url}")
        
        # Test 4: Delete (optional - comment out if you want to keep test file)
        # print("\n🗑️ Test 4: Deleting test recording...")
        # deleted = await r2.delete_recording(result['key'])
        # if deleted:
        #     print("✅ Delete successful")
    else:
        print("❌ Upload failed")
    
    print("\n" + "="*70)
    print("🎉 R2 Storage Test Complete!")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_r2())