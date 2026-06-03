from sqlalchemy import Column, ForeignKey, Table,Integer
from app.db.database import base

# Association table: many-to-many between users and conversations
conversation_participants = Table(
    "conversation_participants",
    base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("conversation_id", Integer, ForeignKey("conversations.id"), primary_key=True),
)