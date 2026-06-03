from sqlalchemy.orm import Session
from sqlalchemy import and_, select
from app.models.chat import ConversationModel, MessageModel
from app.models.user import UserModel
from app.models.participant import conversation_participants
from uuid import UUID
from typing import List


# ─────────────────────────────────────────────────────────────
# Conversations
# ─────────────────────────────────────────────────────────────

def get_conversation_participants_uuids(conv_uuid: UUID, db: Session) -> List[UUID]:
    """Return list of user UUIDs participating in a conversation."""
    rows = db.execute(
        select(conversation_participants.c.user_uuid).where(
            conversation_participants.c.conversation_uuid == conv_uuid
        )
    ).fetchall()
    return [row[0] for row in rows]


def _add_participant(conv_uuid: UUID, user_uuid: UUID, db: Session):
    """Internal: add participant without commit (caller commits)."""
    existing = db.execute(
        select(conversation_participants).where(
            and_(
                conversation_participants.c.conversation_uuid == conv_uuid,
                conversation_participants.c.user_uuid == user_uuid,
            )
        )
    ).first()
    if not existing:
        db.execute(
            conversation_participants.insert().values(
                conversation_uuid=conv_uuid, user_uuid=user_uuid
            )
        )


def get_or_create_conversation(
    initiator_uuid: UUID, recipient_uuid: UUID, db: Session
) -> ConversationModel:
    """
    Find an existing 1-on-1 conversation between two users.
    If none exists, create one and add both as participants.
    """
    # Find all conversations that contain initiator
    initiator_convs = db.execute(
        select(conversation_participants.c.conversation_uuid).where(
            conversation_participants.c.user_uuid == initiator_uuid
        )
    ).fetchall()
    initiator_conv_ids = {row[0] for row in initiator_convs}

    # Find all conversations that contain recipient
    recipient_convs = db.execute(
        select(conversation_participants.c.conversation_uuid).where(
            conversation_participants.c.user_uuid == recipient_uuid
        )
    ).fetchall()
    recipient_conv_ids = {row[0] for row in recipient_convs}

    # Intersection = shared conversations
    shared = initiator_conv_ids & recipient_conv_ids
    if shared:
        conv_uuid = next(iter(shared))
        return db.query(ConversationModel).filter(ConversationModel.uuid == conv_uuid).first()

    # Create new conversation
    conversation = ConversationModel(created_by=initiator_uuid)
    db.add(conversation)
    db.flush()  # get UUID before commit

    _add_participant(conversation.uuid, initiator_uuid, db)
    _add_participant(conversation.uuid, recipient_uuid, db)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation_by_uuid(conv_uuid: UUID, db: Session) -> ConversationModel | None:
    return db.query(ConversationModel).filter(ConversationModel.uuid == conv_uuid).first()


def get_conversations_for_user(user_uuid: UUID, db: Session) -> List[ConversationModel]:
    """Return all conversations a user participates in."""
    conv_ids = db.execute(
        select(conversation_participants.c.conversation_uuid).where(
            conversation_participants.c.user_uuid == user_uuid
        )
    ).fetchall()
    ids = [row[0] for row in conv_ids]
    if not ids:
        return []
    return db.query(ConversationModel).filter(ConversationModel.uuid.in_(ids)).all()


def get_participants_info(conv_uuid: UUID, db: Session) -> List[UserModel]:
    """Return full UserModel objects for each participant."""
    user_uuids = get_conversation_participants_uuids(conv_uuid, db)
    if not user_uuids:
        return []
    return db.query(UserModel).filter(UserModel.uuid.in_(user_uuids)).all()


# ─────────────────────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────────────────────

def save_message(
    conv_uuid: UUID, sender_uuid: UUID, content: str, db: Session
) -> tuple[MessageModel, str]:
    msg = MessageModel(
        conversation_uuid=conv_uuid,
        sender_uuid=sender_uuid,
        content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    user = db.query(UserModel).filter(UserModel.uuid == sender_uuid).first()
    sender_name = user.username if user else "Unknown"
    return msg, sender_name


def get_messages(conv_uuid: UUID, db: Session, limit: int = 100, offset: int = 0):
    """Return paginated messages with sender name."""
    results = (
        db.query(MessageModel, UserModel.username)
        .join(UserModel, MessageModel.sender_uuid == UserModel.uuid)
        .filter(MessageModel.conversation_uuid == conv_uuid)
        .order_by(MessageModel.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "uuid": str(msg.uuid),
            "conversation_uuid": str(msg.conversation_uuid),
            "sender_uuid": str(msg.sender_uuid),
            "sender_name": name,
            "content": msg.content,
            "created_at": str(msg.created_at),
        }
        for msg, name in results
    ]