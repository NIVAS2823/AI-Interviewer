import json
import logging
from typing import Dict, List, Optional
from groq import Groq
from app.core.config import settings
from app.models.interview import (
    Evaluation,
    EvaluationScore,
    SentimentAnalysis,
    ConversationMessage,
    Question
)

logger = logging.getLogger(__name__)


class EvaluationService:
    """
    AI-powered interview evaluation using FREE Groq Cloud
    Analyzes conversation and provides detailed feedback
    """

    def __init__(self):
        """Initialize Groq client"""
        self.client = None
        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info("✅ Evaluation Service initialized (Groq AI - FREE)")
            except Exception as exc:
                logger.exception("Failed to init Groq client: %s", exc)
                self.client = None

    # -------------------------
    # Public evaluate entry
    # -------------------------
    async def evaluate_interview(
        self,
        conversation: List[ConversationMessage],
        questions: List[Question],
        interview_type: str,
        difficulty: str
    ) -> Evaluation:
        """
        Evaluate complete interview
        """
        if not self.client or not settings.GROQ_API_KEY:
            logger.info("Groq API key missing or client not available — using basic fallback evaluation")
            return self._create_basic_evaluation(conversation, questions)

        try:
            context = self._build_conversation_context(conversation, questions)
            evaluation = await self._evaluate_with_groq(context, interview_type, difficulty)
            return evaluation
        except Exception as e:
            logger.exception("❌ Evaluation error: %s", e)
            return self._create_basic_evaluation(conversation, questions)

    # -------------------------
    # Helpers
    # -------------------------
    def _build_conversation_context(
        self,
        conversation: List[ConversationMessage],
        questions: List[Question]
    ) -> str:
        """Build formatted conversation for AI analysis"""
        context_parts = []
        context_parts.append("=== INTERVIEW CONVERSATION ===\n")
        for msg in conversation:
            speaker = "INTERVIEWER" if msg.speaker == "ai" else "CANDIDATE"
            context_parts.append(f"{speaker}: {msg.text}")
        context_parts.append("\n=== QUESTIONS ASKED ===\n")
        for i, q in enumerate(questions, 1):
            context_parts.append(f"Q{i} ({q.category}, {q.difficulty}): {q.question_text}")
        return "\n".join(context_parts)

    async def _evaluate_with_groq(
        self,
        context: str,
        interview_type: str,
        difficulty: str
    ) -> Evaluation:
        """
        Evaluate interview using Groq AI (FREE)
        """
        prompt = f"""You are an expert technical interviewer and evaluator. Analyze this interview conversation and provide a detailed evaluation.

Interview Type: {interview_type}
Difficulty: {difficulty}

{context}

Return ONLY valid JSON with structure:
{{
  "scores": {{
    "overall_score": 0-100,
    "technical_score": 0-100,
    "communication_score": 0-100,
    "confidence_score": 0-100,
    "behavioral_score": 0-100
  }},
  "sentiment": {{
    "positive": 0.0-1.0,
    "neutral": 0.0-1.0,
    "negative": 0.0-1.0
  }},
  "strengths": [...],
  "improvements": [...],
  "detailed_feedback": "...",
  "question_scores": [...]
}}
"""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert interview evaluator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=2000,
            )

            response_text = chat_completion.choices[0].message.content
            response_text = response_text.strip()

            # strip fences if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON
            data = json.loads(response_text)

            # Normalize scores (coerce floats/strings -> ints, clamp 0-100)
            scores_raw = data.get("scores", {})
            scores_norm = self._normalize_scores(scores_raw)

            # Normalize sentiment if present
            sentiment_raw = data.get("sentiment")
            sentiment_norm = self._normalize_sentiment(sentiment_raw) if sentiment_raw else None

            evaluation = Evaluation(
                scores=EvaluationScore(**scores_norm),
                sentiment=SentimentAnalysis(**sentiment_norm) if sentiment_norm else None,
                strengths=data.get("strengths", []),
                improvements=data.get("improvements", []),
                detailed_feedback=data.get("detailed_feedback"),
                question_scores=data.get("question_scores", []),
            )

            logger.info("✅ Groq evaluation parsed successfully")
            return evaluation

        except Exception as e:
            logger.exception("❌ Groq evaluation error: %s", e)
            raise

    def _normalize_scores(self, scores: Dict) -> Dict:
        """
        Coerce numbers to ints and clamp 0..100.
        Accepts ints, floats, numeric strings.
        """
        def to_int(v):
            try:
                if isinstance(v, str):
                    v = float(v)
                if isinstance(v, float):
                    return int(round(v))
                return int(v)
            except Exception:
                return 0

        normalized = {}
        for key in ["overall_score", "technical_score", "communication_score", "confidence_score", "behavioral_score"]:
            normalized[key] = max(0, min(100, to_int(scores.get(key, 0))))
        return normalized

    def _normalize_sentiment(self, raw: Dict) -> Dict:
        try:
            pos = float(raw.get("positive", 0.0))
            neu = float(raw.get("neutral", 0.0))
            neg = float(raw.get("negative", 0.0))
            # small safeguard: normalize to sum 1 if necessary
            total = pos + neu + neg
            if total > 0:
                pos, neu, neg = pos / total, neu / total, neg / total
            return {
                "positive": round(pos, 2),
                "neutral": round(neu, 2),
                "negative": round(neg, 2)
            }
        except Exception:
            return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}

    def _create_basic_evaluation(
        self,
        conversation: List[ConversationMessage],
        questions: List[Question]
    ) -> Evaluation:
        """
        Fallback: Create basic evaluation without AI
        """
        candidate_responses = [msg for msg in conversation if msg.speaker == "candidate"]
        response_count = len(candidate_responses)
        avg_response_length = sum(len(msg.text) for msg in candidate_responses) / max(response_count, 1)

        overall_score = min(100, int(response_count * 15 + (avg_response_length / 50)))
        technical_score = overall_score
        communication_score = min(100, int((avg_response_length / 30)))
        confidence_score = overall_score
        behavioral_score = overall_score

        return Evaluation(
            scores=EvaluationScore(
                overall_score=overall_score,
                technical_score=technical_score,
                communication_score=communication_score,
                confidence_score=confidence_score,
                behavioral_score=behavioral_score
            ),
            sentiment=SentimentAnalysis(positive=0.6, neutral=0.3, negative=0.1),
            strengths=[
                "Completed the interview",
                "Provided responses to questions",
                "Engaged in the conversation"
            ],
            improvements=[
                "Provide more detailed technical explanations",
                "Use specific examples from experience",
                "Structure answers using STAR method"
            ],
            detailed_feedback="The candidate participated in the interview and provided responses. For a more detailed evaluation, enable Groq AI.",
            question_scores=[]
        )

    async def evaluate_single_answer(
        self,
        question: str,
        answer: str,
        expected_topics: List[str]
    ) -> Dict:
        """
        Evaluate a single question-answer pair
        """
        if not self.client or not settings.GROQ_API_KEY:
            return {"score": 70, "feedback": "Answer received. Enable Groq AI for detailed evaluation."}

        prompt = f"""Evaluate this interview answer:

Question: {question}
Expected Topics: {', '.join(expected_topics)}
Candidate's Answer: {answer}

Return ONLY valid JSON:
{{
  "score": 0-100,
  "feedback": "Brief specific feedback on this answer",
  "topics_covered": ["topic1"],
  "topics_missed": ["topic2"]
}}"""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an interview evaluator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=300,
            )
            response_text = chat_completion.choices[0].message.content.strip()

            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            return json.loads(response_text)

        except Exception as e:
            logger.exception("❌ Single answer evaluation error: %s", e)
            return {"score": 70, "feedback": "Answer evaluated. Check logs for details.", "topics_covered": [], "topics_missed": expected_topics}
