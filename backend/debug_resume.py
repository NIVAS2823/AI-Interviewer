"""
Debug resume data structure
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import json

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "ai_interviewer"

async def check_resume():
    # Load credentials
    with open("test_credentials.json", "r") as f:
        creds = json.load(f)
        interview_id = creds["interview_id"]
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    # Get interview
    interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
    print("Interview data:")
    print(f"  Type: {interview.get('interview_type')}")
    print(f"  Difficulty: {interview.get('difficulty')}")
    print(f"  Max Questions: {interview.get('max_questions')}")
    print(f"  Job Description: {interview.get('job_description', 'None')[:100]}...")
    
    # Get resume
    resume = await db.resumes.find_one({"_id": interview.get("resume_id")})
    
    if resume:
        parsed = resume.get("parsed_data", {})
        print("\nResume parsed_data structure:")
        print(f"  Keys: {list(parsed.keys())}")
        print(f"  personal_info: {parsed.get('personal_info')}")
        print(f"  education: {len(parsed.get('education', []))} entries")
        print(f"  experience: {len(parsed.get('experience', []))} entries")
        print(f"  skills: {parsed.get('skills')}")

        # Try to create ParsedData model
        try:
            from app.models.resume import ParsedData
            resume_data = ParsedData(**parsed)
            print("\n✅ ParsedData created successfully")

            # --- FLEXIBLE NAME HANDLING ---
            name = None

            # 1. New format → name/email/phone at root
            if hasattr(resume_data, "name"):
                name = resume_data.name

            # 2. Old format → personal_info block
            elif hasattr(resume_data, "personal_info") and resume_data.personal_info:
                name = resume_data.personal_info.get("name")

            # 3. If still missing
            if not name:
                name = "Name missing"

            print(f"  Name: {name}")

        except Exception as e:
            print(f"\n❌ Failed to create ParsedData: {e}")

    client.close()


if __name__ == "__main__":
    asyncio.run(check_resume())
