from fastapi import WebSocket
from typing import Dict, List


class ConnectionManager:
    """Manages active WebSocket connections keyed by conversation ID string."""

    def __init__(self):
        # key: conversation_id (str), value: list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, conversation_id: str, websocket: WebSocket):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)

    def disconnect(self, conversation_id: str, websocket: WebSocket):
        if conversation_id in self.active_connections:
            connections = self.active_connections[conversation_id]
            if websocket in connections:
                connections.remove(websocket)
            # Clean up empty chat rooms
            if not connections:
                del self.active_connections[conversation_id]

    async def broadcast(self, conversation_id: str, message: dict):
        """Send a real-time message to all active participants in a specific conversation."""
        connections = self.active_connections.get(conversation_id, [])
        dead = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        
        # Safely remove any dead or disconnected sockets discovered during broadcast
        for d in dead:
            self.disconnect(conversation_id, d)

    def get_online_count(self, conversation_id: str) -> int:
        return len(self.active_connections.get(conversation_id, []))


manager = ConnectionManager()