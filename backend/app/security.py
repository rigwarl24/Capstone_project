"""Password hashing (scrypt) and login tokens (JWT)."""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from .config import settings

# scrypt parameters - OWASP recommended setting (N=2^14, r=8, p=5)
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 5
_SCRYPT_MAXMEM = 64 * 1024 * 1024
_KEY_LENGTH = 64
_SALT_BYTES = 16


def _b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt, n=n, r=r, p=p,
        maxmem=_SCRYPT_MAXMEM, dklen=_KEY_LENGTH,
    )


def hash_password(password: str) -> str:
    """Return a salted scrypt hash, stored as: scrypt$n$r$p$salt$hash"""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = _scrypt(password, salt, _SCRYPT_N, _SCRYPT_R, _SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a password against a stored hash (constant-time comparison)."""
    try:
        algorithm, n, r, p, salt_b64, digest_b64 = stored_hash.split("$")
        if algorithm != "scrypt":
            return False
        expected = base64.b64decode(digest_b64)
        actual = _scrypt(password, base64.b64decode(salt_b64), int(n), int(r), int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Used to keep login time the same whether or not the username exists
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def create_access_token(user_id: int) -> str:
    """Create a signed JWT that identifies the user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Return the user id from a valid token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None