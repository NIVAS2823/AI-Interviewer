from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
import re


class UserRegisterSchema(BaseModel):
    """Schema for user registration"""
    
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default="job_seeker")
    
    @validator("name")
    def validate_name(cls, v):
        if not re.match(r"^[a-zA-Z\s]+$", v):
            raise ValueError("Name must contain only letters and spaces")
        return v.strip()
    
    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v
    
    @validator("role")
    def validate_role(cls, v):
        allowed_roles = ["job_seeker", "hr_professional"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "name": "John Doe",
                "password": "SecurePass123!",
                "role": "job_seeker"
            }
        }


class UserLoginSchema(BaseModel):
    """Schema for user login"""
    
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "password": "SecurePass123!"
            }
        }


class UserResponseSchema(BaseModel):
    """Schema for user response (without sensitive data)"""
    
    id: str
    email: EmailStr
    name: str
    role: str
    is_active: bool
    email_verified: bool
    profile: Optional[dict] = None
    subscription: Optional[dict] = None
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "john.doe@example.com",
                "name": "John Doe",
                "role": "job_seeker",
                "is_active": True,
                "email_verified": False,
                "subscription": {
                    "plan": "free",
                    "interviews_remaining": 3
                },
                "created_at": "2025-01-15T10:00:00Z"
            }
        }


class TokenSchema(BaseModel):
    """Schema for JWT token response"""
    
    access_token: str
    token_type: str = "bearer"
    user: UserResponseSchema
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "507f1f77bcf86cd799439011",
                    "email": "john.doe@example.com",
                    "name": "John Doe",
                    "role": "job_seeker"
                }
            }
        }


class UserUpdateSchema(BaseModel):
    """Schema for updating user profile"""
    
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    profile: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Updated Doe",
                "profile": {
                    "phone": "+1234567890",
                    "location": "San Francisco, CA",
                    "linkedin": "https://linkedin.com/in/johndoe"
                }
            }
        }