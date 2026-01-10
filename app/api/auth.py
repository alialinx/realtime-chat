from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.api.functions import hash_password, verify_password
from app.db.db import get_db, close_db
from app.schemas.schemas import UserRegister
from app.tokens.token import active_or_new_token

router = APIRouter()


@router.post('/register', summary='Register a new user', tags=['Register'])
def register(payload: UserRegister):
    conn, cur = get_db()
    try:
        cur.execute("select * from users where username = %s ", (payload.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username already registered")

        cur.execute("SELECT 1 FROM users WHERE email = %s", (payload.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered")

        data = {
            'username': payload.username,
            'email': payload.email,
            'password_hash': hash_password(payload.password),
        }

        cur.execute(
            """
            insert into users (username, email, password_hash, is_admin, is_active)
            values (%s, %s, %s, %s, %s) RETURNING id, username, email, is_admin, is_active, created_at
            """,
            (data["username"], data["email"], data["password_hash"],)
        )

        user = cur.fetchone()
        conn.commit()
    finally:
        close_db(conn, cur)

    return {"success": True, "message": "User registered", "user": user}


@router.post('/login', summary='Login a user', tags=['Login'])
def login(username: str, password: str):
    conn, cur = get_db()
    try:

        now = datetime.now(timezone.utc)

        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_db_password = user["password_hash"]

        check_password = verify_password(password, user_db_password)

        if not check_password:
            raise HTTPException(status_code=400, detail="Incorrect password")

        token ,expire_at = active_or_new_token(user)

        cur.execute("update users set last_login_at = %s where username = %s", (now, user["id"]))
        conn.commit()
    finally:
        close_db(conn, cur)

    return {"success": True, "message": "login successfull", "access_token": token, "token_type": "bearer", "expire_at": expire_at}


@router.post('/logout', summary='Logout a user', tags=['Logout'])
def logout():
    return {"success": True, "message": "Logout successful"}
