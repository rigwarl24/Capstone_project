"""User endpoints: public profiles, profile updates and match history."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ..dependencies import USER_COLUMNS, CurrentUser, DbConnection
from ..schemas import MatchHistoryItem, UserProfile, UserPublic, UserUpdate
from ..security import hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["Users"])

# win_rate = wins as a percentage of matches played (0 if no matches yet)
PROFILE_COLUMNS = """
    id, username, elo_rating, rank_tier, matches_played, wins, losses, draws,
    ROUND(IF(matches_played = 0, 0, wins * 100 / matches_played), 1) AS win_rate,
    created_at
"""


def _find_user_id(db: DbConnection, username: str) -> int:
    row = db.execute(
        text("SELECT id FROM users WHERE username = :username"), {"username": username}
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return row.id


@router.patch("/me", response_model=UserPublic)
def update_my_account(data: UserUpdate, current_user: CurrentUser, db: DbConnection):
    """Change your email and/or password. Requires your current password."""
    if data.email is None and data.new_password is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Nothing to update: give an email or a new_password")

    row = db.execute(text("SELECT password_hash FROM users WHERE id = :id"),
                     {"id": current_user["id"]}).first()
    if not verify_password(data.current_password, row.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Current password is incorrect")

    changes, params = [], {"id": current_user["id"]}
    if data.email is not None:
        changes.append("email = :email")
        params["email"] = data.email.lower()
    if data.new_password is not None:
        changes.append("password_hash = :password_hash")
        params["password_hash"] = hash_password(data.new_password)

    try:
        db.execute(text(f"UPDATE users SET {', '.join(changes)} WHERE id = :id"), params)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Email is already registered") from None

    updated = db.execute(text(f"SELECT {USER_COLUMNS} FROM users WHERE id = :id"),
                         {"id": current_user["id"]}).mappings().one()
    return dict(updated)


@router.get("/{username}", response_model=UserProfile)
def get_profile(username: str, db: DbConnection):
    """Public profile and statistics of any player."""
    row = db.execute(
        text(f"SELECT {PROFILE_COLUMNS} FROM users WHERE username = :username"),
        {"username": username},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return dict(row)


@router.get("/{username}/matches", response_model=list[MatchHistoryItem])
def get_match_history(
    username: str,
    db: DbConnection,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """A player's matches, newest first."""
    user_id = _find_user_id(db, username)
    rows = db.execute(
        text("""
            SELECT
                m.id AS match_id,
                opp.username AS opponent,
                p.title AS problem_title,
                p.difficulty,
                m.game_mode,
                m.status,
                CASE
                    WHEN m.status = 'in_progress' THEN 'in_progress'
                    WHEN m.winner_id IS NULL AND m.status = 'abandoned' THEN 'abandoned'
                    WHEN m.winner_id IS NULL THEN 'draw'
                    WHEN m.winner_id = :uid THEN 'win'
                    ELSE 'loss'
                END AS result,
                IF(m.player1_id = :uid, m.player1_elo_before, m.player2_elo_before) AS elo_before,
                IF(m.player1_id = :uid, m.player1_elo_change, m.player2_elo_change) AS elo_change,
                m.started_at,
                m.ended_at,
                m.duration_seconds
            FROM matches m
            JOIN users opp
              ON opp.id = IF(m.player1_id = :uid, m.player2_id, m.player1_id)
            JOIN problems p ON p.id = m.problem_id
            WHERE m.player1_id = :uid OR m.player2_id = :uid
            ORDER BY m.started_at DESC, m.id DESC
            LIMIT :limit OFFSET :offset
        """),
        {"uid": user_id, "limit": limit, "offset": offset},
    ).mappings().all()
    return [dict(r) for r in rows]