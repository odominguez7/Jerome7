"""Community Matcher Agent — pod formation algorithm.

Pods are 3-5 people in a real accountability relationship.
Pod names are permanent and become part of community identity.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.agents.context import UserContext
from src.db.models import User, Pod, PodMember, PodMemberStatus

ADJECTIVES = [
    "Iron", "Quiet", "Dawn", "Still", "Wild", "Bright", "Swift",
    "Calm", "Fierce", "Steady", "Bold", "True", "Deep", "Clear",
    "Warm", "Sharp", "Strong", "Free", "Pure", "Last",
]

ANIMALS = [
    "Otters", "Lions", "Foxes", "Bears", "Hawks", "Wolves", "Eagles",
    "Owls", "Ravens", "Stags", "Falcons", "Cranes", "Tigers", "Pumas",
    "Lynx", "Herons", "Jaguars", "Marlins", "Cobras", "Vipers",
]


@dataclass
class PodMatch:
    proposed_members: list[str]  # user_ids
    shared_windows: list[dict] = field(default_factory=list)
    compatibility_score: float = 0.0


class CommunityMatcherAgent:

    def find_pod(self, ctx: UserContext, db: DBSession) -> Optional[PodMatch]:
        """Find compatible pod members for a user."""
        # Get unmatched users (no active pod, pledged in last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        # Users without active pod membership
        matched_user_ids = {
            m.user_id for m in
            db.query(PodMember).filter(PodMember.status == PodMemberStatus.active).all()
        }

        candidates = (
            db.query(User)
            .filter(
                User.id != ctx.user_id,
                User.created_at >= seven_days_ago,
                User.id.notin_(matched_user_ids) if matched_user_ids else True,
            )
            .all()
        )

        if not candidates:
            return None

        scored = []
        for candidate in candidates:
            score = self._score_compatibility(ctx, candidate)
            if score > 0.4:
                scored.append((candidate.id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:4]  # Max 4 others + the requesting user = 5

        if len(top) < 2:  # Need at least 2 others for a pod of 3
            return None

        return PodMatch(
            proposed_members=[ctx.user_id] + [uid for uid, _ in top],
            compatibility_score=sum(s for _, s in top) / len(top),
        )

    def form_pod(self, user_ids: list[str], db: DBSession) -> Pod:
        """Create a pod and assign members."""
        name = self._generate_pod_name(db)

        pod = Pod(name=name)
        db.add(pod)
        db.flush()

        for uid in user_ids:
            member = PodMember(pod_id=pod.id, user_id=uid)
            db.add(member)

        db.commit()
        return pod

    def _score_compatibility(self, ctx: UserContext, candidate: User) -> float:
        """Score compatibility between the requesting user and a candidate."""
        # Timezone overlap score (0-1)
        tz_score = 1.0 if ctx.timezone == candidate.timezone else 0.5

        # Level score
        level_map = {"beginner": 0, "returning": 1, "active": 2}
        ctx_level = level_map.get(ctx.fitness_level, 0)
        cand_level = level_map.get(candidate.fitness_level.value if candidate.fitness_level else "beginner", 0)
        diff = abs(ctx_level - cand_level)
        level_scores = {0: 1.0, 1: 0.8, 2: 0.3}
        level_score = level_scores.get(diff, 0.3)

        # Window overlap (simplified — use timezone as proxy)
        window_score = tz_score

        total = (window_score * 0.5) + (level_score * 0.3) + (tz_score * 0.2)
        return total

    def _generate_pod_name(self, db: DBSession) -> str:
        """Generate a unique two-word pod name."""
        existing_names = {p.name for p in db.query(Pod).all()}
        for _ in range(100):
            name = f"{random.choice(ADJECTIVES)} {random.choice(ANIMALS)}"
            if name not in existing_names:
                return name
        return f"{random.choice(ADJECTIVES)} {random.choice(ANIMALS)} {random.randint(1, 99)}"
