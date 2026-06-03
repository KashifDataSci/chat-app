from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.user import (
    CheckEmailRequest, CheckEmailResponse,
    UserRegisterRequest, OtpVerifyRequest,
    LoginRequest, UserResponse,
)
from app.repositories.user import (
    get_user_by_email, create_user, verify_user, get_user_by_uuid,
)
from app.repositories.otp import create_otp, get_valid_otp, mark_otp_used
from app.services.otp_service import generate_otp, send_otp_email

router = APIRouter(prefix="/auth", tags=["Auth"])


# ─────────────────────────────────────────────────────────────
# POST /auth/check-email
# ─────────────────────────────────────────────────────────────
@router.post(
    "/check-email",
    response_model=CheckEmailResponse,
    summary="Check if an email is already registered",
)
def check_email(payload: CheckEmailRequest, db: Session = Depends(get_db)):
    """
    Returns { registered: true } if the email belongs to a verified user,
    { registered: false } if the email is unknown or unverified.
    """
    user = get_user_by_email(payload.email, db)
    registered = user is not None and user.is_verified
    return CheckEmailResponse(registered=registered)


# ─────────────────────────────────────────────────────────────
# POST /auth/register
# ─────────────────────────────────────────────────────────────
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user and send OTP",
)
async def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new user (unverified). Sends a 6-digit OTP to their email.
    If the email already belongs to a verified user, returns 409 Conflict.
    If the email exists but is unverified (previous attempt), resends OTP.
    """
    existing = get_user_by_email(payload.email, db)

    if existing and existing.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered. Use /auth/login instead.",
        )

    # Create user record if not present, or reuse existing unverified record
    if not existing:
        user = create_user(username=payload.username, email=payload.email, db=db)
    else:
        user = existing  # unverified — just resend OTP

    otp_code = generate_otp()
    create_otp(email=payload.email, otp_code=otp_code, db=db)

    try:
        await send_otp_email(
            recipient_email=payload.email,
            otp_code=otp_code,
            username=user.username,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User created but failed to send OTP email: {str(e)}",
        )

    return {
        "message": f"OTP sent to {payload.email}. Please verify to complete registration.",
        "email": payload.email,
    }


# ─────────────────────────────────────────────────────────────
# POST /auth/verify-otp
# ─────────────────────────────────────────────────────────────
@router.post(
    "/verify-otp",
    response_model=UserResponse,
    summary="Verify OTP and activate account",
)
def verify_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)):
    """
    Validates the OTP code for the given email.
    On success: marks user as verified and returns their profile with UUID.
    """
    otp_record = get_valid_otp(email=payload.email, otp_code=payload.otp, db=db)

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP. Please request a new one.",
        )

    mark_otp_used(otp_id=otp_record.id, db=db)
    user = verify_user(email=payload.email, db=db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


# ─────────────────────────────────────────────────────────────
# POST /auth/resend-otp
# ─────────────────────────────────────────────────────────────
@router.post(
    "/resend-otp",
    summary="Resend OTP to an unverified email",
)
async def resend_otp(payload: CheckEmailRequest, db: Session = Depends(get_db)):
    """
    Resends a fresh OTP to an unverified user's email.
    Returns 404 if the email is not registered.
    Returns 409 if the user is already verified.
    """
    user = get_user_by_email(payload.email, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered. Please register first.",
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already verified. Use /auth/login.",
        )

    otp_code = generate_otp()
    create_otp(email=payload.email, otp_code=otp_code, db=db)

    try:
        await send_otp_email(
            recipient_email=payload.email,
            otp_code=otp_code,
            username=user.username,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP email: {str(e)}",
        )

    return {"message": f"New OTP sent to {payload.email}."}


# ─────────────────────────────────────────────────────────────
# POST /auth/login
# ─────────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=UserResponse,
    summary="Login with a registered email",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    For already-verified users. Returns the user's UUID and profile.
    Use the returned UUID as identity in conversation and WebSocket calls.
    """
    user = get_user_by_email(payload.email, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please complete OTP verification.",
        )

    return user


# ─────────────────────────────────────────────────────────────
# GET /auth/me/{user_uuid}
# ─────────────────────────────────────────────────────────────
@router.get(
    "/me/{user_uuid}",
    response_model=UserResponse,
    summary="Get user profile by UUID",
)
def get_me(user_uuid: str, db: Session = Depends(get_db)):
    """Fetch any user's public profile by their UUID."""
    from uuid import UUID as PyUUID
    try:
        uid = PyUUID(user_uuid)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format.")

    user = get_user_by_uuid(uid, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return user
