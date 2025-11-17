from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from bson import ObjectId
from app.models.user import PyObjectId


# -----------------------------
# Work Experience
# -----------------------------
class WorkExperience(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[List[str]] = []


# -----------------------------
# Education
# -----------------------------
class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    year: Optional[str] = None
    gpa: Optional[str] = None


# -----------------------------
# Project
# -----------------------------
class Project(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[List[str]] = []
    url: Optional[str] = None


# -----------------------------
# ParsedData (AI Output)
# -----------------------------
class ParsedData(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None

    skills: Optional[List[str]] = []
    experience: Optional[List[WorkExperience]] = []
    education: Optional[List[Education]] = []
    certifications: Optional[List[str]] = []
    projects: Optional[List[Project]] = []
    languages: Optional[List[str]] = []

    raw_text: Optional[str] = None

    # ⭐ Required field (your service depends on this)
    completeness_score: Optional[int] = 0


# -----------------------------
# Resume DB Model
# -----------------------------
class ResumeModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: PyObjectId
    file_name: str
    file_path: str
    file_size: int
    mime_type: str

    parsed_data: Optional[ParsedData] = None
    completeness_score: int = 0
    parsing_status: str = "pending"
    parsing_error: Optional[str] = None

    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    parsed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
