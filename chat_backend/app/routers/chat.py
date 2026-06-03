from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool
from uuid import UUID

from app.db.database import get_db, session_local
from app.services.connection_manager import manager
from app.repositories.chat import (
    get_or_create_conversation,
    get_conversation_by_uuid,
    get_conversations_for_user,
    get_participants_info,
    save_message,
    get_messages,
)
from app.repositories.user import get_user_by_uuid

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# ─────────────────────────────────────────────────────────────
# Helper — build conversation response dict
# ─────────────────────────────────────────────────────────────
def _build_conversation_response(conv, db: Session) -> dict:
    participants = get_participants_info(conv.uuid, db)
    return {
        "uuid": str(conv.uuid),
        "created_by": str(conv.created_by),
        "created_at": str(conv.created_at),
        "participants": [
            {
                "uuid": str(p.uuid),
                "username": p.username,
                "email": p.email,
            }
            for p in participants
        ],
    }


# ─────────────────────────────────────────────────────────────
# POST /conversations
# ─────────────────────────────────────────────────────────────
@router.post(
    "",
    status_code=201,
    summary="Start or retrieve a 1-on-1 conversation",
)
def start_conversation(
    initiator_uuid: UUID,
    recipient_uuid: UUID,
    db: Session = Depends(get_db),
):
    """
    Creates a new conversation between two users, or returns the existing one.
    Both UUIDs must belong to verified users.
    Pass as query params: ?initiator_uuid=...&recipient_uuid=...
    """
    if initiator_uuid == recipient_uuid:
        raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself.")

    initiator = get_user_by_uuid(initiator_uuid, db)
    if not initiator or not initiator.is_verified:
        raise HTTPException(status_code=404, detail="Initiator user not found or not verified.")

    recipient = get_user_by_uuid(recipient_uuid, db)
    if not recipient or not recipient.is_verified:
        raise HTTPException(status_code=404, detail="Recipient user not found or not verified.")

    conv = get_or_create_conversation(initiator_uuid, recipient_uuid, db)
    return _build_conversation_response(conv, db)


# ─────────────────────────────────────────────────────────────
# GET /conversations?user_uuid=
# ─────────────────────────────────────────────────────────────
@router.get(
    "",
    summary="List all conversations for a user",
)
def list_conversations(
    user_uuid: UUID = Query(..., description="UUID of the requesting user"),
    db: Session = Depends(get_db),
):
    """Returns all conversations the user is participating in, with participant details."""
    user = get_user_by_uuid(user_uuid, db)
    if not user or not user.is_verified:
        raise HTTPException(status_code=404, detail="User not found or not verified.")

    conversations = get_conversations_for_user(user_uuid, db)
    return [_build_conversation_response(c, db) for c in conversations]


# ─────────────────────────────────────────────────────────────
# GET /conversations/{conv_uuid}
# ─────────────────────────────────────────────────────────────
@router.get(
    "/{conv_uuid}",
    summary="Get conversation details",
)
def get_conversation(conv_uuid: UUID, db: Session = Depends(get_db)):
    """Returns conversation metadata and participant info."""
    conv = get_conversation_by_uuid(conv_uuid, db)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return _build_conversation_response(conv, db)


# ─────────────────────────────────────────────────────────────
# GET /conversations/{conv_uuid}/messages
# ─────────────────────────────────────────────────────────────
@router.get(
    "/{conv_uuid}/messages",
    summary="Fetch message history",
)
def get_conversation_messages(
    conv_uuid: UUID,
    limit: int = Query(100, ge=1, le=500, description="Max messages to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """
    Returns paginated message history for a conversation, ordered oldest-first.
    Use limit/offset for pagination.
    """
    conv = get_conversation_by_uuid(conv_uuid, db)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages = get_messages(conv_uuid, db, limit=limit, offset=offset)
    return {
        "conversation_uuid": str(conv_uuid),
        "total_returned": len(messages),
        "offset": offset,
        "limit": limit,
        "messages": messages,
    }


# ─────────────────────────────────────────────────────────────
# WebSocket  /ws/{conv_uuid}?user_uuid=
# ─────────────────────────────────────────────────────────────
@router.websocket("/ws/{conv_uuid}")
async def websocket_chat(
    websocket: WebSocket,
    conv_uuid: str,
    user_uuid: str = Query(..., description="UUID of the connecting user"),
):
    """
    Real-time WebSocket endpoint for a conversation.

    Connect: ws://<host>/api/conversations/ws/{conv_uuid}?user_uuid={user_uuid}

    Send JSON:  { "content": "Hello!" }
    Receive JSON:
    {
        "uuid": "...",
        "conversation_uuid": "...",
        "sender_uuid": "...",
        "sender_name": "John",
        "content": "Hello!",
        "created_at": "..."
    }
    System events (type field set):
        { "type": "joined",  "user_uuid": "...", "username": "...", "online": 2 }
        { "type": "left",    "user_uuid": "...", "username": "...", "online": 1 }
        { "type": "error",   "detail": "..." }
    """
    db = session_local()

    # ── Validate conversation ────────────────────────────────
    try:
        conv_id = UUID(conv_uuid)
    except ValueError:
        await websocket.close(code=4000, reason="Invalid conversation UUID.")
        db.close()
        return

    conv = get_conversation_by_uuid(conv_id, db)
    if not conv:
        await websocket.close(code=4004, reason="Conversation not found.")
        db.close()
        return

    # ── Validate user ────────────────────────────────────────
    try:
        u_id = UUID(user_uuid)
    except ValueError:
        await websocket.close(code=4000, reason="Invalid user UUID.")
        db.close()
        return

    user = get_user_by_uuid(u_id, db)
    if not user or not user.is_verified:
        await websocket.close(code=4003, reason="User not found or not verified.")
        db.close()
        return

    # ── Accept & join ────────────────────────────────────────
    await manager.connect(conv_uuid, websocket)
    online_count = manager.get_online_count(conv_uuid)

    await manager.broadcast(conv_uuid, {
        "type": "joined",
        "user_uuid": str(user.uuid),
        "username": user.username,
        "online": online_count,
    })

    # ── Message loop ─────────────────────────────────────────
    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "").strip()

            if not content:
                await websocket.send_json({"type": "error", "detail": "Empty message ignored."})
                continue

            new_msg, sender_name = await run_in_threadpool(
                save_message, conv_id, u_id, content, db
            )

            await manager.broadcast(conv_uuid, {
                "uuid": str(new_msg.uuid),
                "conversation_uuid": str(new_msg.conversation_uuid),
                "sender_uuid": str(new_msg.sender_uuid),
                "sender_name": sender_name,
                "content": new_msg.content,
                "created_at": str(new_msg.created_at),
            })

    except WebSocketDisconnect:
        manager.disconnect(conv_uuid, websocket)
        online_count = manager.get_online_count(conv_uuid)
        await manager.broadcast(conv_uuid, {
            "type": "left",
            "user_uuid": str(user.uuid),
            "username": user.username,
            "online": online_count,
        })

    finally:
        db.close()