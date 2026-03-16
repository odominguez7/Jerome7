"""Health check endpoint."""

import os

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.models import HealthResponse
from src.db.database import get_db

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        env=os.getenv("APP_ENV", "development"),
        db_connected=db_ok,
        agents_ready=bool(os.getenv("GEMINI_API_KEY")),
    )
