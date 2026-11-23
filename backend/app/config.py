"""Application settings, read from the backend/.env file."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env  (this file is in backend/app/, so go up one folder)
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "coderace_app"
    db_password: str
    db_name: str = "coderace"

    # Login tokens (JWT)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")


settings = Settings()