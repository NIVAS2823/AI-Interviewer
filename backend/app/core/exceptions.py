from fastapi import HTTPException, status


class UserAlreadyExistsException(HTTPException):
    """Exception raised when user already exists"""
    
    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{email}' already exists"
        )


class UserNotFoundException(HTTPException):
    """Exception raised when user is not found"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


class InvalidCredentialsException(HTTPException):
    """Exception raised when credentials are invalid"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )


class InactiveUserException(HTTPException):
    """Exception raised when user account is inactive"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )


class UnauthorizedException(HTTPException):
    """Exception raised when user is not authorized"""
    
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )