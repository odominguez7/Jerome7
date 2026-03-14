"""UserContext — the shared state object passed to every agent."""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Streak, Session, Pod, PodMember, Seven7Session, Nudge


MILESTONES = [7, 14, 30, 50, 100, 200, 365]


@dataclass
class UserContext:
    user_id: str
    name: str
    timezone: str
    fitness_level: str
    energy_today: Optional[str] = None
    available_windows: Optional[list] = None
    current_streak: int = 0
    longest_streak: int = 0
    last_session: Optional[dict] = None
    sessions_last_7_days: list = field(default_factory=list)
    skip_history: list = field(default_factory=list)
    pod: Optional[dict] = None
    pod_activity_24h: list = field(default_factory=list)
    last_nudge_at: Optional[datetime] = None
    milestone_next: int = 7
    saves_remaining: int = 1
    todays_seven7: Optional[dict] = None


def build_user_context(user_id: str, db: DBSession) -> UserContext:
    """Fetch all required data and assemble a UserContext."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()

    # Last session
    last_session_obj = (
        db.query(Session)
        .filter(Session.user_id == user_id)
        .order_by(Session.logged_at.desc())
        .first()
    )
    last_session = None
    if last_session_obj:
        last_session = {
            "title": last_session_obj.seven7_title,
            "logged_at": last_session_obj.logged_at.isoformat() if last_session_obj.logged_at else None,
        }

    # Sessions last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_sessions = (
        db.query(Session)
        .filter(Session.user_id == user_id, Session.logged_at >= seven_days_ago)
        .order_by(Session.logged_at.desc())
        .all()
    )
    sessions_last_7 = [
        {"title": s.seven7_title, "date": s.logged_at.date().isoformat() if s.logged_at else None}
        for s in recent_sessions
    ]

    # Pod info
    pod_info = None
    pod_activity = []
    membership = (
        db.query(PodMember)
        .filter(PodMember.user_id == user_id, PodMember.status == "active")
        .first()
    )
    if membership:
        pod = db.query(Pod).filter(Pod.id == membership.pod_id).first()
        if pod:
            members = db.query(PodMember).filter(PodMember.pod_id == pod.id).all()
            pod_info = {
                "id": pod.id,
                "name": pod.name,
                "members": [m.user_id for m in members],
            }

    # Next milestone
    current = streak.current_streak if streak else 0
    next_milestone = 7
    for m in MILESTONES:
        if current < m:
            next_milestone = m
            break
    else:
        next_milestone = current + 100  # beyond 365

    # Saves remaining
    saves_remaining = 1
    if streak and streak.last_save_date:
        days_since_save = (date.today() - streak.last_save_date).days
        if days_since_save < 30:
            saves_remaining = 0

    # Today's Seven 7
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays = (
        db.query(Seven7Session)
        .filter(Seven7Session.user_id == user_id, Seven7Session.generated_at >= today_start)
        .first()
    )
    todays_seven7 = None
    if todays:
        todays_seven7 = {
            "title": todays.session_title,
            "greeting": todays.greeting,
            "blocks": todays.blocks,
            "closing": todays.closing,
        }

    # Last nudge
    last_nudge = (
        db.query(Nudge)
        .filter(Nudge.user_id == user_id)
        .order_by(Nudge.sent_at.desc())
        .first()
    )

    return UserContext(
        user_id=user.id,
        name=user.name,
        timezone=user.timezone,
        fitness_level=user.fitness_level.value if user.fitness_level else "beginner",
        energy_today=user.energy_today.value if user.energy_today else None,
        available_windows=user.available_windows or [],
        current_streak=streak.current_streak if streak else 0,
        longest_streak=streak.longest_streak if streak else 0,
        last_session=last_session,
        sessions_last_7_days=sessions_last_7,
        pod=pod_info,
        pod_activity_24h=pod_activity,
        last_nudge_at=last_nudge.sent_at if last_nudge else None,
        milestone_next=next_milestone,
        saves_remaining=saves_remaining,
        todays_seven7=todays_seven7,
    )


def context_to_prompt_string(ctx: UserContext) -> str:
    """Serialize UserContext into a compact string for Claude input."""
    lines = [
        f"Name: {ctx.name}",
        f"Streak: {ctx.current_streak} days (longest: {ctx.longest_streak})",
        f"Fitness level: {ctx.fitness_level}",
    ]

    if ctx.energy_today:
        lines.append(f"Energy today: {ctx.energy_today}")

    if ctx.last_session:
        lines.append(f"Last session: {ctx.last_session.get('title', 'unknown')}")

    days_since_rest = len(ctx.sessions_last_7_days)
    lines.append(f"Sessions in last 7 days: {days_since_rest}")

    if ctx.pod:
        active_count = len(ctx.pod_activity_24h)
        lines.append(f"Pod: {ctx.pod.get('name', 'none')} ({active_count} members active today)")

    lines.append(f"Next milestone: {ctx.milestone_next} days")

    return "\n".join(lines)
