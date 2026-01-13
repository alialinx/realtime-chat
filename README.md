# realtime-chat
Realtime - Chat











# PostgreSQL Database Schema (Realtime Chat)

This project uses **PostgreSQL** for persistence.  
Below is the complete schema used for authentication, real-time messaging, and the optional friends system.

---

## Full SQL Schema

```sql

-- USERS

CREATE TABLE IF NOT EXISTS users
(
    id            SERIAL PRIMARY KEY,

    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,

    is_admin      BOOLEAN NOT NULL DEFAULT false,
    is_active     BOOLEAN NOT NULL DEFAULT true,

    last_login_at TIMESTAMPTZ NULL,
    
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);



-- TOKENS


CREATE TABLE IF NOT EXISTS tokens
(
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER     NOT NULL,
    token      TEXT        NOT NULL,
    expire_at  TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tokens_token ON tokens(token);
CREATE INDEX IF NOT EXISTS idx_tokens_user_id ON tokens(user_id);



-- CONVERSATIONS (DM)


CREATE TABLE IF NOT EXISTS conversations
(
    id         SERIAL PRIMARY KEY,
    user1_id   INTEGER NOT NULL,
    user2_id   INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT conversations_unique_pair UNIQUE (user1_id, user2_id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_user1 ON conversations(user1_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user2 ON conversations(user2_id);


-- MESSAGES

CREATE TABLE IF NOT EXISTS messages
(
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    sender_id       INTEGER NOT NULL,
    body            TEXT NOT NULL,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at    TIMESTAMPTZ NULL,
    read_at         TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);




-- FRIEND REQUESTS

CREATE TABLE IF NOT EXISTS friend_requests
(
    id           BIGSERIAL PRIMARY KEY,
    from_user_id INTEGER NOT NULL,
    to_user_id   INTEGER NOT NULL,

    status       TEXT NOT NULL DEFAULT 'pending', -- pending | accepted | declined

    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT friend_requests_unique_pair UNIQUE (from_user_id, to_user_id)
);

CREATE INDEX IF NOT EXISTS idx_friend_requests_to_user ON friend_requests(to_user_id);
CREATE INDEX IF NOT EXISTS idx_friend_requests_from_user ON friend_requests(from_user_id);
CREATE INDEX IF NOT EXISTS idx_friend_requests_status ON friend_requests(status);



-- FRIENDS

CREATE TABLE IF NOT EXISTS friends
(
    id         BIGSERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    friend_id  INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT friends_unique_pair UNIQUE (user_id, friend_id),
    CONSTRAINT friends_not_self CHECK (user_id <> friend_id)
);

CREATE INDEX IF NOT EXISTS idx_friends_user_id ON friends(user_id);
CREATE INDEX IF NOT EXISTS idx_friends_friend_id ON friends(friend_id);

=
-- BLOCKING


CREATE TABLE IF NOT EXISTS blocks
(
    id         BIGSERIAL PRIMARY KEY,
    blocker_id INTEGER NOT NULL,
    blocked_id INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT blocks_unique_pair UNIQUE (blocker_id, blocked_id),
    CONSTRAINT blocks_not_self CHECK (blocker_id <> blocked_id)
);

CREATE INDEX IF NOT EXISTS idx_blocks_blocker_id ON blocks(blocker_id);
CREATE INDEX IF NOT EXISTS idx_blocks_blocked_id ON blocks(blocked_id);
````


# WebSocket Realtime Chat (FastAPI) – System Documentation

This project implements a **realtime chat** system using **FastAPI WebSocket**.

The main idea:

- Users connect to a WebSocket endpoint for a conversation.
- The server keeps active WebSocket connections in memory.
- When a message is sent:
  1) it is saved into PostgreSQL (`messages` table)
  2) it is broadcasted to all connected users in that conversation

This document explains the WebSocket flow and the realtime connection management logic in simple English.

---

## 1) WebSocket Endpoint

WebSocket URL:

/ws/conversations/{conversation_id}?token=JWT_TOKEN

Example:

ws://127.0.0.1:7722/ws/conversations/1?token=eyJhbGciOi...




### Basic flow

1. Read JWT token from query params
2. Decode token → get `user_id`
3. Check if user belongs to the conversation (security)
4. Accept WebSocket connection
5. Register WebSocket in ConnectionManager
6. Start infinite `while True` receive loop

---

## 2) ConnectionManager (Core Concept)

The ConnectionManager stores and manages active realtime connections.

It uses **3 mappings**:

### A) `active_connections`

- Type: `Dict[int, Set[WebSocket]]`
- Key: `conversation_id`
- Value: all WebSockets connected to that conversation

This is used to broadcast messages to a specific conversation room.

---

### B) `user_connections`

- Type: `Dict[int, Set[WebSocket]]`
- Key: `user_id`
- Value: all WebSockets opened by that user

This supports multi-tab and multi-device use cases.

A user is online if:

- `len(user_connections[user_id]) > 0`

---

### C) `ws_user`

- Type: `Dict[WebSocket, int]`
- Key: websocket instance
- Value: user_id

This helps to identify the user that owns a WebSocket during cleanup.

---

## 3) Broadcasting Messages

Broadcast means:

> Send the same JSON payload to all users connected to the same conversation.

Pseudo logic:

- loop all websockets in `active_connections[conversation_id]`
- send message using `ws.send_json(...)`

### Handling broken (dead) sockets

Sometimes clients disconnect without sending a proper close event (internet crash, browser closed, etc.)

During broadcast:
- if sending fails (`send_json` raises exception)
- mark that websocket as dead
- remove it from memory to avoid memory leaks

---

## 4) Heartbeat (Ping / Pong)

Presence and online status require heartbeat updates.

Clients should send a ping every 20–30 seconds:



Client → Server:
```json
{ "type": "ping" }
````
Server → Client:
````json
{ "type": "pong" }
````



