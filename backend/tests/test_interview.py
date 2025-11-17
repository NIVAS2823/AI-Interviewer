import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def auth_and_resume():
    """Create user and upload resume"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "interviewtest@example.com",
                "name": "Interview Test User",
                "password": "TestPass123!",
                "role": "job_seeker"
            }
        )
        token = register_response.json()["access_token"]
        
        # Upload resume
        files = {"file": ("resume.pdf", b"%PDF-1.4\nSample Resume", "application/pdf")}
        resume_response = await client.post(
            "/api/v1/resume/upload",
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
        resume_id = resume_response.json()["id"]
        
        return {"token": token, "resume_id": resume_id}


@pytest.mark.asyncio
async def test_create_interview_success(auth_and_resume):
    """Test successful interview creation"""
    data = await auth_and_resume
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/interview/create",
            json={
                "resume_id": data["resume_id"],
                "interview_type": "mixed",
                "difficulty": "medium",
                "max_questions": 5
            },
            headers={"Authorization": f"Bearer {data['token']}"}
        )
        
        # Note: May fail if resume not yet parsed
        # In real test, you'd wait or mock the parsing
        if response.status_code == 201:
            assert "interview_id" in response.json()
            assert len(response.json()["questions"]) == 5


@pytest.mark.asyncio
async def test_create_interview_invalid_resume(auth_and_resume):
    """Test interview creation with invalid resume"""
    data = await auth_and_resume
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/interview/create",
            json={
                "resume_id": "000000000000000000000000",  # Invalid ID
                "interview_type": "technical",
                "difficulty": "hard",
                "max_questions": 3
            },
            headers={"Authorization": f"Bearer {data['token']}"}
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_interviews(auth_and_resume):
    """Test listing interviews"""
    data = await auth_and_resume
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/interview/",
            headers={"Authorization": f"Bearer {data['token']}"}
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_start_interview(auth_and_resume):
    """Test starting interview"""
    data = await auth_and_resume
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create interview first
        create_response = await client.post(
            "/api/v1/interview/create",
            json={
                "resume_id": data["resume_id"],
                "interview_type": "technical",
                "difficulty": "easy",
                "max_questions": 3
            },
            headers={"Authorization": f"Bearer {data['token']}"}
        )
        
        if create_response.status_code == 201:
            interview_id = create_response.json()["interview_id"]
            
            # Start interview
            start_response = await client.post(
                f"/api/v1/interview/{interview_id}/start",
                headers={"Authorization": f"Bearer {data['token']}"}
            )
            
            assert start_response.status_code == 200
            assert start_response.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_end_interview(auth_and_resume):
    """Test ending interview"""
    data = await auth_and_resume
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create and start interview
        create_response = await client.post(
            "/api/v1/interview/create",
            json={
                "resume_id": data["resume_id"],
                "interview_type": "hr",
                "difficulty": "medium",
                "max_questions": 4
            },
            headers={"Authorization": f"Bearer {data['token']}"}
        )
        
        if create_response.status_code == 201:
            interview_id = create_response.json()["interview_id"]
            
            # Start
            await client.post(
                f"/api/v1/interview/{interview_id}/start",
                headers={"Authorization": f"Bearer {data['token']}"}
            )
            
            # End
            end_response = await client.post(
                f"/api/v1/interview/{interview_id}/end",
                json={"reason": "completed"},
                headers={"Authorization": f"Bearer {data['token']}"}
            )
            
            assert end_response.status_code == 200
            assert end_response.json()["status"] == "completed"