from pydantic import BaseModel
from datetime import datetime
from typing import List


# ── Conversation ──────────────────────────────────────────────
class ConversationCreateRequest(BaseModel):
    initiator_id: int
    recipient_id: int


class ParticipantInfo(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    created_by: int
    created_at: datetime
    participants: List[ParticipantInfo] = []

    class Config:
        from_attributes = True


# ── Messages ──────────────────────────────────────────────────
class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_name: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── WebSocket incoming payload ────────────────────────────────
class WsMessagePayload(BaseModel):
    content: str