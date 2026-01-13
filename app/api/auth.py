from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.schemas.schemas import UserRegister
from app.api.tokens.token import active_or_new_token, current_user
from app.api.utils import hash_password, verify_password
from app.api.ws.ws import manager
from app.db.db import get_db, close_db

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
            insert into users (username, email, password_hash)
            values (%s, %s, %s) RETURNING id, username, email, is_admin, is_active, created_at
            """,
            (data["username"], data["email"], data["password_hash"])
        )

        user = cur.fetchone()

        conn.commit()
    finally:
        close_db(conn, cur)

    return {"success": True, "message": "User registered", "user": user}


@router.post('/login', summary='Login a user', tags=['Login'])
def login(form: OAuth2PasswordRequestForm = Depends()):
    conn, cur = get_db()
    try:

        username = form.username
        password = form.password

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

        cur.execute("UPDATE users SET last_login_at = %s WHERE id = %s", (now, user["id"]))
        conn.commit()
    finally:
        close_db(conn, cur)

    return {"success": True, "message": "login successfull", "access_token": token, "token_type": "bearer", "expire_at": expire_at}


@router.post('/logout', summary='Logout a user', tags=['Logout'])
def logout(current: dict = Depends(current_user)):
    conn, cur = get_db()
    try:
        user_id = current["user_id"]
        if not manager.is_user_online(user_id):
            cur.execute("UPDATE users SET is_online = FALSE, last_seen_at = now() WHERE id = %s", (user_id,))
        else:
            cur.execute("UPDATE users SET last_seen_at = now() WHERE id = %s", (user_id,))

        conn.commit()
        return {"success": True, "message": "Logout successful"}
    finally:
        close_db(conn, cur)
