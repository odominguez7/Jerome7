"""POST /twitter — auto-post daily sessions and leaderboard to Twitter/X."""

import os
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from src.db.database import get_db
from src.api.routes.daily import get_daily
from src.api.routes.analytics import analytics_overview
from src.api.routes.leaderboard import leaderboard_data

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_twitter_client():
    """Create a tweepy v2 Client from environment variables."""
    try:
        import tweepy
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="tweepy is not installed. Run: pip install tweepy",
        )

    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_SECRET")
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

    if not all([api_key, api_secret, access_token, access_secret]):
        raise HTTPException(
            status_code=500,
            detail="Twitter API credentials not configured. Set TWITTER_API_KEY, "
                   "TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET.",
        )

    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )
    return client


def _tweet_url(tweet_id: str, username: str = "jerome7app") -> str:
    """Build a tweet URL from its ID."""
    return f"https://x.com/{username}/status/{tweet_id}"


@router.post("/twitter/post-daily")
def post_daily_tweet(db: DBSession = Depends(get_db)):
    """Post today's session + analytics as a tweet thread."""
    # 1. Get today's session title (use cached data via httpx, not internal call)
    import httpx
    try:
        resp = httpx.get("https://jerome7.com/daily", timeout=15)
        session = resp.json()
        session_title = session.get("session_title", "the seven 7")
    except Exception:
        session_title = "the seven 7"

    # 2. Get analytics overview
    overview = analytics_overview(db)
    total_users = overview["total_users"]
    active_streaks = overview["active_streaks"]
    countries = overview.get("demographics", {}).get("countries", {})
    countries_count = len(countries)

    # 3. Compose tweet thread
    tweet_1 = (
        f"\u2600\ufe0f {session_title} \u2014 today's Jerome7\n\n"
        f"7 blocks. 60s each. Same for everyone on earth.\n\n"
        f"jerome7.com/timer"
    )

    tweet_2 = (
        f"\U0001f30d {total_users} builders. {active_streaks} active streaks. "
        f"{countries_count} countries.\n\n"
        f"Free forever. Open source.\n"
        f"github.com/odominguez7/Jerome7"
    )

    # 4. Post via tweepy v2
    client = _get_twitter_client()

    try:
        # Post first tweet
        response_1 = client.create_tweet(text=tweet_1)
        tweet_1_id = response_1.data["id"]

        # Post second tweet as reply (thread)
        response_2 = client.create_tweet(
            text=tweet_2,
            in_reply_to_tweet_id=tweet_1_id,
        )
        tweet_2_id = response_2.data["id"]
    except Exception as e:
        logger.error(f"Twitter API error: {e}")
        raise HTTPException(status_code=502, detail=f"Twitter API error: {e}")

    return {
        "status": "posted",
        "tweets": [
            {"id": tweet_1_id, "url": _tweet_url(tweet_1_id), "text": tweet_1},
            {"id": tweet_2_id, "url": _tweet_url(tweet_2_id), "text": tweet_2},
        ],
    }


@router.post("/twitter/post-leaderboard")
def post_leaderboard_tweet(db: DBSession = Depends(get_db)):
    """Post top 5 streaks as a tweet with country flags."""
    # 1. Get leaderboard data
    data = leaderboard_data(db)
    # leaderboard_data may return a JSONResponse on DB error instead of a dict
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="Leaderboard data unavailable.")
    leaderboard = data.get("leaderboard", [])

    if not leaderboard:
        raise HTTPException(status_code=404, detail="No active streaks to post.")

    # 2. Compose tweet — top 5 streaks with flags
    top_5 = leaderboard[:5]
    lines = ["\U0001f525 Jerome7 Streak Leaderboard\n"]

    for i, entry in enumerate(top_5):
        rank = i + 1
        medal = {1: "\U0001f947", 2: "\U0001f948", 3: "\U0001f949"}.get(rank, f" {rank}.")
        flag = entry.get("flag", "\U0001f30d")
        name = entry["name"]
        streak = entry["streak"]
        lines.append(f"{medal} {flag} {name} \u2014 {streak} days")

    lines.append("\nShow up. 7 minutes. jerome7.com/timer")

    tweet_text = "\n".join(lines)

    # 3. Post via tweepy v2
    client = _get_twitter_client()

    try:
        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]
    except Exception as e:
        logger.error(f"Twitter API error: {e}")
        raise HTTPException(status_code=502, detail=f"Twitter API error: {e}")

    return {
        "status": "posted",
        "tweet": {
            "id": tweet_id,
            "url": _tweet_url(tweet_id),
            "text": tweet_text,
        },
    }
