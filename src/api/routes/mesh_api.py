"""Agent Mesh API — REST endpoints for mesh, personal agents, checkups, social."""

import hashlib
from datetime import datetime, timedelta, date, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.db.models import (
    User, Streak, Session as SessionModel, Nudge, PodMember, SessionFeedback,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Try importing mesh / personal agent / social modules (built in parallel).
# If they don't exist yet, we fall back to direct DB queries.
# ---------------------------------------------------------------------------
try:
    from src.agents.mesh import AgentMesh  # type: ignore
    _MESH_AVAILABLE = True
except Exception:
    _MESH_AVAILABLE = False

try:
    from src.agents.personal_agent import PersonalAgent  # type: ignore
    _PERSONAL_AGENT_AVAILABLE = True
except Exception:
    _PERSONAL_AGENT_AVAILABLE = False

try:
    from src.agents.daily_checkup import DailyCheckup  # type: ignore
    _CHECKUP_AVAILABLE = True
except Exception:
    _CHECKUP_AVAILABLE = False

try:
    from src.agents.social import SocialEngine  # type: ignore
    _SOCIAL_AVAILABLE = True
except Exception:
    _SOCIAL_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _wellness_score(db: DBSession, user_id: str) -> int:
    """Compute a 0-100 wellness score from streak, session recency, feedback."""
    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    if not streak:
        return 0

    score = 0
    # Streak component (max 40)
    score += min(streak.current_streak * 5, 40)

    # Recency component (max 30)
    if streak.last_session_date:
        days_since = (date.today() - streak.last_session_date).days
        if days_since == 0:
            score += 30
        elif days_since == 1:
            score += 20
        elif days_since <= 3:
            score += 10

    # Consistency component (max 30)
    if streak.total_sessions > 0:
        consistency = min(streak.total_sessions / max(streak.total_sessions + streak.streak_broken_count, 1), 1.0)
        score += int(consistency * 30)

    return min(score, 100)


def _burnout_risk(db: DBSession, user_id: str) -> dict:
    """Detect burnout risk signals for a user."""
    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    if not streak:
        return {"risk": "unknown", "score": 0, "signals": ["No streak data"]}

    signals = []
    risk_score = 0

    # Long streak without breaks can signal burnout
    if streak.current_streak > 30:
        signals.append("Extended streak (30+ days) - check for fatigue")
        risk_score += 15

    # Recent difficulty ratings trending high
    recent_feedback = (
        db.query(SessionFeedback)
        .filter(SessionFeedback.user_id == user_id)
        .order_by(SessionFeedback.created_at.desc())
        .limit(5)
        .all()
    )
    if recent_feedback:
        avg_diff = sum(f.difficulty_rating or 3 for f in recent_feedback) / len(recent_feedback)
        if avg_diff >= 4.5:
            signals.append(f"High difficulty ratings (avg {avg_diff:.1f}/5)")
            risk_score += 30
        elif avg_diff >= 3.5:
            signals.append(f"Moderate difficulty (avg {avg_diff:.1f}/5)")
            risk_score += 10

    # Declining session completions
    if recent_feedback and len(recent_feedback) >= 3:
        completions = [f.completed_blocks or 7 for f in recent_feedback]
        if completions[0] < completions[-1]:
            signals.append("Declining block completions")
            risk_score += 20

    # Multiple streak breaks
    if streak.streak_broken_count >= 3:
        signals.append(f"{streak.streak_broken_count} streak breaks - possible frustration cycle")
        risk_score += 15

    # Days since last session
    if streak.last_session_date:
        gap = (date.today() - streak.last_session_date).days
        if gap >= 3:
            signals.append(f"No session in {gap} days")
            risk_score += 25

    risk_score = min(risk_score, 100)
    if risk_score >= 60:
        level = "high"
    elif risk_score >= 30:
        level = "moderate"
    else:
        level = "low"

    if not signals:
        signals.append("No burnout signals detected")

    return {"risk": level, "score": risk_score, "signals": signals}


def _adaptive_question(db: DBSession, user_id: str) -> dict:
    """Pick today's adaptive checkup question based on user state."""
    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    wellness = _wellness_score(db, user_id)

    # Pool of questions by category
    questions = {
        "new_user": [
            "How are you feeling about starting your movement journey?",
            "What made you decide to try 7 minutes today?",
        ],
        "streak_building": [
            "You're building momentum. What's helping you show up?",
            "How does your body feel compared to when you started?",
        ],
        "high_wellness": [
            "You're in a great rhythm. What would you tell someone just starting?",
            "What has surprised you most about showing up daily?",
        ],
        "low_wellness": [
            "No judgment. What's been getting in the way?",
            "What's one thing that would make it easier to show up tomorrow?",
        ],
        "streak_risk": [
            "It's been a few days. What happened?",
            "Just 7 minutes. What's the smallest step you could take right now?",
        ],
    }

    # Select category
    if not streak or streak.total_sessions == 0:
        cat = "new_user"
    elif streak.last_session_date and (date.today() - streak.last_session_date).days >= 3:
        cat = "streak_risk"
    elif wellness >= 70:
        cat = "high_wellness"
    elif wellness <= 30:
        cat = "low_wellness"
    else:
        cat = "streak_building"

    # Deterministic daily pick using date hash
    day_hash = int(hashlib.md5(f"{user_id}-{date.today().isoformat()}".encode()).hexdigest(), 16)
    pool = questions[cat]
    question = pool[day_hash % len(pool)]

    return {
        "category": cat,
        "question": question,
        "wellness_score": wellness,
    }


# ═══════════════════════════════════════════════════════════════════════════
# AGENT MESH ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/mesh/status")
async def mesh_status(db: DBSession = Depends(get_db)):
    """Return current mesh status: active agents, messages, insights."""
    try:
        if _MESH_AVAILABLE:
            mesh = AgentMesh(db)
            return mesh.status()
    except Exception:
        pass

    # Fallback: build status from DB
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day)

    total_users = db.query(User).count()
    active_streaks = db.query(Streak).filter(Streak.current_streak > 0).count()
    sessions_today = db.query(SessionModel).filter(SessionModel.logged_at >= today_start).count()
    nudges_today = db.query(Nudge).filter(Nudge.sent_at >= today_start).count()

    # Approximate mesh agents = users with active streaks (they have personal agents)
    agents_online = active_streaks

    # Avg wellness across active users
    active_user_ids = [r[0] for r in db.query(Streak.user_id).filter(Streak.current_streak > 0).limit(50).all()]
    wellness_scores = [_wellness_score(db, uid) for uid in active_user_ids] if active_user_ids else [0]
    avg_wellness = round(sum(wellness_scores) / max(len(wellness_scores), 1))

    return {
        "mesh": "online",
        "agents_registered": total_users,
        "agents_online": agents_online,
        "avg_wellness": avg_wellness,
        "sessions_today": sessions_today,
        "nudges_today": nudges_today,
        "messages_today": sessions_today + nudges_today,
        "insights": [
            f"{active_streaks} active streaks across the mesh",
            f"{sessions_today} sessions completed today",
            f"Average wellness: {avg_wellness}/100",
        ],
        "timestamp": now.isoformat(),
    }


