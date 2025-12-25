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
    AI-powered interview evaluation using Groq Cloud
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

        # -----------------------------------
        # JSON TEMPLATE (Safe for f-strings)
        # -----------------------------------
        self.EVAL_JSON_TEMPLATE = """
{
  "scores": {
    "overall_score": 0,
    "technical_score": 0,
    "communication_score": 0,
    "confidence_score": 0,
    "behavioral_score": 0
  },
  "sentiment": {
    "positive": 0.0,
    "neutral": 0.0,
    "negative": 0.0
  },
  "strengths": [],
  "improvements": [],
  "detailed_feedback": "",
  "question_scores": [
    {
      "question": "",
      "score": 0,
      "answer_quality": "",
      "topics_covered": [],
      "topics_missed": []
    }
  ]
}
"""

        self.SINGLE_QA_TEMPLATE = """
{
  "score": 0,
  "feedback": "",
  "topics_covered": [],
  "topics_missed": [],
  "answer_quality": "",
  "clarity_score": 0,
  "depth_score": 0,
  "relevance_score": 0,
  "confidence_signals": ""
}
"""

    # ==========================================================
    # PUBLIC API
    # ==========================================================
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

    # ==========================================================
    # CONTEXT BUILDERS
    # ==========================================================
    def _build_conversation_context(
        self,
        conversation: List[ConversationMessage],
        questions: List[Question]
    ) -> str:

        parts = ["=== INTERVIEW CONVERSATION ===\n"]

        for msg in conversation:
            role = "INTERVIEWER" if getattr(msg, "speaker", "") == "ai" else "CANDIDATE"
            parts.append(f"{role}: {getattr(msg, 'text', '')}")

        parts.append("\n=== QUESTIONS ASKED ===\n")
        for i, q in enumerate(questions, 1):
            qtext = getattr(q, "question_text", "")
            qcat = getattr(q, "category", "")
            qdiff = getattr(q, "difficulty", "")
            parts.append(f"Q{i} ({qcat}, {qdiff}): {qtext}")

        return "\n".join(parts)

    # ==========================================================
    # LLM EVALUATION
    # ==========================================================
    async def _evaluate_with_groq(self, context: str, interview_type: str, difficulty: str) -> Evaluation:
        prompt = f"""
You are a senior hiring panel evaluator (Tech Lead + HR + Behavioral Analyst).
Evaluate the interview with extreme precision and return ONLY valid JSON.

Use the following criteria:
- Technical correctness and depth
- Clarity and structure
- Reasoning ability
- Communication quality
- Confidence and tone
- Behavioral insight
- Question-specific answer quality
- Missing concepts or red flags

==========================
INTERVIEW METADATA
==========================
Interview Type: {interview_type}
Difficulty: {difficulty}

==========================
INTERVIEW CONTENT
==========================
{context}

==========================
OUTPUT JSON FORMAT
==========================
Return JSON ONLY matching this structure:
{self.EVAL_JSON_TEMPLATE}

==========================
SCORING NOTES
==========================
- All scores MUST be between 0 and 100.
- overall_score is the final percentage (0–100).
- technical_score, communication_score, confidence_score, behavioral_score are also 0–100.
- Score strictly.
- Never hallucinate knowledge.
- Evaluate only what the candidate actually said.
- Provide clear strengths and improvements.
- Every question must have its own evaluation entry.

BEGIN NOW.
"""

        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Return ONLY JSON."},
                {"role": "user", "content": prompt},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=2000,
        )

        text = chat_completion.choices[0].message.content.strip()
        text = self._clean_json(text)
        data = json.loads(text)

        return Evaluation(
            scores=EvaluationScore(**self._normalize_scores(data.get("scores", {}))),
            sentiment=SentimentAnalysis(**self._normalize_sentiment(data.get("sentiment", {}))),
            strengths=data.get("strengths", []),
            improvements=data.get("improvements", []),
            detailed_feedback=data.get("detailed_feedback", ""),
            question_scores=data.get("question_scores", []),
        )

    # ==========================================================
    # JSON SANITIZER
    # ==========================================================
    def _clean_json(self, text: str) -> str:
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    # ==========================================================
    # NORMALIZERS
    # ==========================================================
    def _normalize_scores(self, raw: Dict) -> Dict:
        def to_f(v):
            try:
                if isinstance(v, str):
                    v = float(v)
                return float(v)
            except:
                return 0.0

        raw_vals = [
            to_f(raw.get("overall_score", 0)),
            to_f(raw.get("technical_score", 0)),
            to_f(raw.get("communication_score", 0)),
            to_f(raw.get("confidence_score", 0)),
            to_f(raw.get("behavioral_score", 0)),
        ]

    # Detect "0–10" style scoring and scale up
        max_val = max(raw_vals) if raw_vals else 0
        scale = 10 if 0 < max_val <= 10 else 1

        def norm(v):
            v = to_f(v) * scale
            return max(0, min(100, int(round(v))))

        return {
            "overall_score": norm(raw.get("overall_score", 0)),
            "technical_score": norm(raw.get("technical_score", 0)),
            "communication_score": norm(raw.get("communication_score", 0)),
            "confidence_score": norm(raw.get("confidence_score", 0)),
            "behavioral_score": norm(raw.get("behavioral_score", 0)),
        }

    def _normalize_sentiment(self, raw: Dict) -> Dict:
        try:
            pos = float(raw.get("positive", 0))
            neu = float(raw.get("neutral", 0))
            neg = float(raw.get("negative", 0))
        except:
            pos, neu, neg = 0, 0, 0

        total = pos + neu + neg or 1
        return {
            "positive": round(pos / total, 2),
            "neutral": round(neu / total, 2),
            "negative": round(neg / total, 2),
        }

    # ==========================================================
    # BASIC FALLBACK
    # ==========================================================
    def _create_basic_evaluation(self, conversation, questions) -> Evaluation:
        candidate_msgs = [m for m in conversation if getattr(m, "speaker", "") == "candidate"]
        count = len(candidate_msgs)
        avg_len = sum(len(m.text) for m in candidate_msgs) / max(1, count)

        base = min(100, int(count * 15 + avg_len / 50))

        return Evaluation(
            scores=EvaluationScore(
                overall_score=base,
                technical_score=base,
                communication_score=min(100, int(avg_len / 20)),
                confidence_score=base,
                behavioral_score=base,
            ),
            sentiment=SentimentAnalysis(positive=0.6, neutral=0.3, negative=0.1),
            strengths=["Good participation"],
            improvements=["Add more depth in answers"],
            detailed_feedback="Fallback evaluation (Groq unavailable).",
            question_scores=[],
        )

    # ==========================================================
    # SINGLE ANSWER EVALUATION
    # ==========================================================
    async def evaluate_single_answer(
        self,
        question: str,
        answer: str,
        expected_topics: List[str]
    ) -> Dict:

        if not self.client:
            return {"score": 70, "feedback": "Groq unavailable — basic score only."}

        prompt = f"""
You are a senior technical interviewer.
Evaluate this single answer with high precision.

==========================
QUESTION
==========================
{question}

EXPECTED TOPICS:
{', '.join(expected_topics)}

==========================
ANSWER
==========================
{answer}

==========================
EVALUATION RULES
==========================
- Score only what the candidate said.
- No assumptions, no hallucinations.
- Strict topic coverage check.
- Penalize vagueness, incorrect info, or generic answers.
- Reward clarity, accuracy, structure, reasoning, and depth.

Return ONLY JSON exactly matching this structure:
{self.SINGLE_QA_TEMPLATE}

BEGIN.
"""

        chat = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Return ONLY JSON."},
                {"role": "user", "content": prompt},
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=400,
        )

        raw = self._clean_json(chat.choices[0].message.content)
        return json.loads(raw)
