"""
Voice Message Generator
Generates text content for voice interview messages
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class VoiceMessageGenerator:
    """
    Service for generating voice interview message texts
    
    Responsibilities:
    - Generate greeting messages
    - Generate closing messages
    - Generate transition messages
    
    Does NOT:
    - Generate audio (that's TTS service's job)
    - Handle caching (that's cache service's job)
    """

    def __init__(self, interviewer_name: str = "Sarah"):
        """
        Initialize message generator
        
        Args:
            interviewer_name: Name of AI interviewer
        """
        self.interviewer_name = interviewer_name

    def create_greeting_text(
        self,
        candidate_name: str,
        interview_type: str,
        num_questions: int,
    ) -> str:
        """
        Generate greeting message text
        
        Args:
            candidate_name: Candidate's name
            interview_type: Type of interview
            num_questions: Number of questions
            
        Returns:
            Greeting text
        """
        greeting = (
            f"Hello {candidate_name}! I'm {self.interviewer_name}, your AI interviewer. "
            f"This will be a {interview_type} interview with {num_questions} questions. "
            f"Please answer clearly and take your time. Let's begin!"
        )

        logger.debug(f"📝 Generated greeting for {candidate_name}")
        
        return greeting

    def create_greeting_text_short(self, candidate_name: str) -> str:
        """
        Generate short greeting (for follow-up sessions)
        
        Args:
            candidate_name: Candidate's name
            
        Returns:
            Short greeting text
        """
        return f"Hello {candidate_name}! I'm {self.interviewer_name}. Let's get started!"

    def create_closing_text(
        self,
        candidate_name: str,
        custom_message: Optional[str] = None,
    ) -> str:
        """
        Generate closing message text
        
        Args:
            candidate_name: Candidate's name
            custom_message: Optional custom closing message
            
        Returns:
            Closing text
        """
        if custom_message:
            return custom_message

        closing = (
            f"Thank you, {candidate_name}, for your time. "
            f"We'll now evaluate your answers. Good luck!"
        )

        logger.debug(f"📝 Generated closing for {candidate_name}")
        
        return closing

    def create_closing_text_with_summary(
        self,
        candidate_name: str,
        num_questions_answered: int,
    ) -> str:
        """
        Generate closing with summary
        
        Args:
            candidate_name: Candidate's name
            num_questions_answered: Number of questions answered
            
        Returns:
            Closing text with summary
        """
        return (
            f"Thank you, {candidate_name}! You've answered {num_questions_answered} questions. "
            f"We'll now evaluate your responses. Best of luck with your application!"
        )

    def create_transition_text(
        self,
        context: str = "general",
    ) -> str:
        """
        Generate transition message
        
        Args:
            context: Transition context
            
        Returns:
            Transition text
        """
        transitions = {
            "general": "Let's move on to the next question.",
            "technical": "Now, let me ask you about your technical experience.",
            "behavioral": "Let's discuss your work style and experiences.",
            "final": "This will be our final question.",
        }

        return transitions.get(context, transitions["general"])

    def create_clarification_request(self, topic: Optional[str] = None) -> str:
        """
        Generate clarification request
        
        Args:
            topic: Specific topic to clarify
            
        Returns:
            Clarification request text
        """
        if topic:
            return f"Could you elaborate more on your experience with {topic}?"
        
        return "Could you provide more details about that?"

    def create_pause_message(self, duration_seconds: int = 5) -> str:
        """
        Generate pause message
        
        Args:
            duration_seconds: Pause duration
            
        Returns:
            Pause message text
        """
        return f"Please take a moment to think. I'll wait {duration_seconds} seconds."

    def create_technical_difficulty_message(self) -> str:
        """Generate technical difficulty message"""
        return (
            "I'm having some technical difficulties. "
            "Please bear with me for a moment."
        )

    def create_retry_message(self) -> str:
        """Generate retry message"""
        return (
            "I didn't quite catch that. "
            "Could you please repeat your answer?"
        )

    def create_time_warning_message(self, remaining_minutes: int) -> str:
        """
        Generate time warning
        
        Args:
            remaining_minutes: Minutes remaining
            
        Returns:
            Time warning text
        """
        return f"Just a reminder, we have about {remaining_minutes} minutes remaining."

    def create_welcome_back_message(self, candidate_name: str) -> str:
        """
        Generate welcome back message (for resumed interviews)
        
        Args:
            candidate_name: Candidate's name
            
        Returns:
            Welcome back text
        """
        return f"Welcome back, {candidate_name}! Let's continue where we left off."

    def create_progress_update(
        self,
        current_question: int,
        total_questions: int,
    ) -> str:
        """
        Generate progress update
        
        Args:
            current_question: Current question number
            total_questions: Total questions
            
        Returns:
            Progress update text
        """
        remaining = total_questions - current_question
        
        if remaining == 1:
            return "We're almost done. One more question."
        elif remaining == 2:
            return "Just two more questions to go."
        else:
            return f"We have {remaining} questions remaining."

    def create_encouragement_message(self) -> str:
        """Generate encouragement message"""
        encouragements = [
            "You're doing great!",
            "Great answer! Let's continue.",
            "Excellent! Moving on.",
            "That's a thoughtful response.",
        ]

        import random
        return random.choice(encouragements)

    def personalize_message(
        self,
        template: str,
        candidate_name: str,
        **kwargs
    ) -> str:
        """
        Personalize message template
        
        Args:
            template: Message template with placeholders
            candidate_name: Candidate's name
            **kwargs: Additional template variables
            
        Returns:
            Personalized message
        """
        variables = {
            "candidate_name": candidate_name,
            "interviewer_name": self.interviewer_name,
            **kwargs
        }

        try:
            return template.format(**variables)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            return template

    def validate_message_length(self, text: str, max_length: int = 500) -> bool:
        """
        Validate message length
        
        Args:
            text: Message text
            max_length: Maximum allowed length
            
        Returns:
            True if valid
        """
        if len(text) > max_length:
            logger.warning(f"⚠️ Message too long: {len(text)} chars (max: {max_length})")
            return False
        
        return True