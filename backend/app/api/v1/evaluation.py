from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from typing import Dict
import logging

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
    """Request to evaluate a single answer"""
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
    Get evaluation for completed interview.
    """

    if not ObjectId.is_valid(interview_id):
        raise HTTPException(400, "Invalid interview ID")

    # Ownership check
    interview = await db.interviews.find_one(
        {"_id": ObjectId(interview_id), "candidate_id": current_user.id}
    )

    if not interview:
        raise HTTPException(404, "Interview not found")

    evaluation = interview.get("evaluation")

    if not evaluation:
        raise HTTPException(
            404,
            "Evaluation not yet available. Complete the interview first."
        )

    return Evaluation(**evaluation)


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
