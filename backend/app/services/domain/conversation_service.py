"""
Conversation Service
Simulates interview conversations for testing/fallback
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.models.interview import Question
from app.services.integration.groq_service import GroqService
from app.services.domain.response_service import ResponseService

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Service for simulating interview conversations
    Used for testing and fallback when agent unavailable
    """

    def __init__(
        self,
        groq_service: Optional[GroqService] = None,
        response_service: Optional[ResponseService] = None,
    ):
        """
        Initialize conversation service
        
        Args:
            groq_service: LLM service for answer generation
            response_service: Response service for acknowledgments
        """
        self.groq = groq_service or GroqService()
        self.response = response_service or ResponseService()

    async def simulate_full_conversation(
        self,
        questions: List[Question],
    ) -> List[Dict[str, Any]]:
        """
        Simulate complete interview conversation
        
        Args:
            questions: List of questions to ask
            
        Returns:
            List of conversation message dicts
        """
        if not questions:
            logger.warning("No questions provided for simulation")
            return []

        logger.info(f"Simulating conversation with {len(questions)} questions")

        conversation = []

        # Opening greeting
        conversation.append({
            "speaker": "ai",
            "text": self.response.get_opening_greeting(),
            "timestamp": datetime.utcnow(),
        })

        # Question-answer pairs
        for i, question in enumerate(questions, 1):
            # Ask question
            conversation.append({
                "speaker": "ai",
                "text": question.question_text,
                "timestamp": datetime.utcnow(),
            })

            # Generate candidate answer
            answer = await self._generate_candidate_answer(
                question=question.question_text,
                category=question.category,
            )

            conversation.append({
                "speaker": "candidate",
                "text": answer,
                "timestamp": datetime.utcnow(),
            })

            # Add acknowledgment (except after last question)
            if i < len(questions):
                conversation.append({
                    "speaker": "ai",
                    "text": self.response.get_acknowledgment(),
                    "timestamp": datetime.utcnow(),
                })

        # Closing statement
        conversation.append({
            "speaker": "ai",
            "text": self.response.get_closing_statement(),
            "timestamp": datetime.utcnow(),
        })

        logger.info(f"✅ Simulated {len(conversation)} messages")
        return conversation

    async def simulate_conversation_with_pauses(
        self,
        questions: List[Question],
        pause_after_each: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Simulate conversation with natural pauses
        
        Args:
            questions: List of questions to ask
            pause_after_each: Number of Q&A pairs before pause
            
        Returns:
            List of conversation message dicts
        """
        conversation = []

        # Opening
        conversation.append({
            "speaker": "ai",
            "text": self.response.get_opening_greeting(),
            "timestamp": datetime.utcnow(),
        })

        for i, question in enumerate(questions, 1):
            # Ask question
            conversation.append({
                "speaker": "ai",
                "text": question.question_text,
                "timestamp": datetime.utcnow(),
            })

            # Candidate answer
            answer = await self._generate_candidate_answer(
                question=question.question_text,
                category=question.category,
            )

            conversation.append({
                "speaker": "candidate",
                "text": answer,
                "timestamp": datetime.utcnow(),
            })

            # Add acknowledgment
            conversation.append({
                "speaker": "ai",
                "text": self.response.get_acknowledgment(),
                "timestamp": datetime.utcnow(),
            })

            # Add transition message at intervals
            if i % pause_after_each == 0 and i < len(questions):
                transition = self.response.generate_transition_message(i, len(questions))
                conversation.append({
                    "speaker": "ai",
                    "text": transition,
                    "timestamp": datetime.utcnow(),
                })

        # Closing
        conversation.append({
            "speaker": "ai",
            "text": self.response.get_closing_statement(),
            "timestamp": datetime.utcnow(),
        })

        return conversation

    async def _generate_candidate_answer(
        self,
        question: str,
        category: str,
    ) -> str:
        """
        Generate simulated candidate answer
        
        Args:
            question: Question text
            category: Question category
            
        Returns:
            Generated answer text
        """
        if self.groq.is_available():
            answer = await self.groq.generate_interview_answer(
                question=question,
                category=category,
            )
            if answer:
                return answer

        # Fallback answers
        return self._get_fallback_answer(category)

    def _get_fallback_answer(self, category: str) -> str:
        """
        Get fallback answer when LLM unavailable
        
        Args:
            category: Question category
            
        Returns:
            Fallback answer string
        """
        fallbacks = {
            "technical": (
                "Based on my experience, I would analyze the requirements carefully, "
                "break down the problem into manageable components, and implement a solution "
                "following best practices and design patterns."
            ),
            "behavioral": (
                "In my previous role, I encountered a similar situation. I approached it by "
                "communicating clearly with stakeholders, breaking down the challenge into steps, "
                "and working collaboratively with my team to achieve the best outcome."
            ),
            "hr": (
                "I'm very interested in this opportunity because it aligns well with my skills "
                "and career goals. I believe my experience and passion for the field make me "
                "a strong fit for this role."
            ),
        }

        return fallbacks.get(
            category,
            "I would approach this systematically, drawing on my experience and skills "
            "to deliver an effective solution."
        )

    def create_minimal_conversation(self, num_exchanges: int = 1) -> List[Dict[str, Any]]:
        """
        Create minimal conversation for testing
        
        Args:
            num_exchanges: Number of Q&A exchanges
            
        Returns:
            List of conversation messages
        """
        conversation = []

        # Greeting
        conversation.append({
            "speaker": "ai",
            "text": "Hello! Let's begin the interview.",
            "timestamp": datetime.utcnow(),
        })

        # Simple exchanges
        for i in range(num_exchanges):
            conversation.extend([
                {
                    "speaker": "ai",
                    "text": f"Question {i+1}: Tell me about your experience.",
                    "timestamp": datetime.utcnow(),
                },
                {
                    "speaker": "candidate",
                    "text": "I have relevant experience in this field.",
                    "timestamp": datetime.utcnow(),
                },
            ])

        # Closing
        conversation.append({
            "speaker": "ai",
            "text": "Thank you for your time.",
            "timestamp": datetime.utcnow(),
        })

        return conversation

    def validate_conversation(self, conversation: List[Dict[str, Any]]) -> bool:
        """
        Validate conversation structure
        
        Args:
            conversation: List of conversation messages
            
        Returns:
            True if valid, False otherwise
        """
        if not conversation:
            logger.warning("Empty conversation")
            return False

        # Check for required fields
        for msg in conversation:
            if "speaker" not in msg or "text" not in msg:
                logger.error("Missing required fields in conversation message")
                return False

            if msg["speaker"] not in ["ai", "candidate"]:
                logger.error(f"Invalid speaker: {msg['speaker']}")
                return False

        # Check for at least one candidate message
        candidate_msgs = [m for m in conversation if m["speaker"] == "candidate"]
        if not candidate_msgs:
            logger.warning("No candidate messages in conversation")
            return False

        return True