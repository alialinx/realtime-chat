from datetime import timezone

from passlib.handlers.sha2_crypt import sha256_crypt


def hash_password(password: str) -> str:
    return sha256_crypt.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return sha256_crypt.verify(plain, hashed)


def ensure_utc_aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
