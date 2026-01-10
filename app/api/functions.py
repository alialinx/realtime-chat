from passlib.handlers.sha2_crypt import sha256_crypt


def hash_password(password: str) -> str:
    return sha256_crypt.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return sha256_crypt.verify(plain, hashed)

