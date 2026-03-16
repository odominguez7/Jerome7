"""Database engine and session management."""

import os

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from src.db.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jerome7.db")

_is_sqlite = "sqlite" in DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
    **({"pool_size": 5, "max_overflow": 5} if not _is_sqlite else {}),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_add_columns():
    """Add new columns to existing tables if they're missing (lightweight migration)."""
    inspector = inspect(engine)

    # Columns to add to the 'users' table (name, SQL type)
    desired_user_cols = {
        "age_bracket": "VARCHAR",
        "gender": "VARCHAR",
        "country": "VARCHAR",
        "source": "VARCHAR",
        "goal": "VARCHAR",
        "invited_by": "VARCHAR",
        "jerome_number": "INTEGER",
        "display_name": "VARCHAR",
        "role": "VARCHAR",
        "github_username": "VARCHAR",
        "avatar_url": "VARCHAR",
        "onboarding_complete": "BOOLEAN",
        "latitude": "FLOAT",
        "longitude": "FLOAT",
        "city": "VARCHAR",
        "auth_token": "VARCHAR",
    }

    if "users" in inspector.get_table_names():
        existing = {col["name"] for col in inspector.get_columns("users")}
        with engine.begin() as conn:
            for col_name, col_type in desired_user_cols.items():
                if col_name not in existing:
                    conn.execute(text(
                        f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"
                    ))

    # Pods table migrations
    desired_pod_cols = {
        "scheduled_time": "JSON",
        "last_active_at": "TIMESTAMP",
        "fitness_level_range": "VARCHAR",
        "discord_channel_id": "VARCHAR",
    }
    if "pods" in inspector.get_table_names():
        existing = {col["name"] for col in inspector.get_columns("pods")}
        with engine.begin() as conn:
            for col_name, col_type in desired_pod_cols.items():
                if col_name not in existing:
                    conn.execute(text(
                        f"ALTER TABLE pods ADD COLUMN {col_name} {col_type}"
                    ))


def init_db():
    """Create all tables + run lightweight migrations."""
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
