from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from typing import Dict, List
from datetime import datetime as dt
import asyncio
import logging

from app.models.user import UserModel
from app.models.interview import Evaluation, ConversationMessage, Question
from app.core.database import get_database
from app.core.deps import get_current_user
from app.services.evaluation_service import EvaluationService
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

evaluation_service = EvaluationService()


class SingleAnswerEvaluationRequest(BaseModel):
    question: str
    answer: str
    expected_topics: List[str] = []


# ------------------------------------------------------------
# Utility: Build zero-evaluation object
# ------------------------------------------------------------
def build_zero_evaluation(reason: str):
    return {
        "scores": {
            "overall_score": 0,
            "technical_score": 0,
            "communication_score": 0,
            "confidence_score": 0,
            "behavioral_score": 0,
        },
        "sentiment": {"positive": 0.0, "neutral": 1.0, "negative": 0.0},
        "strengths": [],
        "improvements": [reason],
        "detailed_feedback": reason,
        "question_scores": [],
    }


# ------------------------------------------------------------
# MAIN EVALUATION ENDPOINT
# ------------------------------------------------------------
@router.get("/{interview_id}", response_model=Evaluation)
async def get_evaluation(
    interview_id: str,
    current_user: UserModel = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    Returns the evaluation for a completed interview.
    Handles all worst-case scenarios gracefully:
    - Candidate answered nothing
    - Evaluation requested before DB sync
    - Missing/partial data
    - Internal evaluation failure
    - Corrupted stored evaluation
    """

    if not ObjectId.is_valid(interview_id):
        raise HTTPException(status_code=400, detail="Invalid interview ID")

    # Security check
    interview = await db.interviews.find_one(
        {"_id": ObjectId(interview_id), "candidate_id": current_user.id}
    )

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    status_flag = interview.get("status")
    stored_eval = interview.get("evaluation")

    # ------------------------------------------------------------
    # CASE 1: Evaluation exists → return safely
    # ------------------------------------------------------------
    if stored_eval:
        try:
            return Evaluation(**stored_eval)
        except Exception:
            logger.error("Corrupted stored evaluation → repairing structure")
            return Evaluation(
                scores=stored_eval.get("scores", {}),
                sentiment=stored_eval.get("sentiment"),
                strengths=stored_eval.get("strengths", []),
                improvements=stored_eval.get("improvements", []),
                detailed_feedback=stored_eval.get("detailed_feedback", ""),
                question_scores=stored_eval.get("question_scores", []),
            )

    # ------------------------------------------------------------
    # CASE 2: Interview not completed → cannot evaluate
    # ------------------------------------------------------------
    if status_flag != "completed":
        raise HTTPException(
            status_code=404,
            detail="Evaluation not yet available. Complete the interview first.",
        )

    # ------------------------------------------------------------
    # CASE 3: Evaluation missing but interview completed → generate now
    # Handles:
    # - DB still saving transcript
    # - Slow writes due to TTS/R2 upload
    # ------------------------------------------------------------

    MAX_RETRIES = 3
    WAIT_TIME = 1.2

    for attempt in range(MAX_RETRIES):
        # Reload fresh DB state
        interview = await db.interviews.find_one({"_id": ObjectId(interview_id)})
        conversation = interview.get("conversation", [])
        questions = interview.get("questions", [])

        candidate_msgs = [m for m in conversation if m.get("speaker") == "candidate"]

        # CASE A: Candidate answered nothing → early exit with clean zero-eval
        if len(candidate_msgs) == 0:
            reason = "Candidate did not answer any questions."
            logger.info(f"[Evaluation] No answers for interview {interview_id} → zero eval")
            zero_eval = build_zero_evaluation(reason)

            await db.interviews.update_one(
                {"_id": ObjectId(interview_id)},
                {"$set": {"evaluation": zero_eval, "updated_at": dt.utcnow()}},
            )

            return Evaluation(**zero_eval)

        # CASE B: Conversation or questions incomplete → wait & retry
        if (len(conversation) == 0 or len(questions) == 0) and attempt < MAX_RETRIES - 1:
            logger.warning(
                f"[Evaluation] Data incomplete (attempt {attempt+1}) → retrying..."
            )
            await asyncio.sleep(WAIT_TIME)
            continue

        # CASE C: Still empty after retries → fallback zero-eval
        if (len(conversation) == 0 or len(questions) == 0):
            logger.error(
                f"[Evaluation] Data still incomplete after retries → fallback."
            )
            zero_eval = build_zero_evaluation("Incomplete interview data.")
            await db.interviews.update_one(
                {"_id": ObjectId(interview_id)},
                {"$set": {"evaluation": zero_eval, "updated_at": dt.utcnow()}},
            )
            return Evaluation(**zero_eval)

        # ------------------------------------------------------------
        # CASE D: Data valid → run real evaluation
        # ------------------------------------------------------------

        try:
            conv_objs = [ConversationMessage(**m) for m in conversation]
            q_objs = [Question(**q) for q in questions]

            evaluation = await evaluation_service.evaluate_interview(
                conv_objs,
                q_objs,
                interview.get("interview_type", "mixed"),
                interview.get("difficulty", "medium"),
            )

            await db.interviews.update_one(
                {"_id": ObjectId(interview_id)},
                {"$set": {"evaluation": evaluation.dict(), "updated_at": dt.utcnow()}},
            )

            logger.info(f"[Evaluation] Successfully generated for {interview_id}")
            return evaluation

        except Exception as e:
            logger.exception(f"[Evaluation] Evaluation failed → fallback used: {e}")

            zero_eval = build_zero_evaluation("Evaluation failed due to system error.")

            await db.interviews.update_one(
                {"_id": ObjectId(interview_id)},
                {"$set": {"evaluation": zero_eval, "updated_at": dt.utcnow()}},
            )
            return Evaluation(**zero_eval)

    # Should never reach here
    raise HTTPException(status_code=500, detail="Unexpected evaluation error.")


# ------------------------------------------------------------
# SINGLE ANSWER EVALUATION
# ------------------------------------------------------------
@router.post("/evaluate-answer", response_model=Dict)
async def evaluate_single_answer(
    request: SingleAnswerEvaluationRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Real-time evaluation of one question-answer pair."""
    result = await evaluation_service.evaluate_single_answer(
        question=request.question,
        answer=request.answer,
        expected_topics=request.expected_topics,
    )
    return result
