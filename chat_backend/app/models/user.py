from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.db.database import base


class UserModel(base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())