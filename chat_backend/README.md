Based on your new structure, you have shifted from a 1-on-1 direct conversation flow to a Group/Room-based chat flow with a vastly simplified registration setup (/user/enter via email, matching your updated SQL tables).

Let's rewrite the README to match your exact current endpoints, message formats, database schema, and technical flow perfectly.

Chat Backend API
A minimalist, high-performance chat backend for React Native built using FastAPI, SQLAlchemy, and PostgreSQL/Supabase. It utilizes sequential auto-incrementing integer IDs (1, 2, 3...) instead of complex UUIDs, handling user entry with email verification and room-based WebSocket broadcasting.

🚀 Features
Email-Based User Entry: Instantly sign up or log in via email. If a user doesn't exist, the system automatically creates their record and returns their unique integer ID.

Room-Based Architecture: Create public or private chat rooms managed dynamically by an explicit table of room participants.

Real-Time Subscriptions: WebSocket connections bind directly to a room_id for instant group messaging and automated online state syncs.

Scannable Tracking: Easily retrieve message history, current active rooms, and participants tied to an explicit user.

🛠️ API Endpoints
👥 User Endpoints
POST /api/user/enter

Description: Enter with an email address.

Payload: { "email": "user@example.com", "name": "Kashif" }

Returns: Full user profile containing the auto-incremented primary key id.

💬 Chat (Room-Based) Endpoints
GET /api/chat/rooms - List all available chat rooms on the server.

POST /api/chat/rooms?name=RoomName&created_by=UserId - Create a new chat room.

GET /api/chat/{room_id} - Fetch all historical message logs from a specific room.

GET /api/chat/{room_id}/participants - View a complete list of users registered inside a room.

POST /api/chat/{room_id}/participants/{userId} - Add or invite a user into a chat room.

DELETE /api/chat/{room_id}/participants/{userId} - Remove a participant from a room or leave it.

GET /api/chat/users/{userId}/rooms - List all rooms where the specific user is a participant.

🔌 WebSocket Connection
WS /api/chat/ws/{room_id}

Description: Opens a persistent stateful duplex pipeline for real-time messaging.

Guardrails: Validates room existence prior to connection upgrading; instantly rejects with close code 4004 if the target room_id does not exist.