import json
import logging
from typing import List, Dict, Optional, Any
from groq import Groq
from app.core.config import settings
from app.models.interview import Question
from app.models.resume import ParsedData


logger = logging.getLogger(__name__)


class QuestionGeneratorService:
    """Generate interview questions using FREE Groq AI"""

    def _safe_list(self, value: Any) -> List[str]:
        """Convert skills/education/etc. into a safe list."""
        if value is None:
            return []

        if isinstance(value, list):
            return [str(v) for v in value if v]

        # Sometimes parser returns Skills() object → convert to list
        if hasattr(value, "__dict__"):
            # extract any fields that look like lists
            for k, v in value.__dict__.items():
                if isinstance(v, list):
                    return [str(x) for x in v]
                if isinstance(v, str):
                    return [v]

        if isinstance(value, str):
            return [value]

        return []

    def __init__(self):
        """Initialize Groq client"""
        self.client = None
        if settings.GROQ_API_KEY:
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info("✓ Question Generator initialized (Groq AI - FREE)")
        else:
            logger.warning("⚠️ No GROQ_API_KEY found — using fallback questions")

    def _normalize_message(self, msg):
        """Supports both dict and ConversationMessage objects."""
        # ConversationMessage / Pydantic model
        if hasattr(msg, "speaker") and hasattr(msg, "text"):
            return msg.speaker, msg.text

        if isinstance(msg, dict):
            # Standard dict structure
            speaker = msg.get("speaker") or msg.get("role")
            text = msg.get("text") or msg.get("content")
            return speaker, text

        return None, None

    async def generate_questions(
        self,
        parsed_resume: ParsedData,
        interview_type: str,
        difficulty: str,
        max_questions: int,
        job_description: str,
        asked_questions: Optional[List[str]] = None,
        conversation_history: Optional[List[Dict]] = None,
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
                job_description,
                interview_type,
                difficulty,
                max_questions,
                asked_questions,
                conversation_history
            )

            # Remove duplicates using asked_questions + conversation
            questions = self._filter_duplicates(questions, asked_questions)

            # Ensure we have enough questions (fallback if needed)
            while len(questions) < max_questions and self.client:
                additional = await self._generate_with_groq(
                    context, job_description, interview_type, difficulty,
                    max_questions - len(questions), asked_questions, conversation_history
                )
                additional = self._filter_duplicates(additional, asked_questions)
                questions.extend(additional[:max_questions - len(questions)])
                break  # Prevent infinite loop

            return questions[:max_questions]

        except Exception as e:
            logger.error(f"❌ Question generation error: {e}")
            fallback = self._generate_template_questions(interview_type, max_questions)
            return self._filter_duplicates(fallback, asked_questions)

    def _filter_duplicates(
        self,
        questions: List[Question],
        asked_questions: List[str]
    ) -> List[Question]:
        """Remove exact & approximate duplicates."""
        clean = []

        for q in questions:
            if not q.question_text:  # Skip empty questions
                continue

            qtext = q.question_text.strip().lower()

            # Exact repeat?
            if any(qtext == x.lower().strip() for x in asked_questions):
                logger.info(f"⛔ Skipping duplicate question: {qtext[:80]}...")
                continue

            # Approximate repeat (first 6 words match)
            is_duplicate = False
            for asked in asked_questions:
                asked_words = asked.lower().strip().split()[:6]
                q_words = qtext.split()[:6]
                if len(asked_words) >= 4 and len(q_words) >= 4 and asked_words == q_words:
                    logger.info(f"⛔ Skipping near-duplicate question: {qtext[:80]}...")
                    is_duplicate = True
                    break

            if not is_duplicate:
                clean.append(q)

        return clean

    def _build_resume_context(self, resume: ParsedData) -> str:
        logger.info("📄 Building resume context")

        skills = self._safe_list(resume.skills)
        exp = resume.experience or []
        edu = resume.education or []
        proj = resume.projects or []

        parts = []

        if resume.name:
            parts.append(f"Name: {resume.name}")

        if skills:
            parts.append(f"Skills: {', '.join(skills[:10])}")

        if exp:
            exp_lines = []
            for e in exp[:3]:
                role = getattr(e, "role", "N/A")
                company = getattr(e, "company", "N/A")
                duration = getattr(e, "duration", "N/A")
                exp_lines.append(f"{role} at {company} ({duration})")
            parts.append(f"Experience: {'; '.join(exp_lines)}")

        if edu:
            edu_lines = []
            for e in edu[:2]:
                degree = getattr(e, "degree", "N/A")
                field = getattr(e, "field", "N/A")
                inst = getattr(e, "institution", "N/A")
                edu_lines.append(f"{degree} in {field} from {inst}")
            parts.append(f"Education: {'; '.join(edu_lines)}")

        if proj:
            names = [getattr(p, "name", "Project") for p in proj[:3]]
            parts.append(f"Projects: {', '.join(names)}")

        return "\n".join(parts) or "No resume data available."

    async def _generate_with_groq(
        self,
        resume_context: str,
        job_description: str,
        interview_type: str,
        difficulty: str,
        max_questions: int,
        asked_questions: List[str],
        conversation_history: List[Dict]
    ) -> List[Question]:
        """Generate questions using Groq AI"""

        logger.info("⚡ Calling Groq LLaMA-3.3-70B to generate questions")

        # Format conversation history for prompt
        conv_summary = ""
        if conversation_history:
            lines = []
            for msg in conversation_history[-4:]:  # Last 4 messages
                speaker, text = self._normalize_message(msg)
                if not text:
                    continue

                if speaker in ["candidate", "user"]:
                    lines.append(f"CANDIDATE: {text[:100]}...")
                elif speaker in ["ai", "assistant"]:
                    lines.append(f"INTERVIEWER: {text[:100]}...")

                if len(lines) >= 3:  # limit
                    break

            conv_summary = "\n".join(lines)

        asked_summary = "; ".join(asked_questions[-5:]) if asked_questions else "None"

        prompt = f"""You are an expert interviewer. Your job is to generate highly diverse, non-repetitive, 
context-aware interview questions based on the Job Description (JD) and the Candidate Resume.

GOALS:
1. Produce UNIQUE, NON-REPEATING questions (avoid anything similar to earlier questions).
2. Questions must be HIGH-QUALITY, job-relevant, and focused on the JD + Resume.
3. Adapt question style based on interview_type:
   - technical → ask DIRECT technical questions (definitions, concepts, coding fundamentals,
     implementation questions, API usage, OOP, DBMS, DSA, frameworks like FastAPI, Django, 
     React, JVM, JDBC, AWS, etc.). 
     Examples:
       • "What is a constructor in OOP?"
       • "Explain polymorphism."
       • "What is JDBC and how does it work?"
       • "How does FastAPI handle dependency injection?"
       • "Explain ACID properties."
       • "Difference between threads and processes."
       • "Explain event loop in Python."
   - behavioral → ask scenario-based, experience-based questions.
   - hr → ask motivation, expectations, culture-fit questions.
   - mixed → combine all types but still ensure variety.

STRICT RULES:
1. DO NOT repeat or rephrase any previously asked question.
2. Every question MUST follow a DIFFERENT pattern. Examples:
   - direct knowledge check
   - compare X vs Y
   - explain workflow
   - debug scenario
   - why/how reasoning
   - architecture or design choices
   - performance optimization
   - "when did you last..." experience questions
   - "walk me through..." methodological questions
   - hypothetical "how would you approach…" questions
3. Avoid starting more than one question with the same phrase.
4. Cover multiple dimensions:
   - core technical concepts
   - applied project experience
   - tools/frameworks in resume
   - job-specific responsibilities from JD
   - performance, optimization, debugging
   - system design or API design (if relevant)
5. Output MUST be valid JSON only.

CONTEXT:
Job Description: {job_description}

Candidate Resume:
{resume_context}

Previously Asked Questions: {asked_summary}

Recent Conversation: {conv_summary}

Generate exactly {max_questions} diverse questions in this JSON format:
{{
  "questions": [
    {{
      "question_text": "Full question here",
      "category": "technical|behavioral|hr|mixed",
      "difficulty": "{difficulty}",
      "expected_topics": ["topic1", "topic2"]
    }}
  ]
}}"""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert interviewer. Return ONLY valid JSON response. No explanations."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=2000,
            )

            response_text = chat_completion.choices[0].message.content.strip()

            # Clean JSON response - remove markdown code blocks
            if response_text.startswith("```"):
                # Remove opening ```json or ```
                response_text = response_text.split("\n", 1)[1] if "\n" in response_text else response_text[3:]
            if response_text.endswith("```"):
                # Remove closing ```
                response_text = response_text.rsplit("\n", 1)[0] if "\n" in response_text else response_text[:-3]
            
            response_text = response_text.strip()

            data = json.loads(response_text)

            questions = []
            for q_data in data.get("questions", [])[:max_questions]:
                if q_data.get("question_text"):  # Validate
                    questions.append(
                        Question(
                            question_text=q_data.get("question_text", ""),
                            category=q_data.get("category", interview_type),
                            difficulty=q_data.get("difficulty", difficulty),
                            expected_topics=q_data.get("expected_topics", [])
                        )
                    )

            logger.info(f"✅ Generated {len(questions)} questions successfully")
            return questions

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON from Groq: {e}\nResponse: {response_text[:200]}")
            raise
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
                Question(question_text="Tell me about your experience with the technologies listed in your resume.", category="technical", difficulty="medium", expected_topics=["experience", "technologies"]),
                Question(question_text="Describe a challenging technical problem you solved recently.", category="technical", difficulty="medium", expected_topics=["problem-solving", "technical skills"]),
                Question(question_text="How do you approach debugging complex issues?", category="technical", difficulty="medium", expected_topics=["debugging", "methodology"]),
                Question(question_text="Explain your experience with version control and collaboration.", category="technical", difficulty="easy", expected_topics=["git", "collaboration"]),
                Question(question_text="What's your experience with testing and quality assurance?", category="technical", difficulty="medium", expected_topics=["testing", "quality"]),
            ],
            "behavioral": [
                Question(question_text="Tell me about yourself and your professional background.", category="behavioral", difficulty="easy", expected_topics=["background", "experience"]),
                Question(question_text="Describe a time when you had to work with a difficult team member.", category="behavioral", difficulty="medium", expected_topics=["teamwork", "conflict resolution"]),
                Question(question_text="Tell me about a project you're most proud of.", category="behavioral", difficulty="medium", expected_topics=["achievement", "pride"]),
                Question(question_text="How do you handle tight deadlines and pressure?", category="behavioral", difficulty="medium", expected_topics=["stress management", "time management"]),
                Question(question_text="Describe a situation where you had to learn something new quickly.", category="behavioral", difficulty="medium", expected_topics=["learning", "adaptability"]),
            ],
            "hr": [
                Question(question_text="Why are you interested in this position?", category="hr", difficulty="easy", expected_topics=["motivation", "interest"]),
                Question(question_text="What are your salary expectations?", category="hr", difficulty="easy", expected_topics=["compensation"]),
                Question(question_text="Where do you see yourself in 5 years?", category="hr", difficulty="medium", expected_topics=["career goals"]),
                Question(question_text="What is your notice period?", category="hr", difficulty="easy", expected_topics=["availability"]),
                Question(question_text="Why are you looking to leave your current role?", category="hr", difficulty="medium", expected_topics=["motivation", "career change"]),
            ],
            "mixed": [
                Question(question_text="Tell me about yourself and your technical background.", category="behavioral", difficulty="easy", expected_topics=["background", "introduction"]),
                Question(question_text="Describe a challenging technical project you worked on.", category="technical", difficulty="medium", expected_topics=["project", "challenges"]),
                Question(question_text="How do you stay updated with new technologies?", category="behavioral", difficulty="medium", expected_topics=["learning", "growth"]),
                Question(question_text="What motivates you in your career?", category="hr", difficulty="medium", expected_topics=["motivation", "career"]),
                Question(question_text="Tell me about your experience working in teams.", category="behavioral", difficulty="medium", expected_topics=["teamwork", "collaboration"]),
            ]
        }

        return templates.get(interview_type, templates["mixed"])[:max_questions]