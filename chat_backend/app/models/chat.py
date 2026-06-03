from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Text
from app.db.database import base


class ConversationModel(base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MessageModel(base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())