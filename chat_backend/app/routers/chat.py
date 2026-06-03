from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool

from app.db.database import get_db, session_local
from app.services.connection_manager import manager
from app.repositories.chat import (
    get_or_create_conversation,
    get_participants_info,
    save_message,
)
from app.repositories.user import get_user_by_id

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# ─────────────────────────────────────────────────────────────
# Helper — build conversation response dict using IDs
# ─────────────────────────────────────────────────────────────
def _build_conversation_response(conv, db: Session) -> dict:
    participants = get_participants_info(conv.id, db)
    return {
        "id": conv.id,
        "created_by": conv.created_by,
        "created_at": str(conv.created_at),
        "participants": [
            {
                "id": p.id,
                "username": p.username,
                "email": p.email,
            }
            for p in participants
        ],
    }


# ─────────────────────────────────────────────────────────────
# POST /conversations (Start / Retrieve 1-on-1 Conversation)
# ─────────────────────────────────────────────────────────────
@router.post(
    "",
    status_code=201,
    summary="Start or retrieve a 1-on-1 conversation",
)
def start_conversation(
    initiator_id: int,
    recipient_id: int,
    db: Session = Depends(get_db),
):
    """
    Creates a new conversation between two users or returns an existing one.
    Both IDs must be standard primary key integers.
    Pass as query params: ?initiator_id=1&recipient_id=2
    """
    if initiator_id == recipient_id:
        raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself.")

    initiator = get_user_by_id(initiator_id, db)
    if not initiator or not initiator.is_verified:
        raise HTTPException(status_code=404, detail="Initiator user not found or not verified.")

    recipient = get_user_by_id(recipient_id, db)
    if not recipient or not recipient.is_verified:
        raise HTTPException(status_code=404, detail="Recipient user not found or not verified.")

    conv = get_or_create_conversation(initiator_id, recipient_id, db)
    return _build_conversation_response(conv, db)


# ─────────────────────────────────────────────────────────────
# WebSocket  /ws/{conv_id}?user_id=
# ─────────────────────────────────────────────────────────────
@router.websocket("/ws/{conv_id}")
async def websocket_chat(
    websocket: WebSocket,
    conv_id: int,
    user_id: int = Query(..., description="Integer ID of the connecting user"),
):
    """
    Real-time minimalist WebSocket endpoint for 1-on-1 communication using integer routing variables.

    Connect: ws://<host>/api/conversations/ws/{conv_id}?user_id={user_id}
    Send JSON:    { "content": "Hello!" }
    """
    db = session_local()
    conv_str_id = str(conv_id)  # String representation tracking format for connection manager layout

    # ── Validate user existence ──────────────────────────────
    user = get_user_by_id(user_id, db)
    if not user or not user.is_verified:
        await websocket.close(code=4003, reason="User not found or not verified.")
        db.close()
        return

    # ── Accept & join ────────────────────────────────────────
    await manager.connect(conv_str_id, websocket)
    online_count = manager.get_online_count(conv_str_id)

    await manager.broadcast(conv_str_id, {
        "type": "joined",
        "user_id": user.id,
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
                save_message, conv_id, user_id, content, db
            )

            await manager.broadcast(conv_str_id, {
                "id": new_msg.id,
                "conversation_id": new_msg.conversation_id,
                "sender_id": new_msg.sender_id,
                "sender_name": sender_name,
                "content": new_msg.content,
                "created_at": str(new_msg.created_at),
            })

    except WebSocketDisconnect:
        manager.disconnect(conv_str_id, websocket)
        online_count = manager.get_online_count(conv_str_id)
        await manager.broadcast(conv_str_id, {
            "type": "left",
            "user_id": user.id,
            "username": user.username,
            "online": online_count,
        })

    finally:
        db.close()