import pytest
from httpx import AsyncClient
from app.main import app
import os
from pathlib import Path


@pytest.fixture
async def auth_token():
    """Get authentication token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "resumetest@example.com",
                "name": "Resume Test User",
                "password": "TestPass123!",
                "role": "job_seeker"
            }
        )
        return response.json()["access_token"]


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing"""
    # For testing, we'll use a simple text file as PDF
    # In production, use actual PDF
    content = b"%PDF-1.4\nSample Resume Content"
    return ("resume.pdf", content, "application/pdf")


@pytest.mark.asyncio
async def test_upload_resume_success(auth_token, sample_pdf):
    """Test successful resume upload"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        files = {"file": sample_pdf}
        response = await client.post(
            "/api/v1/resume/upload",
            files=files,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["file_name"] == "resume.pdf"
        assert data["parsing_status"] in ["pending", "processing"]


@pytest.mark.asyncio
async def test_upload_resume_without_auth():
    """Test upload without authentication"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        files = {"file": ("resume.pdf", b"content", "application/pdf")}
        response = await client.post("/api/v1/resume/upload", files=files)
        
        assert response.status_code == 403  # Unauthorized


@pytest.mark.asyncio
async def test_upload_invalid_file_type(auth_token):
    """Test upload with invalid file type"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        files = {"file": ("document.txt", b"content", "text/plain")}
        response = await client.post(
            "/api/v1/resume/upload",
            files=files,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_resumes(auth_token):
    """Test listing user resumes"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/resume/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_resume_detail(auth_token, sample_pdf):
    """Test getting resume details"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload resume first
        files = {"file": sample_pdf}
        upload_response = await client.post(
            "/api/v1/resume/upload",
            files=files,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        resume_id = upload_response.json()["id"]
        
        # Get resume details
        response = await client.get(
            f"/api/v1/resume/{resume_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == resume_id
        assert "parsed_data" in data


@pytest.mark.asyncio
async def test_delete_resume(auth_token, sample_pdf):
    """Test deleting resume"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload resume first
        files = {"file": sample_pdf}
        upload_response = await client.post(
            "/api/v1/resume/upload",
            files=files,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        resume_id = upload_response.json()["id"]
        
        # Delete resume
        response = await client.delete(
            f"/api/v1/resume/{resume_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 204
        
        # Verify deleted
        get_response = await client.get(
            f"/api/v1/resume/{resume_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 404