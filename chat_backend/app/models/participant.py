from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import base

# Association table: many-to-many between users and conversations
conversation_participants = Table(
    "conversation_participants",
    base.metadata,
    Column("user_uuid", UUID(as_uuid=True), ForeignKey("users.uuid"), primary_key=True),
    Column("conversation_uuid", UUID(as_uuid=True), ForeignKey("conversations.uuid"), primary_key=True),
)