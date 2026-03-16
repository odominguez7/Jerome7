"""YU MCP Bridge — graduation gate from Show Up to real class booking.

The bridge opens at 14 days unbroken.
"""

import logging
import os
from dataclasses import dataclass

from src.agents.context import UserContext

logger = logging.getLogger(__name__)


@dataclass
class ClassOption:
    class_id: str
    studio_name: str
    activity_type: str
    start_time: str
    price: float
    spots_remaining: int
    studio_distance_km: float


@dataclass
class Booking:
    booking_id: str
    class_id: str
    confirmed: bool
    message: str


class IneligibleError(Exception):
    pass


GRADUATION_MESSAGE = """You have been unbroken for 14 days.
The bridge is open.
Here are 3 classes near you.
This is where the Seven 7 becomes the real thing."""


class YUMCPBridge:

    def __init__(self):
        self.mcp_url = os.getenv("YU_MCP_SERVER_URL")

    def is_eligible(self, ctx: UserContext) -> bool:
        return ctx.current_streak >= 14

    async def find_classes(self, ctx: UserContext, activity_type: str = "any") -> list[ClassOption]:
        if not self.is_eligible(ctx):
            raise IneligibleError(
                f"The bridge opens at 14 days unbroken. You are at day {ctx.current_streak}."
            )

        if not self.mcp_url:
            return self.mock_classes(activity_type)

        # Production: call YU MCP server
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.mcp_url}/tools/search_classes", json={
                    "activity_type": activity_type,
                    "location": ctx.timezone,
                    "price_max": 30,
                }) as resp:
                    data = await resp.json()
                    return [ClassOption(**c) for c in data.get("classes", [])]
        except Exception as e:
            logger.error("[YU Bridge] MCP call failed: %s", e)
            return self.mock_classes(activity_type)

    async def book_class(self, ctx: UserContext, class_id: str) -> Booking:
        if not self.is_eligible(ctx):
            raise IneligibleError(
                f"The bridge opens at 14 days unbroken. You are at day {ctx.current_streak}."
            )

        if not self.mcp_url:
            return Booking(
                booking_id="mock-booking-001",
                class_id=class_id,
                confirmed=True,
                message="Mock booking confirmed. Set YU_MCP_SERVER_URL for live bookings.",
            )

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.mcp_url}/tools/book_class", json={
                    "class_id": class_id,
                    "user_id": ctx.user_id,
                }) as resp:
                    data = await resp.json()
                    return Booking(**data)
        except Exception as e:
            logger.error("[YU Bridge] Booking failed: %s", e)
            raise

    def mock_classes(self, activity_type: str = "any") -> list[ClassOption]:
        """Return 3 realistic mock classes for local dev."""
        logger.info("[YU Bridge] Running in mock mode — set YU_MCP_SERVER_URL for live.")
        return [
            ClassOption(
                class_id="mock-yoga-001",
                studio_name="Flow Studio",
                activity_type="yoga",
                start_time="2026-03-14T07:00:00",
                price=18.00,
                spots_remaining=4,
                studio_distance_km=1.2,
            ),
            ClassOption(
                class_id="mock-hiit-002",
                studio_name="Burn Box",
                activity_type="hiit",
                start_time="2026-03-14T06:30:00",
                price=22.00,
                spots_remaining=8,
                studio_distance_km=2.5,
            ),
            ClassOption(
                class_id="mock-spin-003",
                studio_name="Cycle House",
                activity_type="cycling",
                start_time="2026-03-14T07:30:00",
                price=25.00,
                spots_remaining=2,
                studio_distance_km=0.8,
            ),
        ]
