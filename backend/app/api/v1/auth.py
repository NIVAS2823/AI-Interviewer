from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user import (
    UserRegisterSchema,
    UserLoginSchema,
    UserResponseSchema,
    TokenSchema
)
from app.models.user import UserModel
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.database import get_database
from app.core.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    InactiveUserException
)
from bson import ObjectId
from datetime import datetime

import logging

logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/register", response_model=TokenSchema, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterSchema,
    db = Depends(get_database)
):
    """
    Register a new user
    
    - **email**: Valid email address (must be unique)
    - **name**: Full name (2-100 characters, letters and spaces only)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit)
    - **role**: User role (job_seeker or hr_professional)
    
    Returns JWT token and user data
    """
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email.lower()})
    if existing_user:
        raise UserAlreadyExistsException(user_data.email)
    
    # Create user document
    user_dict = {
        "email": user_data.email.lower(),
        "name": user_data.name,
        "hashed_password": get_password_hash(user_data.password),
        "role": user_data.role,
        "is_active": True,
        "email_verified": False,
        "profile": None,
        "subscription": {
            "plan": "free",
            "interviews_remaining": 3,
            "expires_at": None
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    # Insert user into database
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    # Create user model
    user = UserModel(**user_dict)
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    # Prepare user response
    user_response = UserResponseSchema(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        profile=user.profile,
        subscription=user.subscription,
        created_at=user.created_at
    )
    
    return TokenSchema(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post("/login", response_model=TokenSchema)
async def login(
    credentials: UserLoginSchema,
    db = Depends(get_database)
):
    """
    Authenticate user and return JWT token
    
    - **email**: User email address
    - **password**: User password
    
    Returns JWT token and user data
    """
    
    # Find user by email
    user_dict = await db.users.find_one({"email": credentials.email.lower()})
    
    if not user_dict:
        raise InvalidCredentialsException()
    
    # Verify password
    if not verify_password(credentials.password, user_dict["hashed_password"]):
        raise InvalidCredentialsException()
    
    # Check if user is active
    if not user_dict.get("is_active", True):
        raise InactiveUserException()
    
    # Create user model
    try:
        user = UserModel(**user_dict)
    except Exception as e:
        logger.exception("❌ Failed to parse UserModel from DB: %s", e)
        raise HTTPException(status_code=500, detail="Internal user parsing error")
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    # Prepare user response
    user_response = UserResponseSchema(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        profile=user.profile,
        subscription=user.subscription,
        created_at=user.created_at
    )
    
    return TokenSchema(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.get("/me", response_model=UserResponseSchema)
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get current authenticated user information
    
    Requires: Valid JWT token in Authorization header
    
    Returns current user data
    """
    
    return UserResponseSchema(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        profile=current_user.profile,
        subscription=current_user.subscription,
        created_at=current_user.created_at
    )