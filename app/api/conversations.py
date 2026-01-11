from fastapi import APIRouter, HTTPException, Depends

from app.db.db import get_db, close_db
from app.tokens.token import current_user

router = APIRouter()


@router.get("/conversations", summary="Get all conversations", tags=["Conversations"])
def get_conversations(current: dict = Depends(current_user)):
    conn, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute(
            """
            SELECT id, user1_id, user2_id, created_at
            FROM conversations
            WHERE user1_id = %s
               OR user2_id = %s
            ORDER BY created_at DESC
            """,
            (user_id, user_id),
        )
        conversations = cur.fetchall()

        if not conversations:
            return {"success": False, "message": "No conversations found", "data": [[]]}

        return {"success": True, "message": "All conversations found", "data": conversations}

    finally:
        close_db(conn, cur)


@router.post("/conversations/{friend_id}", summary="Create a new conversation", tags=["Conversations"])
def post_conversation(friend_id: int, current: dict = Depends(current_user)):
    conn, cur = get_db()

    try:
        user_id = current["user_id"]

        if friend_id == user_id:
            raise HTTPException(status_code=400, detail="Cannot create conversation with yourself")

        cur.execute("SELECT 1 FROM users WHERE id = %s", (friend_id,))

        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")

        user1_id = min(user_id, friend_id)
        user2_id = max(user_id, friend_id)

        cur.execute("SELECT id  FROM conversations WHERE user1_id = %s AND user2_id = %s ", (user1_id, user2_id))
        existing = cur.fetchone()

        if existing:
            return {"success": True, "message": "User already exists", "conversation_id": existing["id"]}

        cur.execute("INSERT INTO conversations (user1_id, user2_id) VALUES (%s, %s) RETURNING id ", (user1_id, user2_id))

        conversation_id = cur.fetchone()["id"]
        conn.commit()

        return {"success": True, "message": "New conversation created", "conversation_id": conversation_id}

    finally:
        close_db(conn, cur)
