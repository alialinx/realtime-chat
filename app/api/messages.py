from fastapi import APIRouter, HTTPException, Depends

from app.api.schemas.schemas import MessageCreate
from app.api.tokens.token import current_user
from app.db.db import get_db, close_db

router = APIRouter()



@router.get("/messages/{conversation_id}", summary="Get all messages", tags=["Messages"])
def get_messages(conversation_id:int,current: dict = Depends(current_user), page: int = 0, limit: int = 100):

    conn,cur = get_db()
    try:

        user_id = current["user_id"]

        if limit > 100:
            limit = 100
        if page < 0:
            page = 0

        offset = page * limit

        cur.execute("select 1 from conversations where id = %s and (user1_id = %s OR user2_id = %s)", (conversation_id, user_id, user_id))

        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Conversation not found")

        cur.execute(
            """
            SELECT * FROM messages 
            WHERE conversation_id = %s
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
            """, (conversation_id, limit, offset))

        messages = cur.fetchall()
        messages = list(reversed(messages))

        return {"success": True, "message": "all messages", "data": messages, "page": page, "limit": limit}


    finally:
        close_db(conn,cur)



@router.post("/messages/{conversation_id}", summary="Create a new message", tags=["Messages"])
def create_new_message(conversation_id:int, payload:MessageCreate, current: dict = Depends(current_user)):
    conn,cur = get_db()
    try:

        user_id = current["user_id"]

        cur.execute("select 1 from conversations where id = %s and (user1_id = %s OR user2_id = %s)", (conversation_id, user_id, user_id))

        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Conversation not found")


        cur.execute(
            """
            INSERT INTO messages (conversation_id,sender_id, body) 
            VALUES (%s, %s, %s)
            RETURNING conversation_id, sender_id, body, created_at, delivered_at, read_at
            """,
            (conversation_id, user_id, payload.body))

        msg = cur.fetchone()
        conn.commit()

        return {"success": True, "message": "sent", "data": msg}


    finally:
        close_db(conn,cur)
