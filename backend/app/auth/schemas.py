"""Pydantic schemas for authentication, user management, and password reset."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import EmailAddress as EmailStr


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Must contain upper, lower, and special char")
    full_name: str = Field(..., min_length=2, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=64)
    billing_address: Optional[str] = Field(default="", max_length=1000)
    city: Optional[str] = Field(default=None, max_length=128)
    state: Optional[str] = Field(default=None, max_length=128)
    country: Optional[str] = Field(default="US", max_length=128)
    postal_code: Optional[str] = Field(default=None, max_length=32)


class StaffCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(default="staff", pattern="^(staff|admin)$")


class UserStatusUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    full_name: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(admin|staff|customer)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    customer_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None
    expires_in_minutes: int
