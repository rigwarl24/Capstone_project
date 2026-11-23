"""Match endpoints, called by the real-time engine (Member 5) with the X-Internal-Key header.

Flow:  POST /api/matches            -> start a duel, pick a problem, save ratings
       POST /api/matches/{id}/finish -> save the result and update both players' Elo
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from ..dependencies import DbConnection, InternalOnly
from ..elo import rating_changes
from ..schemas import MatchCreate, MatchDetail, MatchFinish

router = APIRouter(prefix="/api/matches", tags=["Matches"])


def _difficulty_for(average_elo: float) -> str:
    """Pick a difficulty that suits the players' average rating."""
    if average_elo < 1200:
        return "Easy"      # Bronze
    if average_elo < 1500:
        return "Medium"    # Silver
    return "Hard"          # Gold and Diamond


def _get_match(db: DbConnection, match_id: int) -> dict:
    row = db.execute(text("""
        SELECT m.id, m.status, m.game_mode, m.problem_id,
               p.title AS problem_title, p.difficulty,
               m.player1_id, u1.username AS player1_username,
               m.player1_elo_before, m.player1_elo_change,
               m.player2_id, u2.username AS player2_username,
               m.player2_elo_before, m.player2_elo_change,
               w.username AS winner_username,
               m.started_at, m.ended_at, m.duration_seconds
        FROM matches m
        JOIN problems p ON p.id = m.problem_id
        JOIN users u1 ON u1.id = m.player1_id
        JOIN users u2 ON u2.id = m.player2_id
        LEFT JOIN users w ON w.id = m.winner_id
        WHERE m.id = :id
    """), {"id": match_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return {
        "id": row.id, "status": row.status, "game_mode": row.game_mode,
        "problem_id": row.problem_id, "problem_title": row.problem_title,
        "difficulty": row.difficulty,
        "player1": {"id": row.player1_id, "username": row.player1_username,
                    "elo_before": row.player1_elo_before, "elo_change": row.player1_elo_change},
        "player2": {"id": row.player2_id, "username": row.player2_username,
                    "elo_before": row.player2_elo_before, "elo_change": row.player2_elo_change},
        "winner_username": row.winner_username,
        "started_at": row.started_at, "ended_at": row.ended_at,
        "duration_seconds": row.duration_seconds,
    }


@router.post("", response_model=MatchDetail, status_code=status.HTTP_201_CREATED,
             dependencies=[InternalOnly])
def create_match(data: MatchCreate, db: DbConnection):
    """Internal: start a match between two players and choose a problem for them."""
    if data.player1_username.lower() == data.player2_username.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="A player cannot play against themselves")

    players = []
    for username in (data.player1_username, data.player2_username):
        row = db.execute(text("SELECT id, elo_rating FROM users WHERE username = :u"),
                         {"u": username}).first()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"User '{username}' not found")
        players.append(row)
    p1, p2 = players

    busy = db.execute(text("""
        SELECT id FROM matches
        WHERE status = 'in_progress'
          AND (player1_id IN (:a, :b) OR player2_id IN (:a, :b))
        LIMIT 1
    """), {"a": p1.id, "b": p2.id}).first()
    if busy is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"A player is already in match {busy.id}")

    if data.problem_id is not None:
        problem = db.execute(
            text("SELECT id, game_mode FROM problems WHERE id = :id AND is_active"),
            {"id": data.problem_id},
        ).first()
        if problem is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Problem not found")
        problem_id, game_mode = problem.id, problem.game_mode
    else:
        game_mode = data.game_mode
        difficulty = data.difficulty or _difficulty_for((p1.elo_rating + p2.elo_rating) / 2)
        pick = text("""
            SELECT id FROM problems
            WHERE is_active AND game_mode = :mode AND (:difficulty IS NULL OR difficulty = :difficulty)
            ORDER BY RAND() LIMIT 1
        """)
        problem = db.execute(pick, {"mode": game_mode, "difficulty": difficulty}).first()
        if problem is None and data.difficulty is None:
            # no problem at the ideal difficulty: take any problem of this game mode
            problem = db.execute(pick, {"mode": game_mode, "difficulty": None}).first()
        if problem is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No problem available for this game mode")
        problem_id = problem.id

    result = db.execute(text("""
        INSERT INTO matches (problem_id, game_mode, player1_id, player2_id,
                             player1_elo_before, player2_elo_before)
        VALUES (:problem_id, :game_mode, :p1, :p2, :elo1, :elo2)
    """), {"problem_id": problem_id, "game_mode": game_mode, "p1": p1.id, "p2": p2.id,
           "elo1": p1.elo_rating, "elo2": p2.elo_rating})
    db.commit()
    return _get_match(db, result.lastrowid)


@router.post("/{match_id}/finish", response_model=MatchDetail, dependencies=[InternalOnly])
def finish_match(match_id: int, data: MatchFinish, db: DbConnection):
    """Internal: record the result and update both players' Elo and statistics.

    - winner_username set           -> that player wins
    - winner_username empty         -> draw (or, with abandoned=true, no rating change)
    """
    match = db.execute(text("""
        SELECT id, status, player1_id, player2_id, player1_elo_before, player2_elo_before
        FROM matches WHERE id = :id FOR UPDATE
    """), {"id": match_id}).first()
    if match is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if match.status != "in_progress":
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Match is already {match.status}")

    winner_id = None
    if data.winner_username is not None:
        row = db.execute(text("SELECT id FROM users WHERE username = :u"),
                         {"u": data.winner_username}).first()
        if row is None or row.id not in (match.player1_id, match.player2_id):
            db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="The winner must be one of the two players")
        winner_id = row.id

    rated = not (data.abandoned and winner_id is None)  # abandoned without winner = unrated
    if rated:
        if winner_id is None:
            score1 = 0.5
        else:
            score1 = 1.0 if winner_id == match.player1_id else 0.0
        change1, change2 = rating_changes(match.player1_elo_before, match.player2_elo_before,
                                          score1)
    else:
        score1, change1, change2 = None, 0, 0

    db.execute(text("""
        UPDATE matches
        SET status = :status, winner_id = :winner_id,
            player1_elo_change = :c1, player2_elo_change = :c2,
            ended_at = NOW(), duration_seconds = TIMESTAMPDIFF(SECOND, started_at, NOW())
        WHERE id = :id
    """), {"status": "abandoned" if data.abandoned else "finished", "winner_id": winner_id,
           "c1": change1, "c2": change2, "id": match_id})

    if rated:
        for player_id, change, score in ((match.player1_id, change1, score1),
                                         (match.player2_id, change2, 1 - score1)):
            db.execute(text("""
                UPDATE users
                SET elo_rating = GREATEST(0, elo_rating + :change),
                    matches_played = matches_played + 1,
                    wins   = wins   + :win,
                    losses = losses + :loss,
                    draws  = draws  + :draw
                WHERE id = :id
            """), {"change": change, "id": player_id, "win": int(score == 1),
                   "loss": int(score == 0), "draw": int(score == 0.5)})
    db.commit()
    return _get_match(db, match_id)


@router.get("/{match_id}", response_model=MatchDetail)
def get_match(match_id: int, db: DbConnection):
    """Details and result of one match (public)."""
    return _get_match(db, match_id)