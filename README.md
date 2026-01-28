# realtime-chat

A production-ready **Realtime Chat Backend** built with **FastAPI + WebSocket + PostgreSQL**.

✅ Live test (frontend + backend):
- You can test the public chat UI at: **https://chat.alialin.me**

This backend provides:
- JWT authentication (access token)
- 1-to-1 direct conversations
- Realtime messaging via WebSocket
- Message delivery + read receipts (WhatsApp-like)
- Optional friends system (requests / accept / decline)
- Multi-tab / multi-device WebSocket support

---

## Tech Stack
- Python + FastAPI
- PostgreSQL
- WebSocket (FastAPI)
- Docker / Docker Compose
- Nginx (reverse proxy + TLS)

---

## Features
- Register / Login / Logout
- Token stored in DB (`tokens` table)
- Direct conversations (unique user pair)
- Realtime broadcast to all connected clients in a conversation
- Heartbeat (ping / pong)
- Message status fields:
  - `created_at` (sent)
  - `delivered_at` (delivered)
  - `read_at` (read)
- Friends system:
  - send request
  - accept / decline
  - friends table
- Blocking system (optional)

---


# Group Chat

This project supports **Group Chat** with realtime messaging.

## Features
- Create public or private groups
- Add / remove group members
- Member roles (owner, admin, member)
- Group message history (REST)
- Realtime group messages via WebSocket

---

## Group APIs

### Groups
- `GET /groups`
- `GET /groups/{group_id}`
- `POST /groups`
- `PUT /groups/{group_id}`
- `PUT /groups/{group_id}/visibility`
- `DELETE /groups/{group_id}`

### Group Members
- `GET /groups/{group_id}/members`
- `POST /groups/{group_id}/members`
- `DELETE /groups/{group_id}/members/{member_id}`
- `DELETE /groups/{group_id}/members/me`
- `PUT /groups/{group_id}/members/{member_id}/role`
- `PUT /groups/{group_id}/members/{member_id}/mute`

### Group Messages (REST)
- `GET /groups/{group_id}/messages`
- `PUT /groups/{group_id}/messages/{message_id}`
- `DELETE /groups/{group_id}/messages/{message_id}`

---

## Group WebSocket

### Endpoint
```
/ws/groups/{group_id}?token=JWT_TOKEN
```

### Events

#### Send message
Client → Server
```json
{
  "type": "group.message.send",
  "body": "hello"
}
```

Server → Group
```json
{
  "type": "group.message.new",
  "data": {}
}
```

#### Heartbeat
```json
{ "type": "ping" }
```

---

## Notes
- Only group members can connect to group WebSocket
- Group WebSocket is separate from direct messages
- Message timestamps are serialized before sending



---

## HTTP API Endpoints

### Authentication

**POST /register**  
Create a new user.

Request (JSON):
```json
{
  "username": "ali",
  "email": "ali@example.com",
  "password": "StrongPassword123"
}
```

**POST /login**  
Login and receive an access token.  
Uses `application/x-www-form-urlencoded` (OAuth2PasswordRequestForm).

Example:
```bash
curl -X POST "http://127.0.0.1:7722/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ali&password=StrongPassword123"
```

Response:
```json
{
  "access_token": "JWT_TOKEN_HERE",
  "token_type": "bearer"
}
```

**POST /logout**  
Logout (requires Bearer token).

Example:
```bash
curl -X POST "http://127.0.0.1:7722/logout" \
  -H "Authorization: Bearer JWT_TOKEN_HERE"
```

---

### Friends

**GET /friends**  
Returns your friends list.

**GET /friends/requests**  
Returns pending friend requests.

**POST /friends/requests/{friend_id}**  
Send a friend request.

**POST /requests/{request_id}/accept**  
Accept a friend request.

**POST /requests/{request_id}/decline**  
Decline a friend request.

---

### Conversations & Messages

**POST /conversations/{friend_id}**  
Creates (or returns) a DM conversation between you and the friend.

Response example:
```json
{ "conversation_id": 1 }
```

**GET /messages/{conversation_id}?page=0&limit=100**  
Fetch messages of a conversation (paginated).

---

## WebSocket Realtime Chat

### WebSocket Endpoint

Format:
```
/ws/conversations/{conversation_id}?token=JWT_TOKEN
```

Example:
```
ws://127.0.0.1:7722/ws/conversations/1?token=eyJhbGciOi...
```

### Connection Flow (simple)
1) Read `token` from query params
2) Decode token → get `user_id`
3) Verify user belongs to the conversation
4) Accept WebSocket
5) Store the WebSocket in ConnectionManager
6) Start receiving events in a loop

---

## ConnectionManager (in-memory)

The server stores active sockets in memory:

- `active_connections[conversation_id] -> Set[WebSocket]`  
  Used to broadcast to a conversation.

- `user_connections[user_id] -> Set[WebSocket]`  
  Supports multi-tab / multi-device.

- `ws_user[WebSocket] -> user_id`  
  Helps cleanup on disconnect.

---

## WebSocket Event Protocol

All events are JSON.

### 1) Heartbeat (ping / pong)

Client → Server:
```json
{ "type": "ping" }
```

Server → Client:
```json
{ "type": "pong" }
```

### 2) Send message

Client → Server:
```json
{
  "type": "message.send",
  "body": "hello"
}
```

Server → Clients:
```json
{
  "type": "message.new",
  "data": {
    "id": 21,
    "conversation_id": 1,
    "sender_id": 2,
    "body": "hello",
    "created_at": "2026-01-13T17:00:29.317890+00:00",
    "delivered_at": null,
    "read_at": null
  }
}
```

### 3) Read receipt

Client → Server:
```json
{
  "type": "conversation.read",
  "last_message_id": 21
}
```

Server → Clients:
```json
{
  "type": "conversation.read",
  "data": {
    "conversation_id": 1,
    "reader_id": 2,
    "last_message_id": 21,
    "updated_count": 5
  }
}
```

---

## Message Status Logic

✅ **Sent**  
- Message saved in DB → `created_at`

✅✅ **Delivered**  
- Recipient has at least one active WebSocket connection → set `delivered_at`

✅✅ **Read**  
- Recipient opens the conversation and sends `conversation.read` → set `read_at`

---

## JSON Serialization Notes
Timestamps from PostgreSQL are Python `datetime`.  
Before sending via WebSocket, convert them to strings:
- `dt.isoformat()`

---

## Run with Docker

Build and start:
```bash
docker compose up -d --build
```

Stop:
```bash
docker compose down
```

---

## Local Development

Run locally:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger docs:
- `http://127.0.0.1:8000/docs`

---

## Testing

### 1) Test HTTP Login
```bash
curl -X POST "http://127.0.0.1:7722/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=test"
```

### 2) Test WebSocket
Connect:
```
ws://127.0.0.1:7722/ws/conversations/1?token=YOUR_TOKEN
```

Send message:
```json
{"type":"message.send","body":"selam"}
```

Ping:
```json
{"type":"ping"}
```

Read:
```json
{"type":"conversation.read","last_message_id":21}
```
## PostgreSQL Database Schema

This project uses **PostgreSQL** for persistence.