@router.post("/mesh/register/{user_id}")
async def register_agent(user_id: str, db: DBSession = Depends(get_db)):
    """Register a personal agent for a user."""
    try:
        if _MESH_AVAILABLE:
            mesh = AgentMesh(db)
            return mesh.register(user_id)
    except Exception:
        pass

    # Fallback
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    wellness = _wellness_score(db, user_id)
    return {
        "agent_id": f"agent-{user_id[:8]}",
        "user_id": user_id,
        "user_name": user.name,
        "status": "registered",
        "wellness_score": wellness,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/mesh/agents")
async def list_agents(db: DBSession = Depends(get_db)):
    """List all registered agents with their status."""
    try:
        if _MESH_AVAILABLE:
            mesh = AgentMesh(db)
            return mesh.list_agents()
    except Exception:
        pass

    # Fallback: treat every user with a streak as having a personal agent
    users_with_streaks = (
        db.query(User, Streak)
        .join(Streak, User.id == Streak.user_id)
        .order_by(Streak.current_streak.desc())
        .limit(100)
        .all()
    )

    agents = []
    for user, streak in users_with_streaks:
        wellness = _wellness_score(db, user.id)
        agents.append({
            "agent_id": f"agent-{user.id[:8]}",
            "user_id": user.id,
            "user_name": user.name,
            "streak": streak.current_streak,
            "wellness_score": wellness,
            "status": "active" if streak.current_streak > 0 else "dormant",
            "last_session": streak.last_session_date.isoformat() if streak.last_session_date else None,
        })

    return {"agents": agents, "total": len(agents)}


# ═══════════════════════════════════════════════════════════════════════════
# PERSONAL AGENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/agent/{user_id}/status")
async def agent_status(user_id: str, db: DBSession = Depends(get_db)):
    """Get a user's personal agent status and wellness score."""
    try:
        if _PERSONAL_AGENT_AVAILABLE:
            agent = PersonalAgent(user_id, db)
            return agent.status()
    except Exception:
        pass

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    wellness = _wellness_score(db, user_id)
    burnout = _burnout_risk(db, user_id)

    last_session = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .order_by(SessionModel.logged_at.desc())
        .first()
    )

    return {
        "agent_id": f"agent-{user_id[:8]}",
        "user_id": user_id,
        "user_name": user.name,
        "wellness_score": wellness,
        "burnout_risk": burnout["risk"],
        "current_streak": streak.current_streak if streak else 0,
        "total_sessions": streak.total_sessions if streak else 0,
        "last_session": last_session.logged_at.isoformat() if last_session else None,
        "fitness_level": user.fitness_level.value if user.fitness_level else "beginner",
    }


