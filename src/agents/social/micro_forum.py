"""Micro Forum — small-group AI-moderated conversations.

Groups of 3-7 users. Like a group chat but Jerome keeps it healthy.
Powered by Google Gemini 2.5 Flash.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from src.db.models import User, Event, generate_uuid


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


MODERATION_PROMPT = """You are Jerome — the community moderator for micro-forums.
Given a list of recent messages in a small group, assess the forum's health.

Output JSON only:
{
  "health_score": 0-100,
  "silent_members": ["name1"],
  "flagged_messages": [{"message_id": "...", "reason": "..."}],
  "conversation_starter": "A question or prompt to spark healthy conversation, or null if not needed"
}

Rules:
- Flag anything toxic, shaming, or discouraging.
- If someone hasn't posted in 3+ days, list them as silent.
- Only suggest a conversation starter if the forum has been quiet for 24+ hours.
- Keep it warm. This is a support group, not a courtroom."""


class MicroForum:
    """Create micro-forums for small groups of 3-7 users.

    Like a group chat but AI-moderated.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    async def create_forum(
        self, name: str, user_ids: list, db: DBSession
    ) -> dict:
        """Create a micro-forum. Returns forum details.

        Forums are stored as events — lightweight, no new tables needed.
        """
        if len(user_ids) < 2 or len(user_ids) > 7:
            return {
                "success": False,
                "error": "Forums need 2-7 members.",
            }

        forum_id = generate_uuid()

        # Verify all users exist
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        if len(users) != len(user_ids):
            return {
                "success": False,
                "error": "One or more user IDs not found.",
            }

        member_names = {u.id: u.name for u in users}

        # Create the forum as an event
        event = Event(
            event_type="forum_created",
            payload={
                "forum_id": forum_id,
                "name": name,
                "member_ids": user_ids,
                "member_names": member_names,
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        db.add(event)
        db.commit()

        return {
            "success": True,
            "forum_id": forum_id,
            "name": name,
            "members": member_names,
        }

    async def post_message(
        self, forum_id: str, user_id: str, message: str, db: DBSession
    ) -> dict:
        """Post a message to a forum."""
        # Verify forum exists
        forum_event = (
            db.query(Event)
            .filter(
                Event.event_type == "forum_created",
            )
            .all()
        )
        forum = None
        for evt in forum_event:
            if evt.payload and evt.payload.get("forum_id") == forum_id:
                forum = evt.payload
                break

        if not forum:
            return {"success": False, "error": "Forum not found."}

        # Verify user is a member
        if user_id not in forum.get("member_ids", []):
            return {"success": False, "error": "User is not a member of this forum."}

        user = db.query(User).filter(User.id == user_id).first()
        message_id = generate_uuid()

        event = Event(
            event_type="forum_message",
            user_id=user_id,
            payload={
                "forum_id": forum_id,
                "message_id": message_id,
                "author_name": user.name if user else "Unknown",
                "text": message,
                "posted_at": datetime.utcnow().isoformat(),
            },
        )
        db.add(event)
        db.commit()

        return {
            "success": True,
            "message_id": message_id,
            "forum_id": forum_id,
        }

    async def get_messages(
        self, forum_id: str, db: DBSession, limit: int = 50
    ) -> list:
        """Get recent messages from a forum."""
        events = (
            db.query(Event)
            .filter(Event.event_type == "forum_message")
            .order_by(Event.created_at.desc())
            .all()
        )

        messages = []
        for evt in events:
            if evt.payload and evt.payload.get("forum_id") == forum_id:
                messages.append({
                    "message_id": evt.payload.get("message_id"),
                    "author_id": evt.user_id,
                    "author_name": evt.payload.get("author_name"),
                    "text": evt.payload.get("text"),
                    "posted_at": evt.payload.get("posted_at"),
                })
                if len(messages) >= limit:
                    break

        return messages

    async def ai_moderate(self, forum_id: str, db: DBSession) -> dict:
        """AI moderator checks forum health.

        - Is everyone participating?
        - Any toxic messages?
        - Suggest conversation starters if quiet.
        """
        # Get forum info
        forum_events = (
            db.query(Event)
            .filter(Event.event_type == "forum_created")
            .all()
        )
        forum = None
        for evt in forum_events:
            if evt.payload and evt.payload.get("forum_id") == forum_id:
                forum = evt.payload
                break

        if not forum:
            return {"error": "Forum not found."}

        # Get recent messages
        messages = await self.get_messages(forum_id, db, limit=50)

        member_ids = set(forum.get("member_ids", []))
        member_names = forum.get("member_names", {})

        # Track who has posted recently (last 3 days)
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        recent_posters = set()
        for msg in messages:
            posted_at = msg.get("posted_at", "")
            try:
                if datetime.fromisoformat(posted_at) >= three_days_ago:
                    recent_posters.add(msg["author_id"])
            except (ValueError, TypeError):
                recent_posters.add(msg["author_id"])

        silent_member_ids = member_ids - recent_posters
        silent_names = [
            member_names.get(uid, uid) for uid in silent_member_ids
        ]

        # Use Gemini for deeper moderation if available
        if self.api_key and messages:
            return await self._gemini_moderate(
                messages, silent_names, forum.get("name", "")
            )

        # Fallback moderation
        last_message_time = None
        if messages:
            try:
                last_message_time = datetime.fromisoformat(
                    messages[0].get("posted_at", "")
                )
            except (ValueError, TypeError):
                pass

        needs_starter = False
        if last_message_time:
            if datetime.utcnow() - last_message_time > timedelta(hours=24):
                needs_starter = True
        elif not messages:
            needs_starter = True

        return {
            "health_score": 70 if not silent_names else 50,
            "silent_members": silent_names,
            "flagged_messages": [],
            "conversation_starter": (
                "What's one thing you're proud of from this week?"
                if needs_starter
                else None
            ),
        }

    async def _gemini_moderate(
        self, messages: list, silent_names: list, forum_name: str
    ) -> dict:
        """Use Gemini for AI moderation."""
        # Build message summary for Gemini (last 20 messages)
        msg_summary = []
        for msg in messages[:20]:
            msg_summary.append(
                f"[{msg['author_name']}]: {msg['text']}"
            )

        user_content = (
            f"Forum: {forum_name}\n"
            f"Silent members (no posts in 3 days): {', '.join(silent_names) if silent_names else 'none'}\n"
            f"Recent messages:\n" + "\n".join(msg_summary)
        )

        try:
            content = await asyncio.wait_for(
                asyncio.to_thread(
                    _call_gemini, MODERATION_PROMPT, user_content, self.api_key
                ),
                timeout=15,
            )
            return json.loads(content)
        except Exception as e:
            print(f"[MicroForum] Moderation failed: {e}")
            return {
                "health_score": 60,
                "silent_members": silent_names,
                "flagged_messages": [],
                "conversation_starter": None,
            }
