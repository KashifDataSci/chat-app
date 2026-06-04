from sqlalchemy.orm import Session
from sqlalchemy import and_, select
from app.models.chat import ConversationModel, MessageModel
from app.models.user import UserModel
from app.models.participant import conversation_participants
from typing import List
import uuid as uuid_lib


# ─────────────────────────────────────────────────────────────
# Conversations
# ─────────────────────────────────────────────────────────────

def get_conversation_participants_uuids(conv_uuid, db: Session) -> List:
    """Return list of user UUIDs participating in a conversation."""
    rows = db.execute(
        select(conversation_participants.c.user_uuid).where(
            conversation_participants.c.conversation_uuid == conv_uuid
        )
    ).fetchall()
    return [row[0] for row in rows]


def _add_participant(conv_uuid, user_uuid, db: Session):
    """Internal: add participant to connection table without commit."""
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
    initiator_uuid, recipient_uuid, db: Session
) -> ConversationModel:
    """
    Find an existing 1-on-1 conversation between two users using UUIDs.
    If none exists, create one and add both as participants.
    """
    # Find all conversation UUIDs containing initiator
    initiator_convs = db.execute(
        select(conversation_participants.c.conversation_uuid).where(
            conversation_participants.c.user_uuid == initiator_uuid
        )
    ).fetchall()
    initiator_conv_uuids = {row[0] for row in initiator_convs}

    # Find all conversation UUIDs containing recipient
    recipient_convs = db.execute(
        select(conversation_participants.c.conversation_uuid).where(
            conversation_participants.c.user_uuid == recipient_uuid
        )
    ).fetchall()
    recipient_conv_uuids = {row[0] for row in recipient_convs}

    # Intersection find shared 1-on-1 room
    shared = initiator_conv_uuids & recipient_conv_uuids
    if shared:
        conv_uuid = next(iter(shared))
        return db.query(ConversationModel).filter(ConversationModel.uuid == conv_uuid).first()

    # Create brand new clean conversation instance
    conversation = ConversationModel(created_by=initiator_uuid)
    db.add(conversation)
    db.flush()  # Populates UUID immediately

    _add_participant(conversation.uuid, initiator_uuid, db)
    _add_participant(conversation.uuid, recipient_uuid, db)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_participants_info(conv_uuid, db: Session) -> List[UserModel]:
    """Return full UserModel objects for each participant via UUIDs."""
    user_uuids = get_conversation_participants_uuids(conv_uuid, db)
    if not user_uuids:
        return []
    return db.query(UserModel).filter(UserModel.uuid.in_(user_uuids)).all()


# ─────────────────────────────────────────────────────────────
# Messages
# ─────────────────────────────────────────────────────────────

def save_message(
    conv_uuid, sender_uuid, content: str, db: Session
) -> tuple[MessageModel, str]:
    """Save a clean text message linked via UUID tracking attributes."""
    msg = MessageModel(
        conversation_uuid=conv_uuid,
        sender_uuid=sender_uuid,
        content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    user = db.query(UserModel).filter(UserModel.uuid == sender_uuid).first()
    sender_data = {
        "data": user.data if user else None,
        "iv": user.iv if user else None,
        "authtag": user.authtag if user else None,
    }
    return msg, sender_data


def get_user_conversations(user_uuid, db: Session) -> List[dict]:
    """Return all conversations for a user, with participant info and last message."""
    # Get all conversation UUIDs the user participates in
    rows = db.execute(
        select(conversation_participants.c.conversation_uuid).where(
            conversation_participants.c.user_uuid == user_uuid
        )
    ).fetchall()
    conv_uuids = [row[0] for row in rows]

    if not conv_uuids:
        return []

    results = []
    for conv_uuid in conv_uuids:
        conv = db.query(ConversationModel).filter(ConversationModel.uuid == conv_uuid).first()
        if not conv:
            continue

        # Get participants
        participants = get_participants_info(conv_uuid, db)

        # Get last message
        last_msg = (
            db.query(MessageModel)
            .filter(MessageModel.conversation_uuid == conv_uuid)
            .order_by(MessageModel.created_at.desc())
            .first()
        )

        last_message_data = None
        if last_msg:
            sender = db.query(UserModel).filter(UserModel.uuid == last_msg.sender_uuid).first()
            last_message_data = {
                "id": str(last_msg.uuid),
                "content": last_msg.content,
                "sender_data": {
                    "data": sender.data if sender else None,
                    "iv": sender.iv if sender else None,
                    "authtag": sender.authtag if sender else None,
                },
                "sender_uuid": str(last_msg.sender_uuid),
                "created_at": str(last_msg.created_at),
            }

        results.append({
            "id": str(conv.uuid),
            "created_at": str(conv.created_at),
            "participants": [
                {
                    "id": str(p.uuid),
                    "data": p.data,
                    "iv": p.iv,
                    "authtag": p.authtag,
                    "email": p.email,
                }
                for p in participants
            ],
            "last_message": last_message_data,
        })

    # Sort by last message time (most recent first), conversations with no messages last
    results.sort(
        key=lambda c: c["last_message"]["created_at"] if c["last_message"] else "",
        reverse=True,
    )
    return results


def get_conversation_messages(conv_uuid, db: Session) -> List[dict]:
    """Return all messages for a conversation, ordered by time ascending."""
    messages = (
        db.query(MessageModel)
        .filter(MessageModel.conversation_uuid == conv_uuid)
        .order_by(MessageModel.created_at.asc())
        .all()
    )

    result = []
    for msg in messages:
        sender = db.query(UserModel).filter(UserModel.uuid == msg.sender_uuid).first()
        result.append({
            "id": str(msg.uuid),
            "conversation_id": str(msg.conversation_uuid),
            "sender_id": str(msg.sender_uuid),
            "sender_data": {
                "data": sender.data if sender else None,
                "iv": sender.iv if sender else None,
                "authtag": sender.authtag if sender else None,
            },
            "content": msg.content,
            "created_at": str(msg.created_at),
        })
    return result