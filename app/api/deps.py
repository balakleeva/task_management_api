"""
FastAPI dependencies for dependency injection.
Provides database sessions, current user authentication, etc.
"""

from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from app.database import AsyncSessionLocal
from app.core.security import verify_token, ACCESS_TOKEN_TYPE
from app.core.exceptions import AuthenticationError, InactiveUserError, UnverifiedUserError
from app.models.user import User
from app.repositories.user_repository import user_repository
import uuid

# HTTPBearer for token authentication (shows "Authorize" button in Swagger)
security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides database session.
    
    Yields:
        AsyncSession: Database session
        
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            # Use db here
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
        finally:
            await session.close()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency that gets current authenticated user from JWT token.
    
    Args:
        db: Database session
        credentials: HTTPBearer credentials with token
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
        
    Usage:
        @app.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract token from credentials
        token = credentials.credentials
        
        # Verify token and extract user_id
        user_id_str = verify_token(token, ACCESS_TOKEN_TYPE)
        
        if user_id_str is None:
            raise credentials_exception
        
        user_id = uuid.UUID(user_id_str)
        
    except (JWTError, ValueError, AttributeError):
        raise credentials_exception
    
    # Get user from database
    user = await user_repository.get(db, user_id)
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency that ensures current user is active.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Active user
        
    Raises:
        HTTPException: If user is inactive
        
    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_active_user)):
            # User is guaranteed to be active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency that ensures current user is verified.
    
    Args:
        current_user: Current active user
        
    Returns:
        Verified user
        
    Raises:
        HTTPException: If user email is not verified
        
    Usage:
        @app.get("/verified-only")
        async def verified_route(user: User = Depends(get_current_verified_user)):
            # User is guaranteed to be verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email to access this resource."
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency that ensures current user is an administrator.

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# Optional: Dependency that allows unauthenticated access but provides user if authenticated
async def get_current_user_optional(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """
    Dependency that optionally gets current user.
    Returns None if no valid token provided.
    
    Args:
        db: Database session
        credentials: Optional HTTPBearer credentials
        
    Returns:
        User if authenticated, None otherwise
        
    Usage:
        @app.get("/public-but-personalized")
        async def public_route(user: Optional[User] = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Hello {user.username}"}
            return {"message": "Hello guest"}
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user_id_str = verify_token(token, ACCESS_TOKEN_TYPE)
        if user_id_str is None:
            return None
        
        user_id = uuid.UUID(user_id_str)
        user = await user_repository.get(db, user_id)
        return user
        
    except (JWTError, ValueError, AttributeError):
        return None