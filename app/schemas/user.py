
"""
Pydantic schemas for User model.
Request/response validation for user-related endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid


# Base schema with common fields
class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=100)
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "john.doe@example.com",
                    "username": "johndoe",
                    "password": "securepass123",
                    "full_name": "John Doe"
                }
            ]
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)


class UserUpdatePassword(BaseModel):
    """Schema for password update."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserInDB(UserBase):
    """Schema for user as stored in database."""
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserInDB):
    """Schema for user in API responses (public profile; no admin flag)."""
    pass


class UserMeResponse(UserResponse):
    """Schema for the authenticated user's own profile."""
    is_admin: bool = False


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "johndoe",
                    "password": "securepass123"
                }
            ]
        }
    )


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordReset(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class EmailVerificationRequest(BaseModel):
    """Schema for email verification."""
    token: str


class ResendVerificationRequest(BaseModel):
    """Schema for resending verification email."""
    email: EmailStr