@router.get("/agent/{user_id}/wellness")
async def agent_wellness(user_id: str, days: int = Query(default=7, ge=1, le=90), db: DBSession = Depends(get_db)):
    """Get wellness analysis for a user over N days."""
    try:
        if _PERSONAL_AGENT_AVAILABLE:
            agent = PersonalAgent(user_id, db)
            return agent.wellness(days=days)
    except Exception:
        pass

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    today = date.today()
    start = today - timedelta(days=days)

    sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.user_id == user_id,
            SessionModel.logged_at >= datetime(start.year, start.month, start.day),
        )
        .all()
    )

    feedback = (
        db.query(SessionFeedback)
        .filter(
            SessionFeedback.user_id == user_id,
            SessionFeedback.session_date >= start,
        )
        .order_by(SessionFeedback.session_date)
        .all()
    )

    # Build daily map
    daily = {}
    for d in range(days):
        day = start + timedelta(days=d)
        daily[day.isoformat()] = {"completed": False, "difficulty": None, "enjoyment": None}

    for sess in sessions:
        day_key = sess.logged_at.date().isoformat()
        if day_key in daily:
            daily[day_key]["completed"] = True

    for fb in feedback:
        day_key = fb.session_date.isoformat()
        if day_key in daily:
            daily[day_key]["difficulty"] = fb.difficulty_rating
            daily[day_key]["enjoyment"] = fb.enjoyment_rating

    active_days = sum(1 for v in daily.values() if v["completed"])
    consistency = round(active_days / max(days, 1) * 100)

    return {
        "user_id": user_id,
        "period_days": days,
        "wellness_score": _wellness_score(db, user_id),
        "active_days": active_days,
        "consistency_pct": consistency,
        "daily": daily,
        "burnout": _burnout_risk(db, user_id),
    }


@router.get("/agent/{user_id}/burnout")
async def agent_burnout(user_id: str, db: DBSession = Depends(get_db)):
    """Run burnout detection for a user."""
    try:
        if _PERSONAL_AGENT_AVAILABLE:
            agent = PersonalAgent(user_id, db)
            return agent.burnout_check()
    except Exception:
        pass

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    return {
        "user_id": user_id,
        "user_name": user.name,
        **_burnout_risk(db, user_id),
    }


# ═══════════════════════════════════════════════════════════════════════════
# DAILY CHECKUP ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/checkup/run")
async def run_all_checkups(db: DBSession = Depends(get_db)):
    """Run daily checkups for all users. Returns summary."""
    try:
        if _CHECKUP_AVAILABLE:
            checkup = DailyCheckup(db)
            return checkup.run_all()
    except Exception:
        pass

    # Fallback: compute checkups from DB
    users_with_streaks = (
        db.query(User, Streak)
        .join(Streak, User.id == Streak.user_id)
        .filter(Streak.current_streak > 0)
        .all()
    )

    results = []
    at_risk = 0
    healthy = 0

    for user, streak in users_with_streaks:
        wellness = _wellness_score(db, user.id)
        burnout = _burnout_risk(db, user.id)
        logged_today = (
            db.query(SessionModel)
            .filter(
                SessionModel.user_id == user.id,
                SessionModel.logged_at >= datetime(datetime.now(timezone.utc).year, datetime.now(timezone.utc).month, datetime.now(timezone.utc).day),
            )
            .first()
        )

        status = "completed" if logged_today else "pending"
        if burnout["risk"] in ("high", "moderate") and not logged_today:
            at_risk += 1
        else:
            healthy += 1

        results.append({
            "user_id": user.id,
            "user_name": user.name,
            "wellness": wellness,
            "burnout_risk": burnout["risk"],
            "today_status": status,
        })

    return {
        "checkup_time": datetime.now(timezone.utc).isoformat(),
        "users_checked": len(results),
        "at_risk": at_risk,
        "healthy": healthy,
        "results": results,
    }


