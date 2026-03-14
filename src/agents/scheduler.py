"""Scheduler Agent — finds your seven minutes.

Reads your timezone, your habits, your pod. Returns the window
where showing up is easiest. Pure logic, no AI needed.
"""

from datetime import datetime
from typing import Optional

from src.agents.context import UserContext


# Hour-of-day preference buckets
_MORNING = range(5, 12)    # 5 AM – 11 AM
_AFTERNOON = range(12, 17) # 12 PM – 4 PM
_EVENING = range(17, 22)   # 5 PM – 9 PM

_BUCKET_LABELS = {
    "morning": "Morning sessions work best for you",
    "afternoon": "Afternoon sessions work best for you",
    "evening": "Evening sessions work best for you",
    "default": "Based on your availability",
}


def _bucket_for_hour(hour: int) -> str:
    if hour in _MORNING:
        return "morning"
    if hour in _AFTERNOON:
        return "afternoon"
    if hour in _EVENING:
        return "evening"
    return "default"


def _parse_session_hours(sessions: list[dict]) -> list[int]:
    """Extract the hour-of-day from each session's logged_at timestamp."""
    hours = []
    for s in sessions:
        logged = s.get("logged_at") or s.get("date")
        if not logged:
            continue
        try:
            dt = datetime.fromisoformat(str(logged))
            hours.append(dt.hour)
        except (ValueError, TypeError):
            continue
    return hours


def _most_common_hour(hours: list[int]) -> Optional[int]:
    """Return the most frequently occurring hour, or None if empty."""
    if not hours:
        return None
    counts: dict[int, int] = {}
    for h in hours:
        counts[h] = counts.get(h, 0) + 1
    return max(counts, key=counts.get)


class SchedulerAgent:
    """Finds optimal windows for a 7-minute session."""

    def find_optimal_window(self, ctx: UserContext) -> dict:
        """Return the best time window for this user.

        Priority order:
        1. Historical habit — when they usually log sessions.
        2. Explicit available_windows from their profile.
        3. Sensible default (8:00 AM in their timezone).
        """
        timezone = ctx.timezone or "UTC"

        # --- Try session history first ---
        all_sessions = list(ctx.sessions_last_7_days)
        if ctx.last_session:
            all_sessions.append(ctx.last_session)

        habit_hours = _parse_session_hours(all_sessions)
        preferred_hour = _most_common_hour(habit_hours)

        if preferred_hour is not None:
            bucket = _bucket_for_hour(preferred_hour)
            return {
                "hour": preferred_hour,
                "minute": 0,
                "timezone": timezone,
                "suggestion": _BUCKET_LABELS.get(bucket, _BUCKET_LABELS["default"]),
            }

        # --- Fall back to available_windows ---
        windows = ctx.available_windows or []
        if windows:
            # Each window is expected as {"hour": int, "minute": int} or
            # a plain hour int.
            first = windows[0]
            if isinstance(first, dict):
                hour = first.get("hour", 8)
                minute = first.get("minute", 0)
            elif isinstance(first, (int, float)):
                hour = int(first)
                minute = 0
            else:
                hour, minute = 8, 0

            bucket = _bucket_for_hour(hour)
            return {
                "hour": hour,
                "minute": minute,
                "timezone": timezone,
                "suggestion": _BUCKET_LABELS.get(bucket, _BUCKET_LABELS["default"]),
            }

        # --- Sensible default ---
        return {
            "hour": 8,
            "minute": 0,
            "timezone": timezone,
            "suggestion": _BUCKET_LABELS["morning"],
        }

    def suggest_pod_time(self, members: list[UserContext]) -> dict:
        """Find the overlap window for a pod of 3-5 people.

        Strategy: collect each member's preferred hour, then pick the
        hour that satisfies the most members. Ties break toward the
        earlier hour.
        """
        if not members:
            return {
                "hour": 8,
                "minute": 0,
                "timezone": "UTC",
                "members_available": 0,
                "suggestion": "No members provided",
            }

        # Build a preference map: hour -> list of member names
        hour_members: dict[int, list[str]] = {}

        for ctx in members:
            optimal = self.find_optimal_window(ctx)
            h = optimal["hour"]
            hour_members.setdefault(h, []).append(ctx.name)

        # Find the hour with the most members; break ties with earlier hour
        best_hour = max(
            hour_members,
            key=lambda h: (len(hour_members[h]), -h),
        )
        available_count = len(hour_members[best_hour])

        # Use the first member's timezone as reference (pods are often
        # same-timezone); callers can convert as needed.
        ref_tz = members[0].timezone or "UTC"
        bucket = _bucket_for_hour(best_hour)

        return {
            "hour": best_hour,
            "minute": 0,
            "timezone": ref_tz,
            "members_available": available_count,
            "suggestion": f"Best overlap window — {_BUCKET_LABELS.get(bucket, 'works for the group')}",
        }
