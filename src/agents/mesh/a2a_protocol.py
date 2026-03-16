"""A2AProtocol — Agent-to-agent communication, persisted via the Event table.

Inspired by Google's A2A protocol. Every message is stored as an Event
so we have a full audit trail without needing new DB migrations.

Event convention:
    event_type = "a2a:{message_type}"   e.g. "a2a:insight", "a2a:nudge_request"
    user_id    = from_agent             (the sender)
    payload    = {
        "to_agent": str | None,         # None means broadcast
        "message_type": str,
        "data": dict,
        "read": bool,
    }
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.db.models import Event, User, generate_uuid


class A2AProtocol:
    """Google A2A-inspired agent-to-agent communication protocol."""

    def __init__(self, db: DBSession):
        self.db = db

    async def send_message(
        self,
        from_agent: str,
        to_agent: str,
        message_type: str,
        payload: dict,
    ) -> dict:
        """Send a message from one agent to another. Stored in the Event table.

        Returns the created message dict with its id.
        """
        msg_id = generate_uuid()
        event = Event(
            id=msg_id,
            event_type=f"a2a:{message_type}",
            user_id=from_agent,
            payload={
                "to_agent": to_agent,
                "message_type": message_type,
                "data": payload,
                "read": False,
            },
        )
        self.db.add(event)
        self.db.commit()

        return {
            "id": msg_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "data": payload,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }

    async def get_messages(
        self,
        agent_id: str,
        since: Optional[datetime] = None,
        message_type: Optional[str] = None,
        unread_only: bool = False,
    ) -> list:
        """Get messages for an agent since a given time.

        Searches for events where payload->to_agent matches agent_id,
        or where to_agent is None (broadcasts).
        """
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=24)

        query = (
            self.db.query(Event)
            .filter(
                Event.event_type.like("a2a:%"),
                Event.created_at >= since,
            )
        )

        if message_type:
            query = query.filter(Event.event_type == f"a2a:{message_type}")

        query = query.order_by(Event.created_at.desc())
        events = query.all()

        messages = []
        for ev in events:
            p = ev.payload or {}
            target = p.get("to_agent")
            # Include if addressed to this agent or is a broadcast
            if target is not None and target != agent_id:
                continue
            if unread_only and p.get("read"):
                continue

            messages.append({
                "id": ev.id,
                "from_agent": ev.user_id,
                "to_agent": target,
                "message_type": p.get("message_type", "unknown"),
                "data": p.get("data", {}),
                "read": p.get("read", False),
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            })

        return messages

    async def mark_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        event = self.db.query(Event).filter(Event.id == message_id).first()
        if not event or not event.payload:
            return False
        payload = dict(event.payload)
        payload["read"] = True
        event.payload = payload
        self.db.commit()
        return True

    async def broadcast(
        self,
        from_agent: str,
        message_type: str,
        payload: dict,
    ) -> int:
        """Broadcast a message to all active agents. Returns count of recipients.

        Creates one Event per active user (agent). This ensures each agent
        can independently track read/unread state.
        """
        active_users = (
            self.db.query(User)
            .filter(User.id != from_agent)
            .all()
        )

        count = 0
        for user in active_users:
            event = Event(
                event_type=f"a2a:{message_type}",
                user_id=from_agent,
                payload={
                    "to_agent": user.id,
                    "message_type": message_type,
                    "data": payload,
                    "read": False,
                },
            )
            self.db.add(event)
            count += 1

        if count > 0:
            self.db.commit()

        return count

    async def get_conversation(
        self, agent_a: str, agent_b: str, limit: int = 50
    ) -> list:
        """Get the message history between two agents."""
        events = (
            self.db.query(Event)
            .filter(Event.event_type.like("a2a:%"))
            .order_by(Event.created_at.desc())
            .limit(limit * 3)  # over-fetch since we filter in Python
            .all()
        )

        messages = []
        for ev in events:
            p = ev.payload or {}
            sender = ev.user_id
            receiver = p.get("to_agent")
            if (sender == agent_a and receiver == agent_b) or (
                sender == agent_b and receiver == agent_a
            ):
                messages.append({
                    "id": ev.id,
                    "from_agent": sender,
                    "to_agent": receiver,
                    "message_type": p.get("message_type", "unknown"),
                    "data": p.get("data", {}),
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                })

            if len(messages) >= limit:
                break

        return list(reversed(messages))
