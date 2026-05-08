from hashlib import sha256

import bcrypt


def prepare_password(password: str) -> bytes:
    return sha256(password.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(prepare_password(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            prepare_password(plain_password),
            hashed_password.encode("ascii"),
        )
    except ValueError:
        return False
