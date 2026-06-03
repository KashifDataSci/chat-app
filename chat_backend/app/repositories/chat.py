from sqlalchemy.orm import Session
from sqlalchemy import and_, select
from app.models.chat import ConversationModel, MessageModel
from app.models.user import UserModel
from app.models.participant import conversation_participants
from typing import List


# ─────────────────────────────────────────────────────────────
# Conversations
# ─────────────────────────────────────────────────────────────

def get_conversation_participants_ids(conv_id: int, db: Session) -> List[int]:
    """Return list of user integer IDs participating in a conversation."""
    rows = db.execute(
        select(conversation_participants.c.user_id).where(
            conversation_participants.c.conversation_id == conv_id
        )
    ).fetchall()
    return [row[0] for row in rows]


def _add_participant(conv_id: int, user_id: int, db: Session):
    """Internal: add participant to connection table without commit."""
    existing = db.execute(
        select(conversation_participants).where(
            and_(
                conversation_participants.c.conversation_id == conv_id,
                conversation_participants.c.user_id == user_id,
            )
        )
    ).first()
    if not existing:
        db.execute(
            conversation_participants.insert().values(
                conversation_id=conv_id, user_id=user_id
            )
        )


def get_or_create_conversation(
    initiator_id: int, recipient_id: int, db: Session
) -> ConversationModel:
    """
    Find an existing 1-on-1 conversation between two users using integer IDs.
    If none exists, create one and add both as participants.
    """
    # Find all conversation IDs containing initiator
    initiator_convs = db.execute(
        select(conversation_participants.c.conversation_id).where(
            conversation_participants.c.user_id == initiator_id
        )
    ).fetchall()
    initiator_conv_ids = {row[0] for row in initiator_convs}

    # Find all conversation IDs containing recipient
    recipient_convs = db.execute(
        select(conversation_participants.c.conversation_id).where(
            conversation_participants.c.user_id == recipient_id
        )
    ).fetchall()
    recipient_conv_ids = {row[0] for row in recipient_convs}

    # Intersection find shared 1-on-1 room
    shared = initiator_conv_ids & recipient_conv_ids
    if shared:
        conv_id = next(iter(shared))
        return db.query(ConversationModel).filter(ConversationModel.id == conv_id).first()

    # Create brand new clean conversation instance
    conversation = ConversationModel(created_by=initiator_id)
    db.add(conversation)
    db.flush()  # Populates autoincrement integer ID immediately

    _add_participant(conversation.id, initiator_id, db)
    _add_participant(conversation.id, recipient_id, db)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_participants_info(conv_id: int, db: Session) -> List[UserModel]:
    """Return full UserModel objects for each participant via IDs."""
    user_ids = get_conversation_participants_ids(conv_id, db)
    if not user_ids:
        return []
    return db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()


# ─────────────────────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────────────────────

def save_message(
    conv_id: int, sender_id: int, content: str, db: Session
) -> tuple[MessageModel, str]:
    """Save a clean text message linked via integer tracking attributes."""
    msg = MessageModel(
        conversation_id=conv_id,
        sender_id=sender_id,
        content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    user = db.query(UserModel).filter(UserModel.id == sender_id).first()
    sender_name = user.username if user else "Unknown"
    return msg, sender_name