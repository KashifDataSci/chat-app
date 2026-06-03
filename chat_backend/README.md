# Chat Backend API

A simple chat backend for React Native using FastAPI, PostgreSQL/Supabase with email-based user entry and ID-based chat.

## Features

- Email-based user entry (auto-creates user if not exists)
- Create chat rooms
- Participant tracking for rooms (users can join/leave rooms)
- WebSocket real-time messaging
- Message history
- User-centric endpoints for managing chats based on user IDs

## API Endpoints

### User

- `POST /api/user/enter` - Enter with email, returns user info with id

### Chat (Room-based)

- `GET /api/chat/rooms` - List all chat rooms
- `POST /api/chat/rooms?name=RoomName&created_by=UserId` - Create a chat room
- `GET /api/chat/{room_id}` - Get messages from room
- `GET /api/chat/{room_id}/participants` - Get participants in a room
- `POST /api/chat/{room_id}/participants/{userId}` - Add user to room
- `DELETE /api/chat/{room_id}/participants/{userId}` - Remove user from room
- `GET /api/chat/users/{userId}/rooms` - Get rooms where user is a participant

### Chat (WebSocket)

- `WS /api/chat/ws/{room_id}` - WebSocket for real-time chat. Validates room exists before connecting; rejects with code 4004 if not found.

## WebSocket Message Format

Send JSON: `{"sender_id": 1, "message": "Hello!"}`

## Flow

1. User enters with email → get user id
2. Create chat room with user id
3. Add other users as participants to the room
4. Other users join with their email → get their user id  
5. Connect to WebSocket with room_id
6. Send messages by user id

## Setup

```bash
pip install -r requirements.txt
# Update .env with your DATABASE_URL
python run.py
```

## Database Schema

```sql
users table: id, email, name, created_at
chat_rooms table: id, name, created_by
messages table: id, chat_room_id, sender_id, message, created_at
room_participants table: user_id (FK to users.id), room_id (FK to chat_rooms.id) [Primary Key: user_id, room_id]
```

## Database Schema

```sql
users table: id, email, name, created_at
chat_rooms table: id, name, created_by
messages table: id, chat_room_id, sender_id, message, created_at
```