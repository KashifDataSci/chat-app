from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.repositories.user import get_user_by_email, get_or_create_user_by_email, update_user_profile
from app.repositories.otp import create_otp
from app.services.otp_service import send_otp_email

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Request schemas ──────────────────────────────────────────

class GetEmailBody(BaseModel):
    email: str
    code: int


class GetEmailRequest(BaseModel):
    body: GetEmailBody


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
    """
    If the user exists AND has profile data → return user row as a list.
    Otherwise auto-create the user, store the OTP, send the email, and
    return { message, otp, email } so the frontend navigates to OTP screen.
    """
    email = payload.body.email.strip().lower()
    code = str(payload.body.code)

    # Find or auto-create the user
    user = get_or_create_user_by_email(email, db)

    # Existing user with profile already set → direct login
    if user.data:
        return [_user_to_dict(user)]

    # New user or profile not set yet → OTP flow
    # Store the OTP in the database
    create_otp(email=email, otp_code=code, db=db)

    # Try to send the OTP email
    try:
        await send_otp_email(
            recipient_email=email,
            otp_code=code,
            username=email.split("@")[0],  # use email prefix as display name
        )
    except Exception as e:
        # Log but don't block — the frontend already has the code
        print(f"[AUTH] Failed to send OTP email: {e}")

    return {
        "message": "OTP sent",
        "otp": payload.body.code,
        "email": email,
    }


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