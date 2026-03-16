"""Intervention Engine — suggest and execute proactive interventions.

Matches risk scores to the right intervention, then logs and executes them.
"""

import asyncio
import json
import os
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Streak, Event, Nudge, PodMember


def _call_gemini(system_prompt: str, user_content: str, api_key: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
        ),
    )
    return response.text


INTERVENTION_MSG_PROMPT = """You are Jerome — a friend, not a coach.
Write a short intervention message for a user who is at risk of dropping off.

Context will include: their name, streak, risk level, and intervention type.

Output JSON only:
{"message": "2-3 sentences max. warm, specific, never preachy."}

Rules:
- Reference their actual numbers.
- Never use fitness cliches.
- If offering a break, make it feel safe, not like failure.
- If activating a buddy, explain what that means simply."""


class InterventionEngine:
    """Suggest and execute proactive interventions."""

    INTERVENTIONS = {
        "encourage": {
            "threshold": 0.3,
            "action": "Send encouraging message",
            "description": "A warm nudge with streak context.",
        },
        "ease_difficulty": {
            "threshold": 0.5,
            "action": "Suggest easier session variant",
            "description": "Offer a gentler session — 3 blocks instead of 7.",
        },
        "activate_buddy": {
            "threshold": 0.7,
            "action": "Connect with accountability partner",
            "description": "Pair with someone in a similar situation.",
        },
        "offer_break": {
            "threshold": 0.9,
            "action": "Offer pause without chain penalty",
            "description": "A streak save — 1 free day, no penalty.",
        },
    }

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    async def suggest_intervention(
        self, user_id: str, risk_score: float, db: DBSession
    ) -> dict:
        """Suggest the right intervention based on risk score (0-1).

        Returns: {intervention_type, action, reason, risk_score}
        """
        # Find the highest-threshold intervention that the risk score exceeds
        selected = "encourage"
        for itype, config in sorted(
            self.INTERVENTIONS.items(), key=lambda x: x[1]["threshold"], reverse=True
        ):
            if risk_score >= config["threshold"]:
                selected = itype
                break

        # Check if this intervention was already done recently
        recent_intervention = (
            db.query(Event)
            .filter(
                Event.user_id == user_id,
                Event.event_type == "intervention_executed",
                func.date(Event.created_at) >= date.today() - timedelta(days=2),
            )
            .first()
        )

        if recent_intervention:
            # Escalate if the same intervention was already tried
            prev_type = (
                recent_intervention.payload.get("intervention_type")
                if recent_intervention.payload
                else None
            )
            if prev_type == selected:
                # Move up one level
                levels = list(self.INTERVENTIONS.keys())
                idx = levels.index(selected)
                if idx < len(levels) - 1:
                    selected = levels[idx + 1]

        return {
            "intervention_type": selected,
            "action": self.INTERVENTIONS[selected]["action"],
            "description": self.INTERVENTIONS[selected]["description"],
            "risk_score": risk_score,
        }

    async def execute_intervention(
        self, user_id: str, intervention_type: str, db: DBSession
    ) -> dict:
        """Execute an intervention and log it.

        Returns: {success, intervention_type, message, details}
        """
        user = db.query(User).filter(User.id == user_id).first()
        streak = db.query(Streak).filter(Streak.user_id == user_id).first()

        if not user or not streak:
            return {
                "success": False,
                "intervention_type": intervention_type,
                "message": "User not found.",
                "details": None,
            }

        result = {
            "success": True,
            "intervention_type": intervention_type,
            "message": "",
            "details": {},
        }

        if intervention_type == "encourage":
            result["message"] = await self._generate_encourage_message(user, streak)
            result["details"] = {"channel": "nudge"}

            # Create a nudge record
            nudge = Nudge(
                user_id=user_id,
                channel="intervention",
                message_text=result["message"],
            )
            db.add(nudge)

        elif intervention_type == "ease_difficulty":
            result["message"] = await self._generate_intervention_message(
                user, streak, "ease_difficulty"
            )
            result["details"] = {
                "adjusted_blocks": 3,
                "note": "Offer 3-block mini session instead of full 7.",
            }

            nudge = Nudge(
                user_id=user_id,
                channel="intervention",
                message_text=result["message"],
            )
            db.add(nudge)

        elif intervention_type == "activate_buddy":
            buddy = await self._find_buddy(user_id, db)
            result["message"] = await self._generate_intervention_message(
                user, streak, "activate_buddy"
            )
            result["details"] = {
                "buddy_id": buddy.get("buddy_id") if buddy else None,
                "buddy_name": buddy.get("buddy_name") if buddy else None,
            }

            nudge = Nudge(
                user_id=user_id,
                channel="intervention",
                message_text=result["message"],
            )
            db.add(nudge)

        elif intervention_type == "offer_break":
            # Grant a streak save
            can_save = self._can_use_streak_save(streak)
            if can_save:
                streak.saves_used = (streak.saves_used or 0) + 1
                streak.last_save_date = date.today()
                result["message"] = await self._generate_intervention_message(
                    user, streak, "offer_break"
                )
                result["details"] = {
                    "streak_save_granted": True,
                    "saves_used_total": streak.saves_used,
                }
            else:
                result["message"] = (
                    f"{user.name}, you've used your saves recently. "
                    "But your streak still matters — even a 2-minute stretch counts. "
                    "Show up in any way you can."
                )
                result["details"] = {"streak_save_granted": False}

        # Log the intervention event
        event = Event(
            event_type="intervention_executed",
            user_id=user_id,
            payload={
                "intervention_type": intervention_type,
                "message": result["message"],
                "details": result["details"],
                "executed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.add(event)
        db.commit()

        return result

    def _can_use_streak_save(self, streak: Streak) -> bool:
        """Check if a user is eligible for a streak save.

        Rules: max 1 save per 14 days, max 3 total saves.
        """
        if (streak.saves_used or 0) >= 3:
            return False
        if streak.last_save_date:
            days_since_save = (date.today() - streak.last_save_date).days
            if days_since_save < 14:
                return False
        return True

    async def _find_buddy(self, user_id: str, db: DBSession) -> dict | None:
        """Find a potential accountability buddy from the same pod or similar users."""
        # Check if user is in a pod
        membership = (
            db.query(PodMember)
            .filter(
                PodMember.user_id == user_id,
                PodMember.status == "active",
            )
            .first()
        )

        if membership:
            # Find another active member in the same pod
            buddy_member = (
                db.query(PodMember)
                .filter(
                    PodMember.pod_id == membership.pod_id,
                    PodMember.user_id != user_id,
                    PodMember.status == "active",
                )
                .first()
            )
            if buddy_member:
                buddy_user = (
                    db.query(User).filter(User.id == buddy_member.user_id).first()
                )
                if buddy_user:
                    return {
                        "buddy_id": buddy_user.id,
                        "buddy_name": buddy_user.name,
                    }

        # Fallback: find a user with a similar streak length
        user_streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        if user_streak:
            similar = (
                db.query(Streak)
                .filter(
                    Streak.user_id != user_id,
                    Streak.current_streak >= max(user_streak.current_streak - 3, 0),
                    Streak.current_streak <= user_streak.current_streak + 3,
                )
                .first()
            )
            if similar:
                buddy_user = db.query(User).filter(User.id == similar.user_id).first()
                if buddy_user:
                    return {
                        "buddy_id": buddy_user.id,
                        "buddy_name": buddy_user.name,
                    }

        return None

    async def _generate_encourage_message(self, user: User, streak: Streak) -> str:
        """Generate an encouraging message, using Gemini if available."""
        default = (
            f"{user.name}, your {streak.current_streak}-day streak is real. "
            f"Today's session is ready. 7 minutes, that's it."
        )
        if not self.api_key:
            return default

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    _call_gemini,
                    INTERVENTION_MSG_PROMPT,
                    f"Name: {user.name}. Streak: {streak.current_streak} days. "
                    f"Intervention: encourage. Risk: low-medium.",
                    self.api_key,
                ),
                timeout=15,
            )
            data = json.loads(content)
            return data.get("message", default)
        except Exception:
            return default

    async def _generate_intervention_message(
        self, user: User, streak: Streak, intervention_type: str
    ) -> str:
        """Generate intervention-specific message via Gemini."""
        default_messages = {
            "ease_difficulty": (
                f"{user.name}, today can be lighter. Just 3 blocks. "
                f"Your {streak.current_streak}-day chain stays alive either way."
            ),
            "activate_buddy": (
                f"{user.name}, you don't have to do this alone. "
                f"We're pairing you with someone on a similar journey."
            ),
            "offer_break": (
                f"{user.name}, life happens. We're giving you a free day — "
                f"your {streak.current_streak}-day streak is safe. Come back when you're ready."
            ),
        }
        default = default_messages.get(
            intervention_type,
            f"{user.name}, we're here. Your session is waiting.",
        )

        if not self.api_key:
            return default

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    _call_gemini,
                    INTERVENTION_MSG_PROMPT,
                    f"Name: {user.name}. Streak: {streak.current_streak} days. "
                    f"Breaks: {streak.streak_broken_count}. "
                    f"Intervention: {intervention_type}.",
                    self.api_key,
                ),
                timeout=15,
            )
            data = json.loads(content)
            return data.get("message", default)
        except Exception:
            return default
