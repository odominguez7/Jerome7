"""AgentRegistry — Register and discover agents in the mesh.

Each user gets a personal agent. The agent card is stored as an Event
with event_type="mesh:agent_card". This avoids new DB migrations.

Agent card schema (stored in Event.payload):
{
    "agent_id": str,          # same as user_id
    "user_id": str,
    "name": str,
    "timezone": str,
    "goal": str,
    "fitness_level": str,
    "status": "active" | "idle" | "at_risk" | "offline",
    "wellness_score": float,  # 0-100
    "current_streak": int,
    "registered_at": str,     # ISO timestamp
    "last_heartbeat": str,    # ISO timestamp
}
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.db.models import Event, Streak, Session


_AGENT_CARD_EVENT = "mesh:agent_card"


class AgentRegistry:
    """Register and discover agents globally."""

    def __init__(self, db: DBSession):
        self.db = db

    async def register(self, user_id: str, agent_card: dict) -> str:
        """Register a new agent. Returns agent_id.

        If the agent already exists, updates the card instead.
        """
        agent_id = user_id  # 1:1 mapping

        existing = (
            self.db.query(Event)
            .filter(
                Event.event_type == _AGENT_CARD_EVENT,
                Event.user_id == user_id,
            )
            .first()
        )

        card = {
            "agent_id": agent_id,
            "user_id": user_id,
            "status": "active",
            "wellness_score": 50.0,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            **agent_card,
        }

        if existing:
            # Preserve original registration time
            old = existing.payload or {}
            card["registered_at"] = old.get(
                "registered_at", card["registered_at"]
            )
            existing.payload = card
        else:
            event = Event(
                event_type=_AGENT_CARD_EVENT,
                user_id=user_id,
                payload=card,
            )
            self.db.add(event)

        self.db.commit()
        return agent_id

    async def discover(self, filters: Optional[dict] = None) -> list:
        """Discover agents matching filters.

        Supported filters:
            timezone: str — exact match
            goal: str — exact match
            status: str — exact match (default: "active")
            streak_min: int — minimum current streak
            streak_max: int — maximum current streak
            wellness_below: float — wellness score below threshold (at-risk)
        """
        events = (
            self.db.query(Event)
            .filter(Event.event_type == _AGENT_CARD_EVENT)
            .all()
        )

        agents = []
        for ev in events:
            card = ev.payload or {}
            if not filters:
                agents.append(card)
                continue

            match = True

            if "timezone" in filters and card.get("timezone") != filters["timezone"]:
                match = False
            if "goal" in filters and card.get("goal") != filters["goal"]:
                match = False
            if "status" in filters and card.get("status") != filters["status"]:
                match = False
            if "streak_min" in filters:
                if card.get("current_streak", 0) < filters["streak_min"]:
                    match = False
            if "streak_max" in filters:
                if card.get("current_streak", 0) > filters["streak_max"]:
                    match = False
            if "wellness_below" in filters:
                if card.get("wellness_score", 100) >= filters["wellness_below"]:
                    match = False
            if "fitness_level" in filters:
                if card.get("fitness_level") != filters["fitness_level"]:
                    match = False

            if match:
                agents.append(card)

        return agents

    async def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get agent card by ID."""
        event = (
            self.db.query(Event)
            .filter(
                Event.event_type == _AGENT_CARD_EVENT,
                Event.user_id == agent_id,
            )
            .first()
        )
        if not event:
            return None
        return event.payload

    async def update_status(
        self,
        agent_id: str,
        status: str,
        wellness_score: Optional[float] = None,
    ):
        """Update agent status and wellness score."""
        event = (
            self.db.query(Event)
            .filter(
                Event.event_type == _AGENT_CARD_EVENT,
                Event.user_id == agent_id,
            )
            .first()
        )
        if not event:
            return

        card = dict(event.payload or {})
        card["status"] = status
        card["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
        if wellness_score is not None:
            card["wellness_score"] = round(wellness_score, 1)
        event.payload = card
        self.db.commit()

    async def heartbeat(self, agent_id: str):
        """Record that an agent is still alive."""
        event = (
            self.db.query(Event)
            .filter(
                Event.event_type == _AGENT_CARD_EVENT,
                Event.user_id == agent_id,
            )
            .first()
        )
        if event:
            card = dict(event.payload or {})
            card["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
            event.payload = card
            self.db.commit()

    async def get_active_count(self) -> int:
        """Count of active agents (heartbeat within last 24h)."""
        events = (
            self.db.query(Event)
            .filter(Event.event_type == _AGENT_CARD_EVENT)
            .all()
        )

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        count = 0
        for ev in events:
            card = ev.payload or {}
            if card.get("status") == "offline":
                continue
            heartbeat_str = card.get("last_heartbeat")
            if heartbeat_str:
                try:
                    hb = datetime.fromisoformat(heartbeat_str)
                    if hb >= cutoff:
                        count += 1
                except (ValueError, TypeError):
                    pass
        return count

    async def compute_wellness_score(self, user_id: str) -> float:
        """Compute a wellness score (0-100) for a user based on their data.

        Factors:
            - Current streak length (0-30 points)
            - Session completion rate last 7 days (0-25 points)
            - Feedback enjoyment average (0-20 points)
            - Feedback difficulty balance (0-15 points, penalize extremes)
            - Recency of last session (0-10 points)
        """
        streak = self.db.query(Streak).filter(Streak.user_id == user_id).first()
        current_streak = streak.current_streak if streak else 0

        # Streak score: 30 points max, full score at 30+ days
        streak_score = min(30.0, current_streak)

        # Completion rate last 7 days: 25 points
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_sessions = (
            self.db.query(Session)
            .filter(Session.user_id == user_id, Session.logged_at >= seven_days_ago)
            .all()
        )
        completion_rate = len(recent_sessions) / 7.0
        completion_score = completion_rate * 25.0

        # Feedback scores: query recent feedback
        from src.db.models import SessionFeedback

        recent_fb = (
            self.db.query(SessionFeedback)
            .filter(SessionFeedback.user_id == user_id)
            .order_by(SessionFeedback.created_at.desc())
            .limit(5)
            .all()
        )

        enjoyment_score = 10.0  # default neutral
        difficulty_score = 7.5  # default neutral
        if recent_fb:
            enjoyments = [fb.enjoyment_rating for fb in recent_fb if fb.enjoyment_rating]
            if enjoyments:
                avg_enjoyment = sum(enjoyments) / len(enjoyments)
                enjoyment_score = (avg_enjoyment / 5.0) * 20.0

            difficulties = [fb.difficulty_rating for fb in recent_fb if fb.difficulty_rating]
            if difficulties:
                avg_diff = sum(difficulties) / len(difficulties)
                # Best score at difficulty 2.5-3.5, penalize extremes
                distance_from_ideal = abs(avg_diff - 3.0)
                difficulty_score = max(0, 15.0 - (distance_from_ideal * 5.0))

        # Recency: 10 points, full if session today, decays over 7 days
        recency_score = 0.0
        if streak and streak.last_session_date:
            from datetime import date as date_type

            days_since = (date_type.today() - streak.last_session_date).days
            recency_score = max(0, 10.0 - (days_since * 1.5))

        total = streak_score + completion_score + enjoyment_score + difficulty_score + recency_score
        return round(min(100.0, max(0.0, total)), 1)
