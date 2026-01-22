"""
Response Service
Generates AI interviewer responses and acknowledgments
"""
from typing import Optional, List
import random
import logging

from app.models.interview import Question

logger = logging.getLogger(__name__)


class ResponseService:
    """
    Service for generating AI interviewer responses
    Handles acknowledgments, transitions, and closing statements
    """

    # Predefined acknowledgments (can be cached)
    ACKNOWLEDGMENTS = [
        "I appreciate your detailed answer.",
        "I see, thank you for explaining.",
        "That's a good point.",
        "I understand, thank you.",
    ]

    OPENING_GREETINGS = [
        "Hello! I'm your AI interviewer. Let's begin.",
        "Hi there! Thanks for joining. Let's get started.",
        "Welcome! I'm excited to learn more about you. Shall we begin?",
        "Good to meet you! Let's start the interview.",
    ]

    CLOSING_STATEMENTS = [
        "Thank you for your detailed answers throughout this interview. That concludes our conversation today.",
        "I appreciate your time and thoughtful responses. This wraps up our interview.",
        "Thanks for sharing your insights. We've covered all the questions.",
        "That concludes our interview. Thank you for your participation.",
    ]

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize response service
        
        Args:
            seed: Random seed for reproducibility (optional)
        """
        if seed is not None:
            random.seed(seed)

    def get_acknowledgment(self) -> str:
        """
        Get random acknowledgment message
        
        Returns:
            Acknowledgment string
        """
        return random.choice(self.ACKNOWLEDGMENTS)

    def get_opening_greeting(self) -> str:
        """
        Get random opening greeting
        
        Returns:
            Greeting string
        """
        return random.choice(self.OPENING_GREETINGS)

    def get_closing_statement(self) -> str:
        """
        Get random closing statement
        
        Returns:
            Closing string
        """
        return random.choice(self.CLOSING_STATEMENTS)

    def generate_question_response(
        self,
        next_question: Question,
        include_acknowledgment: bool = True,
    ) -> str:
        """
        Generate response with acknowledgment and next question
        
        Args:
            next_question: Next Question to ask
            include_acknowledgment: Whether to include acknowledgment
            
        Returns:
            Formatted response string
        """
        if include_acknowledgment:
            ack = self.get_acknowledgment()
            return f"{ack} {next_question.question_text}"
        else:
            return next_question.question_text

    def generate_completion_message(self, include_instruction: bool = True) -> str:
        """
        Generate interview completion message
        
        Args:
            include_instruction: Include UI instruction about clicking End Interview
            
        Returns:
            Completion message string
        """
        closing = self.get_closing_statement()

        if include_instruction:
            return f"{closing} Click 'End Interview' to see your evaluation results."
        else:
            return closing

    def generate_transition_message(
        self,
        current_question_num: int,
        total_questions: int,
    ) -> str:
        """
        Generate transition message between questions
        
        Args:
            current_question_num: Current question number
            total_questions: Total questions
            
        Returns:
            Transition message
        """
        remaining = total_questions - current_question_num

        if remaining == 1:
            return "We're almost done. One more question."
        elif remaining == 2:
            return "Just a couple more questions."
        elif remaining <= 3:
            return f"Great! {remaining} questions remaining."
        else:
            return "Let's continue."

    def generate_thinking_message(self) -> str:
        """
        Generate message when AI is thinking/processing
        
        Returns:
            Thinking message string
        """
        messages = [
            "Let me think of the next question...",
            "One moment while I prepare the next question...",
            "Give me a second to formulate the next question...",
            "Processing your answer...",
        ]
        return random.choice(messages)

    def generate_error_recovery_message(self) -> str:
        """
        Generate message when error occurs but interview continues
        
        Returns:
            Error recovery message
        """
        messages = [
            "I apologize for the technical issue. Let's continue.",
            "Sorry about that. Let me try again.",
            "Technical hiccup. Let's move forward.",
        ]
        return random.choice(messages)

    def format_conversation_pair(
        self,
        question: str,
        acknowledgment: Optional[str] = None,
    ) -> List[str]:
        """
        Format a question-acknowledgment pair for conversation
        
        Args:
            question: Question text
            acknowledgment: Optional acknowledgment (random if None)
            
        Returns:
            List of [acknowledgment, question] or just [question]
        """
        if acknowledgment is None:
            acknowledgment = self.get_acknowledgment()

        return [acknowledgment, question]

    def should_include_acknowledgment(
        self,
        question_number: int,
        total_questions: int,
    ) -> bool:
        """
        Determine if acknowledgment should be included
        
        Args:
            question_number: Current question number
            total_questions: Total questions
            
        Returns:
            True if acknowledgment should be included
        """
        # Don't acknowledge first question (no previous answer)
        if question_number == 1:
            return False

        # Always acknowledge for all other questions
        return True