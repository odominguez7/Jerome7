"""Pydantic v2 schemas for request/response models."""

from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


# --- Request schemas ---

class PledgeRequest(BaseModel):
    name: str
    email: Optional[str] = None
    timezone: str = "UTC"
    fitness_level: str = "beginner"  # beginner | returning | active
    available_windows: Optional[list[dict]] = None  # [{day, start_hour, end_hour}]


class LogSessionRequest(BaseModel):
    seven7_title: Optional[str] = None
    blocks_completed: Optional[list[dict]] = None
    duration_minutes: int = 7
    note: Optional[str] = None


class EnergyCheckinRequest(BaseModel):
    energy: str  # low | medium | high


# --- Response schemas ---

class UserResponse(BaseModel):
    user_id: str
    name: str
    pledge_confirmed: bool = True
    pod_match_eta: str = "within 24 hours"

    model_config = {"from_attributes": True}


class Seven7Block(BaseModel):
    name: str
    duration_seconds: int
    instruction: str
    why_today: str


class Seven7Response(BaseModel):
    user_id: str
    generated_at: datetime
    greeting: str
    session_title: str
    closing: str
    blocks: list[Seven7Block]
    total_seconds: int = Field(default=420)

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    session_id: str
    streak_updated: bool = True
    new_streak: int
    milestone_reached: Optional[int] = None

    model_config = {"from_attributes": True}


class StreakResponse(BaseModel):
    user_id: str
    username: str
    current_streak: int
    longest_streak: int
    total_sessions: int
    last_session_date: Optional[date] = None
    streak_broken_count: int = 0
    saves_remaining: int = 1
    next_milestone: int = 7
    chain: list[str] = []  # last 30 days: "filled" or "empty"

    model_config = {"from_attributes": True}


class PodMemberInfo(BaseModel):
    name: str
    current_streak: int
    last_active: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PodResponse(BaseModel):
    pod_id: str
    pod_name: str
    members: list[PodMemberInfo]
    shared_windows: Optional[list[dict]] = None
    recent_activity: list[str] = []

    model_config = {"from_attributes": True}


class NudgeResponse(BaseModel):
    subject: str
    body: str
    cta: str

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str = "ok"
    env: str = "development"
    db_connected: bool = True
    agents_ready: bool = True
