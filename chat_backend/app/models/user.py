from sqlalchemy import Column, String, Boolean, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import base
import uuid


class UserModel(base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    data = Column(String, nullable=True)
    iv = Column(String, nullable=True)
    authtag = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)