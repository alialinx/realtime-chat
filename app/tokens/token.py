from datetime import timedelta, datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt

from app.api.functions import ensure_utc_aware
from app.config import TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from app.db.db import get_db, close_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def create_access_token(data: dict):
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)

    payload = {
        'exp': int(expire_at.timestamp()),
        'user_id': data.get('user_id'),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return token, expire_at


def save_token_to_db(token: str, expire_at: datetime, user_id: int):
    conn, cur = get_db()

    cur.execute(f""" INSERT INTO tokens (user_id,token, expire_at) VALUES (%s, %s, %s) """, (user_id, token, expire_at))
    conn.commit()
    close_db(conn, cur)

    return {"success": True}


def check_token(token: str):

    conn, cur = get_db()
    try:
        now = datetime.now(timezone.utc)

        cur.execute("SELECT * FROM tokens WHERE token = %s", (token,))
        token_doc = cur.fetchone()

        if not token_doc:
            raise HTTPException(status_code=401, detail="Invalid token")

        expire_at = ensure_utc_aware(token_doc.get("expire_at"))
        if not expire_at:
            raise HTTPException(status_code=401, detail="Invalid token expiry")

        if expire_at <= now:
            raise HTTPException(status_code=401, detail="Expired token")

        return token_doc
    finally:
        close_db(conn, cur)


def current_user(token:str = Depends(oauth2_scheme)):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid token signature")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token format")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_id not found")
    token_doc = check_token(token)

    if token_doc.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token user mismatch")

    return token_doc


def active_or_new_token(user: dict):
    conn, cur = get_db()
    try:
        user_id = user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User id not found")

        now = datetime.now(timezone.utc)

        cur.execute("""SELECT * FROM tokens WHERE user_id = %s ORDER BY expire_at DESC LIMIT 1 """, (user_id,))
        existing = cur.fetchone()

        if existing:
            expire_at = ensure_utc_aware(existing.get("expire_at"))
            token = existing.get("token")
            if token and expire_at and expire_at > now:
                return token, expire_at

        new_token, expire_at = create_access_token({"user_id": user_id})
        save_token_to_db(new_token, expire_at, user_id)
        return new_token, expire_at
    finally:
        close_db(conn, cur)