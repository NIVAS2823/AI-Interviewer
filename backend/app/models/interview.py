from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from bson import ObjectId
from app.models.user import PyObjectId


class ConversationMessage(BaseModel):
    """Single conversation message"""
    speaker: str  # "ai" or "candidate"
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "speaker": "ai",
                "text": "Tell me about your experience with Python",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }


class Question(BaseModel):
    """Interview question"""
    question_text: str
    category: str  # technical, behavioral, hr
    difficulty: str  # easy, medium, hard
    expected_topics: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "question_text": "Describe your experience with FastAPI",
                "category": "technical",
                "difficulty": "medium",
                "expected_topics": ["FastAPI", "async", "REST API"]
            }
        }


class EvaluationScore(BaseModel):
    """Evaluation scores"""
    overall_score: int = 0  # 0-100
    technical_score: int = 0
    communication_score: int = 0
    confidence_score: int = 0
    behavioral_score: int = 0


class SentimentAnalysis(BaseModel):
    """Sentiment analysis results"""
    positive: float = 0.0
    neutral: float = 0.0
    negative: float = 0.0


class Evaluation(BaseModel):
    """Interview evaluation"""
    scores: EvaluationScore = Field(default_factory=EvaluationScore)
    sentiment: Optional[SentimentAnalysis] = None
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    detailed_feedback: Optional[str] = None
    question_scores: List[Dict] = Field(default_factory=list)  # Individual question scores


class InterviewModel(BaseModel):
    """Interview database model"""

    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    candidate_id: PyObjectId  # User who takes interview
    resume_id: Optional[PyObjectId] = None
    job_id: Optional[PyObjectId] = None  # For HR interviews

    job_description: Optional[str] = None

    # VideoSDK details
    session_id: Optional[str] = None  # VideoSDK meeting ID
    meeting_token: Optional[str] = None
    agent_id: Optional[str] = None

    # Interview configuration
    interview_type: str  # technical, behavioral, hr, mixed
    difficulty: str = "medium"  # easy, medium, hard
    max_questions: int = 5

    # Generated questions
    questions: List[Question] = Field(default_factory=list)
    current_question_index: int = 0

    # Conversation
    conversation: List[ConversationMessage] = Field(default_factory=list)

    # Status
    status: str = "created"  # created, in_progress, completed, failed

    # Evaluation
    evaluation: Optional[Evaluation] = None

    # Metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    recording_url: Optional[str] = None
    transcript_url: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str, PyObjectId: str}
        json_schema_extra = {
            "example": {
                "candidate_id": "507f1f77bcf86cd799439011",
                "resume_id": "507f1f77bcf86cd799439012",
                "interview_type": "mixed",
                "difficulty": "medium",
                "status": "created"
            }
        }
