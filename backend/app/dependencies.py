"""Shared FastAPI dependencies."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import Connection, text

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