from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import List


# ── Conversation ──────────────────────────────────────────────
class ConversationCreateRequest(BaseModel):
    initiator_uuid: UUID
    recipient_uuid: UUID


class ParticipantInfo(BaseModel):
    uuid: UUID
    username: str
    email: str

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    uuid: UUID
    created_by: UUID
    created_at: datetime
    participants: List[ParticipantInfo] = []

    class Config:
        from_attributes = True


# ── Messages ──────────────────────────────────────────────────
class MessageResponse(BaseModel):
    uuid: UUID
    conversation_uuid: UUID
    sender_uuid: UUID
    sender_name: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── WebSocket incoming payload ────────────────────────────────
class WsMessagePayload(BaseModel):
    content: str