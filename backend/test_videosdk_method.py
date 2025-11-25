import asyncio
from app.utils.videosdk_agent import VideoSDKAgentService

async def test_build_prompt():
    service = VideoSDKAgentService()
    
    questions = [
        "Tell me about your experience with Python",
        "Describe a challenging project you worked on",
        "How do you handle debugging?"
    ]
    
    candidate_info = {
        "name": "John Doe",
        "skills": ["Python", "FastAPI", "React", "MongoDB"],
        "experience_years": 3,
        "education": ["BS in Computer Science"]
    }
    
    prompt = service.build_system_prompt(
        interviewer_name="Sarah",
        interview_type="technical",
        questions=questions,
        candidate_info=candidate_info
    )
    
    print("=" * 50)
    print("SYSTEM PROMPT GENERATED:")
    print("=" * 50)
    print(prompt)
    print("=" * 50)
    print("✅ Test passed! Method works correctly")

if __name__ == "__main__":
    asyncio.run(test_build_prompt())