from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from typing import Dict
import logging
from datetime import datetime as dt  # <-- FIXED

from app.models.user import UserModel
from app.models.interview import Evaluation
from app.core.database import get_database
from app.core.deps import get_current_user
from app.services.evaluation_service import EvaluationService
from pydantic import BaseModel

router = APIRouter()
evaluation_service = EvaluationService()
logger = logging.getLogger(__name__)


class SingleAnswerEvaluationRequest(BaseModel):
    question: str
    answer: str
    expected_topics: list[str] = []


@router.get("/{interview_id}", response_model=Evaluation)
async def get_evaluation(
    interview_id: str,
    current_user: UserModel = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Return interview evaluation.
    Never returns 404 if interview is completed.
    """

    if not ObjectId.is_valid(interview_id):
        raise HTTPException(status_code=400, detail="Invalid interview ID")

    # Authorization
    interview = await db.interviews.find_one(
        {"_id": ObjectId(interview_id), "candidate_id": current_user.id}
    )

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    status_flag = interview.get("status")
    evaluation = interview.get("evaluation")

    # -------------------------------
    # CASE 1: Evaluation exists
    # -------------------------------
    if evaluation:
        try:
            return Evaluation(**evaluation)
        except Exception:
            # Stored eval corrupted → recover by wrapping
            logger.error("Corrupted evaluation, repairing...")
            safe = Evaluation(
                scores=evaluation.get("scores", {}),
                sentiment=evaluation.get("sentiment"),
                strengths=evaluation.get("strengths", []),
                improvements=evaluation.get("improvements", []),
                detailed_feedback=evaluation.get("detailed_feedback", ""),
                question_scores=evaluation.get("question_scores", []),
            )
            return safe

    # -------------------------------------------------------
    # CASE 2: Interview completed but evaluation missing → FIX
    # -------------------------------------------------------
    if status_flag == "completed":
        logger.warning(
            f"Missing evaluation for completed interview {interview_id}, creating fallback zero-eval."
        )

        zero_eval = {
            "scores": {
                "overall_score": 0,
                "technical_score": 0,
                "communication_score": 0,
                "confidence_score": 0,
                "behavioral_score": 0,
            },
            "sentiment": {"positive": 0.0, "neutral": 1.0, "negative": 0.0},
            "strengths": [],
            "improvements": ["Candidate did not answer any questions."],
            "detailed_feedback": "Interview ended without any candidate responses.",
            "question_scores": [],
        }

        # Persist fallback evaluation
        try:
            await db.interviews.update_one(
                {"_id": ObjectId(interview_id)},
                {"$set": {"evaluation": zero_eval, "updated_at": dt.utcnow()}}  # <-- FIXED
            )
        except Exception:
            logger.exception("Failed to persist fallback evaluation")

        return Evaluation(**zero_eval)

    # -------------------------------------------------------
    # CASE 3: Interview not completed → legit 404
    # -------------------------------------------------------
    raise HTTPException(
        status_code=404,
        detail="Evaluation not yet available. Complete the interview first."
    )


@router.post("/evaluate-answer", response_model=Dict)
async def evaluate_single_answer(
    request: SingleAnswerEvaluationRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Real-time single question-answer evaluation.
    """
    result = await evaluation_service.evaluate_single_answer(
        question=request.question,
        answer=request.answer,
        expected_topics=request.expected_topics
    )

    return result
