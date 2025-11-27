from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.interview import Question, ConversationMessage, Evaluation


class InterviewCreateRequest(BaseModel):
    """Request to create interview"""
    resume_id: str
    interview_type: str = Field(..., pattern="^(technical|behavioral|hr|mixed)$")
    difficulty: str = Field(default="easy", pattern="^(easy|medium|hard)$")
    max_questions: int = Field(default=5, ge=3, le=10)
    job_description: Optional[str] = Field(
        default=None,
        description="Job description for context (optional but recommended)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "resume_id": "507f1f77bcf86cd799439011",
                "interview_type": "mixed",
                "difficulty": "medium",
                "max_questions": 5,
                 "job_description": "Senior Full Stack Developer with 3+ years experience in React, Python, and FastAPI. Must have strong problem-solving skills and experience with cloud deployment." 
            }
        }


class InterviewCreateResponse(BaseModel):
    """Response for interview creation"""
    interview_id: str
    meeting_id: Optional[str] = None
    meeting_token: Optional[str] = None
    agent_id: Optional[str] = None
    questions: List[Question]
    first_question: str
    status: str
    message: str
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "interview_id": "507f1f77bcf86cd799439011",
                "meeting_id": "vsdk-meeting-abc123",
                "meeting_token": "eyJhbGc...",
                "agent_id": "vsdk-agent-xyz789",
                "questions": [],
                "first_question": "Tell me about yourself",
                "status": "created",
                "message": "Interview created successfully",
                "created_at": "2025-01-15T10:30:00Z"
            }
        }


class InterviewDetailResponse(BaseModel):
    """Detailed interview response"""
    id: str
    candidate_id: str
    resume_id: Optional[str] = None
    job_description: Optional[str] = None  # ADD THIS
    interview_type: str
    difficulty: str
    status: str
    max_questions: int  # ADD THIS
    questions: List[Question]
    conversation: List[ConversationMessage]
    evaluation: Optional[Evaluation] = None
    session_id: Optional[str] = None  # ADD THIS
    meeting_token: Optional[str] = None  # ADD THIS
    agent_id: Optional[str] = None  # ADD THIS
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    created_at: datetime


class InterviewListResponse(BaseModel):
    """Interview list item"""
    id: str
    interview_type: str
    status: str
    overall_score: Optional[int] = None
    created_at: datetime
    duration_minutes: Optional[int] = None


class InterviewEndRequest(BaseModel):
    """Request to end interview"""
    reason: Optional[str] = "completed"


class InterviewEndResponse(BaseModel):
    """Response for ending interview"""
    interview_id: str
    status: str
    evaluation: Optional[Evaluation] = None
    message: str