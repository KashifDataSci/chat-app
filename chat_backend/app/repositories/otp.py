from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.otp import OtpModel
from datetime import datetime, timedelta, timezone
import os

OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", 10))


def create_otp(email: str, otp_code: str, db: Session) -> OtpModel:
    """Invalidate any previous unused OTPs for this email, then create a new one."""
    db.query(OtpModel).filter(
        and_(OtpModel.email == email, OtpModel.is_used == "false")
    ).update({"is_used": "expired"})
    db.commit()

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
    otp = OtpModel(email=email, otp_code=otp_code, expires_at=expires_at, is_used="false")
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return otp


def get_valid_otp(email: str, otp_code: str, db: Session) -> OtpModel | None:
    """Fetch an OTP that is unused and not yet expired."""
    now = datetime.now(timezone.utc)
    return db.query(OtpModel).filter(
        and_(
            OtpModel.email == email,
            OtpModel.otp_code == otp_code,
            OtpModel.is_used == "false",
            OtpModel.expires_at > now,
        )
    ).first()


def mark_otp_used(otp_id, db: Session) -> None:
    db.query(OtpModel).filter(OtpModel.id == otp_id).update({"is_used": "true"})
    db.commit()