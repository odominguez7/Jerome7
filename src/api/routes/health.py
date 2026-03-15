"""Health check endpoint."""

import os

from fastapi import APIRouter

from src.api.models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        env=os.getenv("APP_ENV", "development"),
        db_connected=True,
        agents_ready=bool(os.getenv("GEMINI_API_KEY")),
    )
