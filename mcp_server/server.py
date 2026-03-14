"""Jerome7 MCP Server — expose core functionality as tools for MCP-compatible agents.

Start with:
    python -m mcp_server.server
    # or
    mcp run mcp_server/server.py
"""

import os
import json

import httpx
from mcp.server.fastmcp import FastMCP

API_URL = os.getenv("JEROME7_API_URL", "https://jerome7.com").rstrip("/")

mcp = FastMCP(
    "jerome7",
    description="Jerome7 — 7 minutes a day. An act of love. Tools for session generation, logging, streaks, nudges, and pod matching.",
)


def _api(method: str, path: str, **kwargs) -> dict:
    """Synchronous helper to call the Jerome7 API."""
    url = f"{API_URL}{path}"
    with httpx.Client(timeout=30) as client:
        resp = client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()


# ---------- Tools ----------


@mcp.tool()
def jerome7_daily(user_id: str) -> str:
    """Get today's Seven 7 session for a user.

    Returns the personalised 7-minute session including greeting, blocks,
    and closing message. If a session was already generated today it is
    returned from cache.

    Args:
        user_id: The unique identifier of the user.
    """
    try:
        data = _api("GET", f"/seven7/{user_id}")
        return json.dumps(data, indent=2)
    except httpx.HTTPStatusError as exc:
        return f"API error {exc.response.status_code}: {exc.response.text}"
    except httpx.ConnectError:
        return f"Could not connect to Jerome7 API at {API_URL}. Is the server running?"


@mcp.tool()
def jerome7_pledge(
    user_id: str,
    name: str,
    timezone: str = "UTC",
    fitness_level: str = "beginner",
    age_bracket: str = "",
    gender: str = "",
    goal: str = "",
) -> str:
    """Register (pledge) a new user to Jerome7.

    A pledge is the first act — the user commits to showing up for 7 minutes
    a day. This creates their account and initialises their streak at 0.

    Args:
        user_id: Unique identifier for the new user (e.g. Discord ID).
        name: Display name.
        timezone: IANA timezone string (e.g. 'America/New_York').
        fitness_level: One of 'beginner', 'returning', or 'active'.
        age_bracket: Age range (18-24, 25-34, 35-44, 45-54, 55+). Optional.
        gender: male, female, other, or skip. Optional.
        goal: move_more, build_strength, destress, or just_try. Optional.
    """
    body = {
        "user_id": user_id,
        "name": name,
        "timezone": timezone,
        "fitness_level": fitness_level,
        "source": "mcp",
    }
    if age_bracket:
        body["age_bracket"] = age_bracket
    if gender:
        body["gender"] = gender
    if goal:
        body["goal"] = goal
    try:
        data = _api("POST", "/pledge", json=body)
        return json.dumps(data, indent=2)
    except httpx.HTTPStatusError as exc:
        return f"API error {exc.response.status_code}: {exc.response.text}"
    except httpx.ConnectError:
        return f"Could not connect to Jerome7 API at {API_URL}."


@mcp.tool()
def jerome7_log(
    user_id: str,
    seven7_title: str = "Seven 7",
    blocks_completed: int = 7,
    duration_minutes: float = 7.0,
    note: str = "",
) -> str:
    """Log a completed session for a user.

    After the user finishes their 7-minute session, call this to record it.
    The streak is automatically updated and any milestones are returned.

    Args:
        user_id: The user who completed the session.
        seven7_title: Title of today's session.
        blocks_completed: Number of blocks the user completed (1-7).
        duration_minutes: Actual duration in minutes.
        note: Optional personal note from the user.
    """
    try:
        data = _api(
            "POST",
            f"/log/{user_id}",
            json={
                "seven7_title": seven7_title,
                "blocks_completed": blocks_completed,
                "duration_minutes": duration_minutes,
                "note": note,
            },
        )
        return json.dumps(data, indent=2)
    except httpx.HTTPStatusError as exc:
        return f"API error {exc.response.status_code}: {exc.response.text}"
    except httpx.ConnectError:
        return f"Could not connect to Jerome7 API at {API_URL}."


@mcp.tool()
def jerome7_streak(user_id: str) -> str:
    """Get a user's streak and consistency data.

    Returns current streak, longest streak, total sessions, and the visual
    chain (last 30 days of filled/empty dots).

    Args:
        user_id: The user to look up.
    """
    try:
        data = _api("GET", f"/streak/{user_id}")
        return json.dumps(data, indent=2)
    except httpx.HTTPStatusError as exc:
        return f"API error {exc.response.status_code}: {exc.response.text}"
    except httpx.ConnectError:
        return f"Could not connect to Jerome7 API at {API_URL}."


@mcp.tool()
def jerome7_nudge(user_id: str) -> str:
    """Check whether a user needs a nudge today.

    A nudge is sent when the user has an active streak but has not yet
    logged a session today and time is running out. Returns risk status
    and hours remaining.

    Args:
        user_id: The user to check.
    """
    try:
        data = _api("GET", f"/nudge/{user_id}")
        return json.dumps(data, indent=2)
    except httpx.HTTPStatusError as exc:
        return f"API error {exc.response.status_code}: {exc.response.text}"
    except httpx.ConnectError:
        return f"Could not connect to Jerome7 API at {API_URL}."


@mcp.tool()
def jerome7_pod_match(user_id: str) -> str:
    """Find or create an accountability pod for a user.

    Pods are groups of 3-5 people who hold each other accountable.
    This tool finds compatible users based on timezone, fitness level,
    and activity window, then proposes or forms a pod.

    Args:
        user_id: The user looking for a pod.
    """
    try:
        data = _api("POST", f"/pod/match", json={"user_id": user_id})
        return json.dumps(data, indent=2)
    except httpx.HTTPStatusError as exc:
        return f"API error {exc.response.status_code}: {exc.response.text}"
    except httpx.ConnectError:
        return f"Could not connect to Jerome7 API at {API_URL}."


if __name__ == "__main__":
    mcp.run()
