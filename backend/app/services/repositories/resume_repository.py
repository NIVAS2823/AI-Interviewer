"""
Resume Repository
Handles all database operations related to resumes
"""
from typing import Optional, List
from bson import ObjectId
import logging

from app.models.resume import ResumeModel, ParsedData
from app.services.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ResumeRepository(BaseRepository[ResumeModel]):
    """
    Repository for resume-related database operations
    """

    def __init__(self, db):
        """
        Initialize with database connection
        
        Args:
            db: MongoDB database instance
        """
        super().__init__(db.resumes, ResumeModel)
        self.db = db

    async def get_resume(self, resume_id: str) -> Optional[ResumeModel]:
        """
        Get resume by ID and convert to model
        
        Args:
            resume_id: Resume ID as string
            
        Returns:
            ResumeModel instance or None
        """
        doc = await self.find_by_id(resume_id)
        if not doc:
            logger.warning(f"Resume {resume_id} not found")
            return None
        
        try:
            return ResumeModel(**doc)
        except Exception as e:
            logger.error(f"Error converting resume to model: {e}")
            return None

    async def get_parsed_data(self, resume_id: str) -> Optional[ParsedData]:
        """
        Get parsed resume data
        
        Args:
            resume_id: Resume ID as string
            
        Returns:
            ParsedData instance or None
        """
        doc = await self.find_by_id(resume_id)
        if not doc:
            logger.warning(f"Resume {resume_id} not found")
            return None
        
        parsed_data = doc.get("parsed_data")
        if not parsed_data:
            logger.warning(f"Resume {resume_id} has no parsed_data")
            return None
        
        try:
            return ParsedData(**parsed_data)
        except Exception as e:
            logger.error(f"Error converting parsed_data to model: {e}")
            return None

    async def update_parsed_data(
        self, 
        resume_id: str, 
        parsed_data: ParsedData
    ) -> bool:
        """
        Update parsed resume data
        
        Args:
            resume_id: Resume ID
            parsed_data: ParsedData model instance
            
        Returns:
            True if successful
        """
        result = await self.update(
            resume_id,
            {"$set": {"parsed_data": parsed_data.model_dump()}}
        )
        return result is not None

    async def get_resumes_by_user(
        self, 
        user_id: str, 
        limit: int = 50
    ) -> List[ResumeModel]:
        """
        Get all resumes for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            
        Returns:
            List of ResumeModel instances
        """
        docs = await self.find_many(
            {"user_id": ObjectId(user_id)},
            limit=limit,
            sort=[("created_at", -1)]
        )
        
        try:
            return [ResumeModel(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error converting resumes to models: {e}")
            return []

    async def resume_exists(self, resume_id: str) -> bool:
        """
        Check if resume exists and has parsed data
        
        Args:
            resume_id: Resume ID
            
        Returns:
            True if exists with parsed_data
        """
        try:
            doc = await self.find_by_id(resume_id)
            return doc is not None and doc.get("parsed_data") is not None
        except Exception as e:
            logger.error(f"Error checking resume existence: {e}")
            return False

    async def get_resume_metadata(self, resume_id: str) -> Optional[dict]:
        """
        Get basic resume metadata without full parsed data
        
        Args:
            resume_id: Resume ID
            
        Returns:
            Dict with metadata or None
        """
        try:
            doc = await self.collection.find_one(
                {"_id": ObjectId(resume_id)},
                {
                    "file_name": 1,
                    "user_id": 1,
                    "created_at": 1,
                    "parsed_data.name": 1,
                    "parsed_data.email": 1,
                    "parsed_data.phone": 1
                }
            )
            return doc
        except Exception as e:
            logger.error(f"Error fetching resume metadata: {e}")
            return None