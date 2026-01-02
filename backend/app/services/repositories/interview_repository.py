"""
Interview Repository
Handles all database operations related to interviews
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument
import logging

from app.models.interview import InterviewModel, Question, Evaluation
from app.services.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class InterviewRepository(BaseRepository[InterviewModel]):
    """
    Repository for interview-related database operations
    Extends BaseRepository with interview-specific methods
    """

    def __init__(self, db):
        """
        Initialize with database connection
        
        Args:
            db: MongoDB database instance
        """
        super().__init__(db.interviews, InterviewModel)
        self.db = db

    async def create_interview(
        self,
        candidate_id: str,
        resume_id: str,
        interview_type: str,
        difficulty: str,
        max_questions: int,
        session_id: Optional[str] = None,
        meeting_token: Optional[str] = None,
        agent_id: Optional[str] = None,
        job_description: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a new interview with initial state
        
        Returns:
            Interview ID as string, or None on failure
        """
        interview_data = {
            "candidate_id": ObjectId(candidate_id),
            "resume_id": ObjectId(resume_id),
            "job_description": job_description,
            "session_id": session_id,
            "meeting_token": meeting_token,
            "agent_id": agent_id,
            "interview_type": interview_type,
            "difficulty": difficulty,
            "max_questions": max_questions,
            "questions": [],
            "conversation": [],
            "current_question_index": 0,
            "status": "created",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        return await self.create(interview_data)

    async def get_interview(self, interview_id: str) -> Optional[InterviewModel]:
        """
        Get interview by ID and convert to model
        
        Args:
            interview_id: Interview ID as string
            
        Returns:
            InterviewModel instance or None
        """
        doc = await self.find_by_id(interview_id)
        if not doc:
            return None
        
        try:
            return InterviewModel(**doc)
        except Exception as e:
            logger.error(f"Error converting interview to model: {e}")
            return None

    async def update_status(
        self, 
        interview_id: str, 
        status: str,
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Optional[InterviewModel]:
        """
        Update interview status with optional additional fields
        
        Args:
            interview_id: Interview ID
            status: New status (created, in_progress, completed, etc.)
            additional_fields: Extra fields to update (e.g., start_time, end_time)
            
        Returns:
            Updated InterviewModel or None
        """
        update_data = {"status": status}
        
        if additional_fields:
            update_data.update(additional_fields)
        
        result = await self.update(
            interview_id,
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            return InterviewModel(**result)
        return None

    async def start_interview(self, interview_id: str) -> Optional[InterviewModel]:
        """
        Mark interview as started
        
        Args:
            interview_id: Interview ID
            
        Returns:
            Updated InterviewModel or None
        """
        return await self.update_status(
            interview_id,
            "in_progress",
            {"start_time": datetime.utcnow()}
        )

    async def end_interview(
        self, 
        interview_id: str,
        evaluation: Optional[Evaluation] = None
    ) -> Optional[InterviewModel]:
        """
        Mark interview as completed with optional evaluation
        
        Args:
            interview_id: Interview ID
            evaluation: Evaluation model instance
            
        Returns:
            Updated InterviewModel or None
        """
        end_time = datetime.utcnow()
        
        # Get interview to calculate duration
        interview = await self.find_by_id(interview_id)
        if not interview:
            return None
        
        duration_minutes = 0
        if interview.get("start_time"):
            duration = end_time - interview["start_time"]
            duration_minutes = int(duration.total_seconds() / 60)
        
        update_data = {
            "status": "completed",
            "end_time": end_time,
            "duration_minutes": duration_minutes,
        }
        
        if evaluation:
            update_data["evaluation"] = evaluation.model_dump()
        
        result = await self.update(
            interview_id,
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            return InterviewModel(**result)
        return None

    async def add_question(
        self, 
        interview_id: str, 
        question: Question
    ) -> bool:
        """
        Add a question to the interview
        
        Args:
            interview_id: Interview ID
            question: Question model instance
            
        Returns:
            True if successful, False otherwise
        """
        result = await self.update(
            interview_id,
            {"$push": {"questions": question.model_dump()}}
        )
        return result is not None

    async def get_questions(self, interview_id: str) -> List[Question]:
        """
        Get all questions for an interview
        
        Args:
            interview_id: Interview ID
            
        Returns:
            List of Question models
        """
        interview = await self.find_by_id(interview_id)
        if not interview:
            return []
        
        questions_data = interview.get("questions", [])
        
        try:
            return [Question(**q) for q in questions_data]
        except Exception as e:
            logger.error(f"Error converting questions to models: {e}")
            return []

    async def get_question_count(self, interview_id: str) -> int:
        """
        Get the number of questions in an interview
        
        Args:
            interview_id: Interview ID
            
        Returns:
            Number of questions
        """
        interview = await self.find_by_id(interview_id)
        if not interview:
            return 0
        
        return len(interview.get("questions", []))

    async def update_meeting_info(
        self,
        interview_id: str,
        session_id: Optional[str] = None,
        meeting_token: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> bool:
        """
        Update VideoSDK meeting information
        
        Args:
            interview_id: Interview ID
            session_id: VideoSDK session ID
            meeting_token: Meeting access token
            agent_id: AI agent ID
            
        Returns:
            True if successful
        """
        update_data = {}
        
        if session_id is not None:
            update_data["session_id"] = session_id
        if meeting_token is not None:
            update_data["meeting_token"] = meeting_token
        if agent_id is not None:
            update_data["agent_id"] = agent_id
        
        if not update_data:
            return False
        
        result = await self.update(interview_id, {"$set": update_data})
        return result is not None

    async def get_interviews_by_candidate(
        self, 
        candidate_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[InterviewModel]:
        """
        Get all interviews for a candidate
        
        Args:
            candidate_id: Candidate ID
            status: Optional status filter
            limit: Maximum number of results
            
        Returns:
            List of InterviewModel instances
        """
        filter_dict = {"candidate_id": ObjectId(candidate_id)}
        
        if status:
            filter_dict["status"] = status
        
        docs = await self.find_many(
            filter_dict,
            limit=limit,
            sort=[("created_at", -1)]
        )
        
        try:
            return [InterviewModel(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error converting interviews to models: {e}")
            return []

    async def get_active_interviews(self, limit: int = 100) -> List[InterviewModel]:
        """
        Get all active (in_progress) interviews
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of InterviewModel instances
        """
        docs = await self.find_many(
            {"status": "in_progress"},
            limit=limit,
            sort=[("start_time", -1)]
        )
        
        try:
            return [InterviewModel(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error converting interviews to models: {e}")
            return []