@router.get("/checkup/{user_id}")
async def user_checkup(user_id: str, db: DBSession = Depends(get_db)):
    """Run checkup for a single user."""
    try:
        if _CHECKUP_AVAILABLE:
            checkup = DailyCheckup(db)
            return checkup.run_user(user_id)
    except Exception:
        pass

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    wellness = _wellness_score(db, user_id)
    burnout = _burnout_risk(db, user_id)
    question = _adaptive_question(db, user_id)

    today_start = datetime(datetime.now(timezone.utc).year, datetime.now(timezone.utc).month, datetime.now(timezone.utc).day)
    logged_today = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.logged_at >= today_start,
    ).first()

    streak = db.query(Streak).filter(Streak.user_id == user_id).first()

    return {
        "user_id": user_id,
        "user_name": user.name,
        "wellness_score": wellness,
        "burnout": burnout,
        "today_status": "completed" if logged_today else "pending",
        "current_streak": streak.current_streak if streak else 0,
        "daily_question": question,
        "checkup_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/checkup/{user_id}/question")
async def daily_question(user_id: str, db: DBSession = Depends(get_db)):
    """Get today's adaptive question for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    return _adaptive_question(db, user_id)


# ═══════════════════════════════════════════════════════════════════════════
# SOCIAL ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/social/event/today")
async def todays_event(db: DBSession = Depends(get_db)):
    """Get today's collective event stats."""
    try:
        if _SOCIAL_AVAILABLE:
            engine = SocialEngine(db)
            return engine.todays_event()
    except Exception:
        pass

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day)

    sessions_today = db.query(SessionModel).filter(SessionModel.logged_at >= today_start).count()
    users_today = (
        db.query(SessionModel.user_id)
        .filter(SessionModel.logged_at >= today_start)
        .distinct()
        .count()
    )
    total_minutes = sessions_today * 7  # each session is 7 min
    total_users = db.query(User).count()
    participation = round(users_today / max(total_users, 1) * 100)

    # Streaks survived today
    survived = db.query(Streak).filter(
        Streak.current_streak > 0,
        Streak.last_session_date == now.date(),
    ).count()

    return {
        "date": now.date().isoformat(),
        "sessions_completed": sessions_today,
        "unique_participants": users_today,
        "total_minutes": total_minutes,
        "participation_pct": participation,
        "streaks_survived": survived,
        "collective_message": f"{users_today} builders showed up today. {total_minutes} minutes of movement. Every second counts.",
    }


@router.get("/social/stories")
async def community_stories(db: DBSession = Depends(get_db), limit: int = Query(default=5, ge=1, le=20)):
    """Get community transformation stories."""
    try:
        if _SOCIAL_AVAILABLE:
            engine = SocialEngine(db)
            return engine.stories(limit=limit)
    except Exception:
        pass

    # Build stories from notable streaks and milestones
    notable = (
        db.query(User, Streak)
        .join(Streak, User.id == Streak.user_id)
        .filter(Streak.current_streak >= 7)
        .order_by(Streak.current_streak.desc())
        .limit(limit)
        .all()
    )

    stories = []
    for user, streak in notable:
        wellness = _wellness_score(db, user.id)
        milestone = "week" if streak.current_streak >= 7 else "start"
        if streak.current_streak >= 30:
            milestone = "month"
        if streak.current_streak >= 100:
            milestone = "hundred"

        stories.append({
            "user_name": user.name,
            "streak": streak.current_streak,
            "total_sessions": streak.total_sessions,
            "wellness_score": wellness,
            "milestone": milestone,
            "story": f"@{user.name} has shown up for {streak.current_streak} days straight. "
                     f"{streak.total_sessions} total sessions. Wellness: {wellness}/100.",
        })

    return {"stories": stories, "total": len(stories)}


