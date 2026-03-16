"""MessageBus — In-memory pub/sub for inter-agent communication.

Lightweight event bus that lives in process memory.
For persistence, agents should also write to the Event table via A2AProtocol.
"""

import logging
import time
from collections import defaultdict
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class MessageBus:
    """In-memory message bus for inter-agent communication."""

    def __init__(self):
        self.subscribers: dict[str, list[Callable]] = defaultdict(list)
        self.message_log: list[dict] = []
        self._max_log_size = 500

    def subscribe(self, agent_id: str, callback: Callable):
        """Subscribe an agent to receive messages.

        Args:
            agent_id: Unique agent identifier.
            callback: Async or sync callable that receives a message dict.
        """
        if callback not in self.subscribers[agent_id]:
            self.subscribers[agent_id].append(callback)

    def unsubscribe(self, agent_id: str, callback: Optional[Callable] = None):
        """Remove a subscription. If callback is None, remove all for agent."""
        if callback is None:
            self.subscribers.pop(agent_id, None)
        elif agent_id in self.subscribers:
            self.subscribers[agent_id] = [
                cb for cb in self.subscribers[agent_id] if cb is not callback
            ]

    def publish(self, message: dict):
        """Publish a message to all subscribers.

        The message dict should contain at minimum:
            - message_type: str (e.g. "insight", "nudge", "checkup")
            - from_agent: str (sender agent_id)
            - payload: dict (the actual data)

        Messages are delivered to every subscriber except the sender.
        """
        stamped = {
            **message,
            "published_at": time.time(),
            "bus_seq": len(self.message_log),
        }

        self.message_log.append(stamped)
        if len(self.message_log) > self._max_log_size:
            self.message_log = self.message_log[-self._max_log_size:]

        sender = message.get("from_agent")
        delivered = 0
        for agent_id, callbacks in self.subscribers.items():
            if agent_id == sender:
                continue
            for cb in callbacks:
                try:
                    cb(stamped)
                    delivered += 1
                except Exception as e:
                    logger.error("[MessageBus] Error delivering to %s: %s", agent_id, e)

        return delivered

    def get_recent_messages(self, limit: int = 50) -> list:
        """Get recent messages from the bus, newest first."""
        return list(reversed(self.message_log[-limit:]))

    def get_messages_by_type(self, message_type: str, limit: int = 20) -> list:
        """Filter recent messages by type."""
        matching = [
            m for m in reversed(self.message_log)
            if m.get("message_type") == message_type
        ]
        return matching[:limit]

    @property
    def subscriber_count(self) -> int:
        """Number of unique agents subscribed."""
        return len(self.subscribers)

    @property
    def total_messages(self) -> int:
        """Total messages published since bus creation."""
        if not self.message_log:
            return 0
        return self.message_log[-1].get("bus_seq", 0) + 1
