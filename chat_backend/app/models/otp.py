from sqlalchemy import Column, Integer, String, DateTime, func
from app.db.database import base


class OtpModel(base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, nullable=False, index=True)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(String, default="false", nullable=False)  # "true" / "false" as string for simplicity
    created_at = Column(DateTime(timezone=True), server_default=func.now())
