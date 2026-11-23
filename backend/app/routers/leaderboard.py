"""Global leaderboard."""
from fastapi import APIRouter, Query
from sqlalchemy import text

from ..dependencies import DbConnection
from ..schemas import LeaderboardEntry

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])


@router.get("", response_model=list[LeaderboardEntry])
def get_leaderboard(
    db: DbConnection,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Players ranked by Elo rating (ties: more wins first, then earlier account)."""
    rows = db.execute(
        text("""
            SELECT
                username, elo_rating, rank_tier, matches_played, wins,
                ROUND(IF(matches_played = 0, 0, wins * 100 / matches_played), 1) AS win_rate
            FROM users
            ORDER BY elo_rating DESC, wins DESC, id ASC
            LIMIT :limit OFFSET :offset
        """),
        {"limit": limit, "offset": offset},
    ).mappings().all()
    return [{"position": offset + i + 1, **row} for i, row in enumerate(rows)]