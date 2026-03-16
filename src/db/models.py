"""SQLAlchemy ORM models for Jerome 7 / YU Show Up."""

import enum
import uuid
from datetime import datetime, date, timezone

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Enum, ForeignKey,
    JSON, Text, UniqueConstraint, Float, Index,
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


class AgeBracket(str, enum.Enum):
    age_18_24 = "18-24"
    age_25_34 = "25-34"
    age_35_44 = "35-44"
    age_45_54 = "45-54"
    age_55_plus = "55+"


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    skip = "skip"


class UserSource(str, enum.Enum):
    discord = "discord"
    openclaw = "openclaw"
    zeroclaw = "zeroclaw"
    web = "web"
    api = "api"
    mcp = "mcp"


class UserGoal(str, enum.Enum):
    move_more = "move_more"
    build_strength = "build_strength"
    destress = "destress"
    just_try = "just_try"
    stress_relief = "stress_relief"
    focus = "focus"
    consistency = "consistency"
    community = "community"


class DeliveryChannel(str, enum.Enum):
    cli = "cli"
    discord = "discord"
    web = "web"
    api = "api"


class SessionType(str, enum.Enum):
    breathwork = "breathwork"
    meditation = "meditation"
    reflection = "reflection"
    preparation = "preparation"


class UserRole(str, enum.Enum):
    founder = "founder"
    early_adopter = "early_adopter"
    member = "member"
    ambassador = "ambassador"


class ExperienceLevel(str, enum.Enum):
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"


class SocialPlatform(str, enum.Enum):
    twitter = "twitter"
    linkedin = "linkedin"
    github = "github"
    discord = "discord"
    reddit = "reddit"
    instagram = "instagram"


class AgentType(str, enum.Enum):
    coach = "coach"
    nudge = "nudge"
    streak = "streak"
    community = "community"
    scheduler = "scheduler"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    jerome_number = Column(Integer, unique=True, nullable=True, index=True)
    discord_id = Column(String, unique=True, nullable=True, index=True)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=True)
    email_verified = Column(Boolean, default=False)
    email_verify_token = Column(String, nullable=True)
    timezone = Column(String, nullable=False, default="UTC")
    fitness_level = Column(Enum(FitnessLevel), nullable=False, default=FitnessLevel.beginner)
    energy_today = Column(Enum(EnergyLevel), nullable=True)
    available_windows = Column(JSON, nullable=True)  # [{day, start_hour, end_hour}]

    # Demographics — collected at pledge, all optional
    age_bracket = Column(Enum(AgeBracket), nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    country = Column(String, nullable=True)          # auto-derived from timezone
    source = Column(Enum(UserSource), nullable=True)  # how they found jerome7
    goal = Column(Enum(UserGoal), nullable=True)
    invited_by = Column(String, nullable=True)  # user_id of inviter

    # Jerome# identity
    role = Column(Enum(UserRole), default=UserRole.member)
    github_username = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    onboarding_complete = Column(Boolean, default=False)

    # Auth
    auth_token = Column(String, nullable=True, unique=True, index=True)

    # Location (for globe)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    city = Column(String, nullable=True)

    # Bot protection
    fingerprint = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    sessions = relationship("Session", back_populates="user")
    streak = relationship("Streak", back_populates="user", uselist=False)
    seven7_sessions = relationship("Seven7Session", back_populates="user")
    nudges = relationship("Nudge", back_populates="user")
    pod_memberships = relationship("PodMember", back_populates="user")
    feedback = relationship("SessionFeedback", back_populates="user")
    onboarding_survey = relationship("OnboardingSurvey", back_populates="user", uselist=False)


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_logged_at", "logged_at"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
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
    scheduled_time = Column(JSON, nullable=True)  # {"hour": int, "minute": int, "timezone": str}
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    members = relationship("PodMember", back_populates="pod")


class PodMember(Base):
    __tablename__ = "pod_members"

    id = Column(String, primary_key=True, default=generate_uuid)
    pod_id = Column(String, ForeignKey("pods.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
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
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
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
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    channel = Column(String, nullable=True)
    message_text = Column(Text, nullable=True)
    opened = Column(Boolean, default=False)
    acted_on = Column(Boolean, default=False)

    user = relationship("User", back_populates="nudges")


class SessionFeedback(Base):
    __tablename__ = "session_feedback"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_date = Column(Date, default=date.today)
    difficulty_rating = Column(Integer, nullable=True)   # 1-5
    enjoyment_rating = Column(Integer, nullable=True)    # 1-5
    body_note = Column(Text, nullable=True)              # "knees hurt", "felt great"
    completed_blocks = Column(Integer, nullable=True)    # how many of 7 blocks done
    skipped_phases = Column(Text, nullable=True)         # comma-separated phases skipped
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="feedback")


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, unique=True, nullable=False, index=True)
    inviter_id = Column(String, ForeignKey("users.id"), nullable=False)
    used_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    used_at = Column(DateTime, nullable=True)

    inviter = relationship("User", foreign_keys=[inviter_id])
    used_by = relationship("User", foreign_keys=[used_by_id])


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class OnboardingSurvey(Base):
    __tablename__ = "onboarding_surveys"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    role = Column(String, nullable=True)             # developer, founder, student, designer, other
    experience_level = Column(Enum(ExperienceLevel), nullable=True)
    primary_goal = Column(String, nullable=True)     # stress_relief, focus, consistency, community
    preferred_time = Column(String, nullable=True)   # morning, afternoon, evening
    burnout_level = Column(Integer, nullable=True)   # 1-10
    how_heard = Column(String, nullable=True)        # github, twitter, friend, newsletter, hn, reddit, other
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="onboarding_survey")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    agent_type = Column(Enum(AgentType), nullable=False)
    action = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SocialShare(Base):
    __tablename__ = "social_shares"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    platform = Column(Enum(SocialPlatform), nullable=False)
    share_type = Column(String, nullable=False)  # streak_milestone, session_complete, badge_earned
    content = Column(Text, nullable=True)
    external_url = Column(Text, nullable=True)
    shared_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmailSubscriber(Base):
    __tablename__ = "email_subscribers"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    subscribed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    unsubscribed = Column(Boolean, default=False)
