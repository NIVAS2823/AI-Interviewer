import os
import boto3
from dotenv import load_dotenv

load_dotenv()

def test_r2_upload():
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    endpoint = os.getenv("R2_ENDPOINT")
    bucket_name = os.getenv("R2_BUCKET_NAME")
    
    if not all([access_key, secret_key, endpoint, bucket_name]):
        print("❌ R2 credentials not found in .env")
        return False
    
    print(f"🔧 Testing Cloudflare R2...")
    print(f"   Endpoint: {endpoint}")
    print(f"   Bucket: {bucket_name}")
    
    try:
        # Create S3 client for R2
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='auto'  # R2 uses 'auto'
        )
        
        # Create test file
        test_content = b"Hello from AI Interviewer! This is a test recording."
        test_filename = "test_recording.txt"
        
        print(f"📤 Uploading test file: {test_filename}")
        
        # Upload
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_filename,
            Body=test_content,
            ContentType='text/plain'
        )
        
        print("✅ Upload successful!")
        
        # List files to verify
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        
        if 'Contents' in response:
            print(f"📁 Files in bucket:")
            for obj in response['Contents']:
                print(f"   - {obj['Key']} ({obj['Size']} bytes)")
        
        # Get public URL if available
        public_url = os.getenv("R2_PUBLIC_URL")
        if public_url:
            file_url = f"{public_url}/{test_filename}"
            print(f"\n🌐 Public URL: {file_url}")
            print("   (Visit this URL in browser to verify)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_r2_upload()