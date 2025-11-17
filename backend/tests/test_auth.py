import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_register_success():
    """Test successful user registration"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "name": "Test User",
                "password": "TestPass123!",
                "role": "job_seeker"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["name"] == "Test User"
        assert data["user"]["role"] == "job_seeker"


@pytest.mark.asyncio
async def test_register_duplicate_email():
    """Test registration with existing email"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First registration
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "name": "First User",
                "password": "TestPass123!",
                "role": "job_seeker"
            }
        )
        
        # Duplicate registration
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "name": "Second User",
                "password": "TestPass123!",
                "role": "job_seeker"
            }
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_weak_password():
    """Test registration with weak password"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "name": "Weak Pass User",
                "password": "weak",
                "role": "job_seeker"
            }
        )
        
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register user first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "name": "Login User",
                "password": "TestPass123!",
                "role": "job_seeker"
            }
        )
        
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "TestPass123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPass123!"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user():
    """Test getting current user info"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Register and get token
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "currentuser@example.com",
                "name": "Current User",
                "password": "TestPass123!",
                "role": "job_seeker"
            }
        )
        
        token = register_response.json()["access_token"]
        
        # Get current user
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "currentuser@example.com"
        assert data["name"] == "Current User"


@pytest.mark.asyncio
async def test_get_current_user_without_token():
    """Test getting current user without token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 403  # No credentials provided