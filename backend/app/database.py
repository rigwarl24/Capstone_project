"""MySQL connection (SQLAlchemy engine + PyMySQL driver)."""
from collections.abc import Iterator

from sqlalchemy import Connection, create_engine
from sqlalchemy.engine import URL

from .config import settings

DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=settings.db_user,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
    query={"charset": "utf8mb4"},
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # reconnect automatically if MySQL closed an idle connection
    pool_recycle=3600,
)


def get_db() -> Iterator[Connection]:
    """FastAPI dependency: one database connection per request."""
    with engine.connect() as connection:
        yield connection