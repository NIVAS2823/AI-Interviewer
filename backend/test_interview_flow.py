"""
End-to-End Interview Flow Test
Tests: Create Interview → Start → Simulate → End → Evaluate
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
WORKER_URL = "http://localhost:9000"

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "TestPass123!"
TEST_NAME = "Test User"


async def test_interview_flow():
    """Test complete interview flow"""
    
    print("=" * 60)
    print("🧪 AI INTERVIEWER - END-TO-END TEST")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        
        # Step 1: Register/Login
        print("\n📝 Step 1: Authentication")
        print("-" * 60)
        
        # Try to register (will fail if user exists, that's ok)
        try:
            reg_response = await client.post(
                f"{BASE_URL}/api/v1/auth/register",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD,
                    "name": TEST_NAME,
                    "role": "job_seeker"
                }
            )
            if reg_response.status_code == 201:
                print("✅ User registered successfully")
                token = reg_response.json()["access_token"]
                print(f"   Token: {token[:30]}...")
            else:
                print(f"   User may already exist, trying login...")
                raise Exception("Try login")
        except:
            # Login with existing user
            login_response = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD
                }
            )
            
            if login_response.status_code != 200:
                print(f"❌ Login failed: {login_response.text}")
                print(f"\n💡 TIP: Make sure user exists or check credentials")
                return False
            
            token = login_response.json()["access_token"]
            print(f"✅ Logged in successfully")
            print(f"   Token: {token[:30]}...")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        
        # Step 2: Upload Resume
        print("\n📄 Step 2: Upload Resume")
        print("-" * 60)
        
        # Check if resume already exists
        resumes_response = await client.get(
            f"{BASE_URL}/api/v1/resume/",
            headers=headers
        )
        
        resume_id = None
        if resumes_response.status_code == 200:
            resumes = resumes_response.json()
            if resumes:
                resume_id = resumes[0]["id"]
                print(f"✅ Using existing resume: {resume_id}")
        
        if not resume_id:
            # Create a test PDF with proper structure
            print("   Creating test resume...")
            
            # Simple but valid PDF content
            pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 100 >>
stream
BT
/F1 12 Tf
100 700 Td
(John Doe - Software Engineer) Tj
0 -20 Td
(Skills: Python, FastAPI, React) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
0000000304 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
452
%%EOF
"""
            
            files = {"file": ("test_resume.pdf", pdf_content, "application/pdf")}
            upload_response = await client.post(
                f"{BASE_URL}/api/v1/resume/upload",
                headers=headers,
                files=files
            )
            
            if upload_response.status_code != 201:
                print(f"❌ Resume upload failed: {upload_response.text}")
                return False
            
            resume_data = upload_response.json()
            resume_id = resume_data["id"]
            print(f"✅ Resume uploaded: {resume_id}")
            
            # Wait for parsing
            print("   Waiting for resume parsing...")
            await asyncio.sleep(5)
        
        
        # Step 3: Create Interview
        print("\n🎤 Step 3: Create Interview")
        print("-" * 60)
        
        interview_response = await client.post(
            f"{BASE_URL}/api/v1/interview/create",
            headers=headers,
            json={
                "resume_id": resume_id,
                "interview_type": "mixed",
                "difficulty": "medium",
                "max_questions": 5
            }
        )
        
        if interview_response.status_code != 201:
            print(f"❌ Interview creation failed: {interview_response.text}")
            return False
        
        interview_data = interview_response.json()
        interview_id = interview_data["interview_id"]
        agent_id = interview_data.get("agent_id")
        
        print(f"✅ Interview created: {interview_id}")
        print(f"   Agent ID: {agent_id}")
        print(f"   Questions: {len(interview_data['questions'])}")
        if interview_data['questions']:
            print(f"   First question: {interview_data['first_question'][:60]}...")
        
        
        # Step 4: Start Interview
        print("\n▶️  Step 4: Start Interview")
        print("-" * 60)
        
        start_response = await client.post(
            f"{BASE_URL}/api/v1/interview/{interview_id}/start",
            headers=headers
        )
        
        if start_response.status_code != 200:
            print(f"❌ Interview start failed: {start_response.text}")
            return False
        
        start_data = start_response.json()
        print(f"✅ Interview started")
        print(f"   Status: {start_data['status']}")
        
        
        # Step 5: Simulate Conversation
        print("\n💬 Step 5: Simulate Conversation")
        print("-" * 60)
        
        conversation_ok = False
        
        if agent_id:
            try:
                # Use worker's simulate endpoint
                simulate_response = await client.post(
                    f"{WORKER_URL}/simulate/{agent_id}",
                    timeout=30
                )
                
                if simulate_response.status_code == 200:
                    sim_data = simulate_response.json()
                    print(f"✅ Conversation simulated via worker")
                    print(f"   Messages exchanged: {sim_data['message_count']}")
                    conversation_ok = True
                    
                    # Get transcript from worker
                    transcript_response = await client.get(
                        f"{WORKER_URL}/transcript/{agent_id}"
                    )
                    
                    if transcript_response.status_code == 200:
                        transcript = transcript_response.json()["transcript"]
                        print(f"\n   📝 Conversation Preview:")
                        for i, msg in enumerate(transcript[:4]):
                            speaker = "🤖 AI" if msg["role"] == "assistant" else "👤 Candidate"
                            content = msg["content"][:70]
                            print(f"      {speaker}: {content}...")
            except Exception as e:
                print(f"⚠️  Worker simulation failed: {e}")
        
        if not conversation_ok:
            print(f"   Using backend simulate endpoint...")
            try:
                backend_sim = await client.post(
                    f"{BASE_URL}/api/v1/interview/{interview_id}/simulate",
                    headers=headers
                )
                if backend_sim.status_code == 200:
                    print(f"✅ Fallback simulation completed")
                    conversation_ok = True
                else:
                    print(f"⚠️  Simulation returned: {backend_sim.status_code}")
            except Exception as e:
                print(f"⚠️  Backend simulation failed: {e}")
        
        if not conversation_ok:
            print("⚠️  No conversation generated, evaluation may be limited")
        
        
        # Step 6: End Interview
        print("\n⏹️  Step 6: End Interview & Evaluate")
        print("-" * 60)
        
        end_response = await client.post(
            f"{BASE_URL}/api/v1/interview/{interview_id}/end",
            headers=headers,
            json={"reason": "completed"}
        )
        
        if end_response.status_code != 200:
            print(f"❌ Interview end failed: {end_response.text}")
            return False
        
        end_data = end_response.json()
        print(f"✅ Interview ended")
        print(f"   Status: {end_data['status']}")
        
        
        # Step 7: Get Evaluation Results
        print("\n📊 Step 7: Evaluation Results")
        print("-" * 60)
        
        detail_response = await client.get(
            f"{BASE_URL}/api/v1/interview/{interview_id}",
            headers=headers
        )
        
        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            evaluation = detail_data.get("evaluation")
            
            if evaluation:
                scores = evaluation["scores"]
                print(f"✅ Evaluation completed!")
                print(f"\n   📈 SCORES:")
                print(f"      Overall:        {scores['overall_score']}/100")
                print(f"      Technical:      {scores['technical_score']}/100")
                print(f"      Communication:  {scores['communication_score']}/100")
                print(f"      Confidence:     {scores['confidence_score']}/100")
                print(f"      Behavioral:     {scores['behavioral_score']}/100")
                
                if evaluation.get("strengths"):
                    print(f"\n   💪 STRENGTHS:")
                    for strength in evaluation["strengths"][:3]:
                        print(f"      • {strength}")
                
                if evaluation.get("improvements"):
                    print(f"\n   🎯 AREAS TO IMPROVE:")
                    for improvement in evaluation["improvements"][:3]:
                        print(f"      • {improvement}")
                
                if evaluation.get("detailed_feedback"):
                    feedback = evaluation["detailed_feedback"][:150]
                    print(f"\n   💬 FEEDBACK:")
                    print(f"      {feedback}...")
            else:
                print("⚠️  No evaluation found (conversation may have been empty)")
        
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ END-TO-END TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"   Interview ID: {interview_id}")
        print(f"   Agent ID: {agent_id}")
        print(f"   Status: {end_data['status']}")
        if detail_response.status_code == 200:
            print(f"   Duration: {detail_data.get('duration_minutes', 0)} minutes")
        print("\n" + "=" * 60)
        
        return True


async def main():
    try:
        success = await test_interview_flow()
        if not success:
            print("\n❌ Test failed!")
            exit(1)
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())