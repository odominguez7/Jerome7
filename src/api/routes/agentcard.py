"""GET /.well-known/agent.json — A2A AgentCard for Jerome7."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

AGENT_CARD = {
    "name": "Jerome7 Wellness Agent",
    "description": "Daily 7-minute guided wellness sessions for developers. "
                   "Breathwork, meditation, reflection, and preparation — "
                   "powered by AI agents that learn your patterns.",
    "url": "https://api.jerome7.com/a2a",
    "version": "1.0.0",
    "capabilities": {
        "streaming": True,
        "pushNotifications": True,
    },
    "skills": [
        {
            "id": "daily-session",
            "name": "Daily 7-Minute Session",
            "description": "Generate and deliver today's guided wellness session "
                           "(breathwork, meditation, reflection, or preparation).",
        },
        {
            "id": "streak-check",
            "name": "Streak Status",
            "description": "Check user's current streak and accountability status.",
        },
        {
            "id": "community-match",
            "name": "Community Matching",
            "description": "Find accountability partners by timezone and engagement level.",
        },
        {
            "id": "wellness-nudge",
            "name": "Wellness Nudge",
            "description": "Predict skip patterns and send preemptive wellness reminders.",
        },
        {
            "id": "schedule-optimize",
            "name": "Schedule Optimizer",
            "description": "Find the optimal daily session window from user history.",
        },
    ],
    "authentication": {
        "schemes": ["bearer"],
    },
    "provider": {
        "organization": "Jerome7",
        "url": "https://jerome7.com",
    },
}


@router.get("/.well-known/agent.json")
async def get_agent_card():
    return JSONResponse(content=AGENT_CARD)
