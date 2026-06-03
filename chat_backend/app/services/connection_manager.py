from fastapi import WebSocket
from typing import Dict, List


class ConnectionManager:
    """Manages active WebSocket connections keyed by conversation UUID string."""

    def __init__(self):
        # key: conversation_uuid (str), value: list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, conversation_uuid: str, websocket: WebSocket):
        await websocket.accept()
        if conversation_uuid not in self.active_connections:
            self.active_connections[conversation_uuid] = []
        self.active_connections[conversation_uuid].append(websocket)

    def disconnect(self, conversation_uuid: str, websocket: WebSocket):
        if conversation_uuid in self.active_connections:
            connections = self.active_connections[conversation_uuid]
            if websocket in connections:
                connections.remove(websocket)
            # Clean up empty rooms
            if not connections:
                del self.active_connections[conversation_uuid]

    async def broadcast(self, conversation_uuid: str, message: dict):
        """Send a message to all participants in a conversation."""
        connections = self.active_connections.get(conversation_uuid, [])
        dead = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        # Remove any dead connections
        for d in dead:
            self.disconnect(conversation_uuid, d)

    def get_online_count(self, conversation_uuid: str) -> int:
        return len(self.active_connections.get(conversation_uuid, []))


manager = ConnectionManager()