@router.get("/social/story-of-the-day")
async def story_of_day(db: DBSession = Depends(get_db)):
    """Get today's most inspiring story."""
    try:
        if _SOCIAL_AVAILABLE:
            engine = SocialEngine(db)
            return engine.story_of_the_day()
    except Exception:
        pass

    # Pick the user who hit a milestone today or has highest wellness + streak combo
    today = date.today()
    candidates = (
        db.query(User, Streak)
        .join(Streak, User.id == Streak.user_id)
        .filter(Streak.last_session_date == today, Streak.current_streak > 0)
        .order_by(Streak.current_streak.desc())
        .limit(10)
        .all()
    )

    if not candidates:
        return {
            "story": None,
            "message": "No stories yet today. Be the first to show up.",
        }

    # Prefer milestone streaks (7, 14, 21, 30, 50, 100)
    milestones = {7, 14, 21, 30, 50, 100, 200, 365}
    best = None
    for user, streak in candidates:
        if streak.current_streak in milestones:
            best = (user, streak)
            break

    if not best:
        best = candidates[0]

    user, streak = best
    wellness = _wellness_score(db, user.id)

    return {
        "user_name": user.name,
        "streak": streak.current_streak,
        "wellness_score": wellness,
        "total_sessions": streak.total_sessions,
        "story": f"@{user.name} just hit day {streak.current_streak}. "
                 f"That's {streak.total_sessions} sessions total. Wellness at {wellness}/100. "
                 f"Showing up is the whole game.",
    }


@router.post("/social/find-match/{user_id}")
async def find_match(user_id: str, db: DBSession = Depends(get_db)):
    """Find accountability partner for a user."""
    try:
        if _SOCIAL_AVAILABLE:
            engine = SocialEngine(db)
            return engine.find_match(user_id)
    except Exception:
        pass

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    # Find compatible users: similar timezone, fitness level, active streak
    candidates = (
        db.query(User, Streak)
        .join(Streak, User.id == Streak.user_id)
        .filter(
            User.id != user_id,
            Streak.current_streak > 0,
        )
        .all()
    )

    if not candidates:
        return {"match": None, "message": "No compatible matches found yet. Keep showing up."}

    # Score candidates
    scored = []
    for candidate, streak in candidates:
        score = 0
        # Same timezone bonus
        if candidate.timezone == user.timezone:
            score += 30
        # Same fitness level bonus
        if candidate.fitness_level == user.fitness_level:
            score += 20
        # Similar streak bonus
        user_streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        if user_streak:
            diff = abs(streak.current_streak - user_streak.current_streak)
            if diff <= 3:
                score += 25
            elif diff <= 7:
                score += 15
        # Active today bonus
        if streak.last_session_date == date.today():
            score += 10

        scored.append((candidate, streak, score))

    scored.sort(key=lambda x: x[2], reverse=True)
    match_user, match_streak, match_score = scored[0]

    return {
        "match": {
            "user_id": match_user.id,
            "user_name": match_user.name,
            "streak": match_streak.current_streak,
            "fitness_level": match_user.fitness_level.value if match_user.fitness_level else "beginner",
            "timezone": match_user.timezone,
            "compatibility_score": match_score,
        },
        "message": f"Matched with @{match_user.name} - {match_streak.current_streak} day streak, "
                   f"{'same' if match_user.timezone == user.timezone else 'different'} timezone.",
    }


