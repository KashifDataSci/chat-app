from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool

from app.db.database import get_db, session_local
from app.services.connection_manager import manager
from app.repositories.chat import (
    get_or_create_conversation,
    get_participants_info,
    save_message,
    get_user_conversations,
    get_conversation_messages,
)
from app.repositories.user import get_user_by_email, get_or_create_user_by_email, get_user_by_uuid


def _save_message_threadsafe(conv_uuid: str, sender_uuid: str, content: str):
    """Save a websocket message in a separate DB session for thread safety."""
    with session_local() as db:
        return save_message(conv_uuid, sender_uuid, content, db)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# ─────────────────────────────────────────────────────────────
# Helper — build conversation response dict using UUIDs
# ─────────────────────────────────────────────────────────────
def _build_conversation_response(conv, db: Session) -> dict:
    participants = get_participants_info(conv.uuid, db)
    return {
        "id": str(conv.uuid),
        "created_by": str(conv.created_by),
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
    }


# ─────────────────────────────────────────────────────────────
# POST /conversations (Start / Retrieve 1-on-1 Conversation)
# Uses EMAIL to identify users (since frontend uses N8N, not this backend's auth)
# ─────────────────────────────────────────────────────────────
@router.post(
    "",
    status_code=201,
    summary="Start or retrieve a 1-on-1 conversation",
)
def start_conversation(
    initiator_email: str,
    recipient_email: str = "",
    db: Session = Depends(get_db),
):
    """
    Creates a new conversation between two users or returns an existing one.
    Users are identified by EMAIL (auto-provisioned if they don't exist in the DB).
    Pass as query params: ?initiator_email=a@b.com&recipient_email=c@d.com
    """
    if initiator_email == recipient_email:
        raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself.")

    # Auto-provision users if they don't exist in the backend DB
    initiator = get_or_create_user_by_email(initiator_email, db)
    recipient = get_or_create_user_by_email(recipient_email, db)

    conv = get_or_create_conversation(initiator.uuid, recipient.uuid, db)
    response = _build_conversation_response(conv, db)

    # Include the user's backend UUID so the frontend can use it for WebSocket
    response["my_uuid"] = str(initiator.uuid)
    return response


# ─────────────────────────────────────────────────────────────
# GET /conversations/list — List all conversations for a user
# ─────────────────────────────────────────────────────────────
@router.get(
    "/list",
    summary="List all conversations for a user",
)
def list_conversations(
    user_email: str,
    db: Session = Depends(get_db),
):
    """
    Returns all conversations the user participates in,
    including participant info and last message preview.
    """
    user = get_user_by_email(user_email, db)
    if not user:
        return []
    return get_user_conversations(user.uuid, db)


# ─────────────────────────────────────────────────────────────
# GET /conversations/{conv_id}/messages — Get message history
# ─────────────────────────────────────────────────────────────
@router.get(
    "/{conv_id}/messages",
    summary="Get message history for a conversation",
)
def get_messages(
    conv_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns all messages in a conversation, ordered by time ascending.
    """
    return get_conversation_messages(conv_id, db)


# ─────────────────────────────────────────────────────────────
# WebSocket  /ws/{conv_id}?user_email=
# ─────────────────────────────────────────────────────────────
@router.websocket("/ws/{conv_id}")
async def websocket_chat(
    websocket: WebSocket,
    conv_id: str,
    user_email: str = Query(..., description="Email of the connecting user"),
):
    """
    Real-time WebSocket endpoint for 1-on-1 communication.

    Connect: ws://<host>/api/conversations/ws/{conv_uuid}?user_email={email}
    Send JSON:    { "content": "Hello!" }
    """
    db = session_local()

    # ── Validate user existence ──────────────────────────────
    user = get_user_by_email(user_email, db)
    if not user:
        await websocket.close(code=4003, reason="User not found.")
        db.close()
        return

    user_uuid_str = str(user.uuid)

    # ── Accept & join ────────────────────────────────────────
    await manager.connect(conv_id, websocket)
    online_count = manager.get_online_count(conv_id)

    await manager.broadcast(conv_id, {
        "type": "joined",
        "user_id": user_uuid_str,
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

            new_msg, sender_data = await run_in_threadpool(
                _save_message_threadsafe, conv_id, user.uuid, content
            )

            await manager.broadcast(conv_id, {
                "id": str(new_msg.uuid),
                "conversation_id": str(new_msg.conversation_uuid),
                "sender_id": user_uuid_str,
                "sender_data": sender_data,
                "content": new_msg.content,
                "created_at": str(new_msg.created_at),
            })

    except WebSocketDisconnect:
        manager.disconnect(conv_id, websocket)
        online_count = manager.get_online_count(conv_id)
        await manager.broadcast(conv_id, {
            "type": "left",
            "user_id": user_uuid_str,
            "online": online_count,
        })

    finally:
        db.close()