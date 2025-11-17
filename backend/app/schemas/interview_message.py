from pydantic import BaseModel
from datetime import datetime

class InterviewMessageRequest(BaseModel):
    text: str

class InterviewMessageResponse(BaseModel):
    ai_text: str
    timestamp: datetime
