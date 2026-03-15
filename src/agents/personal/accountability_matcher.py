"""Accountability Matcher — 'YU are one person away.'

Pairs users for mutual accountability based on timezone proximity,
shared goals, and complementary streak lengths.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.db.models import (
    User, Streak, Pod, PodMember, PodMemberStatus, Session,
)


# Timezone offset lookup (simplified — covers major zones).
# Maps IANA zone prefix to approximate UTC offset in hours.
_TZ_OFFSETS = {
    "US/Eastern": -5, "America/New_York": -5, "America/Toronto": -5,
    "US/Central": -6, "America/Chicago": -6, "America/Mexico_City": -6,
    "US/Mountain": -7, "America/Denver": -7,
    "US/Pacific": -8, "America/Los_Angeles": -8, "America/Vancouver": -8,
    "Europe/London": 0, "UTC": 0,
    "Europe/Paris": 1, "Europe/Berlin": 1, "Europe/Madrid": 1,
    "Europe/Istanbul": 3, "Europe/Moscow": 3,
    "Asia/Dubai": 4, "Asia/Kolkata": 5, "Asia/Shanghai": 8,
    "Asia/Tokyo": 9, "Asia/Seoul": 9,
    "Australia/Sydney": 11, "Pacific/Auckland": 13,
}


def _tz_offset(tz_name: str) -> Optional[int]:
    """Best-effort UTC offset for a timezone string."""
    if tz_name in _TZ_OFFSETS:
        return _TZ_OFFSETS[tz_name]
    # Try prefix matching
    for key, offset in _TZ_OFFSETS.items():
        if tz_name.startswith(key.split("/")[0]):
            return offset
    return None


class AccountabilityMatcher:
    """Match users for accountability partnerships."""

    # ------------------------------------------------------------------
    # Find best match
    # ------------------------------------------------------------------

    async def find_best_match(self, user_id: str, db: DBSession) -> dict:
        """Find the best accountability partner for *user_id*.

        Scoring:
            - Same or adjacent timezone (within +/-2h): +40 pts
            - Same goal category:                       +30 pts
            - Complementary streak (beginner+intermediate): +20 pts
            - Both active in last 3 days:               +10 pts

        Returns:
            {match_user_id, compatibility_score, shared_traits, complementary_traits}
            or {match_user_id: None} if no match found.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"match_user_id": None, "reason": "user_not_found"}

        user_streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        user_tz_offset = _tz_offset(user.timezone or "UTC")

        # Get IDs of users already paired with this user
        existing_pair_ids = set()
        user_pods = (
            db.query(PodMember.pod_id)
            .filter(PodMember.user_id == user_id, PodMember.status == PodMemberStatus.active)
            .all()
        )
        for (pod_id,) in user_pods:
            members = (
                db.query(PodMember.user_id)
                .filter(PodMember.pod_id == pod_id, PodMember.status == PodMemberStatus.active)
                .all()
            )
            for (mid,) in members:
                existing_pair_ids.add(mid)

        # Candidate pool: all other active users not already paired
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        candidates = (
            db.query(User)
            .filter(
                User.id != user_id,
                User.last_active_at >= three_days_ago,
            )
            .all()
        )

        best_match = None
        best_score = -1

        for candidate in candidates:
            if candidate.id in existing_pair_ids:
                continue

            score = 0
            shared = []
            complementary = []

            # Timezone proximity
            cand_offset = _tz_offset(candidate.timezone or "UTC")
            if user_tz_offset is not None and cand_offset is not None:
                tz_diff = abs(user_tz_offset - cand_offset)
                if tz_diff <= 2:
                    score += 40
                    if tz_diff == 0:
                        shared.append("same timezone")
                    else:
                        shared.append(f"nearby timezone (±{tz_diff}h)")
                elif tz_diff <= 4:
                    score += 20

            # Goal match
            if user.goal and candidate.goal and user.goal == candidate.goal:
                score += 30
                shared.append(f"same goal: {user.goal.value}")

            # Complementary streak
            cand_streak = db.query(Streak).filter(Streak.user_id == candidate.id).first()
            cand_current = cand_streak.current_streak if cand_streak else 0
            user_current = user_streak.current_streak if user_streak else 0

            streak_diff = abs(user_current - cand_current)
            if 3 <= streak_diff <= 20:
                score += 20
                if user_current > cand_current:
                    complementary.append(f"you can mentor (your streak: {user_current}, theirs: {cand_current})")
                else:
                    complementary.append(f"they can guide you (their streak: {cand_current}, yours: {user_current})")
            elif streak_diff <= 2:
                score += 15
                shared.append(f"similar streak ({user_current} vs {cand_current} days)")

            # Both recently active
            if candidate.last_active_at and candidate.last_active_at >= three_days_ago:
                score += 10
                shared.append("both active recently")

            if score > best_score:
                best_score = score
                best_match = {
                    "match_user_id": candidate.id,
                    "match_name": candidate.name,
                    "compatibility_score": score,
                    "shared_traits": shared,
                    "complementary_traits": complementary,
                }

        if best_match is None:
            return {"match_user_id": None, "reason": "no_compatible_users_found"}

        return best_match

    # ------------------------------------------------------------------
    # Create pair
    # ------------------------------------------------------------------

    async def create_pair(self, user_a: str, user_b: str, db: DBSession) -> dict:
        """Create an accountability pair as a 2-person pod. Notify both agents."""
        user_a_obj = db.query(User).filter(User.id == user_a).first()
        user_b_obj = db.query(User).filter(User.id == user_b).first()

        if not user_a_obj or not user_b_obj:
            return {"success": False, "error": "one_or_both_users_not_found"}

        # Check if already paired
        a_pods = {
            pm.pod_id for pm in
            db.query(PodMember).filter(
                PodMember.user_id == user_a,
                PodMember.status == PodMemberStatus.active,
            ).all()
        }
        b_pods = {
            pm.pod_id for pm in
            db.query(PodMember).filter(
                PodMember.user_id == user_b,
                PodMember.status == PodMemberStatus.active,
            ).all()
        }
        shared_pods = a_pods & b_pods
        if shared_pods:
            return {
                "success": False,
                "error": "already_paired",
                "pod_id": shared_pods.pop(),
            }

        # Create a new 2-person pod
        pod = Pod(
            name=f"{user_a_obj.name} & {user_b_obj.name}",
            timezone=user_a_obj.timezone,
        )
        db.add(pod)
        db.flush()  # get pod.id

        member_a = PodMember(pod_id=pod.id, user_id=user_a)
        member_b = PodMember(pod_id=pod.id, user_id=user_b)
        db.add_all([member_a, member_b])
        db.commit()

        return {
            "success": True,
            "pod_id": pod.id,
            "pod_name": pod.name,
            "members": [user_a, user_b],
        }

    # ------------------------------------------------------------------
    # Pair health
    # ------------------------------------------------------------------

    async def get_pair_health(self, pair_id: str, db: DBSession) -> dict:
        """Check how an accountability pair is doing.

        Returns:
            {
                pod_id, members: [{user_id, name, streak, last_session_date, active}],
                health: 'strong' | 'drifting' | 'at_risk',
                suggestion: str,
            }
        """
        pod = db.query(Pod).filter(Pod.id == pair_id).first()
        if not pod:
            return {"error": "pod_not_found"}

        members_data = []
        three_days_ago = datetime.utcnow() - timedelta(days=3)

        pod_members = (
            db.query(PodMember)
            .filter(PodMember.pod_id == pair_id, PodMember.status == PodMemberStatus.active)
            .all()
        )

        active_count = 0
        streak_values = []

        for pm in pod_members:
            user = db.query(User).filter(User.id == pm.user_id).first()
            streak = db.query(Streak).filter(Streak.user_id == pm.user_id).first()

            last_session = (
                db.query(Session)
                .filter(Session.user_id == pm.user_id)
                .order_by(Session.logged_at.desc())
                .first()
            )

            is_active = (
                last_session is not None
                and last_session.logged_at is not None
                and last_session.logged_at >= three_days_ago
            )
            if is_active:
                active_count += 1

            current_streak = streak.current_streak if streak else 0
            streak_values.append(current_streak)

            members_data.append({
                "user_id": pm.user_id,
                "name": user.name if user else "Unknown",
                "streak": current_streak,
                "last_session_date": (
                    last_session.logged_at.date().isoformat()
                    if last_session and last_session.logged_at else None
                ),
                "active": is_active,
            })

        total_members = len(pod_members)

        # Determine health
        if total_members == 0:
            health = "at_risk"
            suggestion = "This pair has no active members."
        elif active_count == total_members:
            health = "strong"
            suggestion = "Both showing up. Keep the momentum."
        elif active_count >= 1:
            health = "drifting"
            inactive_names = [
                m["name"] for m in members_data if not m["active"]
            ]
            suggestion = (
                f"{', '.join(inactive_names)} hasn't been active in 3+ days. "
                f"A quick check-in might help."
            )
        else:
            health = "at_risk"
            suggestion = (
                "Neither partner has been active recently. "
                "Consider a fresh start or re-matching."
            )

        # Streak divergence warning
        if len(streak_values) == 2 and abs(streak_values[0] - streak_values[1]) > 15:
            suggestion += (
                f" Streaks have diverged ({streak_values[0]} vs {streak_values[1]}). "
                f"The stronger partner could send encouragement."
            )

        return {
            "pod_id": pair_id,
            "pod_name": pod.name,
            "members": members_data,
            "health": health,
            "suggestion": suggestion,
        }
