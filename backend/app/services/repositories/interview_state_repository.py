"""
Interview State Repository
Persists and retrieves interview state for stateful agent
"""
from typing import Optional
from bson import ObjectId
import logging

from app.services.orchestration.interview_state import InterviewState, InterviewStateManager

logger = logging.getLogger(__name__)


class InterviewStateRepository:
    """
    Repository for persisting interview state
    Stores state as embedded document in interview record
    """

    def __init__(self, db):
        """
        Initialize with database connection
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.state_manager = InterviewStateManager()

    async def save_state(self, state: InterviewState) -> bool:
        """
        Save interview state to database
        
        Args:
            state: InterviewState instance
            
        Returns:
            True if successful
        """
        try:
            state_dict = self.state_manager.to_dict(state)
            
            result = await self.db.interviews.update_one(
                {"_id": ObjectId(state.interview_id)},
                {
                    "$set": {
                        "agent_state": state_dict,
                        "updated_at": state_dict["memory"]["turn_count"],  # Use turn count as version
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.debug(f"Saved state for interview {state.interview_id}")
                return True
            else:
                logger.warning(f"State save returned 0 modified count for {state.interview_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to save interview state: {e}")
            return False

    async def load_state(self, interview_id: str) -> Optional[InterviewState]:
        """
        Load interview state from database
        
        Args:
            interview_id: Interview ID
            
        Returns:
            InterviewState instance or None
        """
        try:
            interview = await self.db.interviews.find_one(
                {"_id": ObjectId(interview_id)},
                {"agent_state": 1}
            )
            
            if not interview:
                logger.warning(f"Interview {interview_id} not found")
                return None
            
            state_dict = interview.get("agent_state")
            
            if not state_dict:
                logger.debug(f"No saved state found for interview {interview_id}")
                return None
            
            state = self.state_manager.from_dict(state_dict)
            logger.debug(f"Loaded state for interview {interview_id}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load interview state: {e}")
            return None

    async def state_exists(self, interview_id: str) -> bool:
        """
        Check if state exists for interview
        
        Args:
            interview_id: Interview ID
            
        Returns:
            True if state exists
        """
        try:
            count = await self.db.interviews.count_documents(
                {"_id": ObjectId(interview_id), "agent_state": {"$exists": True}},
                limit=1
            )
            return count > 0
        except Exception as e:
            logger.error(f"Error checking state existence: {e}")
            return False

    async def delete_state(self, interview_id: str) -> bool:
        """
        Delete interview state (cleanup)
        
        Args:
            interview_id: Interview ID
            
        Returns:
            True if successful
        """
        try:
            result = await self.db.interviews.update_one(
                {"_id": ObjectId(interview_id)},
                {"$unset": {"agent_state": ""}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to delete state: {e}")
            return False

    async def create_initial_state_from_interview(
        self,
        interview_id: str,
    ) -> Optional[InterviewState]:
        """
        Create initial state from existing interview record
        
        Args:
            interview_id: Interview ID
            
        Returns:
            New InterviewState instance or None
        """
        try:
            # Fetch interview and resume data
            interview = await self.db.interviews.find_one({"_id": ObjectId(interview_id)})
            
            if not interview:
                logger.error(f"Interview {interview_id} not found")
                return None
            
            resume = await self.db.resumes.find_one({"_id": interview["resume_id"]})
            
            if not resume or not resume.get("parsed_data"):
                logger.error(f"Resume data not found for interview {interview_id}")
                return None
            
            parsed_data = resume["parsed_data"]
            
            # Extract candidate info
            candidate_name = parsed_data.get("name")
            
            # Extract skills
            skills_obj = parsed_data.get("skills", {})
            candidate_skills = (
                skills_obj.get("keywords", []) +
                skills_obj.get("technical", []) +
                skills_obj.get("tools", [])
            )
            candidate_skills = list(dict.fromkeys(candidate_skills))[:15]  # Top 15 unique
            
            # Extract experience
            experiences = parsed_data.get("experience", [])
            candidate_experience = [
                {
                    "role": exp.get("role", ""),
                    "company": exp.get("company", ""),
                }
                for exp in experiences[:5]
            ]
            
            # Create state
            state = self.state_manager.create_initial_state(
                interview_id=interview_id,
                interview_type=interview["interview_type"],
                difficulty=interview["difficulty"],
                max_questions=interview["max_questions"],
                candidate_name=candidate_name,
                candidate_skills=candidate_skills,
                candidate_experience=candidate_experience,
                job_description=interview.get("job_description"),
            )
            
            logger.info(f"Created initial state for interview {interview_id}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to create initial state: {e}")
            return None