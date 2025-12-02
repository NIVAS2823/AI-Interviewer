# test_create_interview.py
"""
Create a test interview with questions for WebSocket testing
Run: python test_create_interview.py
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def create_test_interview():
    print("="*70)
    print("🎬 Creating Test Interview with Questions")
    print("="*70)

    # Step 1: Login
    print("\n1️⃣ Logging in...")
    async with httpx.AsyncClient() as client:
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": "john.doe@example.com",
                "password": "SecurePass123!"
            }
        )

        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(login_response.text)
            return None

        token = login_response.json()["access_token"]
        print("✅ Token obtained")

    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Get resumes
    print("\n2️⃣ Checking for resumes...")
    async with httpx.AsyncClient() as client:
        resumes_response = await client.get(
            f"{BASE_URL}/resume/",
            headers=headers
        )

        if resumes_response.status_code == 200:
            resumes = resumes_response.json()
            if resumes:
                resume_id = resumes[0]["id"]
                print(f"✅ Using existing resume: {resume_id}")
            else:
                print("❌ No resumes found.")
                return None
        else:
            print(f"❌ Failed to get resumes: {resumes_response.status_code}")
            return None

    # Step 3: Create interview
    print("\n3️⃣ Creating interview with questions...")

    interview_data = {
        "resume_id": resume_id,
        "interview_type": "technical",
        "difficulty": "medium",
        "max_questions": 5,
        "job_description": "We need a Python Backend Developer experienced in FastAPI and Docker."
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        interview_response = await client.post(
            f"{BASE_URL}/interview/create",
            headers=headers,
            json=interview_data
        )

        if interview_response.status_code in (200, 201):
            interview = interview_response.json()
            interview_id = interview["interview_id"]

            print(f"✅ Interview created: {interview_id}")
            print(f"📝 First Question: {interview['first_question']}")
            print(f"📋 Status: {interview['status']}")

            num_questions = len(interview.get("questions", []))
            print(f"🧮 Questions returned in array: {num_questions}")

            print("\n" + "="*70)
            print("🎉 Test Interview Ready!")
            print("="*70)
            print(f"\n🔑 Interview ID: {interview_id}")
            print(f"🔑 Token: {token[:30]}...")

            return {
                "interview_id": interview_id,
                "token": token,
                "num_questions": num_questions
            }

        else:
            print(f"❌ Failed to create interview: {interview_response.status_code}")
            print(interview_response.text)
            return None

if __name__ == "__main__":
    result = asyncio.run(create_test_interview())

    if result:
        with open("test_credentials.json", "w") as f:
            json.dump(result, f, indent=2)
        print("\n💾 Credentials saved to: test_credentials.json")
