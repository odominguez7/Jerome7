"""In-process event bus for agent-to-agent communication.

Local dev: asyncio queue. Production: swap to Redis pub/sub.
The interface is identical — swap the backend, keep all agent logic unchanged.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

_subscribers: dict[str, list[Callable]] = defaultdict(list)
_queue: asyncio.Queue | None = None


def subscribe(event_type: str, handler: Callable[..., Coroutine]):
    """Register a handler for an event type."""
    _subscribers[event_type].append(handler)


async def publish(event_type: str, payload: dict[str, Any] | None = None):
    """Publish an event to all subscribers."""
    for handler in _subscribers.get(event_type, []):
        try:
            await handler(payload or {})
        except Exception as e:
            logger.error("[EventBus] Error in handler for %s: %s", event_type, e)


async def publish_and_store(event_type: str, user_id: str | None, payload: dict, db):
    """Publish event and persist it to the Event table."""
    from src.db.models import Event
    event = Event(event_type=event_type, user_id=user_id, payload=payload)
    db.add(event)
    db.commit()
    await publish(event_type, {**payload, "user_id": user_id})
