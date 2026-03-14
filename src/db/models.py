"""SQLAlchemy ORM models for Jerome 7 / YU Show Up."""

import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Enum, ForeignKey,
    JSON, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class FitnessLevel(str, enum.Enum):
    beginner = "beginner"
    returning = "returning"
    active = "active"


class EnergyLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class PodMemberStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    graduated = "graduated"


class DeliveryChannel(str, enum.Enum):
    cli = "cli"
    discord = "discord"
    web = "web"
    api = "api"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    discord_id = Column(String, unique=True, nullable=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    timezone = Column(String, nullable=False, default="UTC")
    fitness_level = Column(Enum(FitnessLevel), nullable=False, default=FitnessLevel.beginner)
    energy_today = Column(Enum(EnergyLevel), nullable=True)
    available_windows = Column(JSON, nullable=True)  # [{day, start_hour, end_hour}]
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = relationship("Session", back_populates="user")
    streak = relationship("Streak", back_populates="user", uselist=False)
    seven7_sessions = relationship("Seven7Session", back_populates="user")
    nudges = relationship("Nudge", back_populates="user")
    pod_memberships = relationship("PodMember", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow)
    seven7_title = Column(String, nullable=True)
    blocks_completed = Column(JSON, nullable=True)
    duration_minutes = Column(Integer, default=7)
    note = Column(Text, nullable=True)

    user = relationship("User", back_populates="sessions")


class Streak(Base):
    __tablename__ = "streaks"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_session_date = Column(Date, nullable=True)
    total_sessions = Column(Integer, default=0)
    streak_broken_count = Column(Integer, default=0)
    saves_used = Column(Integer, default=0)
    last_save_date = Column(Date, nullable=True)

    user = relationship("User", back_populates="streak")


class Pod(Base):
    __tablename__ = "pods"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    timezone = Column(String, nullable=True)
    fitness_level_range = Column(String, nullable=True)
    discord_channel_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("PodMember", back_populates="pod")


class PodMember(Base):
    __tablename__ = "pod_members"

    id = Column(String, primary_key=True, default=generate_uuid)
    pod_id = Column(String, ForeignKey("pods.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(PodMemberStatus), default=PodMemberStatus.active)

    pod = relationship("Pod", back_populates="members")
    user = relationship("User", back_populates="pod_memberships")

    __table_args__ = (
        UniqueConstraint("pod_id", "user_id", name="uq_pod_user"),
    )


class Seven7Session(Base):
    __tablename__ = "seven7_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    greeting = Column(Text, nullable=True)
    session_title = Column(String, nullable=True)
    closing = Column(Text, nullable=True)
    blocks = Column(JSON, nullable=True)
    delivered_via = Column(Enum(DeliveryChannel), nullable=True)
    used = Column(Boolean, default=False)

    user = relationship("User", back_populates="seven7_sessions")


class Nudge(Base):
    __tablename__ = "nudges"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    channel = Column(String, nullable=True)
    message_text = Column(Text, nullable=True)
    opened = Column(Boolean, default=False)
    acted_on = Column(Boolean, default=False)

    user = relationship("User", back_populates="nudges")


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
