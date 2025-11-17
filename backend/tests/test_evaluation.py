import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def setup_interview():
    """Create user, resume, and interview"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "evaltest@example.com",
                "name": "Eval Test User",
                "password": "TestPass123!",
                "role": "job_seeker"
            }
        )
        token = register_response.json()["access_token"]
        
        # Upload resume
        files = {"file": ("resume.pdf", b"%PDF-1.4\nSample Resume Content", "application/pdf")}
        resume_response = await client.post(
            "/api/v1/resume/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
        resume_id = resume_response.json()["id"]
        
        # Wait for parsing (in real test, mock this)
        import asyncio
        await asyncio.sleep(5)
        
        # Create interview
        interview_response = await client.post(
            "/api/v1/interview/create",
            json={
                "resume_id": resume_id,
                "interview_type": "technical",
                "difficulty": "medium",
                "max_questions": 3
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if interview_response.status_code == 201:
            interview_id = interview_response.json()["interview_id"]
            return {"token": token, "interview_id": interview_id}
        
        return None


@pytest.mark.asyncio
async def test_evaluate_single_answer():
    """Test single answer evaluation"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register user for auth
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "singleeval@example.com",
                "name": "Single Eval Test",
                "password": "TestPass123!",
                "role": "job_seeker"
            }
        )
        token = register_response.json()["access_token"]
        
        # Evaluate single answer
        response = await client.post(
            "/api/v1/evaluation/evaluate-answer",
            json={
                "question": "Tell me about your experience with Python",
                "answer": "I have 5 years of experience with Python, building web applications with Django and FastAPI.",
                "expected_topics": ["Python", "experience", "frameworks"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "feedback" in data


@pytest.mark.asyncio
async def test_get_evaluation_not_completed():
    """Test getting evaluation for incomplete interview"""
    setup = await setup_interview()
    
    if setup:
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/evaluation/{setup['interview_id']}",
                headers={"Authorization": f"Bearer {setup['token']}"}
            )
            
            # Should return 404 since interview not completed
            assert response.status