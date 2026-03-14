"""Database engine and session management."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jerome7.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables. Used for development; use Alembic in production."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
