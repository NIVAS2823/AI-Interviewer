from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from typing import List
from bson import ObjectId
from datetime import datetime

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


router = APIRouter()
file_handler = FileHandler()
parser_service = ResumeParserService()


async def process_resume_parsing(resume_id: str, file_path: str, db):
    """
    Background task to parse resume (NO CELERY NEEDED!)
    Uses FastAPI BackgroundTasks - completely free
    """
    try:
        # Update status
        await db.resumes.update_one(
            {"_id": ObjectId(resume_id)},
            {"$set": {"parsing_status": "processing"}}
        )
        
        # Parse resume with Groq AI (FREE)
        parsed_data = await parser_service.parse_resume(file_path)
        
        # Calculate score
        completeness_score = parser_service.calculate_completeness_score(parsed_data)
        
        # Update database
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
        
        print(f"✅ Resume {resume_id} parsed. Score: {completeness_score}")
        
    except Exception as e:
        print(f"❌ Parsing error: {e}")
        await db.resumes.update_one(
            {"_id": ObjectId(resume_id)},
            {
                "$set": {
                    "parsing_status": "failed",
                    "parsing_error": str(e)
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
    Upload resume PDF
    
    - Validates PDF file
    - Saves to local storage
    - Triggers background parsing (Groq AI)
    - Returns immediately (async processing)
    """
    
    # Validate file
    file_handler.validate_file_type(file)
    
    # Save file
    file_path, file_size = await file_handler.save_upload_file(file, str(current_user.id))
    
    # Create resume document
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
    
    # Add background task for parsing (FREE - no Celery needed)
    background_tasks.add_task(process_resume_parsing, resume_id, file_path, db)
    
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
    """Get all resumes for current user"""
    
    cursor = db.resumes.find({"user_id": current_user.id}).sort("uploaded_at", -1)
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
    """Get detailed resume with parsed data"""
    
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
    """Delete resume and associated file"""
    
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
    
    # Delete file from storage
    await file_handler.delete_file(resume["file_path"])
    
    # Delete from database
    await db.resumes.delete_one({"_id": ObjectId(resume_id)})
    
    return None