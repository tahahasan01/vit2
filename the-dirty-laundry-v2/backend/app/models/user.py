"""
User & consent schemas.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ConsentPayload(BaseModel):
    """User must accept before first VTO use."""

    consent_given: bool = Field(
        ...,
        description="User consents to AI processing of their images",
    )
    privacy_acknowledged: bool = Field(
        ...,
        description="User has read and acknowledges the privacy policy",
    )


class UserProfile(BaseModel):
    id: str
    email: str
    consent_given: bool = False
    consent_given_at: Optional[datetime] = None
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserProfile
