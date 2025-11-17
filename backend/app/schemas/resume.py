from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.resume import ParsedData


class ResumeUploadResponse(BaseModel):
    """Response for resume upload"""
    
    id: str
    file_name: str
    file_size: int
    parsing_status: str
    message: str
    uploaded_at: datetime


class ResumeDetailResponse(BaseModel):
    """Detailed resume response with parsed data"""
    
    id: str
    user_id: str
    file_name: str
    file_size: int
    parsed_data: Optional[ParsedData] = None
    completeness_score: int
    parsing_status: str
    uploaded_at: datetime
    parsed_at: Optional[datetime] = None


class ResumeListResponse(BaseModel):
    """Response for listing resumes"""
    
    id: str
    file_name: str
    completeness_score: int
    parsing_status: str
    uploaded_at: datetime