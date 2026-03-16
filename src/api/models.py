"""Pydantic v2 schemas for request/response models."""

from datetime import datetime, date
from typing import Optional, Union

from pydantic import BaseModel, Field


# --- Request schemas ---

class PledgeRequest(BaseModel):
    name: str
    email: Optional[str] = None
    discord_id: Optional[str] = None
    timezone: str = "UTC"
    fitness_level: str = "beginner"  # beginner | returning | active
    available_windows: Optional[list[dict]] = None  # [{day, start_hour, end_hour}]

    # Demographics — all optional, never required
    age_bracket: Optional[str] = None   # 18-24 | 25-34 | 35-44 | 45-54 | 55+
    gender: Optional[str] = None        # male | female | other | skip
    country: Optional[str] = None       # auto-derived from timezone if not provided
    source: Optional[str] = None        # discord | openclaw | zeroclaw | web | api | mcp
    goal: Optional[str] = None          # stress_relief | focus | consistency | community | move_more | build_strength | destress | just_try
    invite_code: Optional[str] = None    # pod chain invite code
    github_username: Optional[str] = None


class LogSessionRequest(BaseModel):
    seven7_title: Optional[str] = None
    blocks_completed: Optional[Union[int, list[dict]]] = None  # int (count) or list of block dicts
    duration_minutes: int = 7
    note: Optional[str] = None


class EnergyCheckinRequest(BaseModel):
    energy: str  # low | medium | high


class FeedbackRequest(BaseModel):
    difficulty: Optional[int] = Field(None, ge=1, le=5)   # 1=easy, 5=hard
    enjoyment: Optional[int] = Field(None, ge=1, le=5)    # 1=low, 5=loved it
    body_note: Optional[str] = None                        # free text
    completed_blocks: Optional[int] = Field(None, ge=0, le=7)


class FeedbackResponse(BaseModel):
    feedback_id: str
    stored: bool = True

    model_config = {"from_attributes": True}


# --- Response schemas ---

class UserResponse(BaseModel):
    user_id: str
    name: str
    jerome_number: Optional[int] = None
    pledge_confirmed: bool = True
    pod_match_eta: str = "within 24 hours"
    country: Optional[str] = None
    auth_token: Optional[str] = None

    model_config = {"from_attributes": True}


class OnboardingSurveyRequest(BaseModel):
    role: Optional[str] = None              # developer, founder, student, designer, other
    experience_level: Optional[str] = None  # junior, mid, senior, lead
    primary_goal: Optional[str] = None      # stress_relief, focus, consistency, community
    preferred_time: Optional[str] = None    # morning, afternoon, evening
    burnout_level: Optional[int] = Field(None, ge=1, le=10)
    how_heard: Optional[str] = None         # github, twitter, friend, newsletter, hn, reddit, other


class OnboardingSurveyResponse(BaseModel):
    survey_id: str
    jerome_number: int
    onboarding_complete: bool = True

    model_config = {"from_attributes": True}


class Seven7Block(BaseModel):
    name: str
    duration_seconds: int
    instruction: str
    phase: Optional[str] = None
    why_today: Optional[str] = None


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
