"""CodeRace REST API - entry point.

Run from the backend folder:
    uvicorn app.main:app --reload
"""
import logging

from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .database import engine

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="CodeRace API",
    description="Database & REST API for CodeRace: Real-Time Coding Duels",
    version="0.1.0",
)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Check that the API is running and can reach the MySQL database."""
    try:
        with engine.connect() as connection:
            tables = connection.execute(text("SHOW TABLES")).scalars().all()
    except SQLAlchemyError as error:
        logger.error("Database connection failed: %s", error)
        raise HTTPException(status_code=503, detail="Database connection failed") from error

    return {"status": "ok", "database": "connected", "tables": sorted(tables)}