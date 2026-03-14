"""UserContext — the shared state object passed to every agent."""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Streak, Session, Pod, PodMember, Seven7Session, Nudge, SessionFeedback


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
    recent_feedback: list = field(default_factory=list)  # last 5 session feedbacks


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

    # Skip history — find hours the user typically skips sessions
    # Look at the last 30 days and find days with no session logged
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    all_sessions = (
        db.query(Session)
        .filter(Session.user_id == user_id, Session.logged_at >= thirty_days_ago)
        .order_by(Session.logged_at.asc())
        .all()
    )
    session_dates = set()
    for s in all_sessions:
        if s.logged_at:
            session_dates.add(s.logged_at.date())

    skip_history = []
    check_date = thirty_days_ago.date()
    today = date.today()
    while check_date <= today:
        if check_date not in session_dates:
            skip_history.append(check_date.isoformat())
        check_date += timedelta(days=1)

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

    # Recent feedback (last 5)
    recent_fb = (
        db.query(SessionFeedback)
        .filter(SessionFeedback.user_id == user_id)
        .order_by(SessionFeedback.created_at.desc())
        .limit(5)
        .all()
    )
    recent_feedback = [
        {
            "date": fb.session_date.isoformat() if fb.session_date else None,
            "difficulty": fb.difficulty_rating,
            "enjoyment": fb.enjoyment_rating,
            "body_note": fb.body_note,
            "completed_blocks": fb.completed_blocks,
            "skipped_phases": fb.skipped_phases,
        }
        for fb in recent_fb
    ]

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
        skip_history=skip_history,
        pod=pod_info,
        pod_activity_24h=pod_activity,
        last_nudge_at=last_nudge.sent_at if last_nudge else None,
        milestone_next=next_milestone,
        saves_remaining=saves_remaining,
        todays_seven7=todays_seven7,
        recent_feedback=recent_feedback,
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

    # Feedback-based learning
    if ctx.recent_feedback:
        lines.append("")
        lines.append("RECENT SESSION FEEDBACK:")
        body_complaints = []
        difficulty_sum = 0
        enjoyment_sum = 0
        completion_sum = 0
        rated_count = 0
        for fb in ctx.recent_feedback:
            parts = []
            if fb.get("date"):
                parts.append(fb["date"])
            if fb.get("difficulty"):
                parts.append(f"difficulty={fb['difficulty']}/5")
                difficulty_sum += fb["difficulty"]
                rated_count += 1
            if fb.get("enjoyment"):
                parts.append(f"enjoyment={fb['enjoyment']}/5")
                enjoyment_sum += fb["enjoyment"]
            if fb.get("completed_blocks") is not None:
                parts.append(f"completed={fb['completed_blocks']}/7")
                completion_sum += fb["completed_blocks"]
            if fb.get("body_note"):
                parts.append(f'note="{fb["body_note"]}"')
                body_complaints.append(fb["body_note"])
            if fb.get("skipped_phases"):
                parts.append(f"skipped={fb['skipped_phases']}")
            if parts:
                lines.append(f"  - {', '.join(parts)}")

        if rated_count > 0:
            lines.append(f"  Avg difficulty: {difficulty_sum / rated_count:.1f}/5")
            lines.append(f"  Avg enjoyment: {enjoyment_sum / rated_count:.1f}/5")
            lines.append(f"  Avg completion: {completion_sum / rated_count:.1f}/7 blocks")
        if body_complaints:
            lines.append(f"  Body notes: {'; '.join(body_complaints)}")

    return "\n".join(lines)