# ═══════════════════════════════════════════════════════════════════════════
# MESH VISUALIZATION PAGE
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/mesh", response_class=HTMLResponse)
async def mesh_page(db: DBSession = Depends(get_db)):
    """HTML page showing the agent mesh visualization."""
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day)

    # Gather data
    active_streaks = db.query(Streak).filter(Streak.current_streak > 0).count()
    sessions_today = db.query(SessionModel).filter(SessionModel.logged_at >= today_start).count()
    nudges_today = db.query(Nudge).filter(Nudge.sent_at >= today_start).count()

    # Get agents (users with streaks) for visualization
    agents_data = (
        db.query(User, Streak)
        .join(Streak, User.id == Streak.user_id)
        .filter(Streak.current_streak > 0)
        .order_by(Streak.current_streak.desc())
        .limit(50)
        .all()
    )

    # Build agent nodes JSON for the canvas
    agent_nodes = []
    for user, streak in agents_data:
        wellness = _wellness_score(db, user.id)
        agent_nodes.append({
            "id": user.id[:8],
            "name": user.name,
            "streak": streak.current_streak,
            "wellness": wellness,
        })

    # Build pairs (pod members)
    pairs = []
    pod_links = (
        db.query(PodMember)
        .order_by(PodMember.joined_at.desc())
        .limit(100)
        .all()
    )
    pod_user_map = {}
    for pm in pod_links:
        pod_user_map.setdefault(pm.pod_id, []).append(pm.user_id[:8])
    for pod_id, members in pod_user_map.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                pairs.append([members[i], members[j]])

    # Avg wellness
    wellness_scores = [n["wellness"] for n in agent_nodes] if agent_nodes else [0]
    avg_wellness = round(sum(wellness_scores) / max(len(wellness_scores), 1))

    # Recent events for live feed
    recent_sessions = (
        db.query(SessionModel, User)
        .join(User, SessionModel.user_id == User.id)
        .order_by(SessionModel.logged_at.desc())
        .limit(8)
        .all()
    )
    recent_nudges_list = (
        db.query(Nudge, User)
        .join(User, Nudge.user_id == User.id)
        .order_by(Nudge.sent_at.desc())
        .limit(4)
        .all()
    )

    feed_items = []
    for sess, user in recent_sessions:
        delta = now - sess.logged_at
        secs = int(delta.total_seconds())
        if secs < 60:
            ago = "just now"
        elif secs < 3600:
            ago = f"{secs // 60}m ago"
        elif secs < 86400:
            ago = f"{secs // 3600}h ago"
        else:
            ago = f"{secs // 86400}d ago"
        feed_items.append({"time": ago, "msg": f"@{user.name} completed a session", "type": "session", "ts": secs})

    for nudge, user in recent_nudges_list:
        delta = now - nudge.sent_at
        secs = int(delta.total_seconds())
        if secs < 60:
            ago = "just now"
        elif secs < 3600:
            ago = f"{secs // 60}m ago"
        elif secs < 86400:
            ago = f"{secs // 3600}h ago"
        else:
            ago = f"{secs // 86400}d ago"
        feed_items.append({"time": ago, "msg": f"Nudge sent to @{user.name}", "type": "nudge", "ts": secs})

    feed_items.sort(key=lambda x: x["ts"])

    # Serialize for JS
    import json
    nodes_json = json.dumps(agent_nodes)
    pairs_json = json.dumps(pairs)
    feed_json = json.dumps(feed_items)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Agent Mesh - Jerome7</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0f1419; color: #c9d1d9;
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh; overflow: hidden;
  }}

  .layout {{
    display: grid;
    grid-template-columns: 1fr 320px;
    height: 100vh;
  }}

  /* Canvas area */
  .canvas-area {{
    position: relative;
    overflow: hidden;
  }}
  canvas {{
    display: block;
    width: 100%;
    height: 100%;
  }}

  /* Sidebar */
  .sidebar {{
    background: #161b22;
    border-left: 1px solid #21262d;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}

  .sidebar-header {{
    padding: 20px 20px 16px;
    border-bottom: 1px solid #21262d;
  }}
  .sidebar-brand {{
    font-size: 10px; letter-spacing: 3px; color: #E85D04;
    text-transform: uppercase; font-weight: 800;
    margin-bottom: 4px;
  }}
  .sidebar-title {{
    font-size: 14px; font-weight: 700; color: #f0f6fc;
    letter-spacing: 1px;
  }}
  .sidebar-live {{
    display: inline-flex; align-items: center; gap: 6px;
    margin-top: 8px; font-size: 9px; color: #3fb950; letter-spacing: 2px;
  }}
  .sidebar-live .dot {{
    width: 6px; height: 6px; border-radius: 50%; background: #3fb950;
    animation: pulse 2s infinite;
  }}

  /* Stats */
  .stats-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1px;
    background: #21262d;
    border-bottom: 1px solid #21262d;
  }}
  .stat-cell {{
    background: #161b22;
    padding: 14px 16px;
  }}
  .stat-val {{
    font-size: 22px; font-weight: 800; color: #f0f6fc; line-height: 1;
  }}
  .stat-val.orange {{ color: #E85D04; }}
  .stat-val.green {{ color: #3fb950; }}
  .stat-val.blue {{ color: #58a6ff; }}
  .stat-label {{
    font-size: 8px; color: #484f58; margin-top: 4px;
    letter-spacing: 1px; text-transform: uppercase;
  }}

  /* Feed */
  .feed-section {{
    flex: 1; overflow-y: auto;
    padding: 0;
  }}
  .feed-title {{
    font-size: 9px; letter-spacing: 3px; color: #E85D04;
    text-transform: uppercase; padding: 14px 20px 10px;
    display: flex; align-items: center; gap: 8px;
  }}
  .feed-dot {{
    width: 5px; height: 5px; border-radius: 50%; background: #3fb950;
    animation: pulse 2s infinite;
  }}
  .feed-item {{
    padding: 8px 20px;
    font-size: 10px;
    border-bottom: 1px solid #0f1419;
    display: flex; gap: 10px; align-items: flex-start;
  }}
  .feed-item:nth-child(odd) {{ background: #0f1419; }}
  .feed-time {{ color: #30363d; min-width: 52px; font-size: 9px; flex-shrink: 0; }}
  .feed-msg {{ color: #8b949e; line-height: 1.4; }}
  .feed-type-session .feed-msg {{ color: #c9d1d9; }}
  .feed-type-nudge .feed-msg {{ color: #d29922; }}

  /* Legend */
  .legend {{
    padding: 14px 20px;
    border-top: 1px solid #21262d;
    font-size: 9px; color: #484f58;
    display: flex; flex-wrap: wrap; gap: 12px;
  }}
  .legend-item {{
    display: flex; align-items: center; gap: 5px;
  }}
  .legend-dot {{
    width: 10px; height: 10px; border-radius: 50%;
  }}

  .nav-back {{
    padding: 12px 20px;
    border-top: 1px solid #21262d;
    font-size: 9px;
  }}
  .nav-back a {{
    color: #484f58; text-decoration: none; letter-spacing: 1px;
  }}
  .nav-back a:hover {{ color: #E85D04; }}

  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.3; }}
  }}

  @media (max-width: 800px) {{
    .layout {{ grid-template-columns: 1fr; grid-template-rows: 50vh 1fr; }}
  }}
</style>
</head>
<body>
<div class="layout">
  <div class="canvas-area">
    <canvas id="meshCanvas"></canvas>
  </div>

  <div class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-brand">JEROME7</div>
      <div class="sidebar-title">Agent Mesh</div>
      <div class="sidebar-live">
        <div class="dot"></div>
        LIVE - {active_streaks} agents online
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-cell">
        <div class="stat-val orange">{active_streaks}</div>
        <div class="stat-label">Agents Online</div>
      </div>
      <div class="stat-cell">
        <div class="stat-val green">{avg_wellness}</div>
        <div class="stat-label">Avg Wellness</div>
      </div>
      <div class="stat-cell">
        <div class="stat-val blue">{sessions_today}</div>
        <div class="stat-label">Sessions Today</div>
      </div>
      <div class="stat-cell">
        <div class="stat-val">{sessions_today + nudges_today}</div>
        <div class="stat-label">Messages Today</div>
      </div>
    </div>

    <div class="feed-section">
      <div class="feed-title"><div class="feed-dot"></div> LIVE FEED</div>
      <div id="feedList"></div>
    </div>

    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:#3fb950;"></div> Wellness 70+</div>
      <div class="legend-item"><div class="legend-dot" style="background:#d29922;"></div> Wellness 40-69</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f85149;"></div> Wellness &lt;40</div>
      <div class="legend-item"><div class="legend-dot" style="background:#21262d;border:1px solid #30363d;"></div> Paired</div>
    </div>

    <div class="nav-back">
      <a href="/">HOME</a> &middot;
      <a href="/agents">OBSERVATORY</a> &middot;
      <a href="/analytics">ANALYTICS</a>
    </div>
  </div>
</div>

<script>
const NODES = {nodes_json};
const PAIRS = {pairs_json};
const FEED  = {feed_json};

// --- Canvas setup ---
const canvas = document.getElementById('meshCanvas');
const ctx = canvas.getContext('2d');
let W, H;

function resize() {{
  const rect = canvas.parentElement.getBoundingClientRect();
  W = canvas.width = rect.width * devicePixelRatio;
  H = canvas.height = rect.height * devicePixelRatio;
  canvas.style.width = rect.width + 'px';
  canvas.style.height = rect.height + 'px';
  ctx.scale(devicePixelRatio, devicePixelRatio);
}}
resize();
window.addEventListener('resize', () => {{ resize(); layoutNodes(); }});

// --- Color by wellness ---
function wellnessColor(w) {{
  if (w >= 70) return '#3fb950';
  if (w >= 40) return '#d29922';
  return '#f85149';
}}

// --- Layout nodes in a circle (or force-directed-lite) ---
const positions = [];
function layoutNodes() {{
  const cw = W / devicePixelRatio;
  const ch = H / devicePixelRatio;
  const cx = cw / 2;
  const cy = ch / 2;
  const r = Math.min(cw, ch) * 0.35;

  positions.length = 0;
  const n = NODES.length || 1;
  for (let i = 0; i < NODES.length; i++) {{
    const angle = (2 * Math.PI * i / n) - Math.PI / 2;
    positions.push({{
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
      vx: 0, vy: 0,
    }});
  }}
}}
layoutNodes();

// --- Animated messages ---
const messages = [];
function spawnMessage() {{
  if (PAIRS.length === 0 && NODES.length >= 2) {{
    // Random pair if no pods
    const a = Math.floor(Math.random() * NODES.length);
    let b = Math.floor(Math.random() * NODES.length);
    if (b === a) b = (a + 1) % NODES.length;
    messages.push({{ from: a, to: b, t: 0 }});
    return;
  }}
  if (PAIRS.length > 0) {{
    const pair = PAIRS[Math.floor(Math.random() * PAIRS.length)];
    const ai = NODES.findIndex(n => n.id === pair[0]);
    const bi = NODES.findIndex(n => n.id === pair[1]);
    if (ai >= 0 && bi >= 0) {{
      messages.push({{ from: ai, to: bi, t: 0 }});
    }}
  }}
}}

// --- Draw ---
let time = 0;
function draw() {{
  const cw = W / devicePixelRatio;
  const ch = H / devicePixelRatio;
  ctx.clearRect(0, 0, cw, ch);

  time += 0.005;

  // Draw connections (pairs)
  ctx.strokeStyle = 'rgba(33, 38, 45, 0.6)';
  ctx.lineWidth = 1;
  for (const pair of PAIRS) {{
    const ai = NODES.findIndex(n => n.id === pair[0]);
    const bi = NODES.findIndex(n => n.id === pair[1]);
    if (ai >= 0 && bi >= 0 && positions[ai] && positions[bi]) {{
      ctx.beginPath();
      ctx.moveTo(positions[ai].x, positions[ai].y);
      ctx.lineTo(positions[bi].x, positions[bi].y);
      ctx.stroke();
    }}
  }}

  // Draw messages
  for (let i = messages.length - 1; i >= 0; i--) {{
    const m = messages[i];
    m.t += 0.015;
    if (m.t >= 1) {{ messages.splice(i, 1); continue; }}
    const pa = positions[m.from];
    const pb = positions[m.to];
    if (!pa || !pb) continue;
    const x = pa.x + (pb.x - pa.x) * m.t;
    const y = pa.y + (pb.y - pa.y) * m.t;
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(232, 93, 4, ' + (1 - m.t) + ')';
    ctx.fill();
  }}

  // Draw nodes
  for (let i = 0; i < NODES.length; i++) {{
    const node = NODES[i];
    const pos = positions[i];
    if (!pos) continue;

    const radius = 12 + (node.streak * 0.5);
    const color = wellnessColor(node.wellness);

    // Glow
    const glow = ctx.createRadialGradient(pos.x, pos.y, radius * 0.5, pos.x, pos.y, radius * 2.5);
    glow.addColorStop(0, color.replace(')', ', 0.15)').replace('rgb', 'rgba'));
    glow.addColorStop(1, 'transparent');
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius * 2.5, 0, Math.PI * 2);
    ctx.fillStyle = glow;
    ctx.fill();

    // Node circle
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.85;
    ctx.fill();
    ctx.globalAlpha = 1;

    // Gentle breathing animation
    const breathe = 1 + Math.sin(time * 2 + i) * 0.06;
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, radius * breathe, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.globalAlpha = 0.4;
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Label
    ctx.fillStyle = '#f0f6fc';
    ctx.font = '9px JetBrains Mono';
    ctx.textAlign = 'center';
    ctx.fillText(node.name, pos.x, pos.y + radius + 16);
    ctx.fillStyle = '#484f58';
    ctx.font = '8px JetBrains Mono';
    ctx.fillText(node.streak + 'd', pos.x, pos.y + radius + 26);
  }}

  // If no nodes, show empty state
  if (NODES.length === 0) {{
    ctx.fillStyle = '#484f58';
    ctx.font = '12px JetBrains Mono';
    ctx.textAlign = 'center';
    ctx.fillText('No agents online yet.', cw / 2, ch / 2 - 10);
    ctx.fillText('Users with active streaks appear as nodes.', cw / 2, ch / 2 + 10);
  }}

  requestAnimationFrame(draw);
}}
draw();

// Spawn messages periodically
if (NODES.length >= 2) {{
  setInterval(spawnMessage, 2000);
}}

// --- Feed ---
const feedList = document.getElementById('feedList');
function renderFeed() {{
  let html = '';
  if (FEED.length === 0) {{
    html = '<div class="feed-item" style="color:#484f58;justify-content:center;">Waiting for activity...</div>';
  }}
  for (const item of FEED) {{
    html += '<div class="feed-item feed-type-' + item.type + '">' +
      '<span class="feed-time">' + item.time + '</span>' +
      '<span class="feed-msg">' + item.msg + '</span>' +
    '</div>';
  }}
  feedList.innerHTML = html;
}}
renderFeed();

// Auto-refresh every 20 seconds
setTimeout(() => location.reload(), 20000);
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
