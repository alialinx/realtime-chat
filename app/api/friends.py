from fastapi import APIRouter, HTTPException, Depends

from app.db.db import get_db, close_db
from app.tokens.token import current_user

router = APIRouter()


@router.get("/friends", summary="Get all friends", tags=["Friends"])
def get_friends(current: dict = Depends(current_user)):
    print(current)
    conn, cur = get_db()
    try:

        user_id = current["user_id"]

        cur.execute("SELECT * FROM friends WHERE user_id = %s", (user_id,))

        cur.execute(
            """
            SELECT u.id, u.username, u.last_login_at
            FROM friends f
                     JOIN users u
                          ON u.id = f.friend_id
            WHERE f.user_id = %s
            ORDER BY u.username ASC
            """,
            (user_id,)
        )

        friends = cur.fetchall()

        return {"succes": True, "messages": "all friends", "user_id": user_id, "data": friends}
    finally:
        close_db(conn, cur)


@router.delete("/friends/{user_id}", summary="Delete a friend", tags=["Friends"])
def delete_friend(friend_id: int, current: dict = Depends(current_user)):
    conn, cur = get_db()
    try:
        user_id = current["user_id"]
        cur.execute("SELECT 1 FROM friends WHERE user_id = %s AND friend_id = %s", (user_id, friend_id))

        check_friend = cur.fetchone()

        if not check_friend:
            raise HTTPException(status_code=404, detail="Friend not found")

        cur.execute("DELETE FROM friends WHERE user_id = %s AND friend_id = %s", (user_id, friend_id))
        conn.commit()

        return {"succes": True, "message": "Friend deleted"}

    finally:
        close_db(conn, cur)


@router.get("/friends/requests", summary="Get friend requests", tags=["Friend Requests"])
def get_friends_requests(current: dict = Depends(current_user)):
    conn, cur = get_db()
    try:
        user_id = current["user_id"]
        cur.execute(
            """
            SELECT fr.id AS request_id u.id, u.username, fr.created_at
            FROM friend_requests fr
                     JOIN users u ON fr.from_user_id = u.id
            WHERE fr.to_user_id = %s
              and fr.status = 'pending'
            """, (user_id,))

        requests_ = cur.fetchall()

        if not requests_:
            return {"succes": True, "messages": "no friends", "data": [], "user_id": user_id}

        return {"succes": True, "messages": "all requests", "data": requests_, "user_id": user_id}
    finally:
        close_db(conn, cur)


@router.post("/friends/requests/{friend_id}", summary="Request a friend request", tags=["Friend Requests"])
def request_friend(friend_id: int, current: dict = Depends(current_user)):
    conn, cur = get_db()
    try:
        user_id = current["user_id"]

        cur.execute("SELECT id FROM users WHERE id = %s", (friend_id,))

        friend = cur.fetchone()

        if not friend:
            raise HTTPException(status_code=404, detail="User not found")

        if friend_id == user_id:
            raise HTTPException(status_code=400, detail="You cannot send a friend request to yourself")

        cur.execute("SELECT 1 FROM friends WHERE user_id = %s AND friend_id = %s", (user_id, friend_id))

        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Already friends")

        cur.execute("SELECT 1 FROM friend_requests WHERE from_user_id = %s AND to_user_id = %s AND status = 'pending'", (user_id, friend_id))

        existing_requests = cur.fetchone()
        if existing_requests:
            raise HTTPException(status_code=409, detail="Friend request already sent")

        cur.execute("INSERT INTO friend_requests (from_user_id, to_user_id, status) VALUES (%s, %s,'pending') RETURNING id ", (user_id, friend_id))

        request_id = cur.fetchone()["id"]
        conn.commit()
        return {"success": True, "message": "Friend request sent", "request_id": request_id}

    finally:
        close_db(conn, cur)


@router.post("/requests/{request_id}/accept", summary="Accept friend request", tags=["Friend Requests"])
def accept_friend(request_id: int, current: dict = Depends(current_user)):
    conn, cur = get_db()

    try:
        to_user_id = current["user_id"]

        cur.execute("SELECT id, from_user_id, to_user_id FROM friend_requests WHERE id = %s AND status = 'pending'", (request_id,))
        check_request_id = cur.fetchone()

        if not check_request_id:
            raise HTTPException(status_code=404, detail="Request not found")

        if check_request_id["to_user_id"] != to_user_id:
            raise HTTPException(status_code=403, detail="This request does not belong to you.")

        from_user_id = check_request_id["from_user_id"]

        cur.execute("UPDATE friend_requests SET status = 'accepted', updated_at = now()  WHERE id = %s", (request_id,))

        cur.execute("INSERT INTO friends (user_id, friend_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (to_user_id, from_user_id))
        cur.execute("INSERT INTO friends (user_id, friend_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (from_user_id,to_user_id))

        conn.commit()
        return {"success": True, "message": "Request accepted"}

    finally:
        close_db(conn, cur)

@router.post("/requests/{request_id}/decline", summary="Decline friend request", tags=["Friend Requests"])
def decline_friend(request_id: int, current: dict = Depends(current_user)):
    conn, cur = get_db()

    try:
        to_user_id = current["user_id"]

        cur.execute("SELECT id, from_user_id, to_user_id FROM friend_requests WHERE id = %s AND status = 'pending'", (request_id,))
        check_request_id = cur.fetchone()

        if not check_request_id:
            raise HTTPException(status_code=404, detail="Request not found")

        if check_request_id["to_user_id"] != to_user_id:
            raise HTTPException(status_code=403, detail="This request does not belong to you.")

        cur.execute("UPDATE friend_requests SET status = 'declined', updated_at = now()  WHERE id = %s", (request_id,))



        conn.commit()
        return {"success": True, "message": "Request declined"}

    finally:
        close_db(conn, cur)