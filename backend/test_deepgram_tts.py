# Create a test file: test_deepgram_tts.py in backend/
import os
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.getenv("DEEPGRAM_API_KEY")

# Test TTS endpoint
url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
headers = {
    "Authorization": f"Token {api_key}",
    "Content-Type": "application/json"
}
data = {
    "text": "Hello, this is a test of Deepgram text to speech."
}

response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.headers.get('content-type')}")

if response.status_code == 200:
    print("✅ Deepgram TTS is working!")
    with open("test_output.mp3", "wb") as f:
        f.write(response.content)
    print("✅ Saved test audio to test_output.mp3")
else:
    print(f"❌ Error: {response.text}")