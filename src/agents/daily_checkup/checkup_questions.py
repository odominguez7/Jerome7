"""Checkup Questions — adaptive daily questions based on BJ Fogg's B=MAP model.

Behavior = Motivation x Ability x Prompt.
Powered by Google Gemini 2.5 Flash.
"""

import asyncio
import json
import logging
import os
import random
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Streak, Session, SessionFeedback, Event

logger = logging.getLogger(__name__)


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


ANSWER_PROCESSING_PROMPT = """You are Jerome's adaptive coach.
A user answered a daily checkup question. Based on their answer, suggest ONE adjustment
to their experience.

Output JSON only:
{
  "interpretation": "1 sentence — what you learned from their answer",
  "adjustment_type": "timing|difficulty|motivation|none",
  "adjustment_detail": "1 sentence — specific change to make",
  "follow_up": "1 sentence — optional follow-up message to user, or null"
}

Rules:
- Be specific and actionable.
- Never patronize. Talk like a friend.
- If the answer is positive, adjustment_type should be "none"."""


class CheckupQuestions:
    """Adaptive daily questions based on BJ Fogg's B=MAP model.

    Behavior = Motivation x Ability x Prompt.
    """

    QUESTION_BANK = {
        "motivation": [
            {
                "id": "mot_scale",
                "text": "On a scale of 1-5, how motivated do you feel to show up today?",
                "response_type": "scale",
            },
            {
                "id": "mot_driver",
                "text": "What's driving you to keep your chain going?",
                "response_type": "text",
            },
            {
                "id": "mot_energy",
                "text": "How's your energy right now? Low, medium, or high?",
                "response_type": "choice",
                "choices": ["low", "medium", "high"],
            },
            {
                "id": "mot_why",
                "text": "In one word, why are you here today?",
                "response_type": "text",
            },
        ],
        "ability": [
            {
                "id": "abl_time",
                "text": "Do you have 7 minutes available right now?",
                "response_type": "choice",
                "choices": ["yes", "not yet", "tight today"],
            },
            {
                "id": "abl_physical",
                "text": "Any physical limitations today?",
                "response_type": "text",
            },
            {
                "id": "abl_space",
                "text": "Do you have enough space to move around?",
                "response_type": "choice",
                "choices": ["yes", "small space", "no"],
            },
            {
                "id": "abl_difficulty",
                "text": "Was yesterday's session too easy, just right, or too hard?",
                "response_type": "choice",
                "choices": ["too easy", "just right", "too hard"],
            },
        ],
        "prompt": [
            {
                "id": "pmt_when",
                "text": "When do you plan to do your session today?",
                "response_type": "text",
            },
            {
                "id": "pmt_reminder",
                "text": "Would you like a reminder at a specific time?",
                "response_type": "text",
            },
            {
                "id": "pmt_trigger",
                "text": "What usually triggers you to start your session?",
                "response_type": "text",
            },
            {
                "id": "pmt_anchor",
                "text": "What activity do you do right before your session? (e.g., morning coffee)",
                "response_type": "text",
            },
        ],
    }

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    async def get_daily_question(self, user_id: str, db: DBSession) -> dict:
        """Select the most relevant question based on user's current state.

        - New user (streak < 3): motivation question
        - At-risk user: ability question (lower barrier)
        - Consistent user: prompt question (optimize timing)
        Returns: {question, category, context}
        """
        streak = db.query(Streak).filter(Streak.user_id == user_id).first()
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return {
                "question": self.QUESTION_BANK["motivation"][0],
                "category": "motivation",
                "context": "unknown_user",
            }

        # Determine which category to ask
        category, context = self._select_category(user_id, streak, db)

        # Pick a question from that category, avoiding recent repeats
        question = self._pick_question(user_id, category, db)

        return {
            "question": question,
            "category": category,
            "context": context,
        }

    async def process_answer(
        self, user_id: str, question_id: str, answer: str, db: DBSession
    ) -> dict:
        """Process the answer and adjust user's agent accordingly."""
        user = db.query(User).filter(User.id == user_id).first()
        name = user.name if user else "friend"

        # Log the Q&A as an event
        event = Event(
            event_type="checkup_answer",
            user_id=user_id,
            payload={
                "question_id": question_id,
                "answer": answer,
                "date": date.today().isoformat(),
            },
        )
        db.add(event)
        db.commit()

        # If it's a simple energy update, apply directly
        if question_id == "mot_energy" and user:
            from src.db.models import EnergyLevel
            energy_map = {
                "low": EnergyLevel.low,
                "medium": EnergyLevel.medium,
                "high": EnergyLevel.high,
            }
            if answer.lower() in energy_map:
                user.energy_today = energy_map[answer.lower()]
                db.commit()
                return {
                    "interpretation": f"Energy set to {answer.lower()}.",
                    "adjustment_type": "none",
                    "adjustment_detail": "Session will adapt to your energy level.",
                    "follow_up": None,
                }

        # If it's the motivation scale, handle numerically
        if question_id == "mot_scale":
            try:
                score = int(answer)
                if score <= 2:
                    return {
                        "interpretation": f"{name} is low on motivation today.",
                        "adjustment_type": "difficulty",
                        "adjustment_detail": "Offer the easiest possible session. Completion > intensity.",
                        "follow_up": "Even 3 blocks count. Just start.",
                    }
                elif score >= 4:
                    return {
                        "interpretation": f"{name} is fired up.",
                        "adjustment_type": "none",
                        "adjustment_detail": "No changes needed.",
                        "follow_up": None,
                    }
            except ValueError:
                pass

        # For text answers, use Gemini to interpret
        if self.api_key:
            return await self._gemini_process_answer(
                name, question_id, answer
            )

        # Fallback
        return {
            "interpretation": "Answer recorded.",
            "adjustment_type": "none",
            "adjustment_detail": "No adjustment.",
            "follow_up": None,
        }

    def _select_category(
        self, user_id: str, streak: Streak | None, db: DBSession
    ) -> tuple[str, str]:
        """Decide which B=MAP category to probe today."""
        if not streak or streak.current_streak < 3:
            return "motivation", "new_user"

        # Check if user has been declining
        week_ago = date.today() - timedelta(days=7)
        recent_feedback = (
            db.query(SessionFeedback)
            .filter(
                SessionFeedback.user_id == user_id,
                SessionFeedback.session_date >= week_ago,
            )
            .all()
        )

        # At-risk signals: low completion, high difficulty, pain
        at_risk = False
        if recent_feedback:
            avg_completion = [
                f.completed_blocks for f in recent_feedback
                if f.completed_blocks is not None
            ]
            if avg_completion and (sum(avg_completion) / len(avg_completion)) < 5:
                at_risk = True

            avg_difficulty = [
                f.difficulty_rating for f in recent_feedback
                if f.difficulty_rating is not None
            ]
            if avg_difficulty and (sum(avg_difficulty) / len(avg_difficulty)) > 4:
                at_risk = True

            for fb in recent_feedback:
                if fb.body_note and any(
                    kw in fb.body_note.lower()
                    for kw in ("pain", "hurt", "sore", "injured")
                ):
                    at_risk = True
                    break

        if at_risk:
            return "ability", "at_risk"

        # Check recent session count
        recent_sessions = (
            db.query(Session)
            .filter(
                Session.user_id == user_id,
                func.date(Session.logged_at) >= week_ago,
            )
            .count()
        )

        if recent_sessions < 4:
            return "motivation", "inconsistent"

        # Consistent user — optimize their prompt/trigger
        if streak.current_streak >= 7:
            return "prompt", "consistent"

        return "motivation", "building_habit"

    def _pick_question(
        self, user_id: str, category: str, db: DBSession
    ) -> dict:
        """Pick a question, avoiding ones asked in the last 3 days."""
        questions = self.QUESTION_BANK[category]

        # Get recently asked question IDs
        three_days_ago = date.today() - timedelta(days=3)
        recent_events = (
            db.query(Event)
            .filter(
                Event.user_id == user_id,
                Event.event_type == "checkup_answer",
                func.date(Event.created_at) >= three_days_ago,
            )
            .all()
        )
        recent_ids = set()
        for evt in recent_events:
            if evt.payload and "question_id" in evt.payload:
                recent_ids.add(evt.payload["question_id"])

        # Filter out recently asked
        available = [q for q in questions if q["id"] not in recent_ids]
        if not available:
            available = questions

        return random.choice(available)

    async def _gemini_process_answer(
        self, name: str, question_id: str, answer: str
    ) -> dict:
        """Use Gemini to interpret a free-text answer."""
        user_content = (
            f"User: {name}\n"
            f"Question ID: {question_id}\n"
            f"Their answer: {answer}"
        )

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    _call_gemini, ANSWER_PROCESSING_PROMPT, user_content, self.api_key
                ),
                timeout=15,
            )
            return json.loads(content)
        except Exception as e:
            logger.error("[CheckupQuestions] Gemini processing failed: %s", e)
            return {
                "interpretation": "Answer recorded.",
                "adjustment_type": "none",
                "adjustment_detail": "No adjustment.",
                "follow_up": None,
            }
