# app/apis/interview.py
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from datetime import datetime
from typing import List, Optional
import logging

from app.schemas.interview import (
    InterviewCreateRequest,
    InterviewCreateResponse,
    InterviewDetailResponse,
    InterviewListResponse,
    InterviewEndRequest,
    InterviewEndResponse,
)
from app.schemas.interview_message import (
    InterviewMessageRequest,
    InterviewMessageResponse,
)
from app.models.user import UserModel
from app.models.interview import InterviewModel
from app.core.database import get_database
from app.core.deps import get_current_user
from app.services.interview_engine import InterviewEngineService

router = APIRouter()
interview_engine = InterviewEngineService()
logger = logging.getLogger(__name__)


# --------------------------------------------------------
# Create Interview
# --------------------------------------------------------
@router.post("/create", response_model=InterviewCreateResponse, status_code=201)
async def create_interview(
    request: InterviewCreateRequest,
    current_user: UserModel = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    Create a new interview session. This will:
      - validate resume ownership & parsing status
      - generate questions
      - create a VideoSDK meeting + AI avatar agent (when possible)
      - persist interview document and return meeting credentials
    """

    # Validate resume ownership and parsing status
    resume = await db.resumes.find_one(
        {"_id": ObjectId(request.resume_id), "user_id": current_user.id}
    )

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found or unauthorized")

    if resume.get("parsing_status") != "completed":
        raise HTTPException(status_code=400, detail="Resume is still being parsed")

    # Create interview
    try:
        interview: InterviewModel = await interview_engine.create_interview(
            candidate_id=str(current_user.id),
            resume_id=request.resume_id,
            interview_type=request.interview_type,
            difficulty=request.difficulty,
            max_questions=request.max_questions,
            job_description=request.job_description,
            db=db,
        )

        first_question = (
            interview.questions[0].question_text if interview.questions else "Tell me about yourself"
        )

        return InterviewCreateResponse(
            interview_id=str(interview.id),
            meeting_id=interview.session_id,
            meeting_token=interview.meeting_token,
            agent_id=interview.agent_id,
            questions=interview.questions,
            first_question=first_question,
            status=interview.status,
            message="Interview created successfully",
            created_at=interview.created_at,
        )

    except Exception as e:
        logger.exception("Interview creation failed")
        raise HTTPException(status_code=500, detail=f"Failed to create interview: {e}")


# --------------------------------------------------------
# List Interviews
# --------------------------------------------------------
@router.get("/", response_model=List[InterviewListResponse])
async def list_interviews(
    current_user: UserModel = Depends(get_current_user), db=Depends(get_database)
):
    """
    Return list of interviews for the current user.
    """
    cursor = db.interviews.find({"candidate_id": current_user.id}).sort("created_at", -1)
    interviews = await cursor.to_list(100)

    return [
        InterviewListResponse(
            id=str(i["_id"]),
            interview_type=i.get("interview_type", "mixed"),
            status=i.get("status"),
            overall_score=(
                i.get("evaluation", {}).get("scores", {}).get("overall_score")
                if i.get("evaluation")
                else None
            ),
            created_at=i["created_at"],
            duration_minutes=i.get("duration_minutes"),
        )
        for i in interviews
    ]


# --------------------------------------------------------
# Get Interview Details
# --------------------------------------------------------
@router.get("/{interview_id}", response_model=InterviewDetailResponse)
async def get_interview(
    interview_id: str,
    current_user: UserModel = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    Return full interview details including meeting credentials (if any),
    questions, conversation, evaluation and timing metadata.
    """
    if not ObjectId.is_valid(interview_id):
        raise HTTPException(status_code=400, detail="Invalid interview ID")

    interview = await db.interviews.find_one(
        {"_id": ObjectId(interview_id), "candidate_id": current_user.id}
    )

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Build response - include meeting/session credentials so frontend can join room
    return InterviewDetailResponse(
        id=str(interview["_id"]),
        candidate_id=str(interview["candidate_id"]),
        resume_id=str(interview["resume_id"]) if interview.get("resume_id") else None,
        job_description=interview.get("job_description"),
        interview_type=interview.get("interview_type"),
        difficulty=interview.get("difficulty"),
        max_questions=interview.get("max_questions", 5),   # ✅ REQUIRED FIX
        status=interview.get("status"),
        questions=interview.get("questions", []),
        conversation=interview.get("conversation", []),
        evaluation=interview.get("evaluation"),
        session_id=interview.get("session_id"),
        meeting_token=interview.get("meeting_token"),
        agent_id=interview.get("agent_id"),
        start_time=interview.get("start_time"),
        end_time=interview.get("end_time"),
        duration_minutes=interview.get("duration_minutes"),
        created_at=interview["created_at"],
        )



# --------------------------------------------------------
# Start Interview
# --------------------------------------------------------
@router.post("/{interview_id}/start")
async def start_interview(
    interview_id: str,
    current_user: UserModel = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    Start the interview — activate the AI agent (if applicable) and set status to in_progress.
    """
    if not ObjectId.is_valid(interview_id):
        raise HTTPException(status_code=400, detail="Invalid interview ID")

    interview = await db.interviews.find_one(
        {"_id": ObjectId(interview_id), "candidate_id": current_user.id}
    )

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.get("status") != "created":
        raise HTTPException(status_code=400, detail=f"Interview already {interview.get('status')}")

    try:
        updated = await interview_engine.start_interview(interview_id, db)
        return {
            "message": "Interview started",
            "interview_id": str(updated.id),
            "status": updated.status,
            "start_time": updated.start_time,
            "session_id": updated.session_id,
            "agent_id": updated.agent_id,
        }
    except Exception as e:
        logger.exception("Failed to start interview")
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {e}")


# --------------------------------------------------------
# End Interview
# --------------------------------------------------------
@router.post("/{interview_id}/end", response_model=InterviewEndResponse)
async def end_interview(
    interview_id: str,
    request: InterviewEndRequest = InterviewEndRequest(),
    current_user: UserModel = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    End interview, retrieve transcript, run evaluation and persist results.
    Returns evaluation object (if generated).
    """
    if not ObjectId.is_valid(interview_id):
        raise HTTPException(status_code=400, detail="Invalid interview ID")

    interview = await db.interviews.find_one(
        {"_id": ObjectId(interview_id), "candidate_id": current_user.id}
    )

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.get("status") not in ["created", "in_progress"]:
        raise HTTPException(
            status_code=400, detail=f"Interview cannot be ended from state: {interview.get('status')}"
        )

    try:
        updated = await interview_engine.end_interview(interview_id, db)

        return InterviewEndResponse(
            interview_id=str(updated.id),
            status=updated.status,
            evaluation=updated.evaluation,
            message="Interview ended. Evaluation generated.",
        )
    except Exception as e:
        logger.exception("Failed to end interview")
        raise HTTPException(status_code=500, detail=f"Failed to end interview: {e}")


# --------------------------------------------------------
# Add Message & AI reply
# --------------------------------------------------------
@router.post("/{interview_id}/message", response_model=InterviewMessageResponse)
async def send_message(
    interview_id: str,
    request: InterviewMessageRequest,
    current_user: UserModel = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    Append a candidate message to conversation and generate AI reply via engine.
    This is a fallback if the real-time VideoSDK agent is not used.
    """
    if not ObjectId.is_valid(interview_id):
        raise HTTPException(status_code=400, detail="Invalid interview ID")

    interview = await db.interviews.find_one(
        {"_id": ObjectId(interview_id), "candidate_id": current_user.id}
    )

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.get("status") != "in_progress":
        raise HTTPException(status_code=400, detail="Interview must be in progress")

    # Save candidate message
    candidate_msg = {"speaker": "candidate", "text": request.text, "timestamp": datetime.utcnow()}
    await db.interviews.update_one(
        {"_id": ObjectId(interview_id)},
        {"$push": {"conversation": candidate_msg}, "$set": {"updated_at": datetime.utcnow()}},
    )

    # Ensure engine provides an AI-reply generator (fallback mode)
    if not hasattr(interview_engine, "generate_ai_reply"):
        logger.error("AI reply generator not implemented in interview engine")
        raise HTTPException(status_code=500, detail="AI reply generator not implemented")

    try:
        ai_text = await interview_engine.generate_ai_reply(interview_id, request.text, db)

        ai_msg = {"speaker": "ai", "text": ai_text, "timestamp": datetime.utcnow()}
        await db.interviews.update_one(
            {"_id": ObjectId(interview_id)},
            {"$push": {"conversation": ai_msg}, "$set": {"updated_at": datetime.utcnow()}},
        )

        return InterviewMessageResponse(ai_text=ai_text, timestamp=ai_msg["timestamp"])
    except Exception as e:
        logger.exception("Failed to generate AI reply")
        raise HTTPException(status_code=500, detail=f"Failed to generate reply: {e}")


# --------------------------------------------------------
# Delete Interview
# --------------------------------------------------------
@router.delete("/{interview_id}", status_code=204)
async def delete_interview(
    interview_id: str, current_user: UserModel = Depends(get_current_user), db=Depends(get_database)
):
    if not ObjectId.is_valid(interview_id):
        raise HTTPException(status_code=400, detail="Invalid interview ID")

    interview = await db.interviews.find_one(
        {"_id": ObjectId(interview_id), "candidate_id": current_user.id}
    )

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.get("status") == "in_progress":
        raise HTTPException(status_code=400, detail="Cannot delete an active interview")

    await db.interviews.delete_one({"_id": ObjectId(interview_id)})
    return None


# --------------------------------------------------------
# Simulate Conversation
# --------------------------------------------------------
@router.post("/{interview_id}/simulate")
async def simulate_interview(
    interview_id: str, current_user: UserModel = Depends(get_current_user), db=Depends(get_database)
):
    if not ObjectId.is_valid(interview_id):
        raise HTTPException(status_code=400, detail="Invalid interview ID")

    interview = await db.interviews.find_one(
        {"_id": ObjectId(interview_id), "candidate_id": current_user.id}
    )

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    ok = await interview_engine.simulate_interview_conversation(interview_id, db)
    if not ok:
        raise HTTPException(status_code=500, detail="Simulation failed")

    return {"message": "Conversation simulated. You can now end the interview.", "interview_id": interview_id}
