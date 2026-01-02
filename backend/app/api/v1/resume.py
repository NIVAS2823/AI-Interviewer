from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from typing import List
from bson import ObjectId
from datetime import datetime
import logging

from app.schemas.resume import (
    ResumeUploadResponse,
    ResumeDetailResponse,
    ResumeListResponse
)
from app.models.user import UserModel
from app.models.resume import ResumeModel
from app.core.database import get_database
from app.core.deps import get_current_user
from app.utils.file_handler import FileHandler
from app.services.resume_parser import ResumeParserService

logger = logging.getLogger(__name__)

router = APIRouter()
file_handler = FileHandler()
parser_service = ResumeParserService()


async def process_resume_parsing(resume_id: str, file_path: str, db):
    """
    Background task to parse resume (FastAPI BackgroundTasks)
    """
    try:
        logger.info(f"🧠 Background parsing started for resume {resume_id}")

        # Mark as processing
        await db.resumes.update_one(
            {"_id": ObjectId(resume_id)},
            {"$set": {"parsing_status": "processing"}}
        )

        # Parse resume (AI or fallback)
        parsed_data = await parser_service.parse_resume(file_path)

        # ⚠️ IMPORTANT:
        # completeness_score is ALREADY calculated inside parse_resume()
        completeness_score = parsed_data.completeness_score

        # Persist parsed data
        await db.resumes.update_one(
            {"_id": ObjectId(resume_id)},
            {
                "$set": {
                    "parsed_data": parsed_data.model_dump(),
                    "completeness_score": completeness_score,
                    "parsing_status": "completed",
                    "parsed_at": datetime.utcnow()
                }
            }
        )

        logger.info(
            f"✅ Resume {resume_id} parsed successfully | Score={completeness_score}/100"
        )

    except Exception as e:
        logger.exception(f"❌ Resume parsing failed for {resume_id}")

        await db.resumes.update_one(
            {"_id": ObjectId(resume_id)},
            {
                "$set": {
                    "parsing_status": "failed",
                    "parsing_error": str(e),
                    "updated_at": datetime.utcnow()
                }
            }
        )


@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    db = Depends(get_database)
):
    """
    Upload resume PDF and trigger background parsing
    """

    # Validate file
    file_handler.validate_file_type(file)

    # Save file
    file_path, file_size = await file_handler.save_upload_file(
        file,
        str(current_user.id)
    )

    # Create DB record
    resume_doc = {
        "user_id": current_user.id,
        "file_name": file.filename,
        "file_path": file_path,
        "file_size": file_size,
        "mime_type": file.content_type,
        "parsed_data": None,
        "completeness_score": 0,
        "parsing_status": "pending",
        "uploaded_at": datetime.utcnow()
    }

    result = await db.resumes.insert_one(resume_doc)
    resume_id = str(result.inserted_id)

    # Fire background parsing
    background_tasks.add_task(
        process_resume_parsing,
        resume_id,
        file_path,
        db
    )

    logger.info(f"📄 Resume uploaded: {resume_id}")

    return ResumeUploadResponse(
        id=resume_id,
        file_name=file.filename,
        file_size=file_size,
        parsing_status="pending",
        message="Resume uploaded successfully. Parsing in progress...",
        uploaded_at=resume_doc["uploaded_at"]
    )


@router.get("/", response_model=List[ResumeListResponse])
async def list_resumes(
    current_user: UserModel = Depends(get_current_user),
    db = Depends(get_database)
):
    """List all resumes for current user"""

    cursor = db.resumes.find(
        {"user_id": current_user.id}
    ).sort("uploaded_at", -1)

    resumes = await cursor.to_list(length=100)

    return [
        ResumeListResponse(
            id=str(resume["_id"]),
            file_name=resume["file_name"],
            completeness_score=resume.get("completeness_score", 0),
            parsing_status=resume.get("parsing_status", "pending"),
            uploaded_at=resume["uploaded_at"]
        )
        for resume in resumes
    ]


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume(
    resume_id: str,
    current_user: UserModel = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get resume details"""

    if not ObjectId.is_valid(resume_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resume ID"
        )

    resume = await db.resumes.find_one({
        "_id": ObjectId(resume_id),
        "user_id": current_user.id
    })

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    return ResumeDetailResponse(
        id=str(resume["_id"]),
        user_id=str(resume["user_id"]),
        file_name=resume["file_name"],
        file_size=resume["file_size"],
        parsed_data=resume.get("parsed_data"),
        completeness_score=resume.get("completeness_score", 0),
        parsing_status=resume.get("parsing_status", "pending"),
        uploaded_at=resume["uploaded_at"],
        parsed_at=resume.get("parsed_at")
    )


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    current_user: UserModel = Depends(get_current_user),
    db = Depends(get_database)
):
    """Delete resume and file"""

    if not ObjectId.is_valid(resume_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resume ID"
        )

    resume = await db.resumes.find_one({
        "_id": ObjectId(resume_id),
        "user_id": current_user.id
    })

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    await file_handler.delete_file(resume["file_path"])
    await db.resumes.delete_one({"_id": ObjectId(resume_id)})

    logger.info(f"🗑️ Resume deleted: {resume_id}")
    return None
