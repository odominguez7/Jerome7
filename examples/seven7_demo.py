"""Demo: generate a Seven 7 session locally without the API."""

import asyncio
import os
import json

# Set a dummy key if not available for demo
if not os.getenv("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = ""

from src.agents.coach import CoachAgent
from src.agents.context import UserContext


async def main():
    ctx = UserContext(
        user_id="demo-user",
        name="Omar",
        timezone="America/New_York",
        fitness_level="active",
        energy_today="medium",
        current_streak=47,
        longest_streak=47,
        milestone_next=50,
    )

    coach = CoachAgent()
    session = await coach.generate(ctx)

    print("\n  JEROME 7 — YOUR SEVEN 7\n")
    print(f"  {session['greeting']}\n")
    print(f"  ── {session['session_title']} ──\n")

    for block in session["blocks"]:
        mins = block["duration_seconds"] // 60
        secs = block["duration_seconds"] % 60
        print(f"  [{mins}:{secs:02d}]  {block['name']}")
        print(f"          {block['instruction']}")
        print(f"          > {block['why_today']}\n")

    print(f"  {session['closing']}")
    total = sum(b["duration_seconds"] for b in session["blocks"])
    print(f"  Total: {total // 60} minutes ({total} seconds)\n")


if __name__ == "__main__":
    asyncio.run(main())
