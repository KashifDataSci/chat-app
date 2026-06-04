from sqlalchemy import Column, String, ForeignKey, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import base
import uuid


class ConversationModel(base):
    __tablename__ = "conversations"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MessageModel(base):
    __tablename__ = "messages"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    conversation_uuid = Column(UUID(as_uuid=True), ForeignKey("conversations.uuid"), nullable=False)
    sender_uuid = Column(UUID(as_uuid=True), ForeignKey("users.uuid"), nullable=False)
    content = Column(Text, nullable=False)
    iv = Column(Text, nullable=True)
    authtag = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())