"""Shared FastAPI dependencies."""
import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import Connection, text

from .config import settings
from .database import get_db
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

USER_COLUMNS = (
    "id, username, email, elo_rating, rank_tier, "
    "matches_played, wins, losses, draws, created_at"
)

DbConnection = Annotated[Connection, Depends(get_db)]


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbConnection) -> dict:
    """Return the logged-in user, or reply 401 if the token is missing/invalid."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise unauthorized

    row = db.execute(
        text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"), {"id": user_id}
    ).mappings().first()
    if row is None:
        raise unauthorized
    return dict(row)


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_internal_key(x_internal_key: Annotated[str | None, Header()] = None) -> None:
    """Allow only trusted servers (e.g. the real-time engine) that send X-Internal-Key."""
    if x_internal_key is None or not hmac.compare_digest(
        x_internal_key.encode(), settings.internal_api_key.encode()
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Missing or invalid internal API key")


InternalOnly = Depends(require_internal_key)