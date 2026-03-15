"""Collective Event — the daily collective 7-minute event.

Everyone on earth, same session, same day.
"""

from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Session, Streak, Event


class CollectiveEvent:
    """The daily collective 7-minute event — everyone on earth, same time."""

    async def get_todays_event(self, db: DBSession) -> dict:
        """Get today's collective event stats.

        Returns: {participants_today, countries_today, live_now, completed, session_name}
        """
        today = date.today()

        # Count users who logged a session today
        todays_sessions = (
            db.query(Session)
            .filter(func.date(Session.logged_at) == today)
            .all()
        )

        completed_user_ids = set()
        session_name = None
        for s in todays_sessions:
            completed_user_ids.add(s.user_id)
            if s.seven7_title and not session_name:
                session_name = s.seven7_title

        participants_today = len(completed_user_ids)

        # Count distinct countries from users who participated today
        countries = set()
        if completed_user_ids:
            users = (
                db.query(User)
                .filter(User.id.in_(completed_user_ids))
                .all()
            )
            for u in users:
                if u.country:
                    countries.add(u.country)
                elif u.timezone:
                    # Derive rough region from timezone
                    tz = u.timezone.split("/")[0] if "/" in u.timezone else u.timezone
                    countries.add(tz)

        # "Live now" — sessions logged in the last 10 minutes
        ten_min_ago = datetime.utcnow().replace(microsecond=0)
        from datetime import timedelta
        ten_min_ago = ten_min_ago - timedelta(minutes=10)

        live_sessions = (
            db.query(Session)
            .filter(Session.logged_at >= ten_min_ago)
            .count()
        )

        # Get session name from today's event or most recent session title
        if not session_name:
            latest = (
                db.query(Event)
                .filter(
                    Event.event_type == "daily_session_generated",
                    func.date(Event.created_at) == today,
                )
                .first()
            )
            if latest and latest.payload:
                session_name = latest.payload.get("session_title", "Today's Seven 7")
            else:
                session_name = "Today's Seven 7"

        return {
            "participants_today": participants_today,
            "countries_today": len(countries),
            "live_now": live_sessions,
            "completed": participants_today,
            "session_name": session_name,
        }

    async def join_event(self, user_id: str, db: DBSession) -> dict:
        """Mark a user as joining today's event.

        This is separate from logging a session — it's the intent to participate.
        """
        today = date.today()

        # Check if already joined today
        existing = (
            db.query(Event)
            .filter(
                Event.user_id == user_id,
                Event.event_type == "collective_event_joined",
                func.date(Event.created_at) == today,
            )
            .first()
        )

        if existing:
            return {
                "success": True,
                "already_joined": True,
                "message": "You're already in today's collective session.",
            }

        user = db.query(User).filter(User.id == user_id).first()

        event = Event(
            event_type="collective_event_joined",
            user_id=user_id,
            payload={
                "date": today.isoformat(),
                "user_name": user.name if user else "Anonymous",
                "joined_at": datetime.utcnow().isoformat(),
            },
        )
        db.add(event)
        db.commit()

        # Get current participant count
        joined_count = (
            db.query(Event)
            .filter(
                Event.event_type == "collective_event_joined",
                func.date(Event.created_at) == today,
            )
            .count()
        )

        return {
            "success": True,
            "already_joined": False,
            "message": f"You're in. {joined_count} people moving together today.",
            "participants": joined_count,
        }

    async def get_live_feed(self, db: DBSession, limit: int = 20) -> list:
        """Get the live feed of who just completed their session.

        Returns: [{user_name, country, streak_day, completed_at}]
        """
        today = date.today()

        # Get today's sessions ordered by most recent
        recent_sessions = (
            db.query(Session)
            .filter(func.date(Session.logged_at) == today)
            .order_by(Session.logged_at.desc())
            .limit(limit)
            .all()
        )

        feed = []
        for session in recent_sessions:
            user = db.query(User).filter(User.id == session.user_id).first()
            streak = (
                db.query(Streak).filter(Streak.user_id == session.user_id).first()
            )

            country = None
            if user:
                country = user.country
                if not country and user.timezone:
                    country = (
                        user.timezone.split("/")[0]
                        if "/" in user.timezone
                        else user.timezone
                    )

            feed.append({
                "user_name": user.name if user else "Anonymous",
                "country": country or "Earth",
                "streak_day": streak.current_streak if streak else 1,
                "completed_at": (
                    session.logged_at.isoformat() if session.logged_at else None
                ),
                "session_title": session.seven7_title,
            })

        return feed
