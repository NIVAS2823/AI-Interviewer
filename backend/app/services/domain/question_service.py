"""
Question Service
Domain service for question generation and management
Pure business logic with dependency injection
"""
from typing import Optional, List, Dict, Any
import logging

from app.models.interview import Question
from app.models.resume import ParsedData
from app.services.domain.context_builder import QuestionContextBuilder
from app.services.integration.groq_service import GroqService

logger = logging.getLogger(__name__)


class QuestionService:
    """
    Domain service for interview question generation
    Separates business logic from infrastructure concerns
    """

    def __init__(
        self,
        groq_service: Optional[GroqService] = None,
        context_builder: Optional[QuestionContextBuilder] = None,
    ):
        """
        Initialize question service with dependencies
        
        Args:
            groq_service: LLM service for question generation
            context_builder: Context builder for prompt construction
        """
        self.groq = groq_service or GroqService()
        self.context_builder = context_builder or QuestionContextBuilder()

    async def generate_question(
        self,
        parsed_resume: ParsedData,
        interview_type: str,
        difficulty: str,
        question_number: int,
        total_questions: int,
        conversation: Optional[List[Dict[str, Any]]] = None,
        job_description: Optional[str] = None,
    ) -> Optional[Question]:
        """
        Generate next interview question
        
        Args:
            parsed_resume: Parsed resume data
            interview_type: Type of interview
            difficulty: Difficulty level
            question_number: Current question number (1-indexed)
            total_questions: Total questions planned
            conversation: Previous conversation messages
            job_description: Optional job description
            
        Returns:
            Generated Question or None on failure
        """
        logger.info(f"Generating question #{question_number}/{total_questions}")

        # Build context
        context = self.context_builder.build_question_generation_context(
            parsed_resume=parsed_resume,
            interview_type=interview_type,
            difficulty=difficulty,
            question_number=question_number,
            total_questions=total_questions,
            conversation=conversation or [],
            job_description=job_description,
        )

        # Generate using LLM
        if self.groq.is_available():
            question_data = await self.groq.generate_question_json(
                context=context,
                interview_type=interview_type,
                difficulty=difficulty,
            )

            if question_data:
                try:
                    question = Question(
                        question_text=question_data["question_text"],
                        category=question_data["category"],
                        difficulty=question_data["difficulty"],
                        expected_topics=question_data.get("expected_topics", []),
                    )
                    logger.info(f"✅ Generated question: {question.question_text[:50]}...")
                    return question
                except Exception as e:
                    logger.error(f"Failed to create Question model: {e}")

        # Fallback question
        logger.warning("Using fallback question")
        return self._generate_fallback_question(
            parsed_resume=parsed_resume,
            interview_type=interview_type,
            difficulty=difficulty,
            question_number=question_number,
        )

    def _generate_fallback_question(
        self,
        parsed_resume: ParsedData,
        interview_type: str,
        difficulty: str,
        question_number: int,
    ) -> Question:
        """
        Generate fallback question when LLM unavailable
        
        Args:
            parsed_resume: Parsed resume data
            interview_type: Type of interview
            difficulty: Difficulty level
            question_number: Current question number
            
        Returns:
            Fallback Question instance
        """
        skills = self.context_builder.extract_top_skills(parsed_resume.skills)

        # Position-specific fallbacks
        if question_number == 1:
            question_text = (
                f"Can you tell me about your background and experience, "
                f"particularly related to {skills[0] if skills else 'your field'}?"
            )
        else:
            question_text = (
                f"Tell me more about your experience with "
                f"{skills[min(question_number-1, len(skills)-1)] if skills else 'the skills'} "
                f"mentioned in your resume."
            )

        return Question(
            question_text=question_text,
            category=interview_type,
            difficulty=difficulty,
            expected_topics=skills[:3] if skills else [],
        )

    async def generate_questions_batch(
        self,
        parsed_resume: ParsedData,
        interview_type: str,
        difficulty: str,
        num_questions: int,
        job_description: Optional[str] = None,
    ) -> List[Question]:
        """
        Generate multiple questions upfront (for optimization)
        
        Args:
            parsed_resume: Parsed resume data
            interview_type: Type of interview
            difficulty: Difficulty level
            num_questions: Number of questions to generate
            job_description: Optional job description
            
        Returns:
            List of generated Questions
        """
        logger.info(f"Generating batch of {num_questions} questions")

        questions = []
        conversation = []  # Start empty

        for i in range(1, num_questions + 1):
            question = await self.generate_question(
                parsed_resume=parsed_resume,
                interview_type=interview_type,
                difficulty=difficulty,
                question_number=i,
                total_questions=num_questions,
                conversation=conversation,
                job_description=job_description,
            )

            if question:
                questions.append(question)

                # Simulate adding question to conversation for context
                conversation.append({
                    "speaker": "ai",
                    "text": question.question_text,
                })

        logger.info(f"✅ Generated {len(questions)}/{num_questions} questions")
        return questions

    def validate_question(self, question: Question) -> bool:
        """
        Validate question meets quality standards
        
        Args:
            question: Question to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check minimum length
        if len(question.question_text) < 10:
            logger.warning("Question text too short")
            return False

        # Check for question mark (optional but recommended)
        if "?" not in question.question_text:
            logger.debug("Question missing question mark")

        # Check category is valid
        valid_categories = ["technical", "behavioral", "hr", "mixed"]
        if question.category not in valid_categories:
            logger.warning(f"Invalid category: {question.category}")
            return False

        # Check difficulty is valid
        valid_difficulties = ["easy", "medium", "hard"]
        if question.difficulty not in valid_difficulties:
            logger.warning(f"Invalid difficulty: {question.difficulty}")
            return False

        return True