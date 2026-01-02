"""
Template Question Service
Provides high-quality fallback questions when LLM is unavailable
"""
from typing import List, Dict
import random
import logging

from app.models.interview import Question

logger = logging.getLogger(__name__)


class TemplateQuestionService:
    """
    Service for generating template/fallback questions
    Organized by interview type and difficulty
    """

    # High-quality question templates by category
    TECHNICAL_QUESTIONS = {
        "easy": [
            Question(
                question_text="Can you walk me through your technical background and the main technologies you work with?",
                category="technical",
                difficulty="easy",
                expected_topics=["background", "technologies"]
            ),
            Question(
                question_text="Tell me about your experience with version control systems like Git.",
                category="technical",
                difficulty="easy",
                expected_topics=["git", "version control"]
            ),
            Question(
                question_text="How do you typically approach learning a new technology or framework?",
                category="technical",
                difficulty="easy",
                expected_topics=["learning", "self-development"]
            ),
            Question(
                question_text="What development tools and IDEs are you most comfortable with?",
                category="technical",
                difficulty="easy",
                expected_topics=["tools", "IDE"]
            ),
        ],
        "medium": [
            Question(
                question_text="Describe a challenging technical problem you solved recently and your approach to solving it.",
                category="technical",
                difficulty="medium",
                expected_topics=["problem-solving", "technical skills"]
            ),
            Question(
                question_text="How do you approach debugging complex issues in production systems?",
                category="technical",
                difficulty="medium",
                expected_topics=["debugging", "production"]
            ),
            Question(
                question_text="Explain your experience with writing tests and ensuring code quality.",
                category="technical",
                difficulty="medium",
                expected_topics=["testing", "quality assurance"]
            ),
            Question(
                question_text="How do you handle technical debt in your projects?",
                category="technical",
                difficulty="medium",
                expected_topics=["technical debt", "code quality"]
            ),
            Question(
                question_text="Describe your experience with API design and development.",
                category="technical",
                difficulty="medium",
                expected_topics=["API", "REST", "design"]
            ),
        ],
        "hard": [
            Question(
                question_text="Explain your approach to designing scalable and maintainable system architectures.",
                category="technical",
                difficulty="hard",
                expected_topics=["architecture", "scalability"]
            ),
            Question(
                question_text="How would you optimize a slow-performing database query in a production system?",
                category="technical",
                difficulty="hard",
                expected_topics=["optimization", "databases"]
            ),
            Question(
                question_text="Describe your experience with distributed systems and handling consistency challenges.",
                category="technical",
                difficulty="hard",
                expected_topics=["distributed systems", "consistency"]
            ),
            Question(
                question_text="How do you approach system design for high-availability applications?",
                category="technical",
                difficulty="hard",
                expected_topics=["system design", "high availability"]
            ),
        ]
    }

    BEHAVIORAL_QUESTIONS = {
        "easy": [
            Question(
                question_text="Tell me about yourself and what brings you here today.",
                category="behavioral",
                difficulty="easy",
                expected_topics=["background", "introduction"]
            ),
            Question(
                question_text="What are you most passionate about in your work?",
                category="behavioral",
                difficulty="easy",
                expected_topics=["passion", "motivation"]
            ),
            Question(
                question_text="How do you prefer to receive feedback from your team?",
                category="behavioral",
                difficulty="easy",
                expected_topics=["feedback", "communication"]
            ),
        ],
        "medium": [
            Question(
                question_text="Describe a time when you had to work with a difficult team member. How did you handle it?",
                category="behavioral",
                difficulty="medium",
                expected_topics=["teamwork", "conflict resolution"]
            ),
            Question(
                question_text="Tell me about a project you're most proud of and why.",
                category="behavioral",
                difficulty="medium",
                expected_topics=["achievement", "pride"]
            ),
            Question(
                question_text="How do you prioritize tasks when facing multiple tight deadlines?",
                category="behavioral",
                difficulty="medium",
                expected_topics=["time management", "prioritization"]
            ),
            Question(
                question_text="Describe a situation where you had to adapt to significant changes quickly.",
                category="behavioral",
                difficulty="medium",
                expected_topics=["adaptability", "change management"]
            ),
            Question(
                question_text="Tell me about a time when you failed and what you learned from it.",
                category="behavioral",
                difficulty="medium",
                expected_topics=["failure", "learning"]
            ),
        ],
        "hard": [
            Question(
                question_text="Describe a situation where you had to make a difficult decision with incomplete information.",
                category="behavioral",
                difficulty="hard",
                expected_topics=["decision making", "uncertainty"]
            ),
            Question(
                question_text="Tell me about a time when you had to influence others without having direct authority.",
                category="behavioral",
                difficulty="hard",
                expected_topics=["leadership", "influence"]
            ),
            Question(
                question_text="How have you handled a situation where your team disagreed with your technical approach?",
                category="behavioral",
                difficulty="hard",
                expected_topics=["conflict", "technical leadership"]
            ),
        ]
    }

    HR_QUESTIONS = {
        "easy": [
            Question(
                question_text="Why are you interested in this position?",
                category="hr",
                difficulty="easy",
                expected_topics=["motivation", "interest"]
            ),
            Question(
                question_text="What are your salary expectations for this role?",
                category="hr",
                difficulty="easy",
                expected_topics=["compensation"]
            ),
            Question(
                question_text="What is your current notice period?",
                category="hr",
                difficulty="easy",
                expected_topics=["availability"]
            ),
            Question(
                question_text="Are you open to relocation if required?",
                category="hr",
                difficulty="easy",
                expected_topics=["relocation", "flexibility"]
            ),
        ],
        "medium": [
            Question(
                question_text="Where do you see yourself in the next 3-5 years?",
                category="hr",
                difficulty="medium",
                expected_topics=["career goals", "ambition"]
            ),
            Question(
                question_text="Why are you looking to leave your current role?",
                category="hr",
                difficulty="medium",
                expected_topics=["motivation", "career change"]
            ),
            Question(
                question_text="What do you know about our company and why do you want to work here?",
                category="hr",
                difficulty="medium",
                expected_topics=["company research", "culture fit"]
            ),
            Question(
                question_text="What are your strengths and how do they align with this role?",
                category="hr",
                difficulty="medium",
                expected_topics=["strengths", "role fit"]
            ),
        ],
        "hard": [
            Question(
                question_text="What would you do in your first 90 days if you got this position?",
                category="hr",
                difficulty="hard",
                expected_topics=["planning", "initiative"]
            ),
            Question(
                question_text="How do you handle work-life balance in demanding roles?",
                category="hr",
                difficulty="hard",
                expected_topics=["work-life balance", "stress management"]
            ),
        ]
    }

    def __init__(self, randomize: bool = True):
        """
        Initialize template question service
        
        Args:
            randomize: Whether to randomize question order
        """
        self.randomize = randomize

    def get_questions(
        self,
        interview_type: str,
        max_questions: int,
        difficulty: str = "medium",
    ) -> List[Question]:
        """
        Get template questions for interview
        
        Args:
            interview_type: Type of interview (technical, behavioral, hr, mixed)
            max_questions: Maximum number of questions to return
            difficulty: Difficulty level (easy, medium, hard)
            
        Returns:
            List of Question objects
        """
        logger.info(f"📝 Getting {max_questions} template questions: {interview_type}/{difficulty}")

        if interview_type == "mixed":
            questions = self._get_mixed_questions(max_questions, difficulty)
        else:
            questions = self._get_typed_questions(interview_type, max_questions, difficulty)

        # Randomize if enabled
        if self.randomize:
            random.shuffle(questions)

        return questions[:max_questions]

    def _get_typed_questions(
        self,
        interview_type: str,
        max_questions: int,
        difficulty: str,
    ) -> List[Question]:
        """Get questions for specific interview type"""
        
        question_pool = self._get_question_pool(interview_type)
        
        if not question_pool:
            logger.warning(f"⚠️ Unknown interview type: {interview_type}")
            return self._get_mixed_questions(max_questions, difficulty)

        # Get questions matching difficulty
        questions = question_pool.get(difficulty, [])
        
        # If not enough, add from other difficulties
        if len(questions) < max_questions:
            for diff in ["easy", "medium", "hard"]:
                if diff != difficulty:
                    questions.extend(question_pool.get(diff, []))
                if len(questions) >= max_questions:
                    break

        return questions

    def _get_mixed_questions(self, max_questions: int, difficulty: str) -> List[Question]:
        """Get balanced mix of technical, behavioral, and HR questions"""
        
        # Distribution: 50% technical, 30% behavioral, 20% HR
        num_technical = max(1, int(max_questions * 0.5))
        num_behavioral = max(1, int(max_questions * 0.3))
        num_hr = max_questions - num_technical - num_behavioral

        questions = []
        questions.extend(self._get_typed_questions("technical", num_technical, difficulty))
        questions.extend(self._get_typed_questions("behavioral", num_behavioral, difficulty))
        questions.extend(self._get_typed_questions("hr", num_hr, difficulty))

        return questions

    def _get_question_pool(self, interview_type: str) -> Dict[str, List[Question]]:
        """Get question pool for interview type"""
        pools = {
            "technical": self.TECHNICAL_QUESTIONS,
            "behavioral": self.BEHAVIORAL_QUESTIONS,
            "hr": self.HR_QUESTIONS,
        }
        return pools.get(interview_type, {})

    def get_opening_question(self, interview_type: str) -> Question:
        """Get a good opening question"""
        opening_questions = {
            "technical": Question(
                question_text="Let's start by having you tell me about your technical background and the projects you've worked on.",
                category="technical",
                difficulty="easy",
                expected_topics=["background", "projects"]
            ),
            "behavioral": Question(
                question_text="Tell me about yourself and what brings you here today.",
                category="behavioral",
                difficulty="easy",
                expected_topics=["background", "introduction"]
            ),
            "hr": Question(
                question_text="Why are you interested in this position and what do you know about our company?",
                category="hr",
                difficulty="easy",
                expected_topics=["motivation", "research"]
            ),
            "mixed": Question(
                question_text="Let's begin with you telling me about your professional background and experience.",
                category="mixed",
                difficulty="easy",
                expected_topics=["background", "experience"]
            ),
        }
        return opening_questions.get(interview_type, opening_questions["mixed"])

    def get_closing_question(self, interview_type: str) -> Question:
        """Get a good closing question"""
        return Question(
            question_text="Is there anything else you'd like to share that we haven't covered, or any questions you have for me?",
            category=interview_type,
            difficulty="easy",
            expected_topics=["wrap-up", "questions"]
        )

    def get_questions_by_topic(
        self,
        topics: List[str],
        max_questions: int,
        difficulty: str = "medium",
    ) -> List[Question]:
        """
        Get questions related to specific topics
        
        Args:
            topics: List of topics to focus on
            max_questions: Maximum questions to return
            difficulty: Difficulty level
            
        Returns:
            List of relevant questions
        """
        all_questions = []
        
        # Gather all questions
        for pool in [self.TECHNICAL_QUESTIONS, self.BEHAVIORAL_QUESTIONS, self.HR_QUESTIONS]:
            for diff_questions in pool.values():
                all_questions.extend(diff_questions)

        # Filter by topics
        relevant_questions = []
        for question in all_questions:
            if any(topic.lower() in ' '.join(question.expected_topics).lower() for topic in topics):
                relevant_questions.append(question)

        if not relevant_questions:
            # No matches, return general questions
            return self.get_questions("mixed", max_questions, difficulty)

        if self.randomize:
            random.shuffle(relevant_questions)

        return relevant_questions[:max_questions]