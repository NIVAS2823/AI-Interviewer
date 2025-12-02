from typing import Optional
from fastapi import Depends, HTTPException, status, WebSocket, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from bson import ObjectId

from app.core.security import decode_access_token
from app.core.database import get_database
from app.models.user import UserModel
from app.core.config import settings


# ------------------------------------------------------------
# HTTP TOKEN AUTH
# ------------------------------------------------------------
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_database)
) -> UserModel:
    """
    Standard HTTP authentication using Bearer token.
    Used for all REST API routes.
    """
    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)
    user_id: str = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user
    user_dict = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check active
    if not user_dict.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return UserModel(**user_dict)


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """Ensure the user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# ------------------------------------------------------------
# ROLE-BASED AUTH
# ------------------------------------------------------------
async def require_role(required_role: str):
    """
    Check if the current user has given role OR admin.
    """
    async def role_checker(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires '{required_role}' role"
            )
        return current_user

    return role_checker


# ------------------------------------------------------------
# WEBSOCKET TOKEN AUTH
# ------------------------------------------------------------
async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    Authenticate WebSocket connection using JWT token passed in URL:

    ws://host/ws/interview?token=JWT_HERE

    Returns user_id (str) or None.
    DOES NOT close the websocket — caller must handle that.
    """
    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")

        if not user_id:
            return None

        return user_id

    except JWTError:
        return None
