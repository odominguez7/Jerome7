"""
Jerome7 Twitter/X daily auto-poster.

Posts today's session + leaderboard snapshot every morning.
Run once manually to test, or add to cron:
  0 7 * * * /usr/local/bin/python3 /path/to/scripts/twitter_daily.py

Requirements:
  pip install tweepy httpx

Env vars needed (add to .env or export):
  TWITTER_API_KEY
  TWITTER_API_SECRET
  TWITTER_ACCESS_TOKEN
  TWITTER_ACCESS_SECRET
  JEROME7_API_URL  (default: https://jerome7.com)
"""

import os
import sys
import json
import httpx
import tweepy
from datetime import datetime

API_URL = os.getenv("JEROME7_API_URL", "https://jerome7.com").rstrip("/")

# --- Twitter client ---
def get_twitter_client():
    return tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_SECRET"],
    )

# --- Fetch data ---
def fetch_daily():
    r = httpx.get(f"{API_URL}/daily", timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_leaderboard():
    r = httpx.get(f"{API_URL}/leaderboard/data", timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_analytics():
    r = httpx.get(f"{API_URL}/analytics/overview", timeout=30)
    r.raise_for_status()
    return r.json()

# --- Build thread ---
def build_thread(daily, leaderboard, analytics):
    session_title = daily.get("session_title", "Today's Session").title()
    blocks = daily.get("blocks", [])
    closing = daily.get("closing", "You showed up. That's the win.")

    total_users = analytics.get("total_users", 0)
    sessions_24h = analytics.get("sessions", {}).get("last_24h", 0)
    active_streaks = analytics.get("active_streaks", 0)

    top = leaderboard.get("leaderboard", [])[:5]
    today_count = leaderboard.get("today_count", 0)

    phase_emoji = {"prime": "🌅", "build": "🔨", "move": "⚡", "reset": "🫁"}

    # Tweet 1 — Hook
    day_of_week = datetime.utcnow().strftime("%A")
    tweet1 = (
        f"Jerome7 {day_of_week} drop 🔥\n\n"
        f"Today's session: **{session_title}**\n"
        f"7 minutes. Same session. Every human on earth.\n\n"
        f"{today_count} builders already showed up today.\n\n"
        f"👇 Full session thread"
    )

    # Tweet 2 — Session blocks
    block_lines = []
    for i, b in enumerate(blocks[:7], 1):
        emoji = phase_emoji.get(b.get("phase", ""), "▸")
        name = b.get("name", "").title()
        secs = b.get("duration_seconds", 60)
        block_lines.append(f"{emoji} {i}. {name} — {secs//60} min")
    tweet2 = "\n".join(block_lines) + f"\n\n⏱️ jerome7.com/timer"

    # Tweet 3 — Closing + leaderboard
    top_str = ""
    for i, u in enumerate(top, 1):
        top_str += f"\n{i}. {u['flag']} {u['name']} — {u['streak']}d 🔥"
    tweet3 = (
        f"_{closing}_\n\n"
        f"🏆 Today's top streaks:{top_str}\n\n"
        f"jerome7.com/leaderboard"
    )

    # Tweet 4 — CTA
    tweet4 = (
        f"🤖 Jerome7 works inside any AI agent:\n\n"
        f"• Claude Desktop (MCP)\n"
        f"• OpenClaw skill\n"
        f"• ZeroClaw TOML\n"
        f"• Direct API\n\n"
        f"{total_users} builders. {active_streaks} active streaks.\n\n"
        f"Free forever. github.com/odominguez7/Jerome7\n\n"
        f"#fitness #AI #buildinpublic #MCP #OpenClaw"
    )

    return [tweet1, tweet2, tweet3, tweet4]

# --- Post thread ---
def post_thread(client, tweets):
    prev_id = None
    posted = []
    for i, text in enumerate(tweets):
        # Twitter limit: 280 chars
        text = text[:277] + "..." if len(text) > 280 else text
        kwargs = {"text": text}
        if prev_id:
            kwargs["in_reply_to_tweet_id"] = prev_id
        resp = client.create_tweet(**kwargs)
        tweet_id = resp.data["id"]
        prev_id = tweet_id
        posted.append(tweet_id)
        print(f"  ✓ Tweet {i+1} posted: https://twitter.com/i/web/status/{tweet_id}")
    return posted


if __name__ == "__main__":
    print(f"[{datetime.utcnow().isoformat()}] Jerome7 Twitter daily poster starting...")

    # Validate env
    required = ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        print("Add them to your .env file or export them.")
        sys.exit(1)

    try:
        print("  Fetching Jerome7 data...")
        daily = fetch_daily()
        lb = fetch_leaderboard()
        stats = fetch_analytics()

        print(f"  Session: {daily.get('session_title')}")
        print(f"  Users: {stats.get('total_users')} | Streaks: {stats.get('active_streaks')}")

        tweets = build_thread(daily, lb, stats)
        print(f"  Built {len(tweets)}-tweet thread")

        if "--dry-run" in sys.argv:
            print("\n--- DRY RUN ---")
            for i, t in enumerate(tweets, 1):
                print(f"\n[Tweet {i} — {len(t)} chars]\n{t}")
            print("\n--- END DRY RUN ---")
        else:
            client = get_twitter_client()
            posted = post_thread(client, tweets)
            print(f"\n✅ Thread posted! {len(posted)} tweets live.")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
