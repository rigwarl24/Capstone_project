"""Request and response data shapes (validated automatically by FastAPI)."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$",
                          examples=["ahmad_rahimi"])
    email: EmailStr = Field(max_length=255, examples=["ahmad.rahimi@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["Herat2026pass"])


class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    elo_rating: int
    rank_tier: str
    matches_played: int
    wins: int
    losses: int
    draws: int
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    """Public profile - visible to everyone (no email)."""
    id: int
    username: str
    elo_rating: int
    rank_tier: str
    matches_played: int
    wins: int
    losses: int
    draws: int
    win_rate: float
    created_at: datetime


class UserUpdate(BaseModel):
    """Change email and/or password. The current password is always required."""
    current_password: str = Field(min_length=1, max_length=128)
    email: EmailStr | None = Field(default=None, max_length=255)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class MatchHistoryItem(BaseModel):
    match_id: int
    opponent: str
    problem_title: str
    difficulty: str
    game_mode: str
    status: str
    result: str          # "win", "loss", "draw", "abandoned" or "in_progress"
    elo_before: int
    elo_change: int | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None


class LeaderboardEntry(BaseModel):
    position: int
    username: str
    elo_rating: int
    rank_tier: str
    matches_played: int
    wins: int
    win_rate: float

    

class PublicTestCase(BaseModel):
    input: list
    expected: object


class FullTestCase(PublicTestCase):
    hidden: bool


class ProblemPublic(BaseModel):
    """What players see: description, starter code and only the visible tests."""
    id: int
    slug: str
    title: str
    description: str
    difficulty: str
    game_mode: str
    function_name: str
    starter_code: str
    time_limit_ms: int
    memory_limit_mb: int
    visible_tests: list[PublicTestCase]


class ProblemWithTests(ProblemPublic):
    """For the code-execution engine only: includes the hidden tests."""
    all_tests: list[FullTestCase]


class MatchCreate(BaseModel):
    player1_username: str
    player2_username: str
    game_mode: str = Field(default="speed_duel", pattern="^(speed_duel|bug_hunt|optimization)$")
    difficulty: str | None = Field(default=None, pattern="^(Easy|Medium|Hard)$")
    problem_id: int | None = None


class MatchFinish(BaseModel):
    winner_username: str | None = Field(
        default=None, description="Leave empty (null) for a draw or an abandoned match")
    abandoned: bool = Field(
        default=False, description="True if the match ended early (e.g. a player left)")


class MatchPlayer(BaseModel):
    id: int
    username: str
    elo_before: int
    elo_change: int | None


class MatchDetail(BaseModel):
    id: int
    status: str
    game_mode: str
    problem_id: int
    problem_title: str
    difficulty: str
    player1: MatchPlayer
    player2: MatchPlayer
    winner_username: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None