-- USERS
CREATE TABLE IF NOT EXISTS users
(
    id            SERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin      BOOLEAN NOT NULL DEFAULT false,
    is_active     BOOLEAN NOT NULL DEFAULT true,

    -- presence
    is_online     BOOLEAN NOT NULL DEFAULT FALSE,
    last_seen_at  TIMESTAMPTZ NULL,

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
    status       TEXT NOT NULL DEFAULT 'pending',
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

-- BLOCKS
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
