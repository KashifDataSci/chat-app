from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID


# ── Registration ──────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr


# ── OTP verification after registration ──────────────────────
class OtpVerifyRequest(BaseModel):
    email: EmailStr
    otp: str


# ── Login (already registered users) ─────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr


# ── Check email ───────────────────────────────────────────────
class CheckEmailRequest(BaseModel):
    email: EmailStr


class CheckEmailResponse(BaseModel):
    registered: bool


# ── Responses ─────────────────────────────────────────────────
class UserResponse(BaseModel):
    uuid: UUID
    username: str
    email: EmailStr
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True