from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.repositories.user import get_user_by_email, get_or_create_user_by_email, update_user_profile
from app.repositories.otp import create_otp, get_valid_otp, mark_otp_used
from app.services.otp_service import generate_otp, send_otp_email

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Request schemas ──────────────────────────────────────────

class GetEmailBody(BaseModel):
    email: str


class GetEmailRequest(BaseModel):
    body: GetEmailBody


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str


class SetUserRequest(BaseModel):
    email: str
    encryptedData: str
    iv: str
    authTag: str


# ── Helper: serialise a user row the way the frontend expects ─

def _user_to_dict(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "data": user.data,
        "iv": user.iv,
        "authtag": user.authtag,
        "created_at": str(user.created_at),
    }


# ─────────────────────────────────────────────────────────────
# POST /auth/get-email   (replaces n8n webhook/get-email)
# ─────────────────────────────────────────────────────────────
@router.post(
    "/get-email",
    summary="Login / send OTP — replaces n8n get-email webhook",
)
async def get_email(payload: GetEmailRequest, db: Session = Depends(get_db)):
    email = payload.body.email.strip().lower()
    print(f"\n[GET-EMAIL] Request received for: {email}")

    # Find or auto-create the user
    user = get_or_create_user_by_email(email, db)
    print(f"[GET-EMAIL] user.data exists: {bool(user.data)}")

    # Existing user with profile already set → direct login
    if user.data:
        print(f"[GET-EMAIL] → Direct login (has profile), skipping OTP")
        return [_user_to_dict(user)]

    # New user or profile not set yet → OTP flow
    print(f"[GET-EMAIL] → Sending OTP to {email}")
    code = generate_otp()
    create_otp(email=email, otp_code=code, db=db)

    try:
        await send_otp_email(
            recipient_email=email,
            otp_code=code,
            username=email.split("@")[0],
        )
        print(f"[GET-EMAIL] ✅ OTP email sent successfully to {email}")
    except Exception as e:
        print(f"[GET-EMAIL] ❌ Failed to send OTP email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again.",
        )

    return {
        "message": "OTP sent",
        "email": email,
    }


# ─────────────────────────────────────────────────────────────
# POST /auth/verify-otp  — validates OTP server-side
# ─────────────────────────────────────────────────────────────
@router.post(
    "/verify-otp",
    summary="Verify the OTP code sent to the user's email",
)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Checks the submitted OTP against the database.
    Marks it as used on success so it cannot be reused.
    """
    email = payload.email.strip().lower()
    otp_record = get_valid_otp(email=email, otp_code=payload.otp.strip(), db=db)

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please request a new code.",
        )

    mark_otp_used(otp_record.id, db)
    return {"message": "OTP verified", "email": email}


# ─────────────────────────────────────────────────────────────
# POST /auth/set-user   (replaces n8n webhook/set-user)
# ─────────────────────────────────────────────────────────────
@router.post(
    "/set-user",
    summary="Save encrypted profile data — replaces n8n set-user webhook",
)
def set_user(payload: SetUserRequest, db: Session = Depends(get_db)):
    """
    Updates the user's encrypted profile fields (data, iv, authtag).
    Returns the updated user row as a list (same format the frontend expects).
    """
    email = payload.email.strip().lower()

    user = update_user_profile(
        email=email,
        data=payload.encryptedData,
        iv=payload.iv,
        authtag=payload.authTag,
        db=db,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Call /auth/get-email first.",
        )

    return [_user_to_dict(user)]