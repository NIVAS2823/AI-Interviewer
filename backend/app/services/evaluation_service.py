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
    """

    def __init__(self):
        """Initialize Groq client"""
        self.client = None
        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info("✓ Evaluation Service initialized (Groq AI - FREE)")
            except Exception as exc:
                logger.exception("Failed to init Groq client: %s", exc)
                self.client = None

    # -------------------------------
    # PUBLIC API
    # -------------------------------
    async def evaluate_interview(
        self,
        conversation: List[ConversationMessage],
        questions: List[Question],
        interview_type: str,
        difficulty: str
    ) -> Evaluation:

        if not self.client:
            logger.warning("Groq unavailable — fallback evaluation used")
            return self._create_basic_evaluation(conversation, questions)

        try:
            context = self._build_conversation_context(conversation, questions)
            evaluation = await self._evaluate_with_groq(context, interview_type, difficulty)
            return evaluation

        except Exception as e:
            logger.exception("❌ Evaluation error: %s", e)
            return self._create_basic_evaluation(conversation, questions)

    async def generate(self, *args, **kwargs):
        return await self.evaluate_interview(*args, **kwargs)

    # -------------------------------
    # CONTEXT BUILDERS
    # -------------------------------
    def _build_conversation_context(
        self,
        conversation: List[ConversationMessage],
        questions: List[Question]
    ) -> str:

        context_parts = ["=== INTERVIEW CONVERSATION ===\n"]
        for msg in conversation:
            role = "INTERVIEWER" if getattr(msg, "speaker", "") == "ai" else "CANDIDATE"
            context_parts.append(f"{role}: {getattr(msg, 'text', '')}")

        context_parts.append("\n=== QUESTIONS ASKED ===\n")
        for i, q in enumerate(questions, 1):
            if isinstance(q, dict):
                qtext = q.get("question_text")
                qcat = q.get("category")
                qdiff = q.get("difficulty")
            else:
                qtext = getattr(q, "question_text", "")
                qcat = getattr(q, "category", "")
                qdiff = getattr(q, "difficulty", "")

            context_parts.append(f"Q{i} ({qcat}, {qdiff}): {qtext}")

        return "\n".join(context_parts)

    # -------------------------------
    # GROQ EVALUATION
    # -------------------------------
    async def _evaluate_with_groq(self, context: str, interview_type: str, difficulty: str) -> Evaluation:

        prompt = f"""
        You are an expert technical interviewer. Evaluate the conversation.

        Interview Type: {interview_type}
        Difficulty: {difficulty}

        {context}

        Return ONLY valid JSON:
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

        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Return only JSON."},
                {"role": "user", "content": prompt},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2000,
        )

        text = chat_completion.choices[0].message.content.strip()

        # Remove ``` fences
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)

        # Normalize sections
        scores_norm = self._normalize_scores(data.get("scores", {}))
        sentiment_norm = self._normalize_sentiment(data.get("sentiment", {}))

        return Evaluation(
            scores=EvaluationScore(**scores_norm),
            sentiment=SentimentAnalysis(**sentiment_norm),
            strengths=data.get("strengths", []),
            improvements=data.get("improvements", []),
            detailed_feedback=data.get("detailed_feedback", ""),
            question_scores=data.get("question_scores", []),
        )

    # -------------------------------
    # NORMALIZERS (MISSING IN YOUR FILE)
    # -------------------------------
    def _normalize_scores(self, raw: Dict) -> Dict:
        """Normalize to valid 0–100 ints"""

        def to_int(v):
            try:
                if isinstance(v, str):
                    v = float(v)
                if isinstance(v, float):
                    return int(round(v))
                return int(v)
            except:
                return 0

        return {
            "overall_score": max(0, min(100, to_int(raw.get("overall_score", 0)))),
            "technical_score": max(0, min(100, to_int(raw.get("technical_score", 0)))),
            "communication_score": max(0, min(100, to_int(raw.get("communication_score", 0)))),
            "confidence_score": max(0, min(100, to_int(raw.get("confidence_score", 0)))),
            "behavioral_score": max(0, min(100, to_int(raw.get("behavioral_score", 0)))),
        }

    def _normalize_sentiment(self, raw: Dict) -> Dict:
        """Normalize sentiment values and ensure they sum to 1"""

        try:
            pos = float(raw.get("positive", 0.0))
            neu = float(raw.get("neutral", 0.0))
            neg = float(raw.get("negative", 0.0))
        except:
            pos, neu, neg = 0.0, 0.0, 0.0

        total = pos + neu + neg
        if total > 0:
            pos, neu, neg = pos / total, neu / total, neg / total

        return {
            "positive": round(pos, 2),
            "neutral": round(neu, 2),
            "negative": round(neg, 2),
        }

    # -------------------------------
    # BASIC FALLBACK (no Groq)
    # -------------------------------
    def _create_basic_evaluation(self, conversation, questions) -> Evaluation:
        candidate_responses = [
            m for m in conversation if getattr(m, "speaker", "") == "candidate"
        ]

        count = len(candidate_responses)
        avg_len = sum(len(m.text) for m in candidate_responses) / max(1, count)

        base = min(100, count * 15 + avg_len // 50)

        return Evaluation(
            scores=EvaluationScore(
                overall_score=base,
                technical_score=base,
                communication_score=min(100, avg_len // 20),
                confidence_score=base,
                behavioral_score=base,
            ),
            sentiment=SentimentAnalysis(
                positive=0.6, neutral=0.3, negative=0.1
            ),
            strengths=["Good participation"],
            improvements=["Provide more detailed answers"],
            detailed_feedback="Basic evaluation (Groq disabled).",
            question_scores=[],
        )
    # ----------------------------------------------------------------------
    # Single answer evaluation
    # ----------------------------------------------------------------------

    async def evaluate_single_answer(
        self,
        question: str,
        answer: str,
        expected_topics: List[str]
    ) -> Dict:
        """
        Evaluate a single question-answer pair.
        """
        if not self.client:
            return {"score": 70, "feedback": "Groq disabled — basic score only."}

        prompt = f"""Evaluate this interview answer:

Q: {question}
Expected Topics: {', '.join(expected_topics)}
Answer: {answer}

Return ONLY valid JSON:
{{
  "score": 0-100,
  "feedback": "...",
  "topics_covered": [...],
  "topics_missed": [...]
}}"""

        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=300,
        )

        raw = chat_completion.choices[0].message.content.strip()

        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

        return json.loads(raw)
