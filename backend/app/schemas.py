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