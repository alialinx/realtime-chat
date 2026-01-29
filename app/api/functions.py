from fastapi import HTTPException

from app.api.tokens.token import current_user
from app.db.db import get_db, close_db

def serialize_message(row: dict) -> dict:
    row = dict(row)

    for k in ("created_at", "delivered_at", "read_at"):
        if k in row and row[k] is not None:
            row[k] = row[k].isoformat()

    return row


def get_recipient_id(conversation_id: int, sender_id: int) -> int | None:
    conn, cur = get_db()
    try:
        cur.execute("SELECT user1_id, user2_id FROM conversations WHERE id = %s",(conversation_id,))
        row = cur.fetchone()
        if not row:
            return None

        if isinstance(row, dict):
            u1, u2 = row["user1_id"], row["user2_id"]
        else:
            u1, u2 = row[0], row[1]

        return u2 if sender_id == u1 else u1
    finally:
        close_db(conn, cur)


def get_user_id_from_token(token):

    token_doc = current_user(token)

    user_id = token_doc['user_id']

    return user_id


def check_conversation(conversation_id:int, user_id:int):

    conn,cur = get_db()

    try:
        cur.execute("SELECT * FROM conversations WHERE id = %s", (conversation_id,))
        conversation = cur.fetchone()
        if not conversation:
            return False, "Conversation not found"

        print(conversation)

        user_id_list = [conversation['user1_id'],conversation['user2_id']]

        if user_id not in user_id_list:
            return False, "user not found in conversation"
        return True, "OK"


    finally:
        close_db(conn,cur)

def check_groups(group_id:int,user_id:int):
    conn, cur = get_db()
    try:
        cur.execute("SELECT 1 FROM groups WHERE id = %s", (group_id,))
        check_group = cur.fetchone()

        if not check_group:
            return False, "Group not found"

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s", (group_id,user_id),)
        check_user_in_group = cur.fetchone()

        if not check_user_in_group:
            return False, "User not found in group"

        return True, "OK"


    finally:
        close_db(conn, cur)


def messages_insert_to_db(conversation_id: int, sender_id: int, body: str) -> dict:
    conn, cur = get_db()
    try:
        cur.execute(
            """
            INSERT INTO messages (conversation_id, sender_id, body)
            VALUES (%s, %s, %s)
            RETURNING id, conversation_id, sender_id, body, created_at, delivered_at, read_at
            """,
            (conversation_id, sender_id, body),
        )
        row = cur.fetchone()
        conn.commit()
        return serialize_message(row)
    finally:
        close_db(conn, cur)

def is_user_muted_in_group(group_id: int, user_id: int) -> bool:
    conn, cur = get_db()
    try:
        cur.execute(
            "SELECT is_mute FROM group_members WHERE group_id = %s AND user_id = %s",
            (group_id, user_id)
        )
        row = cur.fetchone()
        if row is None:
            return True
        return bool(row["is_mute"])
    finally:
        close_db(conn, cur)

def group_messages_insert_to_db(group_id: int, sender_id: int, content: str) -> dict:
    conn, cur = get_db()
    try:
        cur.execute(
            """
            INSERT INTO group_messages (group_id, sender_id, content)
            VALUES (%s, %s, %s)
            RETURNING id, group_id, sender_id, content, created_at
            """,
            (group_id, sender_id, content),
        )
        row = cur.fetchone()

        cur.execute("SELECT username FROM users WHERE id = %s", (sender_id,))
        sender_name = cur.fetchone()["username"]
        row["sender_name"] =sender_name


        cur.execute("SELECT is_mute FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, sender_id,))
        is_mute = cur.fetchone()["is_mute"]
        row["is_mute"] = is_mute

        print("row", row)
        # group preview için faydalı
        cur.execute(
            "UPDATE groups SET last_message_at = now() WHERE id = %s",
            (group_id,),
        )

        conn.commit()
        if row is None:
            raise RuntimeError("insert message failed")

        return serialize_message(row)
    finally:
        close_db(conn, cur)

def check_group_member(group_id: int, user_id: int) -> bool:
    conn, cur = get_db()
    try:
        cur.execute(
            "SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s",
            (group_id, user_id),
        )
        return cur.fetchone() is not None
    finally:
        close_db(conn, cur)

def mark_group_read(group_id: int, user_id: int) -> None:
    conn, cur = get_db()
    try:
        cur.execute(
            """
            UPDATE group_members
            SET last_read_at = now()
            WHERE group_id = %s AND user_id = %s
            """,
            (group_id, user_id),
        )
        conn.commit()
    finally:
        close_db(conn, cur)



import psycopg2

def set_user_online(user_id: int, is_online: bool) -> bool:
    try:
        conn, cur = get_db()
        try:
            cur.execute(
                "UPDATE users SET is_online = %s WHERE id = %s",
                (is_online, user_id),
            )
            conn.commit()
            return True
        finally:
            close_db(conn, cur)
    except psycopg2.OperationalError:
        return False

def touch_last_seen(user_id: int):
    conn, cur = get_db()
    try:
        cur.execute("UPDATE users SET last_seen_at = now() WHERE id = %s", (user_id,))
        conn.commit()
    finally:
        close_db(conn, cur)


def mark_read(message_id: int):
    conn, cur = get_db()
    try:
        cur.execute(
            """
            UPDATE messages
            SET read_at = now()
            WHERE id = %s AND read_at IS NULL
            RETURNING id, read_at
            """,
            (message_id,)
        )
        row = cur.fetchone()
        conn.commit()
        if not row:
            return None

        row = dict(row)
        row["read_at"] = row["read_at"].isoformat() if row["read_at"] else None
        return row
    finally:
        close_db(conn, cur)

def mark_conversation_read(conversation_id: int, reader_id: int, last_message_id: int) -> int:

    conn, cur = get_db()
    try:
        cur.execute(
            """
            UPDATE messages
            SET read_at = now()
            WHERE conversation_id = %s
              AND sender_id <> %s
              AND read_at IS NULL
              AND id <= %s
            """,
            (conversation_id, reader_id, last_message_id),
        )
        updated = cur.rowcount
        conn.commit()
        return updated
    finally:
        close_db(conn, cur)

def mark_delivered(message_id: int) -> dict | None:
    conn, cur = get_db()
    try:
        cur.execute(
            """
            UPDATE messages
            SET delivered_at = now()
            WHERE id = %s AND delivered_at IS NULL
            RETURNING id, conversation_id, sender_id, body, created_at, delivered_at, read_at
            """,
            (message_id,),
        )
        row = cur.fetchone()
        conn.commit()
        if not row:
            return None
        return serialize_message(row)
    finally:
        close_db(conn, cur)