## 5) WebSocket Event Protocol


All WebSocket messages are JSON events.

5.1 Send message event

Client → Server:

````json
{
  "type": "message.send",
  "body": "hello"
}

````

Server:

inserts message into DB

broadcasts to conversation

Server → Clients:

## 5.2 Read receipt event

Client sends this when conversation is opened / messages are visible.

Client → Server:

````json
{
  "type": "message.read",
  "message_id": 21
}
````

Server:

updates DB read_at = now()

broadcasts read event

Server → Clients:

````json
{
  "type": "message.read",
  "data": {
    "id": 21,
    "read_at": "2026-01-13T17:05:12.000000+00:00"
  }
}
````


---

## 6) WhatsApp-Style Message Status Logic (✅ / ✅✅ / Read)

This system supports WhatsApp-like message states:

### ✅ Sent (single tick)

A message is considered **sent** when it is stored in the database successfully.

- `created_at` is always filled

---

### ✅✅ Delivered (double tick)

A message is considered **delivered** when the recipient is **online**
(has at least 1 active WebSocket connection).

Important:
- recipient does NOT need to open the conversation screen
- recipient only needs to be online globally

- `delivered_at` is filled only when recipient user is online

---

### Read (read receipt)

A message is considered **read** only when the recipient opens that conversation.

- `read_at` is filled only after client sends `message.read`

---

## 7) JSON Serialization Notes

Database returns timestamps as Python `datetime` objects.

WebSocket can only send JSON serializable data.

Before broadcasting:
- convert all datetime fields using `.isoformat()`

Example:
- `created_at.isoformat()`
- `delivered_at.isoformat()`
- `read_at.isoformat()`

---

## 8) Multi-tab / Multi-device Support

The same user can open multiple sessions:

- multiple browser tabs
- multiple browsers
- desktop + mobile

This is why `user_connections[user_id]` is a set.

Online check:
- user is online if they have at least 1 active WebSocket connection.

---

## 9) Database Fields (Presence / Delivery / Read)

### users table

Required fields:

- `is_online BOOLEAN NOT NULL DEFAULT FALSE`
- `last_seen_at TIMESTAMPTZ`

### messages table

Required fields:

- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `delivered_at TIMESTAMPTZ`
- `read_at TIMESTAMPTZ`

---

## 10) SQL Setup (Migrations)

Add online presence fields:

```sql
ALTER TABLE users
ADD COLUMN IF NOT EXISTS is_online BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
````

## 11) Testing WebSocket

You can test the realtime chat using a browser extension like **"Simple WebSocket Client"**.

### 11.1 Connect

Open a WebSocket connection using this URL format:

`ws://127.0.0.1:7722/ws/conversations/1?token=YOUR_TOKEN`

- `1` = conversation_id
- `YOUR_TOKEN` = JWT token received from `/login`

### 11.2 Send a message

Send JSON payload:

```json
{"type":"message.send","body":"selam"}`
````
Expected broadcast example:

```json
{"type":"message.new","data":{"id":21,"conversation_id":1,"sender_id":2,"body":"selam","created_at":"2026-01-13T17:00:29.317890+00:00","delivered_at":null,"read_at":null}}`
````
### 11.3 Heartbeat (ping / pong)

Send ping every 20–30 seconds:

```json
{"type":"ping"}`
````
Server response:

```json
{"type":"pong"}`
````
### 11.4 Read receipt test

When the recipient opens the chat screen, the client should send:

```json
{"type":"message.read","message_id":21}`
````
Server will broadcast:

```json
{"type":"message.read","data":{"id":21,"read_at":"2026-01-13T17:05:12.000000+00:00"}}`
````
