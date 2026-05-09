"""
Question Generator Service (Refactored)
Thin facade that delegates to specialized services

This service is now a lightweight coordinator that uses:
- GroqService for LLM calls
- QuestionContextBuilder for context creation
- DeduplicationService for filtering duplicates
- TemplateQuestionService for fallbacks
"""
import logging
from typing import List, Optional

from app.models.interview import Question
from app.models.resume import ParsedData
from app.services.integration.groq_service import GroqService
from app.services.domain.context_builder import QuestionContextBuilder
from app.services.domain.deduplication_service import DeduplicationService
from app.services.domain.template_question_service import TemplateQuestionService

logger = logging.getLogger(__name__)


class QuestionGeneratorService:
    """
    Refactored Question Generator - Now a thin facade
    
    Delegates to:
    - GroqService: LLM API calls
    - QuestionContextBuilder: Context building
    - DeduplicationService: Duplicate filtering
    - TemplateQuestionService: Fallback questions
    
    Responsibilities (reduced from 7 to 1):
    - Coordinate question generation flow ONLY
    """

    def __init__(
        self,
        groq_service: Optional[GroqService] = None,
        context_builder: Optional[QuestionContextBuilder] = None,
        deduplication_service: Optional[DeduplicationService] = None,
        template_service: Optional[TemplateQuestionService] = None,
    ):
        """
        Initialize with dependency injection
        
        Args:
            groq_service: LLM service (optional, creates default)
            context_builder: Context builder (optional, creates default)
            deduplication_service: Deduplication service (optional, creates default)
            template_service: Template service (optional, creates default)
        """
        self.groq = groq_service or GroqService()
        self.context_builder = context_builder or QuestionContextBuilder()
        self.dedupe = deduplication_service or DeduplicationService()
        self.templates = template_service or TemplateQuestionService()

        if self.groq.is_available():
            logger.info("✓ Question Generator initialized (Groq AI)")
        else:
            logger.warning("⚠️ Groq unavailable — using template questions")

    async def generate_question(
        self,
        parsed_resume: ParsedData,
        interview_type: str,
        difficulty: str,
        job_description: str = "",
        asked_questions: Optional[List[str]] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> Optional[Question]:
        """
        Generate exactly ONE interview question
        
        Args:
            parsed_resume: Parsed resume data
            interview_type: Interview type
            difficulty: Difficulty level
            job_description: Job description text
            asked_questions: Previously asked questions
            conversation_history: Conversation history
            
        Returns:
            Single Question or None
        """
        logger.info("🧠 Generating single interview question")

        questions = await self.generate_questions(
            parsed_resume=parsed_resume,
            interview_type=interview_type,
            difficulty=difficulty,
            max_questions=1,
            job_description=job_description,
            asked_questions=asked_questions or [],
            conversation_history=conversation_history or [],
        )

        if not questions:
            logger.warning("⚠️ No question generated")
            return None

        return questions[0]

    async def generate_questions(
        self,
        parsed_resume: ParsedData,
        interview_type: str,
        difficulty: str,
        max_questions: int,
        job_description: str = "",
        asked_questions: Optional[List[str]] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> List[Question]:
        """
        Generate multiple interview questions with deduplication
        
        Args:
            parsed_resume: Parsed resume data
            interview_type: Interview type (technical, behavioral, hr, mixed)
            difficulty: Difficulty level (easy, medium, hard)
            max_questions: Maximum questions to generate
            job_description: Job description text
            asked_questions: Previously asked questions
            conversation_history: Conversation history
            
        Returns:
            List of unique Question objects
        """
        asked_questions = asked_questions or []
        conversation_history = conversation_history or []

        logger.info(
            f"🧠 Generating {max_questions} questions | "
            f"type={interview_type} difficulty={difficulty}"
        )

        # Try AI generation first
        if self.groq.is_available():
            try:
                questions = await self._generate_with_ai(
                    parsed_resume=parsed_resume,
                    interview_type=interview_type,
                    difficulty=difficulty,
                    max_questions=max_questions,
                    job_description=job_description,
                    asked_questions=asked_questions,
                    conversation_history=conversation_history,
                )

                # Filter duplicates
                unique_questions = self.dedupe.filter_duplicate_questions(
                    questions=questions,
                    asked_questions=asked_questions,
                    conversation_history=conversation_history,
                )

                # If we got enough unique questions, return them
                if len(unique_questions) >= max_questions:
                    return unique_questions[:max_questions]

                # Not enough? Try generating more
                if len(unique_questions) < max_questions:
                    logger.info(
                        f"Only got {len(unique_questions)}/{max_questions} unique questions, "
                        f"generating more..."
                    )
                    
                    additional = await self._generate_with_ai(
                        parsed_resume=parsed_resume,
                        interview_type=interview_type,
                        difficulty=difficulty,
                        max_questions=max_questions - len(unique_questions),
                        job_description=job_description,
                        asked_questions=asked_questions + [q.question_text for q in unique_questions],
                        conversation_history=conversation_history,
                    )

                    additional_unique = self.dedupe.filter_duplicate_questions(
                        questions=additional,
                        asked_questions=asked_questions + [q.question_text for q in unique_questions],
                        conversation_history=conversation_history,
                    )

                    unique_questions.extend(additional_unique)

                return unique_questions[:max_questions]

            except Exception as e:
                logger.error(f"❌ AI generation failed: {e}, falling back to templates")

        # Fallback to template questions
        logger.info("📝 Using template questions (AI unavailable)")
        template_questions = self.templates.get_questions(
            interview_type=interview_type,
            max_questions=max_questions * 2,  # Get extras for deduplication
            difficulty=difficulty,
        )

        # Filter template duplicates too
        unique_templates = self.dedupe.filter_duplicate_questions(
            questions=template_questions,
            asked_questions=asked_questions,
            conversation_history=conversation_history,
        )

        return unique_templates[:max_questions]
    
    def _get_difficulty_constraints(self, difficulty: str, resume_context: str) -> str:
        """
        Inject strict cognitive constraints based on difficulty.
        This controls the depth and type of questions.
    """
        if difficulty == "easy":
            return f"""
STRICT EASY MODE ACTIVATED:

You MUST only ask beginner-level, fundamental, 1-to-1 concept questions.

Allowed topics ONLY:
- Programming fundamentals
- Core language concepts (syntax, OOP basics, data types)
- Simple definitions
- Basic usage questions

FORBIDDEN in EASY:
- Framework internals (FastAPI auth, middleware, dependency injection)
- System design
- Architecture
- Distributed systems
- Caching strategies
- Scalability
- Security mechanisms
- Optimization
- Performance tuning

If resume mentions advanced topics, IGNORE them for EASY.

Focus only on fundamentals like:
- What is inheritance?
- Difference between list and dictionary
- What is a function?
- What is an API?
- What is OOP?

This is a HARD CONSTRAINT.
"""

        if difficulty == "medium":
            return """
MEDIUM MODE:

Ask application-level questions.
Cover:
- How things work
- When to use X vs Y
- Practical usage
- Framework usage
Avoid large system design.
"""

        return """
HARD MODE:

Ask system design, architecture, scalability, optimization, and tradeoff questions.
Cover:
- Design decisions
- Architecture
- Performance
- Security
- Scaling
"""


    async def _generate_with_ai(
        self,
        parsed_resume: ParsedData,
        interview_type: str,
        difficulty: str,
        max_questions: int,
        job_description: str,
        asked_questions: List[str],
        conversation_history: List[dict],
    ) -> List[Question]:
        """
        Generate questions using AI (delegates to GroqService)
        
        Args:
            All parameters needed for generation
            
        Returns:
            List of generated questions (may contain duplicates)
        """
        # Build context using QuestionContextBuilder
       
        resume_context = self.context_builder.build_resume_context(parsed_resume)
        job_context = self.context_builder.build_job_description_context(job_description)
        conv_context = self.context_builder.build_conversation_context(conversation_history)

        # Build asked questions summary
        asked_summary = "; ".join(asked_questions[-5:]) if asked_questions else "None"


        difficulty_constraints = self._get_difficulty_constraints(
        difficulty=difficulty,
        resume_context=resume_context,
        )

        # Construct comprehensive prompt
        prompt = self._build_generation_prompt(
    resume_context=resume_context,
    job_context=job_context,
    conversation_context=conv_context,
    interview_type=interview_type,
    difficulty=difficulty,
    max_questions=max_questions,
    asked_summary=asked_summary,
)
        
        prompt = difficulty_constraints + "\n\n" + prompt

        # System prompt for structured output
        system_prompt = f"""
You are an expert AI interviewer that generates professional interview questions based on the given **category** and **difficulty level**.

Your job is to ASK QUESTIONS ONLY (do not answer them).

========================
STRICT OUTPUT REQUIREMENTS
========================
- Always return valid JSON in this exact format:
{{
  "questions": [
    {{
      "question_text": "<the interview question>",
      "category": "technical|hr|mixed",
      "difficulty": "{difficulty}",
      "expected_topics": ["<list of related topics>"]
    }}
  ]
}}
- Output exactly ONE question per response.
- The "category" field MUST match the given category parameter.
- Never include explanatory text, reasoning, or any text outside of the JSON.

========================
CATEGORY RULES
========================
If category = "technical":
- Focus only on technology, programming, systems, or software concepts.
If category = "hr":
- Focus on soft skills, personality, work ethics, leadership, and culture-fit.
If category = "mixed":
- Combine both technical and HR question styles.

========================
DIFFICULTY RULES
========================
EASY:
- Ask simple, definition-based or factual questions.
- Focus on “What is”, “Define”, “Purpose of”, etc.
- Avoid scenarios, system design, and optimization.
- Example (technical): "What is polymorphism in Python?"
- Example (hr): "What motivates you at work?"

MEDIUM:
- Ask application-based or comparative questions.
- Focus on “How does”, “When would you use”, “Explain the difference between”.
- Avoid large-scale designs.
- Example (technical): "How does dependency injection work in FastAPI?"
- Example (hr): "Describe a time you had to resolve a team conflict."

HARD:
- Ask design, optimization, scalability, or trade-off questions.
- Include architectural, analytical, or strategic elements.
- Example (technical): "How would you design a scalable notification system?"
- Example (hr): "How would you lead a remote team through a critical deadline?"

========================
IMPORTANT CONSTRAINTS
========================
- Never exceed the difficulty level. Asking a harder question than assigned is a FAILURE.
- Always respect both the difficulty and category simultaneously.
- Keep questions professional, clear, and single-focused.
"""

        # Call Groq API
        logger.info("⚡ Calling Groq AI for question generation")

        response_data = await self.groq.generate_structured_response(
            system_prompt=system_prompt,
            user_prompt=prompt,
            expected_fields=["questions"],
            temperature=0.8,
            max_tokens=2000,
        )

        if not response_data or "questions" not in response_data:
            logger.error("❌ Invalid response from Groq")
            return []

        # Parse questions
        questions = []
        for q_data in response_data["questions"][:max_questions]:
            if q_data.get("question_text"):
                try:
                    question = Question(
                        question_text=q_data["question_text"],
                        category=q_data.get("category", interview_type),
                        difficulty=q_data.get("difficulty", difficulty),
                        expected_topics=q_data.get("expected_topics", []),
                    )
                    questions.append(question)
                except Exception as e:
                    logger.warning(f"Failed to parse question: {e}")

        logger.info(f"✅ Generated {len(questions)} questions from AI")
        return questions

    def _build_generation_prompt(
        self,
        resume_context: str,
        job_context: str,
        conversation_context: str,
        interview_type: str,
        difficulty: str,
        max_questions: int,
        asked_summary: str,
    ) -> str:
        """
        Build comprehensive prompt for question generation
        
        Args:
            All context components
            
        Returns:
            Complete prompt string
        """
        prompt_parts = [
            "Generate highly diverse, non-repetitive interview questions.",
            "",
            "=== GOALS ===",
            "1. Produce UNIQUE questions (avoid anything similar to previous questions)",
            "2. High-quality, job-relevant questions focused on JD + Resume",
            "3. Adapt to interview type:",
        ]

        # Add type-specific instructions
        if interview_type == "technical":
            prompt_parts.extend([
                "   - Ask DIRECT technical questions",
                "   - Cover: definitions, concepts, coding, frameworks, databases, system design",
                "   - Examples: 'What is X?', 'Explain Y', 'How does Z work?'",
            ])
        elif interview_type == "behavioral":
            prompt_parts.extend([
                "   - Ask scenario-based, experience questions",
                "   - Use STAR format prompts",
                "   - Examples: 'Tell me about a time when...', 'Describe a situation where...'",
            ])
        elif interview_type == "hr":
            prompt_parts.extend([
                "   - Ask motivation, expectations, culture-fit questions",
                "   - Examples: 'Why this role?', 'Career goals?', 'Salary expectations?'",
            ])
        else:  # mixed
            prompt_parts.append("   - Combine technical, behavioral, and HR questions")

        # Add contexts
        prompt_parts.extend([
            "",
            "=== CANDIDATE RESUME ===",
            resume_context,
            "",
        ])

        if job_context:
            prompt_parts.extend([
                "=== JOB DESCRIPTION ===",
                job_context,
                "",
            ])

        if conversation_context:
            prompt_parts.extend([
                "=== RECENT CONVERSATION ===",
                conversation_context,
                "",
            ])

        prompt_parts.extend([
            f"=== PREVIOUSLY ASKED ===",
            asked_summary,
            "",
            f"Generate exactly {max_questions} diverse questions.",
        ])

        return "\n".join(prompt_parts)

    def get_opening_question(self, interview_type: str) -> Question:
        """
        Get a good opening question
        
        Args:
            interview_type: Interview type
            
        Returns:
            Opening question
        """
        return self.templates.get_opening_question(interview_type)

    def get_closing_question(self, interview_type: str) -> Question:
        """
        Get a good closing question
        
        Args:
            interview_type: Interview type
            
        Returns:
            Closing question
        """
        return self.templates.get_closing_question(interview_type)

    def calculate_question_quality(self, questions: List[Question]) -> dict:
        """
        Calculate quality metrics for generated questions
        
        Args:
            questions: Questions to analyze
            
        Returns:
            Dict with quality metrics
        """
        diversity_score = self.dedupe.calculate_question_diversity(questions)
        pattern_analysis = self.dedupe.detect_question_patterns(questions)

        return {
            "total_questions": len(questions),
            "diversity_score": round(diversity_score, 2),
            "pattern_analysis": pattern_analysis,
            "quality_rating": "excellent" if diversity_score > 0.7 else "good" if diversity_score > 0.5 else "poor",
        }