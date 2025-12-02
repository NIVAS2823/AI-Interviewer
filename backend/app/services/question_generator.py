import json
import logging
from typing import List, Dict, Optional
from groq import Groq
from app.core.config import settings
from app.models.interview import Question
from app.models.resume import ParsedData

logger = logging.getLogger(__name__)


class QuestionGeneratorService:
    """Generate interview questions using FREE Groq AI"""

    def __init__(self):
        """Initialize Groq client"""
        self.client = None
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info("✓ Question Generator initialized (Groq AI - FREE)")
        else:
            logger.warning("⚠️ No GROQ_API_KEY found — using fallback questions")

    # ----------------------------------------------------------
    # UPDATED SIGNATURE: supports asked_questions + conversation
    # ----------------------------------------------------------
    async def generate_questions(
        self,
        parsed_resume: ParsedData,
        interview_type: str,
        difficulty: str,
        max_questions: int,
        asked_questions: Optional[List[str]] = None,
        conversation_history: Optional[List] = None,
    ) -> List[Question]:
        """Generate interview questions with de-dupe support"""

        asked_questions = asked_questions or []
        conversation_history = conversation_history or []

        if not self.client or not settings.GROQ_API_KEY:
            logger.warning("⚠️ Groq disabled — using template questions")
            questions = self._generate_template_questions(interview_type, max_questions)
            return self._filter_duplicates(questions, asked_questions)

        try:
            context = self._build_resume_context(parsed_resume)

            logger.info(
                f"🧠 Generating {max_questions} questions | type={interview_type} difficulty={difficulty}"
            )

            questions = await self._generate_with_groq(
                context,
                interview_type,
                difficulty,
                max_questions
            )

            # 🔥 Remove duplicates using asked_questions + conversation
            questions = self._filter_duplicates(questions, asked_questions)

            return questions

        except Exception as e:
            logger.error(f"❌ Question generation error: {e}")
            fallback = self._generate_template_questions(interview_type, max_questions)
            return self._filter_duplicates(fallback, asked_questions)

    # ----------------------------------------------------------
    # NEW: Deduplication logic
    # ----------------------------------------------------------
    def _filter_duplicates(
        self, 
        questions: List[Question], 
        asked_questions: List[str]
    ) -> List[Question]:
        """Remove exact & approximate duplicates."""
        clean = []

        for q in questions:
            qtext = q.question_text.strip().lower()

            # Exact repeat?
            if qtext in [x.lower() for x in asked_questions]:
                logger.info(f"⛔ Skipping duplicate question: {qtext[:80]}")
                continue

            # Approximate repeat (first 6 words match)
            for asked in asked_questions:
                if " ".join(qtext.split()[:6]) == " ".join(asked.lower().split()[:6]):
                    logger.info(f"⛔ Skipping near-duplicate question: {qtext[:80]}")
                    break
            else:
                clean.append(q)

        return clean

    def _build_resume_context(self, resume: ParsedData) -> str:
        """Build context from resume"""

        logger.info("📄 Building resume context")

        context_parts = []

        if resume.name:
            context_parts.append(f"Name: {resume.name}")

        if resume.skills:
            context_parts.append(f"Skills: {', '.join(resume.skills[:10])}")

        if resume.experience:
            exp_text = []
            for exp in resume.experience[:3]:
                exp_text.append(f"{exp.role} at {exp.company} ({exp.duration})")
            context_parts.append(f"Experience: {'; '.join(exp_text)}")

        if resume.education:
            edu_text = []
            for edu in resume.education[:2]:
                edu_text.append(f"{edu.degree} in {edu.field} from {edu.institution}")
            context_parts.append(f"Education: {'; '.join(edu_text)}")

        if resume.projects:
            proj_text = [p.name for p in resume.projects[:3]]
            context_parts.append(f"Projects: {', '.join(proj_text)}")

        return "\n".join(context_parts)

    async def _generate_with_groq(
        self,
        context: str,
        interview_type: str,
        difficulty: str,
        max_questions: int
    ) -> List[Question]:
        """Generate questions using Groq AI"""

        logger.info("⚡ Calling Groq LLaMA-3.3-70B to generate questions")

        prompt = f"""You are an expert technical interviewer. Generate {max_questions} interview questions based on the candidate's resume.

Interview Type: {interview_type}
Difficulty: {difficulty}

Candidate Resume:
{context}

Generate questions that:
1. Are relevant to the candidate's experience and skills
2. Match the difficulty level ({difficulty})
3. Cover the interview type ({interview_type})
4. Are open-ended and thoughtful
5. Test both knowledge and problem-solving

Return ONLY valid JSON (no markdown) with this structure:
{{
  "questions": [
    {{
      "question_text": "The question text here",
      "category": "technical|behavioral|hr",
      "difficulty": "easy|medium|hard",
      "expected_topics": ["topic1", "topic2"]
    }}
  ]
}}

Interview Type Guidelines:
- technical: Focus on technical skills, coding, architecture, problem-solving
- behavioral: Focus on past experiences, teamwork, leadership, conflicts
- hr: Focus on motivation, culture fit, salary, availability
- mixed: Combination of all types (40% technical, 30% behavioral, 30% hr)

Generate exactly {max_questions} questions."""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert interviewer. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=1500,
            )

            response_text = chat_completion.choices[0].message.content.strip()

            # Remove ```json and ``` if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            data = json.loads(response_text)

            questions = []
            for q in data.get("questions", [])[:max_questions]:
                questions.append(
                    Question(
                        question_text=q.get("question_text", ""),
                        category=q.get("category", interview_type),
                        difficulty=q.get("difficulty", difficulty),
                        expected_topics=q.get("expected_topics", [])
                    )
                )

            return questions

        except Exception as e:
            logger.error(f"❌ Groq question generation error: {e}")
            raise

    def _generate_template_questions(
        self,
        interview_type: str,
        max_questions: int
    ) -> List[Question]:
        """Fallback template questions"""

        logger.warning(f"⚠️ Using template questions for type={interview_type}")

        templates = {
            "technical": [
                Question(
                    question_text="Tell me about your experience with the technologies listed in your resume.",
                    category="technical",
                    difficulty="medium",
                    expected_topics=["experience", "technologies"]
                ),
                Question(
                    question_text="Describe a challenging technical problem you solved recently.",
                    category="technical",
                    difficulty="medium",
                    expected_topics=["problem-solving", "technical skills"]
                ),
                Question(
                    question_text="How do you approach debugging complex issues?",
                    category="technical",
                    difficulty="medium",
                    expected_topics=["debugging", "methodology"]
                ),
                Question(
                    question_text="Explain your experience with version control and collaboration.",
                    category="technical",
                    difficulty="easy",
                    expected_topics=["git", "collaboration"]
                ),
                Question(
                    question_text="What's your experience with testing and quality assurance?",
                    category="technical",
                    difficulty="medium",
                    expected_topics=["testing", "quality"]
                ),
            ],
            "behavioral": [
                Question(
                    question_text="Tell me about yourself and your professional background.",
                    category="behavioral",
                    difficulty="easy",
                    expected_topics=["background", "experience"]
                ),
                Question(
                    question_text="Describe a time when you had to work with a difficult team member.",
                    category="behavioral",
                    difficulty="medium",
                    expected_topics=["teamwork", "conflict resolution"]
                ),
                Question(
                    question_text="Tell me about a project you're most proud of.",
                    category="behavioral",
                    difficulty="medium",
                    expected_topics=["achievement", "pride"]
                ),
                Question(
                    question_text="How do you handle tight deadlines and pressure?",
                    category="behavioral",
                    difficulty="medium",
                    expected_topics=["stress management", "time management"]
                ),
                Question(
                    question_text="Describe a situation where you had to learn something new quickly.",
                    category="behavioral",
                    difficulty="medium",
                    expected_topics=["learning", "adaptability"]
                ),
            ],
            "hr": [
                Question(
                    question_text="Why are you interested in this position?",
                    category="hr",
                    difficulty="easy",
                    expected_topics=["motivation", "interest"]
                ),
                Question(
                    question_text="What are your salary expectations?",
                    category="hr",
                    difficulty="easy",
                    expected_topics=["compensation"]
                ),
                Question(
                    question_text="Where do you see yourself in 5 years?",
                    category="hr",
                    difficulty="medium",
                    expected_topics=["career goals"]
                ),
                Question(
                    question_text="What is your notice period?",
                    category="hr",
                    difficulty="easy",
                    expected_topics=["availability"]
                ),
                Question(
                    question_text="Why are you looking to leave your current role?",
                    category="hr",
                    difficulty="medium",
                    expected_topics=["motivation", "career change"]
                ),
            ],
            "mixed": [
                Question(
                    question_text="Tell me about yourself and your technical background.",
                    category="behavioral",
                    difficulty="easy",
                    expected_topics=["background", "introduction"]
                ),
                Question(
                    question_text="Describe a challenging technical project you worked on.",
                    category="technical",
                    difficulty="medium",
                    expected_topics=["project", "challenges"]
                ),
                Question(
                    question_text="How do you stay updated with new technologies?",
                    category="behavioral",
                    difficulty="medium",
                    expected_topics=["learning", "growth"]
                ),
                Question(
                    question_text="What motivates you in your career?",
                    category="hr",
                    difficulty="medium",
                    expected_topics=["motivation", "career"]
                ),
                Question(
                    question_text="Tell me about your experience working in teams.",
                    category="behavioral",
                    difficulty="medium",
                    expected_topics=["teamwork", "collaboration"]
                ),
            ]
        }

        return templates.get(interview_type, templates["mixed"])[:max_questions]
