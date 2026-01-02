"""
Conversation Repository
Handles all conversation/message operations for interviews
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
import logging

from app.models.interview import ConversationMessage
from app.services.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ConversationRepository(BaseRepository):
    """
    Repository for managing interview conversation messages
    Handles message CRUD operations efficiently
    """

    def __init__(self, db):
        """
        Initialize with database connection
        
        Args:
            db: MongoDB database instance
        """
        super().__init__(db.interviews, dict)
        self.db = db

    async def add_message(
        self,
        interview_id: str,
        speaker: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a single message to the conversation
        
        Args:
            interview_id: Interview ID
            speaker: "ai" or "candidate"
            text: Message content
            metadata: Optional additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        message_data = {
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.utcnow(),
        }
        
        if metadata:
            message_data.update(metadata)
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(interview_id)},
                {
                    "$push": {"conversation": message_data},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding message to interview {interview_id}: {e}")
            return False

    async def add_messages_batch(
        self,
        interview_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """
        Add multiple messages at once (more efficient for simulations)
        
        Args:
            interview_id: Interview ID
            messages: List of message dicts with 'speaker' and 'text'
            
        Returns:
            True if successful, False otherwise
        """
        # Ensure all messages have timestamps
        for msg in messages:
            if "timestamp" not in msg:
                msg["timestamp"] = datetime.utcnow()
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(interview_id)},
                {
                    "$push": {"conversation": {"$each": messages}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error adding messages batch to interview {interview_id}: {e}")
            return False

    async def get_conversation(
        self,
        interview_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """
        Get conversation messages for an interview
        
        Args:
            interview_id: Interview ID
            limit: Optional limit for recent messages
            
        Returns:
            List of ConversationMessage models
        """
        try:
            interview = await self.collection.find_one(
                {"_id": ObjectId(interview_id)},
                {"conversation": 1}
            )
            
            if not interview:
                return []
            
            messages = interview.get("conversation", [])
            
            # Apply limit if specified (get most recent)
            if limit and len(messages) > limit:
                messages = messages[-limit:]
            
            return [ConversationMessage(**msg) for msg in messages]
        except Exception as e:
            logger.error(f"Error fetching conversation for interview {interview_id}: {e}")
            return []

    async def get_conversation_raw(self, interview_id: str) -> List[Dict[str, Any]]:
        """
        Get raw conversation data (for backward compatibility)
        
        Args:
            interview_id: Interview ID
            
        Returns:
            List of message dicts
        """
        try:
            interview = await self.collection.find_one(
                {"_id": ObjectId(interview_id)},
                {"conversation": 1}
            )
            
            if not interview:
                return []
            
            return interview.get("conversation", [])
        except Exception as e:
            logger.error(f"Error fetching raw conversation for interview {interview_id}: {e}")
            return []

    async def get_message_count(
        self,
        interview_id: str,
        speaker: Optional[str] = None
    ) -> int:
        """
        Count messages in conversation
        
        Args:
            interview_id: Interview ID
            speaker: Optional filter by speaker ("ai" or "candidate")
            
        Returns:
            Number of messages
        """
        try:
            interview = await self.collection.find_one(
                {"_id": ObjectId(interview_id)},
                {"conversation": 1}
            )
            
            if not interview:
                return 0
            
            messages = interview.get("conversation", [])
            
            if speaker:
                messages = [m for m in messages if m.get("speaker") == speaker]
            
            return len(messages)
        except Exception as e:
            logger.error(f"Error counting messages for interview {interview_id}: {e}")
            return 0

    async def get_last_message(
        self,
        interview_id: str,
        speaker: Optional[str] = None
    ) -> Optional[ConversationMessage]:
        """
        Get the most recent message
        
        Args:
            interview_id: Interview ID
            speaker: Optional filter by speaker
            
        Returns:
            Last ConversationMessage or None
        """
        try:
            interview = await self.collection.find_one(
                {"_id": ObjectId(interview_id)},
                {"conversation": 1}
            )
            
            if not interview:
                return None
            
            messages = interview.get("conversation", [])
            
            if speaker:
                messages = [m for m in messages if m.get("speaker") == speaker]
            
            if not messages:
                return None
            
            return ConversationMessage(**messages[-1])
        except Exception as e:
            logger.error(f"Error fetching last message for interview {interview_id}: {e}")
            return None

    async def clear_conversation(self, interview_id: str) -> bool:
        """
        Clear all conversation messages (for testing/reset)
        
        Args:
            interview_id: Interview ID
            
        Returns:
            True if successful
        """
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(interview_id)},
                {
                    "$set": {
                        "conversation": [],
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error clearing conversation for interview {interview_id}: {e}")
            return False

    async def replace_conversation(
        self,
        interview_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """
        Replace entire conversation (useful for simulations)
        
        Args:
            interview_id: Interview ID
            messages: New conversation messages
            
        Returns:
            True if successful
        """
        # Ensure all messages have timestamps
        for msg in messages:
            if "timestamp" not in msg:
                msg["timestamp"] = datetime.utcnow()
        
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(interview_id)},
                {
                    "$set": {
                        "conversation": messages,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error replacing conversation for interview {interview_id}: {e}")
            return False

    async def get_conversation_summary(self, interview_id: str) -> Dict[str, Any]:
        """
        Get a summary of the conversation
        
        Args:
            interview_id: Interview ID
            
        Returns:
            Dict with summary statistics
        """
        try:
            interview = await self.collection.find_one(
                {"_id": ObjectId(interview_id)},
                {"conversation": 1}
            )
            
            if not interview:
                return {
                    "total_messages": 0,
                    "ai_messages": 0,
                    "candidate_messages": 0,
                    "has_conversation": False
                }
            
            messages = interview.get("conversation", [])
            ai_count = sum(1 for m in messages if m.get("speaker") == "ai")
            candidate_count = sum(1 for m in messages if m.get("speaker") == "candidate")
            
            return {
                "total_messages": len(messages),
                "ai_messages": ai_count,
                "candidate_messages": candidate_count,
                "has_conversation": len(messages) > 0
            }
        except Exception as e:
            logger.error(f"Error getting conversation summary for interview {interview_id}: {e}")
            return {
                "total_messages": 0,
                "ai_messages": 0,
                "candidate_messages": 0,
                "has_conversation": False
            }