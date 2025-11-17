from pydantic import BaseModel
from datetime import datetime

class InterviewMessage(BaseModel):
    speaker: str   # "ai" or "candidate"
    text: str
    timestamp: datetime = datetime.utcnow()
